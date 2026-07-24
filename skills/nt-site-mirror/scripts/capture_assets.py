#!/usr/bin/env python3
"""Observe a page's runtime asset graph and access state without saving bodies.

The v1.3 graph records request method and replay safety, final navigation
identity, bounded settling, scroll coverage, metadata references, and service
worker/cache evidence.  It never submits forms, accepts consent, solves a
CAPTCHA, or clicks through an access control.

Only a later, authorization-gated ``mirror_assets.py`` run may acquire files.
This observer marks a request automatically eligible only when it is a
classified static GET/HEAD request; POSTs, telemetry, personalized data, and
unknown XHR/fetch traffic are never converted into GET downloads.

Usage:
    python capture_assets.py https://example.com [-o asset-graph.json]
        [--scroll-steps 12] [--step-wait 700] [--settle-max 5000]
        [--timeout 45000] [--mobile]
        [--allow-origin https://www.example.com] [--probe-metadata]

``--allow-origin`` applies only to top-level redirects.  External subresources
are observed and classified, not authorized for download.

Requires: pip install playwright && playwright install chromium
"""

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
import time
from urllib.parse import urljoin, urlsplit, urlunsplit

from browser_support import (
    bounded_settle,
    canonical_origin,
    detect_access_state,
    explore_scroll,
    extract_metadata_references,
    inspect_service_workers,
    navigation_origin_allowed,
    normalize_http_url,
    redirect_response_evidence,
    sanitize_url,
)


SCHEMA_VERSION = "1.3"

KNOWN_PROVIDERS = {
    "vimeo.com": "Vimeo", "player.vimeo.com": "Vimeo", "vimeocdn.com": "Vimeo",
    "youtube.com": "YouTube", "youtu.be": "YouTube", "ytimg.com": "YouTube",
    "googlevideo.com": "YouTube",
    "mux.com": "Mux", "litix.io": "Mux", "stream.mux.com": "Mux",
    "fonts.googleapis.com": "Google Fonts (openly licensed)",
    "fonts.gstatic.com": "Google Fonts (openly licensed)",
    "use.typekit.net": "Adobe Fonts (paid)", "p.typekit.net": "Adobe Fonts (paid)",
    "cloud.typography.com": "Hoefler&Co (paid)", "fast.fonts.net": "Monotype (paid)",
    "kit.fontawesome.com": "Font Awesome",
    "cdn.lottiefiles.com": "Lottie", "lottie.host": "Lottie",
    "cdn.rive.app": "Rive",
    "stream.cloudflare.com": "Cloudflare Stream",
    "wistia.com": "Wistia", "fast.wistia.net": "Wistia",
}

TELEMETRY_HOST_MARKERS = (
    "google-analytics.com", "googletagmanager.com", "doubleclick.net",
    "segment.io", "segment.com", "mixpanel.com", "hotjar.com",
    "sentry.io", "newrelic.com", "nr-data.net", "clarity.ms",
    "amplitude.com", "plausible.io", "fullstory.com", "facebook.net",
)
TELEMETRY_PATH_RE = re.compile(
    r"/(collect|analytics|telemetry|track|tracking|pixel|beacon|events?)(/|$)",
    re.IGNORECASE,
)
STATIC_EXTENSIONS = {
    ".avif", ".bin", ".css", ".drc", ".eot", ".exr", ".gif", ".glb",
    ".gltf", ".hdr", ".ico", ".jpeg", ".jpg", ".js", ".jxl", ".ktx",
    ".ktx2", ".m4a", ".mjs", ".mp3", ".mp4", ".ogg", ".otf", ".png",
    ".map", ".pdf", ".svg", ".ttf", ".txt", ".wasm", ".webm",
    ".webmanifest", ".webp", ".woff", ".woff2", ".vtt", ".xml",
}
MANIFEST_PATH_MARKERS = (
    "manifest.webmanifest", "asset-manifest.json", "build-manifest.json",
    "/.vite/manifest.json", "/manifest.json",
)
STATIC_RESOURCE_TYPES = {
    "document", "stylesheet", "image", "media", "font", "script",
    "texttrack", "manifest",
}
NON_REPLAYABLE_TYPES = {"websocket", "eventsource", "ping", "preflight"}


def atomic_write_json(path, value):
    directory = os.path.dirname(os.path.abspath(path))
    os.makedirs(directory, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=".ntsm-capture-", dir=directory)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, indent=2, sort_keys=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except Exception:
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise


def provider_for(host):
    host = (host or "").lower().rstrip(".")
    for key, name in KNOWN_PROVIDERS.items():
        if host == key or host.endswith("." + key):
            return name
    return None


def _extension(url):
    path = urlsplit(url).path.lower()
    name = path.rsplit("/", 1)[-1]
    if "." not in name:
        return ""
    return "." + name.rsplit(".", 1)[-1]


def _telemetry(url, include_path=True):
    parts = urlsplit(url)
    host = (parts.hostname or "").lower()
    known_host = any(host == marker or host.endswith("." + marker)
                     for marker in TELEMETRY_HOST_MARKERS)
    return known_host or (include_path and
                          TELEMETRY_PATH_RE.search(parts.path or "") is not None)


