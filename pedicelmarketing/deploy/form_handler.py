#!/usr/bin/env python3
"""Form relay for pedicelmarketing.com - audit + contact forms.

Why this exists: both Webflow forms declare method="get" with NO action attribute.
On Webflow hosting, webflow.js intercepts submit and AJAX-POSTs to Webflow's endpoint
keyed on data-wf-site. Self-hosted that binding does not exist, and the failure is
silent - the browser falls back to the declared method="get", reloads the page with the
fields in the query string, and the visitor believes the submission succeeded while the
lead is discarded. This service is the repair.

Why it relays through Brevo rather than sending mail directly: a fresh cloud IP has no
reverse DNS, no sending reputation and no DKIM signature, so Gmail files it as spam or
rejects it. pedicelmarketing.com is already provisioned for Brevo - the
brevo-code:23d7a795... TXT verification and the mail._domainkey DKIM selector are live
on the domain - so Brevo sends authenticated mail as the domain with no new DNS setup.

Every submission is appended to a local JSONL ledger BEFORE anything else, so a Brevo or
CRM outage never loses a lead. Then it becomes a lead in the Pedicel Hub CRM (Pedicel's
"Agency sales" pipeline, via the service-role RPC sales_inbound_form) and an email to the
owner. The visitor sees success when the lead is safely recorded (CRM or email).

Stdlib only, to match the rest of the tooling in this repo.

Env:
  BREVO_API_KEY    required
  FORM_TO          destination inbox        (default spalacio@pedicelmarketing.com)
  FORM_FROM        verified Brevo sender    (default website@pedicelmarketing.com)
  FORM_LOG         ledger path              (default /var/log/pedicel-forms.jsonl)
  FORM_BIND/PORT   default 127.0.0.1:8081
  SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY   CRM (optional; skipped when unset)
  CRM_CLIENT       Hub client slug the leads belong to (default pedicel)
"""
from __future__ import annotations

import hashlib
import html
import json
import logging
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs

BREVO_ENDPOINT = "https://api.brevo.com/v3/smtp/email"
MAX_BODY = 64 * 1024
HONEYPOT = "website_url_hp"  # bots fill it; humans never see it

# Content check for bots that skip the honeypot. Seen on 2 and 4 Oct 2026: random-string
# names ("MdSGXradLGdlqwLFCULIRu"), dotted Gmail addresses ("u.x.i.xe.w.a.778@gmail.com") and
# random-string messages. Two signs together = spam: ledger only, no CRM lead, no email.
_VOWELS = set("aeiouyáéíóúàèìòùäëïöü")


def _random_token(t: str) -> bool:
    if len(t) < 12 or not t.isalpha():
        return False
    vowels = sum(ch.lower() in _VOWELS for ch in t) / len(t)
    flips = sum(1 for a, b in zip(t, t[1:]) if a.isupper() != b.isupper())
    run = max((len(r) for r in "".join(" " if ch.lower() in _VOWELS else ch for ch in t).split()), default=0)
    return vowels < 0.25 or flips >= 6 or run >= 7


def spam_signs(fields: dict, spec: dict) -> list[str]:
    """Which bot signs a submission shows (empty for real people)."""
    by_label = {label.lower(): (fields.get(key) or "").strip() for key, label in spec["fields"]}
    signs = []
    name = by_label.get("name", "")
    if any(_random_token(t) for t in name.replace("-", " ").split()):
        signs.append("random name")
    local = by_label.get("email", "").split("@")[0]
    if local.count(".") >= 4:
        signs.append("dotted email")
    for label in ("message", "position", "marketing goals"):
        v = by_label.get(label, "")
        if v and " " not in v and (_random_token(v) or v.isdigit()):
            signs.append(f"random {label}")
    return signs

FORMS = {
    "/api/forms/audit": {
        "label": "Website Audit request",
        "fields": [
            ("Name", "Name"), ("Email", "Email"), ("Phone-Number", "Phone"),
            ("Company-Name", "Company"), ("Company-Website", "Website"),
            ("Position", "Position"), ("Marketing-Goals", "Marketing goals"),
        ],
        # form field -> CRM field (sales_inbound_form keys)
        "crm": {"Name": "name", "Email": "email", "Phone-Number": "phone", "Company-Name": "company",
                "Company-Website": "website", "Position": "title", "Marketing-Goals": "goals"},
        # the free audit: also queue a pitch (AI audit + proposal + video) for the new lead
        "pitch": True,
    },
    "/api/forms/contact": {
        "label": "Contact form",
        "fields": [
            ("name-2", "Name"), ("Email-2", "Email"),
            ("Phone-Number-2", "Phone"), ("Message-2", "Message"),
        ],
        "crm": {"name-2": "name", "Email-2": "email", "Phone-Number-2": "phone", "Message-2": "message"},
    },
}

