#!/usr/bin/env python3
"""Build an authorization-gated local mirror from one or more v1.3 captures.

The downloader intentionally accepts only capture graphs produced by the v1.3
capture script. It recomputes URL/provider/request safety instead of trusting
capture-time flags, follows redirects only inside the authorized scope, hashes
every captured file, and writes the manifest atomically.

Usage:
    python mirror_assets.py route-a.json [route-b.json ...] --out mirror \
        --authorized "client-approved migration" [--allow-host assets.example]

Existing non-empty output is rejected unless ``--resume`` is supplied. Resume
requires a v1.3 manifest and preserves its download inventory, modification
ledger, and construction provenance.

Requires: Python 3 standard library only.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import posixpath
import re
import stat
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple
from urllib.error import HTTPError
from urllib.parse import parse_qsl, urljoin, urlsplit, urlunsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener


GRAPH_SCHEMA_VERSION = "1.3"
MANIFEST_SCHEMA_VERSION = "1.3"
ACTOR = "nt-site-mirror"
CONSTRUCTION_PHASE = "construction"
USER_AGENT = "nt-site-mirror/1.3 (authorized mirroring; see mirror-manifest.json)"
RESERVED_OUTPUT_PATHS = {
    "mirror-manifest.json",
    "serve-contract.json",
    "serve-local.py",
    posixpath.join("_ntsm", "serve.py"),
}

STATIC_RESOURCE_TYPES = {
    "document",
    "stylesheet",
    "script",
    "image",
    "media",
    "font",
    "manifest",
    "texttrack",
}
DATA_RESOURCE_TYPES = {"xhr", "fetch"}
SKIP_TYPES = {"websocket", "eventsource", "ping", "preflight"}
STATIC_DATA_CLASSES = {
    "public-static-data",
    "static-data",
    "static-public",
    "static_public",
}
STATIC_DATA_TYPES = {
    "public-static",
    "public_static",
    "static-data",
    "static_data",
}
BLOCKED_ACCESS_STATES = {
    "access_denied",
    "blocked",
    "blocked_by_access",
    "blocked_by_challenge",
    "blocked_by_consent",
    "blocked_by_login",
    "blocked_by_unauthorized_redirect",
    "capture_runtime_error",
    "captcha",
    "challenge",
    "error_document",
    "http_error",
    "inspection_error",
    "login_required",
    "navigation_error",
}

KNOWN_PROVIDERS = {
    "vimeo.com": "Vimeo",
    "player.vimeo.com": "Vimeo",
    "vimeocdn.com": "Vimeo",
    "youtube.com": "YouTube",
    "youtu.be": "YouTube",
    "ytimg.com": "YouTube",
    "googlevideo.com": "YouTube",
    "mux.com": "Mux",
    "litix.io": "Mux",
    "stream.mux.com": "Mux",
    "fonts.googleapis.com": "Google Fonts (openly licensed)",
    "fonts.gstatic.com": "Google Fonts (openly licensed)",
    "use.typekit.net": "Adobe Fonts (paid)",
    "p.typekit.net": "Adobe Fonts (paid)",
    "cloud.typography.com": "Hoefler&Co (paid)",
    "fast.fonts.net": "Monotype (paid)",
    "kit.fontawesome.com": "Font Awesome",
    "cdn.lottiefiles.com": "Lottie",
    "lottie.host": "Lottie",
    "cdn.rive.app": "Rive",
    "stream.cloudflare.com": "Cloudflare Stream",
    "wistia.com": "Wistia",
    "fast.wistia.net": "Wistia",
}
OPEN_LICENSE_FONT_HOSTS = {"fonts.googleapis.com", "fonts.gstatic.com"}

TELEMETRY_HOSTS = {
    "amplitude.com",
    "analytics.google.com",
    "api.segment.io",
    "app.posthog.com",
    "browser-intake-datadoghq.com",
    "cdn.segment.com",
    "clarity.ms",
    "connect.facebook.net",
    "facebook.net",
    "fullstory.com",
    "google-analytics.com",
    "googletagmanager.com",
    "hotjar.com",
    "mixpanel.com",
    "newrelic.com",
    "nr-data.net",
    "plausible.io",
    "segment.com",
    "sentry.io",
    "stats.g.doubleclick.net",
}
TELEMETRY_PATH_RE = re.compile(
    r"(?:^|/)(?:analytics|beacon|collect|events?|metrics|pageview|pixel|telemetry|track|tracking)(?:/|$)",
    re.IGNORECASE,
)
SENSITIVE_QUERY_RE = re.compile(
    r"(^|[_-])(access[_-]?token|auth|authorization|api[_-]?key|client[_-]?secret|"
    r"credential|jwt|key|pass(word|wd)?|policy|secret|session|sig(nature)?|token)($|[_-])",
    re.IGNORECASE,
)

CHALLENGE_MARKERS = (
    "cf-chl-",
    "challenge-platform",
    "checking your browser",
    "cloudflare ray id",
    "enable javascript and cookies to continue",
    "hcaptcha",
    "recaptcha",
    "turnstile",
    "verify you are human",
)
CHALLENGE_TITLE_MARKERS = (
    "attention required",
    "captcha",
    "checking your browser",
    "just a moment",
    "security check",
    "verify you are human",
)
ACCESS_DENIED_MARKERS = (
    "access denied",
    "request blocked",
    "you don't have permission to access",
)
LOGIN_TITLE_RE = re.compile(r"^\s*(?:log[ -]?in|sign[ -]?in|authentication required)\s*$", re.I)
LOGIN_MARKERS = (
    "sign in",
    "log in",
    "login",
    "authentication required",
    "authorize access",
)
EXACT_CHALLENGE_TITLE_RE = re.compile(
    r"^\s*(?:just a moment(?:\.{1,3})?|checking your browser|"
    r"verify you are human|security check|attention required|captcha)\s*$",
    re.I,
)
EXACT_ACCESS_TITLE_RE = re.compile(
    r"^\s*(?:access denied|request blocked|401(?:\s+unauthorized)?|"
    r"403(?:\s+forbidden)?|unauthorized|forbidden)\s*[.!]?\s*$",
    re.I,
)
ERROR_TITLE_RE = re.compile(
    r"^\s*(?:(?:4\d{2}|5\d{2})(?:\s+(?:not found|server error|"
    r"internal server error|service unavailable|bad gateway|gateway timeout))?|"
    r"page not found|not found|server error|application error|"
    r"internal server error|service unavailable|bad gateway|gateway timeout|"
    r"this site can(?:['’]t|not) be reached)\s*[.!]?\s*$",
    re.I,
)
TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title\s*>", re.I | re.S)


class MirrorError(RuntimeError):
    """Expected integrity or safety failure."""


class UnsafeRedirectError(MirrorError):
    """A redirect left the independently authorized URL scope."""

    def __init__(self, message: str, chain: Sequence[Dict[str, Any]]):
        super().__init__(message)
        self.chain = list(chain)


class AccessBlockedError(MirrorError):
    """A required HTML response is a challenge, login, or error document."""

    def __init__(self, url: str, evidence: Dict[str, Any]):
        self.url = url
        self.evidence = dict(evidence)
        super().__init__(
            "%s: %s" % (self.evidence.get("state", "blocked_access"), url)
        )


@dataclass(frozen=True)
class URLInfo:
    url: str
    normalized_url: str
    scheme: str
    host: str
    port: int
    authority: str
    origin: str
    request_target: str


@dataclass
class Candidate:
    url: str
    normalized_url: str
    method: str
    resource_type: str
    content_type: str
    required: bool
    source_graphs: List[str]
    request_class: str
    data_type: str
    acquisition_reason: str
    first_seen: Optional[str]
    metadata_refs: List[Dict[str, Any]]
    target_rel: Optional[str] = None
    primary: bool = False


@dataclass
class FetchResult:
    url: str
    normalized_url: str
    target_rel: Optional[str]
    method: str
    required: bool
    status: int
    final_url: str
    redirects: List[Dict[str, Any]]
    content_type: Optional[str]
    size: int
    sha256: Optional[str]
    captured: bool
    challenge: Optional[Dict[str, Any]]


def utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_write_bytes(path: str, data: bytes, executable: bool = False) -> None:
    directory = os.path.dirname(os.path.abspath(path))
    os.makedirs(directory, exist_ok=True)
    fd, temp_path = tempfile.mkstemp(prefix=".ntsm-", dir=directory)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        if executable:
            os.chmod(temp_path, os.stat(temp_path).st_mode | stat.S_IXUSR)
        os.replace(temp_path, path)
    except Exception:
        try:
            os.unlink(temp_path)
        except OSError:
            pass
        raise


def atomic_write_json(path: str, value: Any) -> None:
    payload = (json.dumps(value, indent=2, sort_keys=False) + "\n").encode("utf-8")
    atomic_write_bytes(path, payload)


def load_json(path: str) -> Dict[str, Any]:
    try:
        with open(path, "r", encoding="utf-8") as handle:
            value = json.load(handle)
    except (OSError, ValueError) as exc:
        raise MirrorError("Cannot read JSON %s: %s" % (path, exc)) from exc
    if not isinstance(value, dict):
        raise MirrorError("Expected a JSON object in %s" % path)
    return value


def load_graph_with_hash(path: str) -> Dict[str, Any]:
    """Load and hash the exact capture-graph bytes used by this run."""
    try:
        with open(path, "rb") as handle:
            payload = handle.read()
        value = json.loads(payload)
    except (OSError, UnicodeError, ValueError) as exc:
        raise MirrorError("Cannot read capture graph %s: %s" % (path, exc)) from exc
    if not isinstance(value, dict):
        raise MirrorError("Expected a JSON object in capture graph %s" % path)
    value["_ntsm_source_sha256"] = sha256_bytes(payload)
    return value


def _normalized_host(host: str) -> str:
    value = (host or "").rstrip(".").lower()
    if not value:
        raise MirrorError("URL has no host")
    try:
        return value.encode("idna").decode("ascii")
    except UnicodeError as exc:
        raise MirrorError("Invalid internationalized host: %s" % host) from exc


def parse_http_url(url: str) -> URLInfo:
    if not isinstance(url, str) or not url.strip():
        raise MirrorError("Missing URL")
    raw_url = url.strip()
    if "\\" in raw_url or any(ord(char) < 32 or ord(char) == 127 for char in raw_url):
        raise MirrorError("URL contains a backslash or control character")
    try:
        parts = urlsplit(raw_url)
        scheme = parts.scheme.lower()
        if scheme not in {"http", "https"}:
            raise MirrorError("Unsupported URL scheme: %s" % (parts.scheme or "(none)"))
        if parts.username is not None or parts.password is not None:
            raise MirrorError("URLs containing credentials are not accepted")
        host = _normalized_host(parts.hostname or "")
        port = parts.port or (443 if scheme == "https" else 80)
        if not 1 <= port <= 65535:
            raise MirrorError("Invalid URL port")
    except ValueError as exc:
        raise MirrorError("Invalid URL %r: %s" % (url, exc)) from exc

    default_port = 443 if scheme == "https" else 80
    display_host = "[%s]" % host if ":" in host else host
    authority = display_host if port == default_port else "%s:%d" % (display_host, port)
    path = parts.path or "/"
    normalized = urlunsplit((scheme, authority, path, parts.query, ""))
    request_target = path + (("?" + parts.query) if parts.query else "")
    return URLInfo(
        url=url,
        normalized_url=normalized,
        scheme=scheme,
        host=host,
        port=port,
        authority=authority,
        origin="%s://%s" % (scheme, authority),
        request_target=request_target,
    )


def provider_for(host: str) -> Optional[str]:
    host = (host or "").lower()
    for key, name in KNOWN_PROVIDERS.items():
        if host == key or host.endswith("." + key):
            return name
    return None


def sensitive_query_keys(url: str) -> List[str]:
    try:
        return sorted({
            key
            for key, _value in parse_qsl(urlsplit(url).query, keep_blank_values=True)
            if SENSITIVE_QUERY_RE.search(key)
        })
    except (TypeError, ValueError):
        return []


def is_telemetry_url(info: URLInfo, record: Optional[Dict[str, Any]] = None) -> bool:
    record = record or {}
    if any(info.host == host or info.host.endswith("." + host) for host in TELEMETRY_HOSTS):
        return True
    path = urlsplit(info.normalized_url).path
    resource_type = str(record.get("resource_type") or "").lower()
    # A page may legitimately be named /analytics or /events. Path-only
    # telemetry heuristics apply to subresources/data calls, not documents.
    if resource_type != "document" and TELEMETRY_PATH_RE.search(path):
        return True
    labels = " ".join(
        str(record.get(key, "")) for key in ("data_type", "request_class", "purpose")
    ).lower()
    return any(word in labels for word in ("analytics", "beacon", "telemetry", "tracking"))


def parse_allowed_hosts(values: Iterable[str]) -> Tuple[Set[str], Set[Tuple[str, int]]]:
    hosts: Set[str] = set()
    authorities: Set[Tuple[str, int]] = set()
    for raw in values:
        value = (raw or "").strip()
        if not value:
            continue
        probe = value if "://" in value else "https://" + value
        try:
            parsed = urlsplit(probe)
            host = _normalized_host(parsed.hostname or "")
            explicit_port = parsed.port
        except (MirrorError, ValueError) as exc:
            raise MirrorError("Invalid --allow-host %r: %s" % (value, exc)) from exc
        if (parsed.username is not None or parsed.password is not None
                or parsed.path not in ("", "/") or parsed.query or parsed.fragment):
            raise MirrorError(
                "Invalid --allow-host %r: provide only a host or host:port" % value
            )
        if explicit_port is None:
            hosts.add(host)
        else:
            authorities.add((host, explicit_port))
    return hosts, authorities


class AuthorizationPolicy:
    def __init__(
        self,
        primary_origins: Iterable[str],
        allowed_hosts: Iterable[str],
        allowed_authorities: Iterable[Tuple[str, int]],
    ) -> None:
        self.primary_origins = set(primary_origins)
        primary_infos = [parse_http_url(origin) for origin in self.primary_origins]
        self.primary_hosts = {info.host for info in primary_infos}
        self.default_http_hosts = {
            info.host for info in primary_infos if info.scheme == "http" and info.port == 80
        }
        self.allowed_hosts = set(allowed_hosts)
        self.allowed_authorities = set(allowed_authorities)

    def classify(self, url: str, resource_type: str = "") -> Dict[str, Any]:
        try:
            info = parse_http_url(url)
        except MirrorError as exc:
            return {"allowed": False, "scope": "invalid", "reason": str(exc), "provider": None}

        provider = provider_for(info.host)
        sensitive_keys = sensitive_query_keys(info.normalized_url)
        if sensitive_keys:
            return {
                "allowed": False,
                "scope": "sensitive_url",
                "reason": "credential-like query keys are never auto-acquired",
                "provider": provider,
                "sensitive_query_keys": sensitive_keys,
            }
        exact_primary = info.origin in self.primary_origins
        # A same-host HTTP -> HTTPS move on default web ports remains in the
        # primary authorization scope. Other scheme/port changes require an
        # explicit --allow-host authority.
        secure_upgrade = (
            info.scheme == "https"
            and info.port == 443
            and info.host in self.default_http_hosts
        )
        explicitly_allowed = (
            (
                info.host in self.allowed_hosts
                and info.port == (443 if info.scheme == "https" else 80)
            )
            or (info.host, info.port) in self.allowed_authorities
        )

        if provider:
            open_font = (
                info.host in OPEN_LICENSE_FONT_HOSTS
                and explicitly_allowed
                and resource_type != "document"
            )
            if not open_font:
                return {
                    "allowed": False,
                    "scope": "provider",
                    "reason": "provider-hosted resources are not auto-acquired",
                    "provider": provider,
                }

        if exact_primary or secure_upgrade:
            return {"allowed": True, "scope": "primary", "reason": "primary origin", "provider": provider}
        if explicitly_allowed:
            return {"allowed": True, "scope": "allowed_external", "reason": "explicit --allow-host", "provider": provider}
        return {
            "allowed": False,
            "scope": "external",
            "reason": "destination is outside the authorized origin/host set",
            "provider": provider,
        }


class TrackingRedirectHandler(HTTPRedirectHandler):
    def __init__(self, policy: AuthorizationPolicy, resource_type: str):
        super().__init__()
        self.policy = policy
        self.resource_type = resource_type
        self.chain: List[Dict[str, Any]] = []

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[override]
        destination = urljoin(req.full_url, newurl)
        decision = self.policy.classify(destination, self.resource_type)
        item = {
            "from": req.full_url,
            "to": destination,
            "status": int(code),
            "allowed": bool(decision["allowed"]),
            "scope": decision["scope"],
            "provider": decision.get("provider"),
            "reason": decision["reason"],
        }
        self.chain.append(item)
        if not decision["allowed"]:
            raise UnsafeRedirectError(
                "Rejected redirect to unauthorized destination %s (%s)"
                % (destination, decision["reason"]),
                self.chain,
            )
        redirected = super().redirect_request(req, fp, code, msg, headers, destination)
        # urllib otherwise turns a redirected HEAD into GET. Preserve the
        # observed safe method; POST and other methods never reach this code.
        if redirected is not None and req.get_method().upper() == "HEAD":
            redirected.method = "HEAD"
        return redirected


def html_access_block(
    data: bytes,
    content_type: str,
    title_hint: str = "",
    final_url: str = "",
) -> Optional[Dict[str, Any]]:
    if "html" not in (content_type or "").lower() and not data.lstrip().lower().startswith((b"<!doctype html", b"<html")):
        return None
    text = data[: 2 * 1024 * 1024].decode("utf-8", errors="replace")
    lowered = html.unescape(text).lower()
    visible_source = re.sub(
        r"<(?:script|style|template|noscript)\b[^>]*>.*?"
        r"</(?:script|style|template|noscript)\s*>",
        " ",
        lowered,
        flags=re.I | re.S,
    )
    body_text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", visible_source))
    match = TITLE_RE.search(text)
    title = html.unescape(re.sub(r"\s+", " ", match.group(1))).strip() if match else title_hint.strip()
    path = urlsplit(str(final_url or "").lower()).path
    path_segments = {segment for segment in path.split("/") if segment}
    url_challenge = []
    if re.search(r"(?:^|/)cdn-cgi/challenge(?:/|$)", path):
        url_challenge.append("/cdn-cgi/challenge")
    if "challenge-platform" in path_segments:
        url_challenge.append("/challenge-platform/")
    for segment, marker in (
        ("captcha", "/captcha"),
        ("recaptcha", "recaptcha"),
        ("hcaptcha", "hcaptcha"),
        ("turnstile", "turnstile"),
        ("verify-you-are-human", "verify-you-are-human"),
    ):
        if segment in path_segments:
            url_challenge.append(marker)
    url_login = [
        "/" + segment
        for segment in ("login", "log-in", "signin", "sign-in", "auth")
        if segment in path_segments
    ]
    attributes = [
        (name.lower(), value)
        for name, _quote, value in re.findall(
            r"\b([a-z][\w:.-]*)\s*=\s*(['\"])(.*?)\2",
            lowered,
            re.I | re.S,
        )
    ]
    ids = {value.strip() for name, value in attributes if name == "id"}
    class_values = [value for name, value in attributes if name == "class"]
    class_tokens = {
        token
        for value in class_values
        for token in re.split(r"\s+", value.strip())
        if token
    }
    evidence = [marker for marker in CHALLENGE_MARKERS if marker in body_text]
    challenge_textual = bool(
        any(marker in title.lower() for marker in CHALLENGE_TITLE_MARKERS)
        or evidence
    )
    exact_challenge_title = bool(EXACT_CHALLENGE_TITLE_RE.match(title))
    challenge_structure = (
        "challenge-form" in ids
        or "cf-challenge" in class_tokens
        or "g-recaptcha" in class_tokens
        or any("cf-turnstile" in value for value in class_values)
        or any("h-captcha" in value for value in class_values)
        or bool(re.search(
            r"<iframe\b[^>]*\bsrc\s*=\s*['\"][^'\"]*captcha[^'\"]*['\"]",
            lowered,
            re.I | re.S,
        ))
    )
    if (exact_challenge_title or challenge_structure
            or int(challenge_textual) + len(url_challenge) >= 2):
        combined = (
            (["exact challenge title"] if exact_challenge_title else [])
            + (["challenge selector"] if challenge_structure else [])
            + url_challenge
            + evidence
        )
        return {
            "state": "blocked_by_challenge",
            "title": title,
            "evidence": combined[:6],
        }
    denied = [marker for marker in ACCESS_DENIED_MARKERS if marker in body_text]
    exact_access_title = bool(EXACT_ACCESS_TITLE_RE.match(title))
    access_wall = (
        bool({"access-denied", "request-blocked"} & ids)
        or any(name == "data-access-wall" for name, _value in attributes)
        or bool(re.search(r"\bdata-access-wall(?:\s|/?>)", lowered, re.I))
    )
    if exact_access_title or access_wall:
        return {
            "state": "access_denied",
            "title": title,
            "evidence": (
                (["exact access title"] if exact_access_title else [])
                + (["access-wall marker"] if access_wall else [])
                + denied
            )[:6],
        }
    # Avoid treating pages with an ordinary "Sign in" link as login walls.
    if title and LOGIN_TITLE_RE.match(title):
        return {"state": "login_required", "title": title, "evidence": ["login-page title"]}
    password_input_re = re.compile(
        r"<input\b[^>]*\btype\s*=\s*(?:['\"]password['\"]|password)(?:\s|/?>)",
        re.I | re.S,
    )
    login_textual = any(
        marker in title.lower() or marker in body_text for marker in LOGIN_MARKERS
    )
    password_form = any(
        password_input_re.search(form)
        for form in re.findall(r"<form\b[^>]*>.*?</form\s*>", lowered, re.I | re.S)
    )
    login_form = password_form and (login_textual or bool(url_login))
    if login_form or (url_login and login_textual):
        return {
            "state": "login_required",
            "title": title,
            "evidence": ["login form"] if login_form else url_login,
        }
    if title and ERROR_TITLE_RE.match(title):
        return {"state": "error_document", "title": title, "evidence": ["error-page title"]}
    return None


def graph_access_block(graph: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    navigation = graph.get("navigation") if isinstance(graph.get("navigation"), dict) else {}
    access = navigation.get("access") if isinstance(navigation.get("access"), dict) else {}
    state = str(graph.get("access_result") or access.get("state") or "").strip().lower()
    blocked = bool(graph.get("blocked_by_challenge") or access.get("blocked"))
    if blocked or state in BLOCKED_ACCESS_STATES:
        return {
            "state": state or "blocked",
            "blocked": True,
            "evidence": access.get("evidence") or [],
            "final_url": navigation.get("final_url"),
            "title": navigation.get("title"),
        }
    return None


def graph_requested_url(graph: Dict[str, Any]) -> str:
    navigation = graph.get("navigation") if isinstance(graph.get("navigation"), dict) else {}
    return str(
        graph.get("requested_page")
        or navigation.get("requested_url")
        or graph.get("page")
        or ""
    )


def graph_final_url(graph: Dict[str, Any]) -> str:
    navigation = graph.get("navigation") if isinstance(graph.get("navigation"), dict) else {}
    return str(navigation.get("final_url") or graph_requested_url(graph))


def graph_redirects(graph: Dict[str, Any]) -> List[Dict[str, Any]]:
    navigation = graph.get("navigation") if isinstance(graph.get("navigation"), dict) else {}
    redirects = navigation.get("redirects")
    return [item for item in redirects or [] if isinstance(item, dict)]


def validate_capture_graph_shape(path: str, graph: Dict[str, Any]) -> None:
    navigation = graph.get("navigation")
    if not isinstance(navigation, dict):
        raise MirrorError("%s navigation must be an object" % path)
    for field in ("requested_url", "initial_status", "final_url", "final_status", "redirects", "access"):
        if field not in navigation:
            raise MirrorError("%s navigation.%s is required by schema 1.3" % (path, field))
    if not isinstance(navigation.get("redirects"), list):
        raise MirrorError("%s navigation.redirects must be a list" % path)
    for index, redirect in enumerate(navigation["redirects"]):
        if (not isinstance(redirect, dict)
                or not isinstance(redirect.get("from"), str)
                or not isinstance(redirect.get("to"), str)):
            raise MirrorError(
                "%s navigation.redirects[%d] must record from/to URLs"
                % (path, index)
            )
    if not isinstance(navigation.get("access"), dict):
        raise MirrorError("%s navigation.access must be an object" % path)
    if (not isinstance(navigation["access"].get("state"), str)
            or not isinstance(navigation["access"].get("blocked"), bool)):
        raise MirrorError(
            "%s navigation.access must record string state and boolean blocked" % path
        )

    requests = graph.get("requests")
    if not isinstance(requests, list) or not requests:
        raise MirrorError("%s requests must be a non-empty list" % path)
    for index, record in enumerate(requests):
        if not isinstance(record, dict):
            raise MirrorError("%s requests[%d] must be an object" % (path, index))
        for field in ("url", "method", "resource_type", "request_class", "data_type"):
            if not isinstance(record.get(field), str) or not record[field]:
                raise MirrorError(
                    "%s requests[%d].%s is required by schema 1.3"
                    % (path, index, field)
                )
        if "status" not in record:
            raise MirrorError(
                "%s requests[%d].status is required by schema 1.3"
                % (path, index)
            )
        acquisition = record.get("acquisition")
        if (not isinstance(acquisition, dict)
                or not isinstance(acquisition.get("automatic"), bool)):
            raise MirrorError(
                "%s requests[%d].acquisition.automatic must be boolean"
                % (path, index)
            )
    metadata = graph.get("metadata_references", [])
    if not isinstance(metadata, list) or any(not isinstance(item, dict) for item in metadata):
        raise MirrorError("%s metadata_references must be a list of objects" % path)


def validate_graphs(graph_paths: Sequence[str]) -> Tuple[List[Tuple[str, Dict[str, Any]]], Set[str]]:
    loaded: List[Tuple[str, Dict[str, Any]]] = []
    primary_origins: Set[str] = set()
    for path in graph_paths:
        graph = load_graph_with_hash(path)
        if str(graph.get("schema_version", "")) != GRAPH_SCHEMA_VERSION:
            raise MirrorError(
                "%s is schema %r; mirror_assets v1.3 accepts only v1.3 capture graphs"
                % (path, graph.get("schema_version"))
            )
        validate_capture_graph_shape(path, graph)
        requested = graph_requested_url(graph)
        info = parse_http_url(requested)
        primary_origins.add(info.origin)
        loaded.append((os.path.abspath(path), graph))
    if not loaded:
        raise MirrorError("At least one v1.3 capture graph is required")
    return loaded, primary_origins


def validate_graph_redirect_evidence(
    graphs: Sequence[Tuple[str, Dict[str, Any]]], policy: AuthorizationPolicy
) -> List[Dict[str, Any]]:
    errors: List[Dict[str, Any]] = []
    for path, graph in graphs:
        block = graph_access_block(graph)
        if block:
            errors.append({"graph": path, "kind": "blocked_access", **block})
            continue
        for item in graph_redirects(graph):
            destination = str(item.get("to") or "")
            decision = policy.classify(destination, "document")
            if not decision["allowed"]:
                errors.append(
                    {
                        "graph": path,
                        "kind": "unauthorized_captured_redirect",
                        "from": item.get("from"),
                        "to": destination,
                        "status": item.get("status"),
                        "reason": decision["reason"],
                        "provider": decision.get("provider"),
                    }
                )
        final_url = graph_final_url(graph)
        decision = policy.classify(final_url, "document")
        if not decision["allowed"]:
            errors.append(
                {
                    "graph": path,
                    "kind": "unauthorized_captured_final_url",
                    "to": final_url,
                    "reason": decision["reason"],
                    "provider": decision.get("provider"),
                }
            )
    return errors


def inferred_static_type(url: str) -> str:
    path = urlsplit(url).path.lower()
    extension = posixpath.splitext(path)[1]
    if extension in {".css"}:
        return "stylesheet"
    if extension in {".js", ".mjs", ".cjs", ".wasm"}:
        return "script"
    if extension in {".avif", ".bmp", ".gif", ".ico", ".jpeg", ".jpg", ".jxl", ".png", ".svg", ".webp"}:
        return "image"
    if extension in {".eot", ".otf", ".ttf", ".woff", ".woff2"}:
        return "font"
    if extension in {".aac", ".m3u8", ".m4a", ".mp3", ".mp4", ".ogg", ".ogv", ".vtt", ".wav", ".webm"}:
        return "media"
    if extension in {".html", ".htm"}:
        return "document"
    if extension == ".webmanifest" or any(
        marker in path
        for marker in (
            "asset-manifest.json",
            "build-manifest.json",
            "/.vite/manifest.json",
            "/manifest.json",
        )
    ):
        return "manifest"
    if extension in {
        ".bin", ".drc", ".exr", ".glb", ".gltf", ".hdr", ".ktx",
        ".ktx2", ".txt", ".xml",
    }:
        return "fetch"
    return ""


def parse_extra_urls(path: str) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    try:
        with open(path, "r", encoding="utf-8") as handle:
            lines = handle.readlines()
    except OSError as exc:
        raise MirrorError("Cannot read --extra-urls %s: %s" % (path, exc)) from exc
    for line_no, raw in enumerate(lines, 1):
        value = raw.strip()
        if not value or value.startswith("#"):
            continue
        if value.startswith("{"):
            try:
                record = json.loads(value)
            except ValueError as exc:
                raise MirrorError("Invalid JSON at %s:%d: %s" % (path, line_no, exc)) from exc
            if not isinstance(record, dict):
                raise MirrorError("Expected a JSON object at %s:%d" % (path, line_no))
        else:
            pieces = value.split("\t", 1)
            resource_type = pieces[1].strip().lower() if len(pieces) == 2 else inferred_static_type(pieces[0])
            record = {
                "url": pieces[0],
                "method": "GET",
                "resource_type": resource_type or "unknown",
                "request_class": "static" if resource_type else "unknown",
                "data_type": "static_asset" if resource_type else "unknown",
                "acquisition": {
                    "automatic": bool(resource_type),
                    "reason": "classified static extra URL" if resource_type else "unknown extra URL",
                },
                "status": 0,
            }
        record["_extra_url"] = True
        record["_extra_source"] = "%s:%d" % (os.path.abspath(path), line_no)
        records.append(record)
    return records


def metadata_resource_type(item: Dict[str, Any]) -> str:
    kind = str(item.get("kind") or "").lower()
    if any(token in kind for token in ("image", "icon", "logo")):
        return "image"
    if "manifest" in kind:
        return "manifest"
    return inferred_static_type(str(item.get("url") or "")) or "unknown"


def required_record(record: Dict[str, Any], resource_type: str) -> bool:
    if resource_type == "document":
        return True
    if record.get("required") is True or record.get("required_for_baseline") is True:
        return True
    return str(record.get("requirement") or record.get("criticality") or "").lower() == "required"


def classify_request(
    record: Dict[str, Any], policy: AuthorizationPolicy, force_documents: bool = False
) -> Tuple[str, Dict[str, Any]]:
    url = str(record.get("url") or "")
    try:
        info = parse_http_url(url)
    except MirrorError as exc:
        return "skip", {"reason": str(exc), "url": url}

    method = str(record.get("method") or "").upper()
    resource_type = str(record.get("resource_type") or "").lower()
    data_type = str(record.get("data_type") or "").lower()
    request_class = str(record.get("request_class") or "").lower()
    status = record.get("status")

    recomputed_sensitive_keys = sensitive_query_keys(info.normalized_url)
    if (record.get("url_redacted") or record.get("sensitive_query_keys")
            or recomputed_sensitive_keys):
        return "skip", {
            "reason": "credential-like query data was redacted; supply the asset explicitly instead",
            "url": url,
            "sensitive_query_keys": sorted(set(
                list(record.get("sensitive_query_keys") or [])
                + recomputed_sensitive_keys
            )),
        }

    if method not in {"GET", "HEAD"}:
        return "skip", {"reason": "request method is not GET/HEAD", "method": method, "url": url}
    if resource_type in SKIP_TYPES:
        return "skip", {"reason": "non-static request type", "resource_type": resource_type, "url": url}
    if is_telemetry_url(info, record):
        return "skip", {"reason": "telemetry is never auto-acquired", "url": url}

    decision = policy.classify(url, resource_type)
    if not decision["allowed"]:
        category = "provider" if decision["scope"] == "provider" else "external"
        return category, {"url": url, **decision}

    if status not in (None, 0, "", "0"):
        try:
            if not 200 <= int(status) < 300:
                return "skip", {"reason": "non-2xx capture/probe status (%s)" % status, "url": url}
        except (TypeError, ValueError):
            return "skip", {"reason": "invalid capture/probe status", "url": url}

    acquisition = record.get("acquisition") if isinstance(record.get("acquisition"), dict) else {}
    forced_override = False
    if acquisition.get("automatic") is False:
        if force_documents and resource_type == "document":
            forced_override = True  # operator asserts this document is a public page
        else:
            return "skip", {
                "reason": "capture classification disallows automatic acquisition: %s"
                % (acquisition.get("reason") or "unspecified"),
                "url": url,
            }

    labels = " ".join((data_type, request_class)).lower()
    if any(word in labels for word in ("personal", "private", "session", "user-specific")):
        if force_documents and resource_type == "document":
            forced_override = True
        else:
            return "skip", {"reason": "personalized/private response is never auto-acquired", "url": url}

    if resource_type in DATA_RESOURCE_TYPES:
        inferred_type = inferred_static_type(info.normalized_url)
        normalized_content_type = str(record.get("content_type") or "").split(";", 1)[0].lower()
        independently_static = bool(inferred_type) or normalized_content_type.startswith(
            ("image/", "font/", "audio/", "video/", "model/")
        ) or normalized_content_type in {
            "application/javascript", "application/manifest+json",
            "application/wasm", "text/css", "text/javascript",
        }
        explicitly_public_static = (
            data_type in STATIC_DATA_TYPES or request_class in STATIC_DATA_CLASSES
        )
        if (not (independently_static or explicitly_public_static)
                or method != "GET" or acquisition.get("automatic") is not True):
            return "skip", {
                "reason": (
                    "unknown XHR/fetch is not replayed; independent static identity "
                    "or explicit public-static classification is required"
                ),
                "url": url,
            }
    elif resource_type not in STATIC_RESOURCE_TYPES:
        return "skip", {"reason": "resource is not classified as static", "resource_type": resource_type, "url": url}

    if method == "HEAD":
        return "probe", {"url": url, **decision}
    result_detail = {"url": url, **decision}
    if forced_override:
        result_detail["forced_document_override"] = True
        result_detail["override_note"] = (
            "operator --force-document: identity-varying/personalized document "
            "acquired as an asserted-public page"
        )
    return "acquire", result_detail


def candidate_from_record(record: Dict[str, Any], graph_path: str) -> Candidate:
    info = parse_http_url(str(record.get("url") or ""))
    acquisition = record.get("acquisition") if isinstance(record.get("acquisition"), dict) else {}
    resource_type = str(record.get("resource_type") or "").lower()
    return Candidate(
        url=info.url,
        normalized_url=info.normalized_url,
        method=str(record.get("method") or "").upper(),
        resource_type=resource_type,
        content_type=str(record.get("content_type") or ""),
        required=required_record(record, resource_type),
        source_graphs=[graph_path],
        request_class=str(record.get("request_class") or ""),
        data_type=str(record.get("data_type") or ""),
        acquisition_reason=str(acquisition.get("reason") or "recomputed static classification"),
        first_seen=record.get("first_seen"),
        metadata_refs=list(record.get("_metadata_refs") or []),
    )


def merge_candidate(existing: Candidate, incoming: Candidate) -> Candidate:
    existing.required = existing.required or incoming.required
    existing.source_graphs = sorted(set(existing.source_graphs + incoming.source_graphs))
    existing.metadata_refs.extend(incoming.metadata_refs)
    if not existing.content_type and incoming.content_type:
        existing.content_type = incoming.content_type
    if not existing.first_seen and incoming.first_seen:
        existing.first_seen = incoming.first_seen
    return existing


def collect_records(
    graphs: Sequence[Tuple[str, Dict[str, Any]]], extra_urls_path: Optional[str]
) -> Tuple[List[Tuple[Dict[str, Any], str]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    records: List[Tuple[Dict[str, Any], str]] = []
    metadata_inventory: List[Dict[str, Any]] = []
    pages: List[Dict[str, Any]] = []
    for graph_path, graph in graphs:
        navigation = graph.get("navigation") if isinstance(graph.get("navigation"), dict) else {}
        requested = graph_requested_url(graph)
        final = graph_final_url(graph)
        pages.append(
            {
                "graph": graph_path,
                "graph_sha256": graph.get("_ntsm_source_sha256"),
                "requested_url": requested,
                "final_url": final,
                "title": navigation.get("title"),
                "initial_status": navigation.get("initial_status"),
                "final_status": navigation.get("final_status"),
                "redirects": graph_redirects(graph),
                "access": navigation.get("access"),
            }
        )
        graph_requests = [item for item in graph.get("requests", []) if isinstance(item, dict)]
        # Always fetch the user-requested document URL. Its live redirect chain
        # is revalidated by the downloader; capture-time evidence is advisory.
        requested_info = parse_http_url(requested)
        matching_documents = [
            item
            for item in graph_requests
            if str(item.get("method") or "").upper() == "GET"
            and str(item.get("resource_type") or "").lower() == "document"
            and _safe_normalized_url(item.get("url")) == requested_info.normalized_url
        ]
        if matching_documents:
            # The requested document is fetched live even when its capture-time
            # response was a 3xx. Redirect destinations are reauthorized by the
            # downloader. Do not override redaction/non-acquisition evidence.
            for item in matching_documents:
                item["required"] = True
                acquisition = (
                    item.get("acquisition")
                    if isinstance(item.get("acquisition"), dict)
                    else {}
                )
                if (not item.get("url_redacted")
                        and not item.get("sensitive_query_keys")
                        and acquisition.get("automatic") is not False):
                    item["status"] = 0
                    item["acquisition"] = {
                        "automatic": True,
                        "reason": "required requested document; live redirects revalidated",
                    }
        else:
            graph_requests.insert(
                0,
                {
                    "url": requested,
                    "method": "GET",
                    "resource_type": "document",
                    "request_class": "static-document",
                    "data_type": "document",
                    "status": navigation.get("final_status") or 0,
                    "required": True,
                    "acquisition": {"automatic": True, "reason": "requested page document"},
                },
            )
        for record in graph_requests:
            records.append((dict(record), graph_path))

        for item in graph.get("metadata_references", []) or []:
            if not isinstance(item, dict) or not item.get("url"):
                continue
            inventory = {
                **item,
                "graph": graph_path,
                "graph_sha256": graph.get("_ntsm_source_sha256"),
                "observed": bool(item.get("observed", True)),
                "probed": bool(item.get("probed")),
                "captured": False,
            }
            metadata_inventory.append(inventory)
            probe = item.get("probe") if isinstance(item.get("probe"), dict) else {}
            if not inventory["probed"] or not probe:
                continue
            record = {
                "url": item["url"],
                "method": "GET",
                "resource_type": metadata_resource_type(item),
                "request_class": "static-metadata",
                "data_type": "static",
                "status": probe.get("status"),
                "content_type": probe.get("content_type") or "",
                "acquisition": {"automatic": True, "reason": "probed metadata reference"},
                "_metadata_refs": [inventory],
            }
            records.append((record, graph_path))

    if extra_urls_path:
        for record in parse_extra_urls(extra_urls_path):
            records.append((record, record.get("_extra_source", os.path.abspath(extra_urls_path))))
    return records, metadata_inventory, pages


def _safe_normalized_url(value: Any) -> str:
    try:
        return parse_http_url(str(value or "")).normalized_url
    except MirrorError:
        return ""


def _safe_segment(value: str) -> str:
    value = value.replace("\\", "%5C").replace("\x00", "")
    if value in {"", ".", ".."}:
        return "_"
    return value


def _query_suffix(path: str, query: str) -> str:
    if not query:
        return path
    suffix = "__q_" + hashlib.sha256(query.encode("utf-8")).hexdigest()[:16]
    directory, name = posixpath.split(path)
    root, extension = posixpath.splitext(name)
    name = (root + suffix + extension) if extension else (name + suffix)
    return posixpath.join(directory, name)


def local_relative_path(url: str, resource_type: str, primary: bool) -> str:
    info = parse_http_url(url)
    parts = urlsplit(info.normalized_url)
    raw_segments = [_safe_segment(piece) for piece in (parts.path or "/").lstrip("/").split("/")]
    rel = posixpath.join(*raw_segments) if raw_segments else ""
    if resource_type == "document":
        if not rel or (parts.path or "/").endswith("/"):
            rel = posixpath.join(rel, "index.html")
        elif not posixpath.splitext(rel)[1]:
            rel = posixpath.join(rel, "index.html")
    else:
        if not rel:
            rel = "__root_resource"
        elif (parts.path or "/").endswith("/"):
            rel = posixpath.join(rel, "__resource")
    rel = _query_suffix(rel, parts.query)
    if not primary:
        host_segment = re.sub(r"[^A-Za-z0-9._-]", "_", info.authority)
        rel = posixpath.join("_external", host_segment, rel)
    normalized = posixpath.normpath(rel).lstrip("/")
    if normalized in {"", ".", ".."} or normalized.startswith("../"):
        raise MirrorError("Unsafe local path derived from %s" % url)
    return normalized


def absolute_target(out_dir: str, rel: str) -> str:
    root = os.path.abspath(out_dir)
    target = os.path.abspath(os.path.normpath(os.path.join(root, rel)))
    if os.path.commonpath([root, target]) != root or target == root:
        raise MirrorError("Unsafe output path %r" % rel)
    return target


def dedupe_entries(entries: Iterable[Dict[str, Any]], keys: Sequence[str]) -> List[Dict[str, Any]]:
    seen: Set[Tuple[Any, ...]] = set()
    result: List[Dict[str, Any]] = []
    for item in entries:
        identity = tuple(item.get(key) for key in keys)
        if identity in seen:
            continue
        seen.add(identity)
        result.append(item)
    return result


def fetch_candidate(
    candidate: Candidate,
    target: Optional[str],
    timeout: int,
    delay: float,
    policy: AuthorizationPolicy,
) -> FetchResult:
    if delay:
        time.sleep(delay)
    handler = TrackingRedirectHandler(policy, candidate.resource_type)
    opener = build_opener(handler)
    request = Request(
        candidate.url,
        headers={"User-Agent": USER_AGENT, "Accept-Encoding": "identity"},
        method=candidate.method,
    )
    try:
        with opener.open(request, timeout=timeout) as response:
            status = int(getattr(response, "status", response.getcode()))
            final_url = response.geturl()
            final_decision = policy.classify(final_url, candidate.resource_type)
            if not final_decision["allowed"]:
                raise UnsafeRedirectError(
                    "Final response URL is unauthorized: %s (%s)"
                    % (final_url, final_decision["reason"]),
                    handler.chain,
                )
            content_type = response.headers.get("Content-Type")
            content_encoding = (response.headers.get("Content-Encoding") or "").strip().lower()
            if content_encoding not in {"", "identity"}:
                raise MirrorError(
                    "Server ignored Accept-Encoding: identity for %s (Content-Encoding: %s)"
                    % (candidate.url, content_encoding)
                )
            data = b"" if candidate.method == "HEAD" else response.read()
    except UnsafeRedirectError:
        raise
    except HTTPError as exc:
        raise MirrorError("HTTP %s for %s" % (exc.code, candidate.url)) from exc

    challenge = None
    if candidate.resource_type == "document" and candidate.method == "GET":
        htmlish = (
            "text/html" in (content_type or "").lower()
            or "application/xhtml+xml" in (content_type or "").lower()
            or data.lstrip().lower().startswith((b"<!doctype html", b"<html"))
        )
        if not data or not htmlish:
            raise MirrorError(
                "Required document response is empty or not HTML: %s (%s)"
                % (candidate.url, content_type or "unknown content type")
            )
        challenge = html_access_block(
            data,
            content_type or "",
            final_url=final_url,
        )
        if challenge:
            raise AccessBlockedError(candidate.url, challenge)

    digest = sha256_bytes(data) if candidate.method == "GET" else None
    if candidate.method == "GET":
        if target is None:
            raise MirrorError("Internal error: GET candidate has no target")
        atomic_write_bytes(target, data)
    return FetchResult(
        url=candidate.url,
        normalized_url=candidate.normalized_url,
        target_rel=candidate.target_rel,
        method=candidate.method,
        required=candidate.required,
        status=status,
        final_url=parse_http_url(final_url).normalized_url,
        redirects=handler.chain,
        content_type=content_type,
        size=len(data),
        sha256=digest,
        captured=candidate.method == "GET",
        challenge=challenge,
    )


def base_manifest(
    prior: Optional[Dict[str, Any]],
    authorization: str,
    allowed_hosts: Set[str],
    allowed_authorities: Set[Tuple[str, int]],
) -> Dict[str, Any]:
    manifest = dict(prior or {})
    if prior and str(prior.get("schema_version")) != MANIFEST_SCHEMA_VERSION:
        raise MirrorError("--resume requires a v1.3 mirror-manifest.json")
    manifest["schema_version"] = MANIFEST_SCHEMA_VERSION
    manifest.setdefault("created_at", utc_now())
    manifest["updated_at"] = utc_now()
    contexts = list(manifest.get("authorization_contexts") or [])
    if not any(item.get("context") == authorization for item in contexts if isinstance(item, dict)):
        contexts.append({"context": authorization, "recorded_at": utc_now()})
    manifest["authorization_contexts"] = contexts
    manifest["authorization_context"] = authorization
    manifest["allowed_external_hosts"] = sorted(
        set(manifest.get("allowed_external_hosts") or [])
        | allowed_hosts
        | {"%s:%d" % item for item in allowed_authorities}
    )
    manifest.setdefault("pages", [])
    manifest.setdefault("capture_graphs", [])
    manifest.setdefault("route_map", {})
    manifest.setdefault("source_url_map", {})
    manifest.setdefault("downloaded", [])
    manifest.setdefault("probed", [])
    manifest.setdefault("failed", [])
    manifest.setdefault("skipped_external", [])
    manifest.setdefault("skipped_provider_assets", [])
    manifest.setdefault("skipped_other", [])
    manifest.setdefault("metadata_references", [])
    manifest.setdefault("local_modifications", [])
    manifest.setdefault("construction_provenance", [])
    manifest.setdefault("generated_artifacts", [])
    manifest.setdefault("attempts", [])
    return manifest


def validate_resume_manifest_shape(manifest: Dict[str, Any]) -> None:
    list_fields = (
        "authorization_contexts", "pages", "capture_graphs", "downloaded", "probed", "failed",
        "skipped_external", "skipped_provider_assets", "skipped_other",
        "metadata_references", "local_modifications", "construction_provenance",
        "generated_artifacts", "attempts",
    )
    map_fields = ("route_map", "source_url_map")
    for field in list_fields:
        if field in manifest and not isinstance(manifest[field], list):
            raise MirrorError(
                "--resume manifest field %s must be a list" % field
            )
    for field in map_fields:
        if field in manifest and not isinstance(manifest[field], dict):
            raise MirrorError(
                "--resume manifest field %s must be an object" % field
            )
    for field in (
        "local_modifications", "construction_provenance", "generated_artifacts"
    ):
        for index, entry in enumerate(manifest.get(field, []) or []):
            if not isinstance(entry, dict):
                raise MirrorError(
                    "--resume %s[%d] must be an object" % (field, index)
                )
            if entry.get("phase") != CONSTRUCTION_PHASE or not entry.get("actor"):
                raise MirrorError(
                    "--resume %s[%d] must declare phase=construction and actor"
                    % (field, index)
                )


def prepare_output(out_dir: str, resume: bool) -> Optional[Dict[str, Any]]:
    if os.path.exists(out_dir) and not os.path.isdir(out_dir):
        raise MirrorError("Output exists and is not a directory: %s" % out_dir)
    entries = os.listdir(out_dir) if os.path.isdir(out_dir) else []
    if entries and not resume:
        raise MirrorError(
            "Output directory is not empty. Use a fresh directory or pass --resume: %s" % out_dir
        )
    if resume:
        if not entries:
            raise MirrorError("--resume requires a non-empty v1.3 mirror directory")
        prior = load_json(os.path.join(out_dir, "mirror-manifest.json"))
        if str(prior.get("schema_version")) != MANIFEST_SCHEMA_VERSION:
            raise MirrorError("--resume requires mirror-manifest.json schema 1.3")
        validate_resume_manifest_shape(prior)
        return prior
    os.makedirs(out_dir, exist_ok=True)
    return None


def prior_download_index(manifest: Dict[str, Any]) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, Dict[str, Any]]]:
    by_url: Dict[str, Dict[str, Any]] = {}
    by_path: Dict[str, Dict[str, Any]] = {}
    for entry in manifest.get("downloaded", []) or []:
        if not isinstance(entry, dict):
            continue
        normalized = entry.get("normalized_url") or _safe_normalized_url(entry.get("url"))
        path = entry.get("path")
        if normalized:
            by_url[str(normalized)] = entry
        if path:
            by_path[str(path).casefold()] = entry
    return by_url, by_path


def validate_resume_entry(out_dir: str, entry: Dict[str, Any]) -> None:
    rel = str(entry.get("path") or "")
    expected = str(entry.get("sha256") or "")
    if not rel or not expected:
        raise MirrorError("Existing v1.3 download inventory lacks path/sha256")
    target = absolute_target(out_dir, rel)
    if not os.path.isfile(target):
        raise MirrorError("Resume inventory file is missing: %s" % rel)
    actual = sha256_file(target)
    if actual != expected:
        raise MirrorError(
            "Resume hash mismatch for %s; refusing to overwrite a possibly modified file" % rel
        )


def generated_file_entry(out_dir: str, rel: str, kind: str) -> Dict[str, Any]:
    path = absolute_target(out_dir, rel)
    return {
        "path": rel,
        "kind": kind,
        "sha256": sha256_file(path),
        "phase": CONSTRUCTION_PHASE,
        "actor": ACTOR,
        "generated_at": utc_now(),
    }


def write_serve_artifacts(out_dir: str) -> List[Dict[str, Any]]:
    source_serve = os.path.join(os.path.dirname(os.path.abspath(__file__)), "serve.py")
    if not os.path.isfile(source_serve):
        raise MirrorError("Cannot generate portable launcher: serve.py is missing")
    with open(source_serve, "rb") as handle:
        serve_bytes = handle.read()
    bundled_rel = posixpath.join("_ntsm", "serve.py")
    atomic_write_bytes(absolute_target(out_dir, bundled_rel), serve_bytes)

    launcher_rel = "serve-local.py"
    launcher = b'''#!/usr/bin/env python3
"""Portable launcher generated by NT Site Mirror v1.3."""
from pathlib import Path
import runpy
import sys

ROOT = Path(__file__).resolve().parent
SERVER = ROOT / "_ntsm" / "serve.py"
sys.argv = [str(SERVER), str(ROOT)] + sys.argv[1:]
runpy.run_path(str(SERVER), run_name="__main__")
'''
    atomic_write_bytes(absolute_target(out_dir, launcher_rel), launcher, executable=True)

    contract_rel = "serve-contract.json"
    contract = {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "manifest": "mirror-manifest.json",
        "route_map": "mirror-manifest.json#route_map",
        "bind": "127.0.0.1",
        "port": 8000,
        "spa_fallback": False,
        "safe_spa_entry": None,
        "cache_control": "no-store",
        "range_requests": True,
        "launcher": launcher_rel,
        "generated": {"phase": CONSTRUCTION_PHASE, "actor": ACTOR, "at": utc_now()},
    }
    atomic_write_json(absolute_target(out_dir, contract_rel), contract)
    return [
        generated_file_entry(out_dir, bundled_rel, "bundled-local-server"),
        generated_file_entry(out_dir, launcher_rel, "portable-launcher"),
        generated_file_entry(out_dir, contract_rel, "serve-contract"),
    ]


def _upsert_generated(existing: List[Dict[str, Any]], new_items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    by_path = {str(item.get("path")): item for item in existing if isinstance(item, dict)}
    for item in new_items:
        by_path[item["path"]] = item
    return [by_path[key] for key in sorted(by_path)]


def _manifest_summary(manifest: Dict[str, Any], attempt: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "downloaded_total": len(manifest.get("downloaded", [])),
        "probed_total": len(manifest.get("probed", [])),
        "failed_history_total": len(manifest.get("failed", [])),
        "skipped_external_total": len(manifest.get("skipped_external", [])),
        "skipped_provider_assets_total": len(manifest.get("skipped_provider_assets", [])),
        "skipped_other_total": len(manifest.get("skipped_other", [])),
        "metadata_references_total": len(manifest.get("metadata_references", [])),
        "current_attempt": {
            "downloaded": attempt["downloaded"],
            "reused": attempt["reused"],
            "probed": attempt["probed"],
            "failed": attempt["failed"],
            "required_failures": attempt["required_failures"],
            "integrity_errors": attempt["integrity_errors"],
        },
    }


def run(args: argparse.Namespace) -> int:
    authorization = (args.authorized or "").strip() or "inspiration / non-commercial reference"
    if args.workers < 1:
        raise MirrorError("--workers must be at least 1")
    if args.delay < 0 or args.timeout < 1:
        raise MirrorError("--delay must be nonnegative and --timeout must be positive")

    graphs, primary_origins = validate_graphs(args.graphs)
    allowed_hosts, allowed_authorities = parse_allowed_hosts(args.allow_host)
    policy = AuthorizationPolicy(primary_origins, allowed_hosts, allowed_authorities)
    evidence_errors = validate_graph_redirect_evidence(graphs, policy)
    if not evidence_errors:
        # A cross-host final document origin becomes part of the local site's
        # canonical scope only after --allow-host independently authorized it.
        # Live redirects are still checked again during acquisition.
        canonical_origins = set(primary_origins)
        for _path, graph in graphs:
            final_info = parse_http_url(graph_final_url(graph))
            if policy.classify(final_info.normalized_url, "document")["allowed"]:
                canonical_origins.add(final_info.origin)
        policy = AuthorizationPolicy(canonical_origins, allowed_hosts, allowed_authorities)

    out_dir = os.path.abspath(args.out)
    prior = prepare_output(out_dir, args.resume)
    manifest = base_manifest(prior, authorization, allowed_hosts, allowed_authorities)
    graph_inventory = [
        {
            "path": path,
            "sha256": graph["_ntsm_source_sha256"],
            "schema_version": graph.get("schema_version"),
            "requested_url": graph_requested_url(graph),
            "final_url": graph_final_url(graph),
            "captured_at": graph.get("captured_at"),
            "recorded_at": utc_now(),
        }
        for path, graph in graphs
    ]
    manifest["capture_graphs"] = dedupe_entries(
        list(manifest.get("capture_graphs") or []) + graph_inventory,
        ("path", "sha256"),
    )
    attempt_id = "%s-%s-%s" % (
        time.strftime("%Y%m%dT%H%M%SZ", time.gmtime()),
        os.getpid(),
        time.time_ns(),
    )
    attempt = {
        "id": attempt_id,
        "started_at": utc_now(),
        "graphs": [path for path, _ in graphs],
        "capture_graph_sha256": [item["sha256"] for item in graph_inventory],
        "resume": bool(args.resume),
        "downloaded": 0,
        "reused": 0,
        "probed": 0,
        "failed": 0,
        "required_failures": 0,
        "integrity_errors": len(evidence_errors),
        "status": "running",
    }

    records, metadata_inventory, pages = collect_records(graphs, args.extra_urls)
    manifest["pages"] = dedupe_entries(
        list(manifest.get("pages") or []) + pages,
        ("requested_url", "final_url", "graph", "graph_sha256"),
    )
    if manifest["pages"]:
        manifest["page"] = manifest["pages"][0].get("requested_url")
    manifest["metadata_references"] = dedupe_entries(
        list(manifest.get("metadata_references") or []) + metadata_inventory,
        ("url", "kind", "source", "graph", "graph_sha256"),
    )

    if evidence_errors:
        for error in evidence_errors:
            manifest["failed"].append(
                {"attempt_id": attempt_id, "required": True, "error": error}
            )
        attempt["failed"] = len(evidence_errors)
        attempt["required_failures"] = len(evidence_errors)
        attempt["status"] = "blocked"
        blocked_by_challenge = any(
            str(error.get("state") or "") == "blocked_by_challenge"
            for error in evidence_errors
        )
        manifest["result"] = (
            "blocked_by_challenge" if blocked_by_challenge else "blocked_by_access"
        )
        manifest["blocked_by_challenge"] = blocked_by_challenge
        attempt["finished_at"] = utc_now()
        manifest["attempts"].append(attempt)
        manifest["summary"] = _manifest_summary(manifest, attempt)
        manifest["updated_at"] = utc_now()
        atomic_write_json(os.path.join(out_dir, "mirror-manifest.json"), manifest)
        print("Mirror blocked before acquisition:", file=sys.stderr)
        for error in evidence_errors:
            print("  - %s" % json.dumps(error, sort_keys=True), file=sys.stderr)
        return 2

    candidates: Dict[Tuple[str, str], Candidate] = {}
    skipped_external: List[Dict[str, Any]] = []
    skipped_provider: List[Dict[str, Any]] = []
    skipped_other: List[Dict[str, Any]] = []
    classification_failures: List[Dict[str, Any]] = []
    forced_document_overrides: List[str] = []
    force_documents = bool(getattr(args, "force_document", False))
    for record, graph_path in records:
        disposition, detail = classify_request(record, policy, force_documents=force_documents)
        if detail.get("forced_document_override"):
            forced_document_overrides.append(str(record.get("url") or ""))
        if disposition in {"acquire", "probe"}:
            candidate = candidate_from_record(record, graph_path)
            key = (candidate.normalized_url, candidate.method)
            if key in candidates:
                merge_candidate(candidates[key], candidate)
            else:
                candidates[key] = candidate
        elif disposition == "provider":
            skipped_provider.append(
                {
                    **detail,
                    "source_graph": graph_path,
                    "action": "classify: Embed / Kept External / User-Supplied Baseline Asset / Recreated From Observation / Blocked",
                }
            )
        elif disposition == "external":
            skipped_external.append(
                {
                    **detail,
                    "source_graph": graph_path,
                    "action": "classify: Embed / Kept External / User-Supplied Baseline Asset / Recreated From Observation / Blocked",
                }
            )
        else:
            skipped_other.append({**detail, "source_graph": graph_path})
        if disposition not in {"acquire", "probe"}:
            resource_type = str(record.get("resource_type") or "").lower()
            if required_record(record, resource_type):
                classification_failures.append(
                    {
                        "url": record.get("url"),
                        "method": str(record.get("method") or "").upper(),
                        "resource_type": resource_type,
                        "required": True,
                        "error": "Required resource was not eligible for automatic acquisition: %s"
                        % detail.get("reason", disposition),
                        "classification": disposition,
                        "source_graph": graph_path,
                        "attempt_id": attempt_id,
                    }
                )

    if forced_document_overrides:
        unique_forced = sorted(set(forced_document_overrides))
        manifest["forced_document_overrides"] = unique_forced
        print(
            "WARNING --force-document: acquired %d identity-varying/personalized document(s) as "
            "asserted-public pages (recorded in manifest.forced_document_overrides):"
            % len(unique_forced),
            file=sys.stderr,
        )
        for forced_url in unique_forced:
            print("  - %s" % forced_url, file=sys.stderr)

    # An explicitly supplied --extra-urls record is an authorization-gated
    # override for a capture-time classification that was intentionally
    # conservative (for example, Wix documents marked private because of
    # cache-control headers).  Keep the original graph classification in the
    # manifest, but do not fail the attempt before the explicit candidate has
    # been fetched.  If that candidate later fails, fetch_candidate() records
    # the real required failure.
    explicit_acquire_keys = {
        (candidate.normalized_url, candidate.method)
        for candidate in candidates.values()
        if candidate.method == "GET"
    }
    classification_failures = [
        failure
        for failure in classification_failures
        if (
            _safe_normalized_url(failure.get("url")),
            str(failure.get("method") or "").upper(),
        ) not in explicit_acquire_keys
    ]

    prior_by_url, prior_by_path = prior_download_index(manifest)
    target_claims: Dict[str, str] = {
        path.casefold(): "nt-site-mirror:generated/%s" % path
        for path in RESERVED_OUTPUT_PATHS
    }
    integrity_errors: List[Dict[str, Any]] = []
    pending: List[Candidate] = []
    reused_entries: List[Dict[str, Any]] = []

    if args.resume:
        for prior_entry in manifest.get("downloaded", []) or []:
            if not isinstance(prior_entry, dict):
                integrity_errors.append(
                    {"kind": "resume_integrity", "error": "download inventory entry is not an object"}
                )
                continue
            try:
                validate_resume_entry(out_dir, prior_entry)
            except MirrorError as exc:
                integrity_errors.append(
                    {
                        "kind": "resume_integrity",
                        "url": prior_entry.get("normalized_url") or prior_entry.get("url"),
                        "error": str(exc),
                    }
                )
                continue
            prior_path = str(prior_entry.get("path") or "")
            prior_url = str(
                prior_entry.get("normalized_url")
                or _safe_normalized_url(prior_entry.get("url"))
            )
            if prior_path and prior_url:
                collision_key = prior_path.casefold()
                existing_url = target_claims.get(collision_key)
                if existing_url and existing_url != prior_url:
                    integrity_errors.append({
                        "kind": "resume_target_collision",
                        "path": prior_path,
                        "existing_url": existing_url,
                        "new_url": prior_url,
                    })
                else:
                    target_claims[collision_key] = prior_url
        for prior_artifact in manifest.get("generated_artifacts", []) or []:
            if not isinstance(prior_artifact, dict):
                integrity_errors.append(
                    {"kind": "resume_integrity", "error": "generated artifact entry is not an object"}
                )
                continue
            try:
                validate_resume_entry(out_dir, prior_artifact)
            except MirrorError as exc:
                integrity_errors.append(
                    {
                        "kind": "resume_generated_artifact_integrity",
                        "path": prior_artifact.get("path"),
                        "error": str(exc),
                    }
                )

    for candidate in sorted(candidates.values(), key=lambda item: (item.normalized_url, item.method)):
        decision = policy.classify(candidate.url, candidate.resource_type)
        candidate.primary = decision["scope"] == "primary"
        if candidate.method == "GET":
            candidate.target_rel = local_relative_path(
                candidate.url, candidate.resource_type, candidate.primary
            )
            collision_key = candidate.target_rel.casefold()
            claimed = target_claims.get(collision_key)
            if claimed and claimed != candidate.normalized_url:
                integrity_errors.append(
                    {
                        "kind": "target_collision",
                        "path": candidate.target_rel,
                        "urls": [claimed, candidate.normalized_url],
                    }
                )
                continue
            target_claims[collision_key] = candidate.normalized_url

            prior_entry = prior_by_url.get(candidate.normalized_url)
            if prior_entry:
                if str(prior_entry.get("path")) != candidate.target_rel:
                    integrity_errors.append(
                        {
                            "kind": "resume_path_identity_changed",
                            "url": candidate.normalized_url,
                            "before": prior_entry.get("path"),
                            "after": candidate.target_rel,
                        }
                    )
                    continue
                try:
                    validate_resume_entry(out_dir, prior_entry)
                except MirrorError as exc:
                    integrity_errors.append(
                        {"kind": "resume_integrity", "url": candidate.normalized_url, "error": str(exc)}
                    )
                    continue
                reused_entries.append(prior_entry)
                continue

            conflicting = prior_by_path.get(collision_key)
            if conflicting:
                integrity_errors.append(
                    {
                        "kind": "resume_target_collision",
                        "path": candidate.target_rel,
                        "existing_url": conflicting.get("normalized_url") or conflicting.get("url"),
                        "new_url": candidate.normalized_url,
                    }
                )
                continue
            target = absolute_target(out_dir, candidate.target_rel)
            if os.path.exists(target):
                integrity_errors.append(
                    {
                        "kind": "untracked_existing_target",
                        "path": candidate.target_rel,
                        "url": candidate.normalized_url,
                    }
                )
                continue
        pending.append(candidate)

    # Every mapped target is a file. Reject file/directory prefix conflicts
    # before starting any network work (for example `/config` plus
    # `/config/app.js` when the first is an extensionless static resource).
    claimed_paths = sorted(target_claims, key=lambda value: (value.count("/"), value))
    for index, path_key in enumerate(claimed_paths):
        prefix = path_key.rstrip("/") + "/"
        for other in claimed_paths[index + 1 :]:
            if other.startswith(prefix):
                integrity_errors.append(
                    {
                        "kind": "file_directory_collision",
                        "paths": [path_key, other],
                        "urls": [target_claims[path_key], target_claims[other]],
                    }
                )

    attempt["reused"] = len(reused_entries)
    attempt["integrity_errors"] += len(integrity_errors)
    if integrity_errors:
        for error in integrity_errors:
            manifest["failed"].append(
                {"attempt_id": attempt_id, "required": True, "error": error}
            )
        attempt["failed"] += len(integrity_errors)
        attempt["required_failures"] += len(integrity_errors)
        attempt["status"] = "failed_integrity"
        manifest["result"] = "failed_integrity"
        manifest["blocked_by_challenge"] = False
        attempt["finished_at"] = utc_now()
        manifest["skipped_external"] = dedupe_entries(
            list(manifest.get("skipped_external") or []) + skipped_external,
            ("url", "reason", "source_graph"),
        )
        manifest["skipped_provider_assets"] = dedupe_entries(
            list(manifest.get("skipped_provider_assets") or []) + skipped_provider,
            ("url", "provider", "source_graph"),
        )
        manifest["skipped_other"] = dedupe_entries(
            list(manifest.get("skipped_other") or []) + skipped_other,
            ("url", "reason", "source_graph"),
        )
        manifest["attempts"].append(attempt)
        manifest["summary"] = _manifest_summary(manifest, attempt)
        manifest["updated_at"] = utc_now()
        atomic_write_json(os.path.join(out_dir, "mirror-manifest.json"), manifest)
        print("Mirror failed integrity checks before acquisition:", file=sys.stderr)
        for error in integrity_errors:
            print("  - %s" % json.dumps(error, sort_keys=True), file=sys.stderr)
        return 2

    downloaded_now: List[Dict[str, Any]] = []
    probed_now: List[Dict[str, Any]] = []
    failed_now: List[Dict[str, Any]] = list(classification_failures)
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {}
        for candidate in pending:
            target = (
                absolute_target(out_dir, candidate.target_rel)
                if candidate.method == "GET" and candidate.target_rel
                else None
            )
            future = pool.submit(
                fetch_candidate, candidate, target, args.timeout, args.delay, policy
            )
            futures[future] = candidate
        for future in as_completed(futures):
            candidate = futures[future]
            try:
                result = future.result()
                common = {
                    "url": result.url,
                    "normalized_url": result.normalized_url,
                    "method": result.method,
                    "status": result.status,
                    "final_url": result.final_url,
                    "redirects": result.redirects,
                    "resource_type": candidate.resource_type,
                    "request_class": candidate.request_class,
                    "data_type": candidate.data_type,
                    "required": candidate.required,
                    "source_graphs": candidate.source_graphs,
                    "first_seen": candidate.first_seen,
                    "attempt_id": attempt_id,
                }
                if result.captured:
                    entry = {
                        **common,
                        "path": result.target_rel,
                        "bytes": result.size,
                        "sha256": result.sha256,
                        "content_type": result.content_type or candidate.content_type or None,
                        "captured_at": utc_now(),
                    }
                    downloaded_now.append(entry)
                    print("  ok    %s -> %s" % (candidate.url, result.target_rel))
                else:
                    probed_now.append(
                        {
                            **common,
                            "content_type": result.content_type,
                            "probed_at": utc_now(),
                            "captured": False,
                            "reason": "HEAD observation was preserved; it was not replayed as GET",
                        }
                    )
                    if candidate.required:
                        failed_now.append(
                            {
                                "url": candidate.url,
                                "normalized_url": candidate.normalized_url,
                                "method": candidate.method,
                                "resource_type": candidate.resource_type,
                                "required": True,
                                "error": "Required resource was observed only with HEAD and was not replayed as GET",
                                "attempt_id": attempt_id,
                            }
                        )
                    print("  probe %s" % candidate.url)
            except Exception as exc:
                chain = exc.chain if isinstance(exc, UnsafeRedirectError) else []
                failure = {
                    "url": candidate.url,
                    "normalized_url": candidate.normalized_url,
                    "method": candidate.method,
                    "resource_type": candidate.resource_type,
                    "required": candidate.required,
                    "error": str(exc),
                    "redirects": chain,
                    "attempt_id": attempt_id,
                }
                if isinstance(exc, AccessBlockedError):
                    failure["access"] = exc.evidence
                failed_now.append(failure)
                print("  FAIL  %s (%s)" % (candidate.url, exc), file=sys.stderr)

    all_downloaded_by_url = {
        str(item.get("normalized_url") or _safe_normalized_url(item.get("url"))): item
        for item in manifest.get("downloaded", [])
        if isinstance(item, dict)
    }
    for entry in downloaded_now:
        all_downloaded_by_url[entry["normalized_url"]] = entry
    manifest["downloaded"] = sorted(
        all_downloaded_by_url.values(), key=lambda item: str(item.get("path") or "")
    )
    manifest["probed"] = dedupe_entries(
        list(manifest.get("probed") or []) + probed_now,
        ("normalized_url", "method", "status", "attempt_id"),
    )
    manifest["failed"] = list(manifest.get("failed") or []) + failed_now
    manifest["skipped_external"] = dedupe_entries(
        list(manifest.get("skipped_external") or []) + skipped_external,
        ("url", "reason", "source_graph"),
    )
    manifest["skipped_provider_assets"] = dedupe_entries(
        list(manifest.get("skipped_provider_assets") or []) + skipped_provider,
        ("url", "provider", "source_graph"),
    )
    manifest["skipped_other"] = dedupe_entries(
        list(manifest.get("skipped_other") or []) + skipped_other,
        ("url", "reason", "source_graph"),
    )

    # Keep Observed, Probed, and Captured as distinct metadata facts.
    downloaded_urls = {entry.get("normalized_url") for entry in manifest["downloaded"]}
    for item in manifest["metadata_references"]:
        normalized = _safe_normalized_url(item.get("url"))
        item["captured"] = normalized in downloaded_urls
        if item["captured"]:
            matched = next(
                entry for entry in manifest["downloaded"] if entry.get("normalized_url") == normalized
            )
            item["captured_path"] = matched.get("path")
            item["sha256"] = matched.get("sha256")
        item["states"] = (
            (["Observed"] if item.get("observed", True) else [])
            + (["Probed"] if item.get("probed") else [])
            + (["Captured"] if item.get("captured") else [])
        )

    # These maps are derived integrity indexes. Rebuild them from the complete
    # hash-verified download inventory so stale/manual entries cannot survive a
    # resume while acquisition/provenance history remains merged.
    route_map: Dict[str, Dict[str, Any]] = {}
    source_url_map: Dict[str, Dict[str, Any]] = {}
    route_conflicts: List[Dict[str, Any]] = []
    primary_entries: List[Tuple[Dict[str, Any], str, URLInfo, Dict[str, Any]]] = []
    for entry in manifest["downloaded"]:
        normalized = str(entry.get("normalized_url") or _safe_normalized_url(entry.get("url")))
        if not normalized:
            continue
        info = parse_http_url(normalized)
        map_value = {
            "local_path": entry.get("path"),
            "content_type": entry.get("content_type"),
            "source_url": normalized,
            "sha256": entry.get("sha256"),
        }
        source_url_map[normalized] = map_value
        direct_decision = policy.classify(
            info.normalized_url, entry.get("resource_type", "")
        )
        if (direct_decision["allowed"] and direct_decision["scope"] == "primary"
                and not str(entry.get("path", "")).startswith("_external/")):
            existing = route_map.get(info.request_target)
            if existing and existing.get("local_path") != map_value["local_path"]:
                route_conflicts.append({
                    "kind": "request_target_collision",
                    "request_target": info.request_target,
                    "source_urls": [existing.get("source_url"), normalized],
                })
            else:
                route_map[info.request_target] = map_value
            primary_entries.append((entry, normalized, info, map_value))

    # Redirect destinations are useful aliases only when they do not have a
    # directly captured identity of their own. Direct mappings always win.
    direct_targets = set(route_map)
    for entry, normalized, _info, map_value in primary_entries:
        aliases = [
            item.get("to")
            for item in entry.get("redirects", []) or []
            if isinstance(item, dict) and item.get("allowed") and item.get("to")
        ]
        if entry.get("final_url"):
            aliases.append(entry["final_url"])
        for alias in aliases:
            try:
                alias_info = parse_http_url(str(alias))
            except MirrorError:
                continue
            alias_decision = policy.classify(
                alias_info.normalized_url, entry.get("resource_type", "")
            )
            if not alias_decision["allowed"]:
                continue
            source_url_map.setdefault(alias_info.normalized_url, map_value)
            if alias_decision["scope"] != "primary":
                continue
            if alias_info.request_target in direct_targets:
                continue
            existing = route_map.get(alias_info.request_target)
            if existing and existing.get("local_path") != map_value["local_path"]:
                route_conflicts.append({
                    "kind": "request_target_collision",
                    "request_target": alias_info.request_target,
                    "source_urls": [existing.get("source_url"), normalized],
                })
            else:
                route_map[alias_info.request_target] = map_value
    manifest["route_map"] = route_map
    manifest["source_url_map"] = source_url_map

    attempt["downloaded"] = len(downloaded_now)
    attempt["probed"] = len(probed_now)
    attempt["failed"] += len(failed_now) + len(route_conflicts)
    attempt["integrity_errors"] += len(route_conflicts)
    required_failures = [item for item in failed_now if item.get("required")]
    attempt["required_failures"] += len(required_failures) + len(route_conflicts)

    if route_conflicts:
        for error in route_conflicts:
            manifest["failed"].append(
                {"attempt_id": attempt_id, "required": True, "error": error}
            )

    success = attempt["required_failures"] == 0 and attempt["integrity_errors"] == 0
    if success:
        generated = write_serve_artifacts(out_dir)
        manifest["generated_artifacts"] = _upsert_generated(
            list(manifest.get("generated_artifacts") or []), generated
        )
        for item in generated:
            provenance = {
                "path": item["path"],
                "kind": item["kind"],
                "sha256": item["sha256"],
                "phase": CONSTRUCTION_PHASE,
                "actor": ACTOR,
                "reason": "portable local serve contract",
            }
            prior_items = manifest["construction_provenance"]
            prior_items[:] = [old for old in prior_items if old.get("path") != item["path"]]
            prior_items.append(provenance)
        attempt["status"] = "complete_declared_acquisition"
        manifest["result"] = "complete_declared_acquisition"
        manifest["blocked_by_challenge"] = False
    else:
        attempt["status"] = "failed_required"
        blocked_by_challenge = any(
            isinstance(item.get("access"), dict)
            and item["access"].get("state") == "blocked_by_challenge"
            for item in failed_now
        )
        manifest["result"] = (
            "blocked_by_challenge" if blocked_by_challenge else "failed_required"
        )
        manifest["blocked_by_challenge"] = blocked_by_challenge
    attempt["finished_at"] = utc_now()
    manifest["attempts"].append(attempt)
    manifest["summary"] = _manifest_summary(manifest, attempt)
    manifest["updated_at"] = utc_now()
    manifest_path = os.path.join(out_dir, "mirror-manifest.json")
    atomic_write_json(manifest_path, manifest)

    if not success:
        print(
            "Mirror acquisition failed: %d required failure(s), %d integrity error(s)."
            % (attempt["required_failures"], attempt["integrity_errors"]),
            file=sys.stderr,
        )
        print("Failure manifest: %s" % manifest_path, file=sys.stderr)
        return 2

    print("\nMirror: %s" % out_dir)
    print("Manifest: %s" % manifest_path)
    print(
        "  captured now: %d   reused: %d   optional failures: %d"
        % (attempt["downloaded"], attempt["reused"], attempt["failed"])
    )
    print("Serve contract: %s" % os.path.join(out_dir, "serve-contract.json"))
    print("Next: python %s" % os.path.join(out_dir, "serve-local.py"))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("graphs", nargs="+", help="one or more v1.3 asset graph JSON files")
    parser.add_argument("--out", default="mirror")
    parser.add_argument(
        "--authorized",
        default="inspiration / non-commercial reference",
        help='Usage context recorded in the manifest. Defaults to non-commercial reference use; override to describe a specific engagement.',
    )
    parser.add_argument(
        "--force-document",
        action="store_true",
        help="Acquire root/HTML documents even when captured as identity-varying/personalized "
        "(e.g. Wix session tokens). Use ONLY for pages you have confirmed are public marketing "
        "pages with no per-user data. Every forced document is recorded in the manifest.",
    )
    parser.add_argument(
        "--allow-host",
        action="append",
        default=[],
        help="external host or host:port explicitly confirmed as licensed/authorized (repeatable)",
    )
    parser.add_argument(
        "--extra-urls",
        default=None,
        help="optional static URL inventory; use URL<TAB>resource_type or one JSON object per line",
    )
    parser.add_argument("--resume", action="store_true", help="merge into an existing v1.3 mirror after hash checks")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--delay", type=float, default=0.0, help="seconds before each request")
    parser.add_argument("--timeout", type=int, default=30)
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return run(args)
    except MirrorError as exc:
        print("ERROR: %s" % exc, file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("Interrupted; mirror was not completed.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    sys.exit(main())