def classify_request(method, resource_type, url, content_type="",
                     response_headers=None, url_redacted=False):
    """Classify replay safety using observed facts, never stored graph flags."""
    method = (method or "UNKNOWN").upper()
    resource_type = (resource_type or "unknown").lower()
    content_type = (content_type or "").split(";", 1)[0].strip().lower()
    response_headers = {str(k).lower(): str(v) for k, v in
                        (response_headers or {}).items()}
    path = urlsplit(url).path.lower()
    ext = _extension(url)

    privacy_signals = []
    cache_control = response_headers.get("cache-control", "").lower()
    vary = response_headers.get("vary", "").lower()
    if "private" in cache_control:
        privacy_signals.append("cache_control_private")
    if "set-cookie" in response_headers:
        privacy_signals.append("sets_cookie")
    if "cookie" in vary or "authorization" in vary:
        privacy_signals.append("varies_by_identity")
    strongly_personalized = bool(
        {"cache_control_private", "varies_by_identity"}.intersection(privacy_signals)
    )

    if method not in ("GET", "HEAD"):
        request_class, data_type = "non_replayable", "request_body_or_mutation"
        automatic, reason = False, "method_%s_must_not_be_replayed_as_get" % method.lower()
    elif resource_type in NON_REPLAYABLE_TYPES:
        request_class, data_type = "non_replayable", resource_type
        automatic, reason = False, "stream_or_control_request"
    elif _telemetry(url, include_path=resource_type != "document"):
        request_class, data_type = "telemetry", "telemetry"
        automatic, reason = False, "telemetry_is_not_part_of_local_fidelity"
    elif url_redacted:
        request_class, data_type = "personalized_data", "credential_bearing_url"
        automatic, reason = False, "sensitive_query_value_was_redacted"
    elif strongly_personalized:
        request_class, data_type = "personalized_data", "identity_varying_response"
        automatic, reason = False, "response_varies_by_identity_or_is_private"
    elif resource_type == "document":
        request_class, data_type = "document", "html_document"
        automatic, reason = True, "classified_static_document_get_head"
    elif resource_type in STATIC_RESOURCE_TYPES:
        mapping = {
            "stylesheet": "stylesheet", "image": "image", "media": "media",
            "font": "font", "script": "script", "texttrack": "text_track",
            "manifest": "web_manifest",
        }
        request_class = "static"
        data_type = mapping.get(resource_type, "static_asset")
        automatic, reason = True, "classified_static_get_head"
    elif resource_type in ("xhr", "fetch"):
        manifest_like = any(marker in path for marker in MANIFEST_PATH_MARKERS)
        static_by_extension = ext in STATIC_EXTENSIONS
        static_by_content_type = (
            content_type.startswith(("image/", "font/", "audio/", "video/", "model/")) or
            content_type in ("application/wasm", "text/css", "application/javascript",
                             "text/javascript")
        )
        if privacy_signals:
            request_class, data_type = "personalized_data", "api_data"
            automatic, reason = False, "personalized_or_api_response"
        elif static_by_extension or manifest_like or static_by_content_type:
            request_class = "static"
            data_type = "web_manifest" if manifest_like else "static_asset"
            automatic, reason = True, "xhr_fetch_has_classified_static_identity"
        elif re.search(
            r"/(api|graphql|account|profile|session|user|me)(/|$)", path
        ):
            request_class, data_type = "personalized_data", "api_data"
            automatic, reason = False, "personalized_or_api_response"
        else:
            request_class, data_type = "data_api", "unknown_xhr_fetch"
            automatic, reason = False, "unknown_xhr_fetch_is_not_static"
    elif ext in STATIC_EXTENSIONS:
        request_class, data_type = "static", "static_asset"
        automatic, reason = True, "classified_static_extension_get_head"
    elif content_type.startswith(("image/", "font/", "audio/", "video/")):
        request_class, data_type = "static", content_type.split("/", 1)[0]
        automatic, reason = True, "classified_static_content_type_get_head"
    elif content_type in ("application/wasm", "text/css", "application/javascript",
                          "text/javascript"):
        request_class, data_type = "static", "static_asset"
        automatic, reason = True, "classified_static_content_type_get_head"
    else:
        request_class, data_type = "unknown", "unknown"
        automatic, reason = False, "insufficient_evidence_of_static_resource"

    return {
        "request_class": request_class,
        "data_type": data_type,
        "privacy_signals": privacy_signals,
        "acquisition": {"automatic": automatic, "reason": reason},
    }


def _safe_error(exc):
    text = str(exc).split("\n")[0]
    text = re.sub(
        r"https?://[^\s'\"]+",
        lambda match: sanitize_url(match.group(0).rstrip(".,)"))["url"],
        text,
    )
    return "%s: %s" % (type(exc).__name__, text[:500])


def _property(value):
    """Read a Playwright property that may be callable across versions."""
    return value() if callable(value) else value