# pedicelmarketing.ch posts to its own paths so its leads are tagged in the Hub CRM.
FORMS["/api/forms/ch-audit"] = {**FORMS["/api/forms/audit"], "label": "Website Audit request (CH)"}
FORMS["/api/forms/ch-contact"] = {**FORMS["/api/forms/contact"], "label": "Contact form (CH)"}

log = logging.getLogger("pedicel-forms")


def cfg(name: str, default: str | None = None) -> str:
    value = os.environ.get(name, default)
    if value is None:
        sys.exit(f"missing required environment variable: {name}")
    return value


def record(entry: dict) -> None:
    """Append to the ledger. Never let a logging failure break the response."""
    try:
        with open(cfg("FORM_LOG", "/var/log/pedicel-forms.jsonl"), "a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except OSError as exc:
        log.error("ledger write failed: %s", exc)


def send_via_brevo(subject: str, body_html: str, reply_to: str | None) -> tuple[bool, str]:
    payload = {
        "sender": {"email": cfg("FORM_FROM", "website@pedicelmarketing.com"),
                   "name": "Pedicel Marketing website"},
        "to": [{"email": cfg("FORM_TO", "spalacio@pedicelmarketing.com")}],
        "subject": subject,
        "htmlContent": body_html,
    }
    if reply_to and "@" in reply_to:
        payload["replyTo"] = {"email": reply_to}

    request = urllib.request.Request(
        BREVO_ENDPOINT,
        data=json.dumps(payload).encode("utf-8"),
        headers={"api-key": cfg("BREVO_API_KEY"),
                 "content-type": "application/json",
                 "accept": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            return True, f"brevo {response.status}"
    except urllib.error.HTTPError as exc:
        return False, f"brevo HTTP {exc.code}: {exc.read()[:200].decode('utf-8', 'replace')}"
    except Exception as exc:  # network, DNS, timeout
        return False, f"brevo error: {exc}"


def push_to_crm(spec: dict, fields: dict, external_id: str) -> tuple[bool, str]:
    """Create the lead in the Hub CRM. Skipped (not failed) when the CRM isn't configured."""
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        return False, "crm not configured"
    payload = {
        "p_client_slug": os.environ.get("CRM_CLIENT", "pedicel"),
        "p_form": spec["label"],
        "p_fields": {crm: fields.get(src, "").strip() for src, crm in spec["crm"].items() if fields.get(src, "").strip()},
        "p_external_id": external_id,
    }
    request = urllib.request.Request(
        f"{url.rstrip('/')}/rest/v1/rpc/sales_inbound_form",
        data=json.dumps(payload).encode("utf-8"),
        headers={"apikey": key, "authorization": f"Bearer {key}", "content-type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            return True, f"crm {response.status} {response.read()[:200].decode('utf-8', 'replace')}"
    except urllib.error.HTTPError as exc:
        return False, f"crm HTTP {exc.code}: {exc.read()[:200].decode('utf-8', 'replace')}"
    except Exception as exc:  # network, DNS, timeout
        return False, f"crm error: {exc}"


def pitch_payload(spec: dict, fields: dict, crm_detail: str) -> dict | None:
    """A free-audit request with a website → the pitch to build for that new lead (or None).

    crm_detail is push_to_crm's "crm 200 {json}" text; the json carries the contact id.
    """
    if spec.get("pitch") is not True:
        return None
    website = next((fields.get(k, "").strip() for k, crm in spec["crm"].items() if crm == "website" and fields.get(k, "").strip()), "")
    if not website:
        return None
    try:
        contact = json.loads(crm_detail.split(" ", 2)[2]).get("contact_id")
    except (IndexError, ValueError, AttributeError):
        return None
    if not contact:
        return None
    return {"p_url": website, "p_contact_id": contact, "p_depth": "light", "p_origin": "inbound"}


def request_pitch(payload: dict) -> tuple[bool, str]:
    """Queue the free AI audit + proposal for this lead (built by the pitch worker, sent after a manager's OK)."""
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        return False, "crm not configured"
    request = urllib.request.Request(
        f"{url.rstrip('/')}/rest/v1/rpc/pitch_request",
        data=json.dumps(payload).encode("utf-8"),
        headers={"apikey": key, "authorization": f"Bearer {key}", "content-type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            return True, f"pitch {response.status} {response.read()[:80].decode('utf-8', 'replace')}"
    except urllib.error.HTTPError as exc:
        return False, f"pitch HTTP {exc.code}: {exc.read()[:200].decode('utf-8', 'replace')}"
    except Exception as exc:  # network, DNS, timeout
        return False, f"pitch error: {exc}"


class Handler(BaseHTTPRequestHandler):
    server_version = "pedicel-forms"

    def log_message(self, fmt, *args):
        log.info("%s - %s", self.client_address[0], fmt % args)

    def _json(self, code: int, payload: dict) -> None:
        raw = json.dumps(payload).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(raw)

    def do_POST(self) -> None:  # noqa: N802
        spec = FORMS.get(self.path.rstrip("/"))
        if spec is None:
            return self._json(404, {"ok": False, "error": "unknown form"})

        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            return self._json(400, {"ok": False, "error": "bad length"})
        if length <= 0 or length > MAX_BODY:
            return self._json(400, {"ok": False, "error": "bad length"})

        raw = self.rfile.read(length)
        ctype = (self.headers.get("Content-Type") or "").split(";")[0].strip()
        try:
            if ctype == "application/json":
                fields = {k: str(v) for k, v in json.loads(raw.decode("utf-8")).items()}
            else:
                fields = {k: v[0] for k, v in parse_qs(raw.decode("utf-8")).items()}
        except (ValueError, UnicodeDecodeError):
            return self._json(400, {"ok": False, "error": "unparseable body"})

        # Honeypot: report success so the bot does not retry or adapt.
        if fields.get(HONEYPOT):
            log.info("honeypot triggered from %s", self.client_address[0])
            return self._json(200, {"ok": True})

        signs = spam_signs(fields, spec)
        if len(signs) >= 2:
            record({"at": datetime.now(timezone.utc).isoformat(), "form": spec["label"], "spam": signs,
                    "ip": self.headers.get("X-Real-IP") or self.client_address[0],
                    "fields": {label: fields.get(key, "") for key, label in spec["fields"]}})
            log.info("spam dropped (%s) from %s", ", ".join(signs), self.client_address[0])
            return self._json(200, {"ok": True})

        submitter = next((fields.get(key, "") for key, _ in spec["fields"]
                          if "email" in key.lower() and fields.get(key)), "")

        entry = {
            "at": datetime.now(timezone.utc).isoformat(),
            "form": spec["label"],
            "ip": self.headers.get("X-Real-IP") or self.client_address[0],
            "fields": {label: fields.get(key, "") for key, label in spec["fields"]},
        }
        record(entry)  # ledger first - a send failure must not lose the lead

        # Same form + email + second = same submission (a double click or a retry).
        external_id = hashlib.sha256(
            f"{spec['label']}|{submitter.lower()}|{entry['at'][:19]}".encode("utf-8")).hexdigest()[:32]
        crm_ok, crm_detail = push_to_crm(spec, fields, external_id)
        log.info("crm: %s", crm_detail) if crm_ok else log.error("crm failed (lead IS in the ledger): %s", crm_detail)
        pitch = pitch_payload(spec, fields, crm_detail) if crm_ok else None
        if pitch:
            p_ok, p_detail = request_pitch(pitch)
            log.info("pitch: %s", p_detail) if p_ok else log.error("pitch request failed: %s", p_detail)

        rows = "".join(
            f"<tr><td style='padding:4px 12px 4px 0;vertical-align:top'><strong>{html.escape(label)}</strong></td>"
            f"<td style='padding:4px 0'>{html.escape(fields.get(key, '') or '-')}</td></tr>"
            for key, label in spec["fields"]
        )
        body = (
            f"<p>New submission from the <strong>{html.escape(spec['label'])}</strong> "
            f"on pedicelmarketing.com.</p><table>{rows}</table>"
            f"<p style='color:#888;font-size:12px'>Received {entry['at']} from {html.escape(entry['ip'])}</p>"
        )
        subject = f"[Website] {spec['label']}" + (f" - {submitter}" if submitter else "")

        mail_ok, detail = send_via_brevo(subject, body, submitter)
        if mail_ok:
            log.info("delivered: %s", detail)
        else:
            log.error("send failed (lead IS in the ledger): %s", detail)
        # The visitor succeeded if the lead reached a person or the CRM.
        if not (mail_ok or crm_ok):
            return self._json(502, {"ok": False, "error": "delivery failed"})
        return self._json(200, {"ok": True})

    def do_GET(self) -> None:  # noqa: N802
        if self.path.rstrip("/") == "/api/forms/health":
            return self._json(200, {"ok": True, "forms": sorted(FORMS)})
        return self._json(405, {"ok": False, "error": "POST only"})


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    cfg("BREVO_API_KEY")  # fail fast at boot rather than on the first real lead
    bind = os.environ.get("FORM_BIND", "127.0.0.1")
    port = int(os.environ.get("FORM_PORT", "8081"))
    with ThreadingHTTPServer((bind, port), Handler) as httpd:
        log.info("listening on %s:%s -> %s", bind, port, cfg("FORM_TO", "spalacio@pedicelmarketing.com"))
        httpd.serve_forever()


if __name__ == "__main__":
    main()