class NetworkRecorder:
    """Context-level request recorder; includes page, worker, and SW traffic."""

    def __init__(self, phase):
        self.phase = phase
        self.records = {}
        self.errors = []

    def _key(self, request):
        return (request.method.upper(), request.url, request.resource_type)

    def _ensure(self, request):
        key = self._key(request)
        if key not in self.records:
            safe = sanitize_url(request.url)
            classification = classify_request(
                request.method, request.resource_type, request.url,
                url_redacted=safe["redacted"],
            )
            self.records[key] = {
                "url": safe["url"],
                "url_redacted": safe["redacted"],
                "sensitive_query_keys": safe["sensitive_query_keys"],
                "request_identity": hashlib.sha256(
                    (request.method.upper() + "\n" + safe["url"]).encode("utf-8")
                ).hexdigest(),
                "method": request.method.upper(),
                "resource_type": request.resource_type,
                "data_type": classification["data_type"],
                "request_class": classification["request_class"],
                "privacy_signals": classification["privacy_signals"],
                "acquisition": classification["acquisition"],
                "status": None,
                "status_history": [],
                "content_type": "",
                "content_length": None,
                "provider": provider_for(urlsplit(request.url).hostname),
                "from_service_worker": False,
                "first_seen": self.phase["value"],
                "phases": [self.phase["value"]],
                "occurrences": 0,
                "observed": True,
                "probed": False,
                "captured": False,
                "failure": None,
            }
        return self.records[key]

    def on_request(self, request):
        try:
            record = self._ensure(request)
            record["occurrences"] += 1
            if self.phase["value"] not in record["phases"]:
                record["phases"].append(self.phase["value"])
        except Exception as exc:
            self.errors.append("request: " + _safe_error(exc))

    def on_response(self, response):
        try:
            request = response.request
            record = self._ensure(request)
            headers = response.headers or {}
            content_type = headers.get("content-type", "")
            record["status"] = response.status
            if response.status not in record["status_history"]:
                record["status_history"].append(response.status)
            record["content_type"] = content_type
            length = headers.get("content-length")
            try:
                record["content_length"] = int(length) if length is not None else None
            except ValueError:
                record["content_length"] = None
            from_sw = getattr(response, "from_service_worker", False)
            record["from_service_worker"] = (
                record.get("from_service_worker", False) or bool(_property(from_sw))
            )
            classification = classify_request(
                request.method, request.resource_type, request.url,
                content_type=content_type, response_headers=headers,
                url_redacted=record["url_redacted"],
            )
            combined_privacy = sorted(set(
                record.get("privacy_signals", []) + classification["privacy_signals"]
            ))
            prior_personalized = record.get("request_class") == "personalized_data"
            current_personalized = classification["request_class"] == "personalized_data"
            if prior_personalized or current_personalized:
                classification["request_class"] = "personalized_data"
                if prior_personalized and not current_personalized:
                    classification["data_type"] = record["data_type"]
                classification["acquisition"] = {
                    "automatic": False,
                    "reason": "personalized_evidence_observed_in_one_or_more_responses",
                }
            record.update({
                "data_type": classification["data_type"],
                "request_class": classification["request_class"],
                "privacy_signals": combined_privacy,
                "acquisition": classification["acquisition"],
                "probed": True,
            })
        except Exception as exc:
            self.errors.append("response: " + _safe_error(exc))

    def on_request_failed(self, request):
        try:
            record = self._ensure(request)
            failure = _property(getattr(request, "failure", None))
            record["failure"] = str(failure or "request_failed")[:500]
        except Exception as exc:
            self.errors.append("requestfailed: " + _safe_error(exc))

    def finalize(self, final_origin):
        output = []
        for record in self.records.values():
            record = dict(record)
            current_origin = canonical_origin(record["url"])
            # same_origin is always recomputed against the canonical final page
            # origin.  A persisted capture flag is never an authorization fact.
            record["recomputed_origin"] = current_origin
            record["same_origin"] = bool(final_origin and current_origin == final_origin)
            status = record.get("status")
            successful_response = (
                isinstance(status, int) and 200 <= status < 300
            )
            record["required_for_baseline"] = bool(
                record["same_origin"]
                and record.get("method") == "GET"
                and successful_response
                and record.get("acquisition", {}).get("automatic") is True
            )
            if record["required_for_baseline"]:
                record["requirement_reason"] = (
                    "observed successful same-origin static GET in declared capture coverage"
                )
            record["phases"] = sorted(record["phases"])
            output.append(record)
        return sorted(output, key=lambda item: (
            not item["same_origin"], item["url"], item["method"],
            item["resource_type"],
        ))


class NavigationTracker:
    """Track every main-frame navigation, including late client redirects."""

    def __init__(self, page, phase, requested_origin="", allowed_origins=(),
                 unauthorized_redirects=None):
        self.page = page
        self.phase = phase
        self.events = []
        self.requested_origin = requested_origin
        self.allowed_origins = tuple(allowed_origins or ())
        self.unauthorized_redirects = (
            unauthorized_redirects if unauthorized_redirects is not None else []
        )
        page.on("response", self.on_response)

    def on_response(self, response):
        try:
            request = response.request
            if not request.is_navigation_request() or request.frame != self.page.main_frame:
                return
            redirect = redirect_response_evidence(
                response, self.requested_origin, self.allowed_origins
            )
            if (redirect and not redirect["authorized"]
                    and redirect not in self.unauthorized_redirects):
                self.unauthorized_redirects.append(redirect)
            redirected_from = _property(getattr(request, "redirected_from", None))
            self.events.append({
                "url": request.url,
                "status": response.status,
                "phase": self.phase["value"],
                "redirected_from": redirected_from.url if redirected_from else None,
                "request": request,
            })
        except Exception:
            return

    def snapshot(self, requested_url, navigation_error, unauthorized_redirects):
        safe_requested = sanitize_url(requested_url)["url"]
        safe_final = sanitize_url(getattr(self.page, "url", "") or requested_url)["url"]
        events = []
        redirects = []
        for index, event in enumerate(self.events):
            if event["redirected_from"]:
                kind = "http_redirect_target"
                status = None
                try:
                    previous = _property(getattr(event["request"], "redirected_from", None))
                    previous_response = previous.response() if previous else None
                    status = previous_response.status if previous_response else None
                except Exception:
                    pass
                redirects.append({
                    "from": sanitize_url(event["redirected_from"])["url"],
                    "to": sanitize_url(event["url"])["url"],
                    "status": status,
                })
            elif index == 0:
                kind = "initial"
            else:
                kind = "client_navigation"
            events.append({
                "url": sanitize_url(event["url"])["url"],
                "status": event["status"],
                "phase": event["phase"],
                "kind": kind,
            })

        if unauthorized_redirects:
            redirects.extend(unauthorized_redirects)
        initial_status = events[0]["status"] if events else None
        final_event = next(
            (event for event in reversed(events) if event["url"] == safe_final),
            events[-1] if events else None,
        )
        return {
            "requested_url": safe_requested,
            "initial_url": events[0]["url"] if events else safe_requested,
            "initial_status": initial_status,
            "final_url": safe_final,
            "final_status": final_event["status"] if final_event else None,
            "redirects": redirects,
            "navigation_events": events,
            "navigation_error": navigation_error,
            "unauthorized_redirects": unauthorized_redirects,
        }


def _redirect_chain(response):
    if response is None:
        return []
    try:
        requests = []
        request = response.request
        while request is not None:
            requests.append(request)
            request = _property(getattr(request, "redirected_from", None))
        requests.reverse()
        redirects = []
        for index, request in enumerate(requests[:-1]):
            prior_response = request.response()
            redirects.append({
                "from": sanitize_url(request.url)["url"],
                "to": sanitize_url(requests[index + 1].url)["url"],
                "status": prior_response.status if prior_response else None,
            })
        return redirects
    except Exception:
        return []


def _navigation_record(requested_url, page, response, navigation_error,
                       unauthorized_redirects, tracker=None):
    if tracker is not None:
        return tracker.snapshot(requested_url, navigation_error, unauthorized_redirects)
    redirects = _redirect_chain(response)
    if unauthorized_redirects:
        redirects.extend(unauthorized_redirects)
    final_url = getattr(page, "url", "") or requested_url
    safe_requested = sanitize_url(requested_url)["url"]
    safe_final = sanitize_url(final_url)["url"]
    final_status = response.status if response is not None else None
    initial_status = redirects[0].get("status") if redirects else final_status
    initial_url = redirects[0].get("from") if redirects else safe_requested
    return {
        "requested_url": safe_requested,
        "initial_url": initial_url,
        "initial_status": initial_status,
        "final_url": safe_final,
        "final_status": final_status,
        "redirects": redirects,
        "navigation_error": navigation_error,
        "unauthorized_redirects": unauthorized_redirects,
    }


def _reject_unauthorized_final_navigation(navigation, requested_origin,
                                          allowed_origins):
    """Fail closed when Chromium follows a redirect without re-routing it.

    Playwright may deliver an HTTP redirect entirely inside a continued route,
    so the route guard is not the only enforcement point.  This post-navigation
    check reclassifies the actual final destination and rejects the result.
    """
    final_url = navigation.get("final_url", "")
    if navigation_origin_allowed(final_url, requested_origin, allowed_origins):
        return navigation
    if not navigation.get("unauthorized_redirects"):
        redirects = navigation.get("redirects", [])
        source = redirects[-1].get("from") if redirects else navigation.get("requested_url")
        navigation["unauthorized_redirects"] = [{
            "from": source,
            "to": final_url,
            "status": redirects[-1].get("status") if redirects else None,
            "authorized": False,
        }]
    return navigation


def _install_navigation_guard(page, requested_origin, allowed_origins,
                              unauthorized_redirects):
    """Abort an unapproved main-frame destination before its response loads."""
    def guard(route):
        request = route.request
        try:
            is_navigation = request.is_navigation_request()
            is_main = request.frame == page.main_frame
        except Exception:
            is_navigation, is_main = False, False
        if is_navigation and is_main and not navigation_origin_allowed(
            request.url, requested_origin, allowed_origins
        ):
            previous = _property(getattr(request, "redirected_from", None))
            redirect_status = None
            if previous is not None:
                try:
                    previous_response = previous.response()
                    redirect_status = previous_response.status if previous_response else None
                except Exception:
                    pass
            unauthorized_redirects.append({
                "from": sanitize_url(previous.url if previous else page.url)["url"],
                "to": sanitize_url(request.url)["url"],
                "status": redirect_status,
                "authorized": False,
            })
            route.abort("blockedbyclient")
            return
        route.continue_()
    page.route("**/*", guard)
    return guard


def _routes_from_page(page, final_url):
    final_origin = canonical_origin(final_url)
    try:
        hrefs = page.eval_on_selector_all(
            "a[href]", "els => els.map(el => el.href || el.getAttribute('href'))"
        )
    except Exception:
        return []
    routes = {}
    for value in hrefs or []:
        resolved = normalize_http_url(value, final_url)
        if not resolved or canonical_origin(resolved) != final_origin:
            continue
        safe = sanitize_url(resolved)
        parts = urlsplit(safe["url"])
        path = parts.path or "/"
        if parts.query:
            path += "?" + parts.query
        routes[safe["url"]] = {
            "url": safe["url"],
            "path": path,
            "source": "anchor",
            "url_redacted": safe["redacted"],
        }
    return sorted(routes.values(), key=lambda item: item["url"])


def _probe_metadata(context, references, final_origin, timeout_ms):
    """Perform optional same-origin HEAD probes; never follow a redirect."""
    for reference in references:
        prior_probe = reference.get("probe") or {}
        manual_redirect = prior_probe.get("skipped_reason") == "manual_redirect_not_followed"
        if (reference["probed"] and not manual_redirect) or reference["url_redacted"]:
            continue
        if canonical_origin(reference["url"]) != final_origin:
            continue
        try:
            response = context.request.fetch(
                reference["url"], method="HEAD", max_redirects=0,
                fail_on_status_code=False, timeout=timeout_ms,
            )
            headers = response.headers or {}
            final_url = sanitize_url(response.url)["url"]
            location = headers.get("location")
            redirect_target = None
            redirect_authorized = None
            if location:
                redirect_target = sanitize_url(urljoin(reference["url"], location))["url"]
                redirect_authorized = canonical_origin(redirect_target) == final_origin
            head_probe = {
                "method": "HEAD",
                "metadata_only": True,
                "status": response.status,
                "content_type": headers.get("content-type", ""),
                "final_url": final_url,
                "redirect_target": redirect_target,
                "redirect_authorized": redirect_authorized,
            }
            reference.update({
                "probed": True,
                "states": ["Observed", "Probed"],
                "probe": head_probe,
            })
            if prior_probe:
                reference["probes"] = [prior_probe, head_probe]
            try:
                response.dispose()
            except Exception:
                pass
        except Exception as exc:
            reference["probe"] = {
                "method": "HEAD", "metadata_only": True,
                "error": _safe_error(exc),
            }
    return references


def _metadata_with_network_evidence(references, request_records, pass_name):
    by_url = {}
    for record in request_records:
        by_url.setdefault(record["url"], []).append(record)
    output = []
    for reference in references:
        reference = dict(reference)
        matches = by_url.get(reference["url"], [])
        successful = next((item for item in matches if item.get("status") is not None), None)
        if successful and not reference.get("probed"):
            reference["probed"] = True
            reference["states"] = ["Observed", "Probed"]
            reference["probe"] = {
                "method": successful["method"],
                "metadata_only": False,
                "status": successful["status"],
                "content_type": successful["content_type"],
                "final_url": successful["url"],
            }
        reference["passes"] = [pass_name]
        output.append(reference)
    return output


def _merge_metadata(items):
    merged = {}
    for item in items:
        key = (item["kind"], item["url"], item["source"])
        if key not in merged:
            merged[key] = dict(item)
            continue
        current = merged[key]
        current["observed"] = current["observed"] or item["observed"]
        current["probed"] = current["probed"] or item["probed"]
        current["captured"] = current["captured"] or item["captured"]
        current["states"] = ["Observed"] + (["Probed"] if current["probed"] else [])
        if not current.get("probe") and item.get("probe"):
            current["probe"] = item["probe"]
        current["passes"] = sorted(set(current.get("passes", []) + item.get("passes", [])))
    return sorted(merged.values(), key=lambda item: (item["kind"], item["url"]))


def _service_worker_relevant(evidence, recorder):
    return bool(
        evidence.get("controller") or evidence.get("registrations") or
        evidence.get("cache_names") or evidence.get("precache_resources") or
        any(record.get("from_service_worker") for record in recorder.records.values())
    )


def _new_context(browser, viewport, service_workers):
    try:
        return browser.new_context(viewport=viewport, service_workers=service_workers), True
    except TypeError:
        # Older Playwright: do not pretend a blocked probe happened.
        return browser.new_context(viewport=viewport), False


def _close_guarded(page, context, guard):
    try:
        page.unroute("**/*", guard)
    except Exception:
        pass
    page.close()
    context.close()


def _bypassed_service_worker_probe(browser, recorder, phase, requested_url,
                                   requested_origin, allowed_origins, viewport,
                                   timeout_ms, settle_max):
    context, mode_supported = _new_context(browser, viewport, "block")
    if not mode_supported:
        context.close()
        return {"attempted": False, "reason": "playwright_service_workers_block_unsupported"}
    context.on("request", recorder.on_request)
    context.on("response", recorder.on_response)
    context.on("requestfailed", recorder.on_request_failed)
    page = context.new_page()
    unauthorized = []
    tracker = NavigationTracker(
        page, phase, requested_origin, allowed_origins, unauthorized
    )
    guard = _install_navigation_guard(page, requested_origin, allowed_origins, unauthorized)
    phase["value"] = phase["value"].split(":", 1)[0] + ":service-worker-bypassed"
    response = None
    nav_error = None
    try:
        response = page.goto(requested_url, wait_until="domcontentloaded", timeout=timeout_ms)
    except Exception as exc:
        nav_error = _safe_error(exc)
    settle = bounded_settle(page, max_ms=settle_max)
    navigation = _navigation_record(
        requested_url, page, response, nav_error, unauthorized, tracker
    )
    navigation = _reject_unauthorized_final_navigation(
        navigation, requested_origin, allowed_origins
    )
    unauthorized = navigation["unauthorized_redirects"]
    access = ({"state": "blocked_by_unauthorized_redirect", "blocked": True,
               "title": "", "final_url": navigation["final_url"],
               "evidence": {"unauthorized_redirects": unauthorized}}
              if unauthorized else detect_access_state(
                  page, navigation["final_status"], navigation["final_url"]
              ))
    navigation["title"] = access.get("title", "")
    navigation["access"] = access
    workers = inspect_service_workers(page)
    # Re-snapshot after inspection so a delayed navigation cannot slip between
    # the access check and page close.
    navigation = _navigation_record(
        requested_url, page, response, nav_error, unauthorized, tracker
    )
    navigation = _reject_unauthorized_final_navigation(
        navigation, requested_origin, allowed_origins
    )
    unauthorized = navigation["unauthorized_redirects"]
    access = ({"state": "blocked_by_unauthorized_redirect", "blocked": True,
               "title": "", "final_url": navigation["final_url"],
               "evidence": {"unauthorized_redirects": unauthorized}}
              if unauthorized else detect_access_state(
                  page, navigation["final_status"], navigation["final_url"]
              ))
    navigation["title"] = access.get("title", "")
    navigation["access"] = access
    _close_guarded(page, context, guard)
    return {
        "attempted": True,
        "mode": "fresh_context_service_workers_blocked",
        "navigation": navigation,
        "settle": settle,
        "access": access,
        "service_worker": workers,
    }


def _capture_pass(browser, recorder, phase, requested_url, requested_origin,
                  allowed_origins, pass_name, viewport, args):
    context, mode_supported = _new_context(browser, viewport, "allow")
    context.on("request", recorder.on_request)
    context.on("response", recorder.on_response)
    context.on("requestfailed", recorder.on_request_failed)
    page = context.new_page()
    unauthorized = []
    tracker = NavigationTracker(
        page, phase, requested_origin, allowed_origins, unauthorized
    )
    guard = _install_navigation_guard(page, requested_origin, allowed_origins, unauthorized)
    phase["value"] = pass_name + ":load"
    response = None
    nav_error = None
    try:
        response = page.goto(requested_url, wait_until="domcontentloaded", timeout=args.timeout)
    except Exception as exc:
        nav_error = _safe_error(exc)

    settle = bounded_settle(page, max_ms=args.settle_max)
    navigation = _navigation_record(
        requested_url, page, response, nav_error, unauthorized, tracker
    )
    navigation = _reject_unauthorized_final_navigation(
        navigation, requested_origin, allowed_origins
    )
    unauthorized = navigation["unauthorized_redirects"]
    if unauthorized:
        access = {
            "state": "blocked_by_unauthorized_redirect", "blocked": True,
            "title": "", "final_url": navigation["final_url"],
            "evidence": {"unauthorized_redirects": unauthorized},
        }
    elif nav_error:
        access = {
            "state": "navigation_error", "blocked": True,
            "title": "", "final_url": navigation["final_url"],
            "evidence": {"navigation_error": nav_error},
        }
    else:
        access = detect_access_state(
            page, navigation["final_status"], navigation["final_url"]
        )
    navigation["title"] = access.get("title", "")
    navigation["access"] = access

    result = {
        "viewport": pass_name,
        "size": viewport,
        "fresh_isolated_context": True,
        "service_worker_mode": "allow" if mode_supported else "default_unsupported",
        "navigation": navigation,
        "settle": settle,
        "scroll": {"mechanism": "not_exercised", "reason": access["state"]},
        "service_worker": {},
        "service_worker_validation": {"required": False},
        "route_inventory": [],
        "metadata_references": [],
    }

    if access["blocked"]:
        result["service_worker"] = inspect_service_workers(page)
        _close_guarded(page, context, guard)
        return result

    phase["value"] = pass_name + ":scroll"
    result["scroll"] = explore_scroll(
        page, steps=args.scroll_steps, wait_ms=args.step_wait
    )
    result["post_scroll_settle"] = bounded_settle(page, max_ms=args.settle_max)
    navigation = _navigation_record(
        requested_url, page, response, nav_error, unauthorized, tracker
    )
    navigation = _reject_unauthorized_final_navigation(
        navigation, requested_origin, allowed_origins
    )
    unauthorized = navigation["unauthorized_redirects"]
    if unauthorized:
        post_access = {
            "state": "blocked_by_unauthorized_redirect", "blocked": True,
            "title": "", "final_url": navigation["final_url"],
            "evidence": {"unauthorized_redirects": unauthorized},
        }
    else:
        post_access = detect_access_state(
            page, navigation["final_status"], navigation["final_url"]
        )
    navigation["title"] = post_access.get("title", "")
    navigation["access"] = post_access
    result["navigation"] = navigation
    result["post_scroll_access"] = post_access
    if post_access["blocked"]:
        result["service_worker"] = inspect_service_workers(page)
        _close_guarded(page, context, guard)
        return result

    final_url = navigation["final_url"]
    result["route_inventory"] = _routes_from_page(page, final_url)
    phase["value"] = pass_name + ":metadata"
    references = extract_metadata_references(page, include_manifest_icons=True)
    if args.probe_metadata:
        references = _probe_metadata(
            context, references, canonical_origin(final_url), args.timeout
        )
    result["service_worker"] = inspect_service_workers(page)

    # Metadata work can itself span a delayed client navigation.  Re-snapshot
    # before accepting the pass so the full-lifetime origin guard is binding.
    navigation = _navigation_record(
        requested_url, page, response, nav_error, unauthorized, tracker
    )
    navigation = _reject_unauthorized_final_navigation(
        navigation, requested_origin, allowed_origins
    )
    unauthorized = navigation["unauthorized_redirects"]
    if unauthorized:
        metadata_access = {
            "state": "blocked_by_unauthorized_redirect", "blocked": True,
            "title": "", "final_url": navigation["final_url"],
            "evidence": {"unauthorized_redirects": unauthorized},
        }
    else:
        metadata_access = detect_access_state(
            page, navigation["final_status"], navigation["final_url"]
        )
    navigation["title"] = metadata_access.get("title", "")
    navigation["access"] = metadata_access
    result["navigation"] = navigation
    result["post_metadata_access"] = metadata_access
    if metadata_access["blocked"]:
        provisional = recorder.finalize(canonical_origin(final_url))
        result["metadata_references"] = _metadata_with_network_evidence(
            references, provisional, pass_name
        )
        _close_guarded(page, context, guard)
        return result

    if _service_worker_relevant(result["service_worker"], recorder):
        result["service_worker_validation"]["required"] = True
        if result["service_worker"].get("controller"):
            controlled = {
                "attempted": True,
                "mode": "observed_existing_controller_in_fresh_context",
                "navigation": dict(result["navigation"]),
                "settle": result.get("post_scroll_settle", settle),
                "access": metadata_access,
                "service_worker": result["service_worker"],
            }
        else:
            phase["value"] = pass_name + ":service-worker-controlled-reload"
            reload_response = None
            reload_error = None
            try:
                reload_response = page.reload(
                    wait_until="domcontentloaded", timeout=args.timeout
                )
            except Exception as exc:
                reload_error = _safe_error(exc)
            reload_settle = bounded_settle(page, max_ms=args.settle_max)
            reload_navigation = _navigation_record(
                requested_url, page, reload_response, reload_error, unauthorized, tracker
            )
            reload_navigation = _reject_unauthorized_final_navigation(
                reload_navigation, requested_origin, allowed_origins
            )
            if reload_navigation["unauthorized_redirects"]:
                reload_access = {
                    "state": "blocked_by_unauthorized_redirect", "blocked": True,
                    "title": "", "final_url": reload_navigation["final_url"],
                    "evidence": {"unauthorized_redirects":
                                 reload_navigation["unauthorized_redirects"]},
                }
            else:
                reload_access = detect_access_state(
                    page, reload_navigation["final_status"], reload_navigation["final_url"]
                )
            reload_navigation["title"] = reload_access.get("title", "")
            reload_navigation["access"] = reload_access
            controlled = {
                "attempted": True,
                "mode": "same_isolated_context_controlled_reload",
                "navigation": reload_navigation,
                "settle": reload_settle,
                "access": reload_access,
                "service_worker": inspect_service_workers(page),
            }
        result["service_worker_validation"]["controlled"] = controlled
        result["service_worker_validation"]["bypassed"] = _bypassed_service_worker_probe(
            browser, recorder, phase, requested_url, requested_origin, allowed_origins,
            viewport, args.timeout, args.settle_max,
        )

    # The origin guard remains active while SW probes run.  Derive the pass's
    # final URL/status from the last main-frame navigation, not the stale goto
    # response, and surface any delayed blocked destination.
    final_navigation = _navigation_record(
        requested_url, page, response, nav_error, unauthorized, tracker
    )
    final_navigation = _reject_unauthorized_final_navigation(
        final_navigation, requested_origin, allowed_origins
    )
    if final_navigation["unauthorized_redirects"]:
        final_access = {
            "state": "blocked_by_unauthorized_redirect", "blocked": True,
            "title": "", "final_url": final_navigation["final_url"],
            "evidence": {"unauthorized_redirects":
                         final_navigation["unauthorized_redirects"]},
        }
    else:
        final_access = detect_access_state(
            page, final_navigation["final_status"], final_navigation["final_url"]
        )
    final_navigation["title"] = final_access.get("title", "")
    final_navigation["access"] = final_access
    result["navigation"] = final_navigation
    result["final_access"] = final_access
    final_url = final_navigation["final_url"]

    # Add network evidence after manifest fetches and optional probes occurred.
    provisional = recorder.finalize(canonical_origin(final_url))
    result["metadata_references"] = _metadata_with_network_evidence(
        references, provisional, pass_name
    )
    _close_guarded(page, context, guard)
    return result


def _overall_access(passes):
    states = []
    for capture_pass in passes:
        states.append(capture_pass["navigation"]["access"])
        if capture_pass.get("post_scroll_access"):
            states.append(capture_pass["post_scroll_access"])
        validation = capture_pass.get("service_worker_validation", {})
        for key in ("controlled", "bypassed"):
            probe = validation.get(key, {})
            if probe.get("attempted") and probe.get("access"):
                states.append(probe["access"])
    blocked = next((state for state in states if state.get("blocked")), None)
    noteworthy = next((state for state in states if state.get("state") != "ok"), None)
    return blocked or noteworthy or {"state": "ok", "blocked": False, "evidence": {}}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("url")
    parser.add_argument("-o", "--out", default="asset-graph.json")
    parser.add_argument("--scroll-steps", type=int, default=12)
    parser.add_argument("--step-wait", type=int, default=700,
                        help="milliseconds between scroll steps")
    parser.add_argument("--settle-max", type=int, default=5000,
                        help="maximum milliseconds for each reported DOM settle")
    parser.add_argument("--timeout", type=int, default=45000,
                        help="navigation and metadata-probe timeout milliseconds")
    parser.add_argument("--mobile", action="store_true",
                        help="also capture a mobile-viewport pass")
    parser.add_argument("--allow-origin", action="append", default=[],
                        help="explicitly allow a top-level redirect origin (repeatable)")
    parser.add_argument("--probe-metadata", action="store_true",
                        help="HEAD-probe unrequested same-origin metadata references; never follows redirects")
    args = parser.parse_args(argv)

    if args.scroll_steps < 0 or args.step_wait < 0 or args.settle_max < 0:
        parser.error("scroll and settle values must be non-negative")
    if args.timeout < 1:
        parser.error("timeout must be positive")

    requested_origin = canonical_origin(args.url)
    if not requested_origin:
        parser.error("url must be an absolute http:// or https:// URL")
    allowed_origins = []
    for value in args.allow_origin:
        origin = canonical_origin(value)
        if not origin:
            parser.error("invalid --allow-origin: %s" % value)
        allowed_origins.append(origin)

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("playwright not installed. Run: pip install playwright && playwright install chromium",
              file=sys.stderr)
        return 2

    phase = {"value": "init"}
    recorder = NetworkRecorder(phase)
    viewports = [("desktop", {"width": 1440, "height": 900})]
    if args.mobile:
        viewports.append(("mobile", {"width": 390, "height": 844}))

    passes = []
    started_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            try:
                for pass_name, viewport in viewports:
                    passes.append(_capture_pass(
                        browser, recorder, phase, args.url, requested_origin,
                        allowed_origins, pass_name, viewport, args,
                    ))
            finally:
                browser.close()
    except Exception as exc:
        # Still emit a diagnostic graph.  A launch/runtime failure is not a
        # partially successful capture.
        passes.append({
            "viewport": "capture-runtime", "size": None,
            "fresh_isolated_context": False,
            "navigation": {
                "requested_url": sanitize_url(args.url)["url"],
                "initial_url": sanitize_url(args.url)["url"],
                "initial_status": None, "final_url": sanitize_url(args.url)["url"],
                "final_status": None, "redirects": [],
                "navigation_error": _safe_error(exc), "unauthorized_redirects": [],
                "title": "",
                "access": {"state": "capture_runtime_error", "blocked": True,
                           "evidence": {"runtime_error": _safe_error(exc)}},
            },
            "settle": None, "scroll": {"mechanism": "not_exercised"},
            "service_worker": {}, "service_worker_validation": {"required": False},
            "route_inventory": [], "metadata_references": [],
        })

    primary_navigation = passes[0]["navigation"]
    final_url = primary_navigation.get("final_url") or sanitize_url(args.url)["url"]
    final_origin = canonical_origin(final_url) or requested_origin
    requests = recorder.finalize(final_origin)
    route_map = {}
    metadata = []
    for capture_pass in passes:
        for route in capture_pass.get("route_inventory", []):
            route_map[route["url"]] = route
        metadata.extend(capture_pass.get("metadata_references", []))
    routes = sorted(route_map.values(), key=lambda item: item["url"])
    metadata = _merge_metadata(metadata)
    overall_access = _overall_access(passes)

    by_type = {}
    by_class = {}
    for record in requests:
        by_type[record["resource_type"]] = by_type.get(record["resource_type"], 0) + 1
        by_class[record["request_class"]] = by_class.get(record["request_class"], 0) + 1
    same = [record for record in requests if record["same_origin"]]
    late = [record for record in requests if any(":scroll" in phase_name
                                                  for phase_name in record["phases"])]
    providers = sorted({record["provider"] for record in requests if record["provider"]})
    eligible = [record for record in requests if record["acquisition"]["automatic"]]

    report = {
        "schema_version": SCHEMA_VERSION,
        "capture_tool_version": SCHEMA_VERSION,
        "page": sanitize_url(args.url)["url"],
        "requested_page": sanitize_url(args.url)["url"],
        "canonical_origin": final_origin,
        "navigation": primary_navigation,
        "access_result": overall_access["state"],
        "blocked_by_challenge": overall_access["state"] == "blocked_by_challenge",
        "allowed_navigation_origins": sorted(set([requested_origin] + allowed_origins)),
        "capture_started_at": started_at,
        "captured_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "capture_passes": passes,
        "summary": {
            "total_requests": len(requests),
            "total_responses": sum(1 for item in requests if item["status"] is not None),
            "same_origin": len(same),
            "external": len(requests) - len(same),
            "loaded_during_scroll": len(late),
            "automatically_acquirable_static_get_head": len(eligible),
            "metadata_references": len(metadata),
            "by_resource_type": by_type,
            "by_request_class": by_class,
            "providers_detected": providers,
            "recorder_errors": len(recorder.errors),
        },
        "same_site_routes_from_anchors": sorted({item["path"] for item in routes}),
        "route_inventory": routes,
        "metadata_references": metadata,
        "requests": requests,
        "recorder_errors": recorder.errors,
    }

    atomic_write_json(args.out, report)

    if overall_access["blocked"]:
        print("CAPTURE BLOCKED: %s" % overall_access["state"], file=sys.stderr)
        print("Diagnostic graph written to %s; no access control was bypassed." % args.out,
              file=sys.stderr)
        return 3

    print("Wrote " + args.out)
    print("  canonical origin: " + final_origin)
    print("  requests: %d (%d same-origin, %d external)" %
          (len(requests), len(same), len(requests) - len(same)))
    print("  classified static GET/HEAD candidates: %d" % len(eligible))
    print("  metadata references: %d (Observed/Probed/Captured kept separate)" %
          len(metadata))
    print("  same-site routes found: %d" % len(routes))
    for capture_pass in passes:
        scroll = capture_pass.get("scroll", {})
        print("  %s scroll coverage: %s" %
              (capture_pass.get("viewport"), scroll.get("mechanism", "not_exercised")))
    if providers:
        print("  providers detected (classify; do not auto-download): " +
              ", ".join(providers))
    return 0


if __name__ == "__main__":
    sys.exit(main())
