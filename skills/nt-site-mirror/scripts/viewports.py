#!/usr/bin/env python3
"""Capture an evidence-bounded URL x viewport validation matrix.

Each result records the main response status, final URL, title, access-state
evidence, bounded settling, scroll mechanism, service-worker state, browser
errors, and screenshot mode. A challenge, login wall, HTTP/error document,
failed screenshot, or missing matrix cell is never counted as success.

The script uses DOMContentLoaded plus bounded settling; it never waits for
networkidle. Virtual and internal-container scrolling share the same detector
as capture_assets.py through browser_support.py.

Usage:
    python3 viewports.py URL [URL ...] [--out shots]
        [--viewports desktop,tablet,mobile,1512x982]
        [--timeout 45000] [--settle-ms 5000]
        [--service-workers auto|allow|block|both]
        [--allow-origin https://www.example.com]

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
from urllib.parse import urlparse, urlsplit

from browser_support import (
    bounded_settle,
    canonical_origin,
    detect_access_state,
    explore_scroll,
    inspect_service_workers,
    navigation_origin_allowed,
    redirect_response_evidence,
    sanitize_url,
)
from capture_assets import classify_request


SCHEMA_VERSION = "1.3"
VIEWPORTS = {
    "desktop": {"width": 1440, "height": 900},
    "tablet": {"width": 768, "height": 1024},
    "mobile": {"width": 390, "height": 844},
}
CUSTOM_RE = re.compile(r"^(\d{3,4})x(\d{3,4})$")
NONESSENTIAL_TELEMETRY_RESOURCE_TYPES = {"xhr", "fetch", "ping"}


def viewport_for(name):
    if name in VIEWPORTS:
        return VIEWPORTS[name]
    match = CUSTOM_RE.match(name)
    if match:
        return {"width": int(match.group(1)), "height": int(match.group(2))}
    return None


def slug(url):
    parsed = urlparse(url)
    base = (parsed.netloc + parsed.path).strip("/").replace("/", "_") or "page"
    base = re.sub(r"[^A-Za-z0-9._-]+", "-", base)[:64]
    identity = hashlib.sha256(url.encode("utf-8")).hexdigest()[:10]
    return "%s__%s" % (base, identity)


def iso_now():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def safe_error(exc):
    text = str(exc)
    return re.sub(
        r"https?://[^\s'\"]+",
        lambda match: sanitize_url(match.group(0).rstrip(".,)"))["url"],
        text,
    )


def write_json(path, value):
    directory = os.path.dirname(os.path.abspath(path))
    os.makedirs(directory, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=".ntsm-viewports-", dir=directory)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, indent=2, sort_keys=True)
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


def main_response_record(response):
    if response is None:
        return {"status": None, "url": None}
    return {"status": response.status, "url": sanitize_url(response.url)["url"]}


def _property(value):
    return value() if callable(value) else value


def install_navigation_guard(page, requested_origin, allowed_origins, rejected):
    """Abort any unapproved top-level destination without interacting with it."""
    def guard(route):
        request = route.request
        try:
            is_main_navigation = (
                request.is_navigation_request() and request.frame == page.main_frame
            )
        except Exception:
            is_main_navigation = False
        if is_main_navigation and not navigation_origin_allowed(
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
            rejected.append({
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


def record_main_navigation(result, page, response, requested_origin="",
                           allowed_origins=()):
    """Record every main-frame response so late navigations do not look successful."""
    try:
        request = response.request
        if request.is_navigation_request() and request.frame == page.main_frame:
            redirect = redirect_response_evidence(
                response, requested_origin, allowed_origins
            )
            if (redirect and not redirect["authorized"]
                    and redirect not in result["unauthorized_redirects"]):
                result["unauthorized_redirects"].append(redirect)
            result["navigation_responses"].append({
                "url": sanitize_url(response.url)["url"],
                "status": response.status,
            })
    except Exception:
        return


def apply_latest_navigation(result, page):
    responses = result.get("navigation_responses") or []
    final_url = sanitize_url(page.url)["url"]
    result["final_url"] = final_url
    if responses:
        result["initial_status"] = responses[0]["status"]
        result["initial_response_url"] = responses[0]["url"]
        latest = responses[-1]
        result["status"] = latest["status"]
        result["response_url"] = latest["url"]
    redirects = []
    for index, item in enumerate(responses[:-1]):
        if 300 <= int(item.get("status") or 0) < 400:
            redirects.append({
                "from": item.get("url"),
                "to": responses[index + 1].get("url"),
                "status": item.get("status"),
            })
    result["redirects"] = redirects


def maybe_reload_for_service_worker(page, settle_ms):
    """Give a newly registered worker one bounded chance to control a reload."""
    state = inspect_service_workers(page)
    if state.get("controller") or not state.get("registrations"):
        return {"reloaded": False, "state": state}
    try:
        page.evaluate(
            """async (maxMs) => {
                if (!('serviceWorker' in navigator)) return false;
                await Promise.race([
                    navigator.serviceWorker.ready,
                    new Promise(resolve => setTimeout(() => resolve(null), maxMs))
                ]);
                return true;
            }""",
            min(2500, settle_ms),
        )
        response = page.reload(
            wait_until="domcontentloaded", timeout=max(5000, settle_ms * 4)
        )
        settle = bounded_settle(page, max_ms=settle_ms)
        return {
            "reloaded": True,
            "response": main_response_record(response),
            "final_url": sanitize_url(page.url)["url"],
            "settle": settle,
            "state": inspect_service_workers(page),
        }
    except Exception as exc:
        return {
            "reloaded": False,
            "reload_error": safe_error(exc).split("\n", 1)[0],
            "state": inspect_service_workers(page),
        }


def _request_chain_urls(request):
    chain = []
    seen = set()
    current = request
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        chain.append(sanitize_url(current.url)["url"])
        current = _property(getattr(current, "redirected_from", None))
    return list(reversed(chain))


def _network_failure_record(result, records, request):
    safe = sanitize_url(request.url)
    method = request.method.upper()
    resource_type = request.resource_type
    request_chain_urls = _request_chain_urls(request) or [safe["url"]]
    key = (method, tuple(request_chain_urls), resource_type)
    record = records.get(key)
    if record is None:
        request_classification = classify_request(
            method,
            resource_type,
            request.url,
            url_redacted=safe["redacted"],
        )
        record = {
            "event_type": "network",
            "url": safe["url"],
            "initial_request_url": request_chain_urls[0],
            "final_request_url": request_chain_urls[-1],
            "request_chain_urls": request_chain_urls,
            "method": method,
            "resource_type": resource_type,
            "http_status": None,
            "http_status_history": [],
            "request_failure": None,
            "console_message": None,
            "same_origin": None,
            "required": False,
            "allowed_exception": False,
            "classification": "pending",
            "exception_reason": None,
            "context": result["context"],
            "request_class": request_classification["request_class"],
            "data_type": request_classification["data_type"],
            "request_classification_reason": request_classification[
                "acquisition"
            ]["reason"],
        }
        records[key] = record
        result["observed_failures"].append(record)
    return record


def record_http_failure(result, records, response):
    """Persist same- and cross-origin subresource HTTP error evidence."""
    try:
        status = int(response.status)
        if status < 400 or status > 599:
            return
        request = response.request
        record = _network_failure_record(result, records, request)
        record["http_status"] = status
        if status not in record["http_status_history"]:
            record["http_status_history"].append(status)
        result["http_errors"].append({
            "url": record["url"],
            "method": record["method"],
            "resource_type": record["resource_type"],
            "status": status,
            "context": result["context"],
        })
    except Exception as exc:
        result["warnings"].append(
            "HTTP failure evidence could not be recorded: %s"
            % safe_error(exc).split("\n", 1)[0]
        )


def record_request_failure(result, records, request):
    """Merge Playwright requestfailed evidence with any HTTP error record."""
    try:
        failure = _property(getattr(request, "failure", None))
        failure = str(failure or "request_failed")[:500]
        record = _network_failure_record(result, records, request)
        record["request_failure"] = failure
        result["request_failures"].append({
            "url": record["url"],
            "method": record["method"],
            "resource_type": record["resource_type"],
            "failure": failure,
        })
    except Exception as exc:
        result["warnings"].append(
            "request-failure evidence could not be recorded: %s"
            % safe_error(exc).split("\n", 1)[0]
        )


def record_console_error(result, page, message):
    try:
        if _property(getattr(message, "type", "")) != "error":
            return
        text = safe_error(_property(getattr(message, "text", "")))
        location = _property(getattr(message, "location", {})) or {}
        raw_url = location.get("url") or page.url or result["requested_url"]
        safe_url = sanitize_url(raw_url)["url"]
        console_record = {
            "event_type": "console",
            "url": safe_url,
            "method": None,
            "resource_type": "console",
            "http_status": None,
            "http_status_history": [],
            "request_failure": None,
            "console_message": text,
            "console_location": {
                "url": safe_url,
                "line_number": location.get("lineNumber"),
                "column_number": location.get("columnNumber"),
            },
            "same_origin": None,
            "required": False,
            "allowed_exception": False,
            "classification": "pending",
            "exception_reason": None,
            "context": result["context"],
            "request_class": None,
            "data_type": "console_error",
            "request_classification_reason": None,
        }
        result["console_errors"].append({
            "url": safe_url,
            "message": text,
            "location": console_record["console_location"],
            "context": result["context"],
        })
        result["observed_failures"].append(console_record)
    except Exception as exc:
        result["warnings"].append(
            "console-error evidence could not be recorded: %s"
            % safe_error(exc).split("\n", 1)[0]
        )


def record_page_error(result, page, exc):
    text = safe_error(exc)
    result["page_errors"].append(text)
    safe_url = sanitize_url(page.url or result["requested_url"])["url"]
    result["observed_failures"].append({
        "event_type": "page_error",
        "url": safe_url,
        "method": None,
        "resource_type": "document",
        "http_status": None,
        "http_status_history": [],
        "request_failure": text,
        "console_message": None,
        "same_origin": None,
        "required": False,
        "allowed_exception": False,
        "classification": "pending",
        "exception_reason": None,
        "context": result["context"],
        "request_class": None,
        "data_type": "page_error",
        "request_classification_reason": None,
    })


def _correlate_resource_console_errors(result):
    """Fold Chromium's generic load console error into its network evidence."""
    failures = result.get("observed_failures") or []
    network_by_url = {}
    for item in failures:
        if item.get("event_type") == "network":
            network_by_url.setdefault(item.get("url"), []).append(item)

    correlated = []
    remaining = []
    for item in failures:
        message = item.get("console_message") or ""
        candidates = network_by_url.get(item.get("url")) or []
        if (item.get("event_type") == "console"
                and message.startswith("Failed to load resource:")
                and candidates):
            target = next(
                (
                    candidate for candidate in reversed(candidates)
                    if not candidate.get("console_message")
                ),
                candidates[-1],
            )
            target["console_message"] = message
            target["console_location"] = item.get("console_location")
            correlated.append({
                "url": item.get("url"),
                "message": message,
                "network_resource_type": target.get("resource_type"),
            })
            continue
        remaining.append(item)
    result["observed_failures"] = remaining
    result["correlated_console_errors"] = correlated


def classify_failure_evidence(result, allowed_telemetry_urls=()):
    """Classify failures against every observed document origin in the cell."""
    _correlate_resource_console_errors(result)
    document_origins = set()
    for document_url in (
        [result.get("requested_url"), result.get("final_url")]
        + [
            item.get("url")
            for item in result.get("navigation_responses") or []
        ]
    ):
        origin = canonical_origin(document_url or "")
        if origin:
            document_origins.add(origin)
    result["document_origins"] = sorted(document_origins)
    context = result.get("context", "local")

    for item in result.get("observed_failures") or []:
        request_chain_urls = item.get("request_chain_urls") or [item.get("url")]
        same_origin_urls = []
        for request_url in request_chain_urls:
            item_origin = canonical_origin(request_url or "")
            if item_origin and item_origin in document_origins:
                same_origin_urls.append(request_url)
        item["same_origin"] = bool(same_origin_urls)
        item["same_origin_basis_urls"] = same_origin_urls
        item["context"] = context
        item["required"] = False
        item["allowed_exception"] = False
        item["exception_reason"] = None

        explicitly_allowed_telemetry = bool(
            item.get("request_class") == "telemetry"
            and item.get("resource_type") in NONESSENTIAL_TELEMETRY_RESOURCE_TYPES
            and item.get("url") in allowed_telemetry_urls
        )
        if explicitly_allowed_telemetry:
            item["classification"] = "allowed_telemetry_exception"
            item["allowed_exception"] = True
            item["exception_reason"] = (
                "explicit_allowed_nonessential_telemetry_url"
            )
            item["exception_evidence"] = {
                "rule": "--allow-telemetry-url",
                "matched_url": item.get("url"),
                "request_classification_reason": item.get(
                    "request_classification_reason"
                ),
            }
            continue

        if context == "source":
            item["classification"] = "source_observation"
            continue

        event_type = item.get("event_type")
        if event_type == "console":
            item["required"] = True
            item["classification"] = "unclassified_console_error"
        elif event_type == "page_error":
            item["required"] = True
            item["classification"] = "page_error"
        elif item["same_origin"]:
            item["required"] = True
            status = item.get("http_status")
            failure = item.get("request_failure")
            if isinstance(status, int) and 400 <= status <= 599:
                item["classification"] = "required_same_origin_http_error"
            elif failure:
                item["classification"] = "required_same_origin_request_failure"
            else:
                item["classification"] = "required_same_origin_runtime_failure"
        else:
            item["classification"] = "observed_cross_origin_failure"

    recompute_case_verdict(result)


def recompute_case_verdict(result):
    blocking = [
        item for item in result.get("observed_failures") or []
        if item.get("required") and not item.get("allowed_exception")
    ]
    exceptions = [
        item for item in result.get("observed_failures") or []
        if item.get("allowed_exception")
    ]
    result["required_failures"] = blocking
    result["allowed_exceptions"] = exceptions

    warning = "required runtime failures make this matrix cell incomplete"
    result["warnings"] = [
        item for item in result.get("warnings") or [] if item != warning
    ]
    if blocking:
        result["success"] = False
        if result.get("capture_complete"):
            result["failure_reason"] = "required_runtime_failures_observed"
        result["warnings"].append(warning)
    elif result.get("capture_complete"):
        result["success"] = True
        if result.get("failure_reason") == "required_runtime_failures_observed":
            result.pop("failure_reason", None)


def _failure_signature(item):
    event_type = item.get("event_type")
    if event_type == "network":
        chain_identity = tuple(
            (urlsplit(url or "").path, urlsplit(url or "").query)
            for url in item.get("request_chain_urls") or [item.get("url")]
        )
        return (
            "network",
            item.get("method"),
            item.get("resource_type"),
            chain_identity,
            item.get("http_status"),
            item.get("request_failure"),
        )
    if event_type == "console":
        return ("console", item.get("console_message"))
    if event_type == "page_error":
        return ("page_error", item.get("request_failure"))
    return None


def apply_source_baseline_exceptions(results, source_url, local_url):
    """Allow only failures proven equal in an explicitly paired source cell."""
    exceptions = []
    source_cells = {
        (item.get("viewport_name"), item.get("service_worker_mode")): item
        for item in results
        if item.get("context") == "source"
        and item.get("requested_url") == source_url
    }
    for local in results:
        if (local.get("context") != "local"
                or local.get("requested_url") != local_url):
            continue
        source = source_cells.get((
            local.get("viewport_name"), local.get("service_worker_mode")
        ))
        source_usable = bool(
            source
            and source.get("capture_complete")
            and source.get("success")
            and isinstance(source.get("status"), int)
            and 200 <= source["status"] < 300
            and source.get("screenshot")
        )
        if not source_usable:
            continue

        source_by_signature = {}
        for source_issue in source.get("observed_failures") or []:
            signature = _failure_signature(source_issue)
            if signature and source_issue.get("same_origin"):
                source_by_signature.setdefault(signature, []).append(source_issue)

        for local_issue in local.get("observed_failures") or []:
            if (not local_issue.get("required")
                    or local_issue.get("allowed_exception")):
                continue
            signature = _failure_signature(local_issue)
            matches = source_by_signature.get(signature) or []
            if not matches:
                continue
            source_issue = matches[0]
            source_snapshot = {
                "requested_url": source.get("requested_url"),
                "final_url": source.get("final_url"),
                "viewport_name": source.get("viewport_name"),
                "service_worker_mode": source.get("service_worker_mode"),
                "url": source_issue.get("url"),
                "initial_request_url": source_issue.get("initial_request_url"),
                "final_request_url": source_issue.get("final_request_url"),
                "request_chain_urls": source_issue.get("request_chain_urls"),
                "resource_type": source_issue.get("resource_type"),
                "http_status": source_issue.get("http_status"),
                "request_failure": source_issue.get("request_failure"),
                "console_message": source_issue.get("console_message"),
                "same_origin": source_issue.get("same_origin"),
                "context": "source",
            }
            local_issue["classification"] = "allowed_source_baseline_exception"
            local_issue["allowed_exception"] = True
            local_issue["exception_reason"] = (
                "exact_failure_matched_explicit_source_local_pair"
            )
            local_issue["source_evidence"] = source_snapshot
            source_issue["classification"] = "source_baseline_issue"
            source_issue["exception_reason"] = (
                "exact_failure_matched_explicit_source_local_pair"
            )
            source_issue["paired_local_url"] = local.get("requested_url")
            exceptions.append({
                "source_url": source.get("requested_url"),
                "local_url": local.get("requested_url"),
                "viewport_name": local.get("viewport_name"),
                "service_worker_mode": local.get("service_worker_mode"),
                "local_failure": local_issue,
                "source_evidence": source_snapshot,
            })
        recompute_case_verdict(local)
    return exceptions


def capture_case(browser, url, viewport_name, viewport, sw_mode, args,
                 context_name="local", required=True):
    label = "sw-%s" % sw_mode
    safe_requested = sanitize_url(url)
    result = {
        "requested_url": safe_requested["url"],
        "requested_url_redacted": safe_requested["redacted"],
        "sensitive_query_keys": safe_requested["sensitive_query_keys"],
        "viewport_name": viewport_name,
        "viewport": viewport,
        "service_worker_mode": sw_mode,
        "context": context_name,
        "started_at": iso_now(),
        "success": False,
        "required": required,
        "required_reason": (
            "declared_local_viewport_cell"
            if required else "explicit_paired_source_evidence"
        ),
        "capture_complete": False,
        "initial_status": None,
        "initial_response_url": None,
        "status": None,
        "response_url": None,
        "final_url": None,
        "title": None,
        "access": None,
        "service_worker": None,
        "settle": None,
        "scroll": None,
        "screenshot": None,
        "capture_mode": None,
        "warnings": [],
        "page_errors": [],
        "console_errors": [],
        "correlated_console_errors": [],
        "http_errors": [],
        "request_failures": [],
        "observed_failures": [],
        "required_failures": [],
        "allowed_exceptions": [],
        "navigation_responses": [],
        "redirects": [],
        "unauthorized_redirects": [],
    }
    context = browser.new_context(
        viewport=viewport,
        device_scale_factor=2,
        service_workers=sw_mode,
    )
    page = context.new_page()
    network_failure_records = {}
    guard = install_navigation_guard(
        page,
        canonical_origin(url),
        args.allowed_origins,
        result["unauthorized_redirects"],
    )
    page.on(
        "response",
        lambda response: record_main_navigation(
            result, page, response, canonical_origin(url), args.allowed_origins
        ),
    )
    context.on(
        "response",
        lambda response: record_http_failure(
            result, network_failure_records, response
        ),
    )
    page.on("pageerror", lambda exc: record_page_error(result, page, exc))
    context.on(
        "console", lambda message: record_console_error(result, page, message)
    )
    context.on(
        "requestfailed",
        lambda request: record_request_failure(
            result, network_failure_records, request
        ),
    )

    try:
        response = page.goto(url, wait_until="domcontentloaded", timeout=args.timeout)
        main_response = main_response_record(response)
        result["initial_status"] = main_response["status"]
        result["initial_response_url"] = main_response["url"]
        result["status"] = main_response["status"]
        result["response_url"] = main_response["url"]
        result["final_url"] = sanitize_url(page.url)["url"]
        result["title"] = page.title()
        result["settle"] = bounded_settle(page, max_ms=args.settle_ms)
        apply_latest_navigation(result, page)

        if result["unauthorized_redirects"] or not navigation_origin_allowed(
            page.url, canonical_origin(url), args.allowed_origins
        ):
            result["access"] = {
                "state": "blocked_by_unauthorized_redirect",
                "blocked": True,
                "title": result.get("title") or "",
                "final_url": result.get("final_url"),
                "evidence": {
                    "unauthorized_redirects": result["unauthorized_redirects"]
                },
            }
            result["failure_reason"] = "unauthorized_redirect_destination"
            return result

        if sw_mode == "allow":
            controlled = maybe_reload_for_service_worker(page, args.settle_ms)
            result["service_worker_control_probe"] = controlled
            if controlled.get("reloaded"):
                controlled_response = controlled.get("response") or {}
                result["status"] = controlled_response.get("status")
                result["response_url"] = controlled_response.get("url")
                apply_latest_navigation(result, page)
                result["title"] = page.title()

            if result["unauthorized_redirects"] or not navigation_origin_allowed(
                page.url, canonical_origin(url), args.allowed_origins
            ):
                result["access"] = {
                    "state": "blocked_by_unauthorized_redirect",
                    "blocked": True,
                    "title": result.get("title") or "",
                    "final_url": result.get("final_url"),
                    "evidence": {
                        "unauthorized_redirects": result["unauthorized_redirects"]
                    },
                }
                result["failure_reason"] = "unauthorized_redirect_destination"
                return result

        result["service_worker"] = inspect_service_workers(page)
        result["access"] = detect_access_state(
            page,
            response_status=result.get("status"),
            final_url=result.get("final_url"),
        )

        status = result.get("status")
        blocked = bool(result["access"].get("blocked"))
        if status is None or not 200 <= status < 300:
            blocked = True
            result["warnings"].append("main document did not return a 2xx status")

        if blocked:
            rejected_path = os.path.join(
                args.out,
                "%s__%s__%s__REJECTED.png" % (slug(url), viewport_name, label),
            )
            try:
                page.screenshot(path=rejected_path, full_page=False, timeout=args.timeout)
                result["rejected_evidence_screenshot"] = rejected_path
            except Exception as exc:
                result["warnings"].append(
                    "rejected-page evidence screenshot failed: %s"
                    % safe_error(exc).split("\n", 1)[0]
                )
            result["failure_reason"] = "invalid_access_or_document_state"
            return result

        result["scroll"] = explore_scroll(
            page,
            steps=args.scroll_steps,
            wait_ms=args.step_wait,
            wheel_delta=args.wheel_delta,
        )
        after_scroll_worker = inspect_service_workers(page)
        result["service_worker_after_scroll"] = after_scroll_worker
        initial_control_probe = result.get("service_worker_control_probe") or {}
        if (sw_mode == "allow" and after_scroll_worker.get("registrations")
                and not after_scroll_worker.get("controller")
                and not initial_control_probe.get("reloaded")):
            late_control = maybe_reload_for_service_worker(page, args.settle_ms)
            result["service_worker_control_probe_after_scroll"] = late_control
            if late_control.get("reloaded"):
                result["scroll_before_controlled_reload"] = result["scroll"]
                result["scroll"] = explore_scroll(
                    page,
                    steps=args.scroll_steps,
                    wait_ms=args.step_wait,
                    wheel_delta=args.wheel_delta,
                )
            elif late_control.get("reload_error"):
                result["warnings"].append(
                    "late service-worker controlled reload failed: %s"
                    % late_control["reload_error"]
                )
        result["service_worker"] = inspect_service_workers(page)
        apply_latest_navigation(result, page)
        result["title"] = page.title()
        if result["unauthorized_redirects"] or not navigation_origin_allowed(
            page.url, canonical_origin(url), args.allowed_origins
        ):
            result["access"] = {
                "state": "blocked_by_unauthorized_redirect",
                "blocked": True,
                "title": result.get("title") or "",
                "final_url": result.get("final_url"),
                "evidence": {
                    "unauthorized_redirects": result["unauthorized_redirects"]
                },
            }
            result["failure_reason"] = "unauthorized_redirect_destination"
            return result
        post_scroll_access = detect_access_state(
            page,
            response_status=result.get("status"),
            final_url=result.get("final_url"),
        )
        result["post_scroll_access"] = post_scroll_access
        if post_scroll_access.get("blocked"):
            result["access"] = post_scroll_access
            result["failure_reason"] = "invalid_post_scroll_access_or_document_state"
            return result
        mechanism = result["scroll"].get("mechanism", "none")
        full_page = mechanism in ("window_scroll", "none", "not_exercised")
        result["capture_mode"] = "full_page" if full_page else "viewport_only"
        screenshot_path = os.path.join(
            args.out,
            "%s__%s__%s%s.png"
            % (
                slug(url),
                viewport_name,
                label,
                "" if full_page else "__viewport-only",
            ),
        )
        try:
            page.screenshot(path=screenshot_path, full_page=full_page, timeout=args.timeout)
        except Exception as exc:
            if not full_page:
                raise
            result["warnings"].append(
                "full-page screenshot failed; captured viewport only: %s"
                % safe_error(exc).split("\n", 1)[0]
            )
            result["capture_mode"] = "viewport_only_fallback"
            screenshot_path = os.path.join(
                args.out,
                "%s__%s__%s__viewport-only.png" % (slug(url), viewport_name, label),
            )
            page.screenshot(path=screenshot_path, full_page=False, timeout=args.timeout)

        result["screenshot"] = screenshot_path
        # A navigation can race with screenshot encoding. Recheck the actual
        # final document before accepting this matrix cell.
        apply_latest_navigation(result, page)
        result["title"] = page.title()
        if result["unauthorized_redirects"] or not navigation_origin_allowed(
            page.url, canonical_origin(url), args.allowed_origins
        ):
            result["access"] = {
                "state": "blocked_by_unauthorized_redirect",
                "blocked": True,
                "title": result.get("title") or "",
                "final_url": result.get("final_url"),
                "evidence": {
                    "unauthorized_redirects": result["unauthorized_redirects"]
                },
            }
            result["failure_reason"] = "unauthorized_redirect_destination"
            return result
        final_access = detect_access_state(
            page,
            response_status=result.get("status"),
            final_url=result.get("final_url"),
        )
        result["final_access"] = final_access
        final_status = result.get("status")
        if (final_access.get("blocked") or final_status is None
                or not 200 <= final_status < 300):
            result["access"] = final_access
            result["failure_reason"] = "invalid_final_access_or_document_state"
            return result
        result["capture_complete"] = True
        result["success"] = True
        return result
    except Exception as exc:
        try:
            apply_latest_navigation(result, page)
        except Exception:
            pass
        if result["unauthorized_redirects"]:
            result["access"] = {
                "state": "blocked_by_unauthorized_redirect",
                "blocked": True,
                "title": result.get("title") or "",
                "final_url": result.get("final_url"),
                "evidence": {
                    "unauthorized_redirects": result["unauthorized_redirects"]
                },
            }
            result["failure_reason"] = "unauthorized_redirect_destination"
        else:
            result["failure_reason"] = "browser_or_capture_failure"
        result["error"] = safe_error(exc)
        return result
    finally:
        try:
            page.unroute("**/*", guard)
        except Exception:
            pass
        try:
            context.close()
        except Exception as exc:
            result["warnings"].append(
                "browser context close failed: %s" % safe_error(exc).split("\n", 1)[0]
            )
        classify_failure_evidence(result, args.allowed_telemetry_urls)
        result["finished_at"] = iso_now()


def sw_is_relevant(result):
    state = result.get("service_worker") or {}
    return bool(
        state.get("controller")
        or state.get("registrations")
        or state.get("precache_resources")
        or state.get("cache_names")
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("urls", nargs="+")
    parser.add_argument("--out", default="shots")
    parser.add_argument("--report", default=None,
                        help="structured JSON result (default: <out>/viewport-results.json)")
    parser.add_argument("--viewports", default="desktop,tablet,mobile",
                        help="named presets and/or custom WxH (e.g. desktop,1512x982)")
    parser.add_argument("--timeout", type=int, default=45000)
    parser.add_argument("--settle-ms", type=int, default=5000,
                        help="maximum bounded DOM settling time; networkidle is never used")
    parser.add_argument("--scroll-steps", type=int, default=10)
    parser.add_argument("--step-wait", type=int, default=400)
    parser.add_argument("--wheel-delta", type=int, default=800)
    parser.add_argument(
        "--service-workers",
        choices=("auto", "allow", "block", "both"),
        default="auto",
        help="auto runs an isolated bypassed pass when a worker/cache is observed",
    )
    parser.add_argument(
        "--allow-origin",
        action="append",
        default=[],
        help="explicitly authorize a top-level redirect origin (repeatable)",
    )
    parser.add_argument(
        "--source-url",
        default=None,
        help=(
            "explicitly label one of exactly two requested URLs as paired source "
            "evidence; the other URL remains the required local matrix target"
        ),
    )
    parser.add_argument(
        "--allow-telemetry-url",
        action="append",
        default=[],
        help=(
            "explicitly permit one exact nonessential telemetry transport URL; "
            "repeatable and never applicable to scripts, stylesheets, images, "
            "or other static assets"
        ),
    )
    args = parser.parse_args()

    if args.settle_ms < 0 or args.scroll_steps < 0 or args.step_wait < 0:
        parser.error("settle and scroll timing values must be non-negative")
    if args.timeout < 1 or args.wheel_delta < 1:
        parser.error("timeout and wheel delta must be positive")

    invalid_urls = [url for url in args.urls if not canonical_origin(url)]
    if invalid_urls:
        parser.error("every URL must be an absolute http:// or https:// URL")
    requested_safe_urls = [sanitize_url(url)["url"] for url in args.urls]
    source_url = None
    local_paired_url = None
    if args.source_url is not None:
        if not canonical_origin(args.source_url):
            parser.error("--source-url must be an absolute http:// or https:// URL")
        source_url = sanitize_url(args.source_url)["url"]
        if len(args.urls) != 2:
            parser.error(
                "--source-url requires exactly two requested URLs: one source and one local"
            )
        if requested_safe_urls.count(source_url) != 1:
            parser.error("--source-url must exactly match one requested URL")
        local_paired_url = next(
            url for url in requested_safe_urls if url != source_url
        )
    args.allowed_origins = []
    for value in args.allow_origin:
        origin = canonical_origin(value)
        if not origin:
            parser.error("invalid --allow-origin: %s" % value)
        args.allowed_origins.append(origin)
    args.allowed_telemetry_urls = []
    for value in args.allow_telemetry_url:
        if not canonical_origin(value):
            parser.error(
                "--allow-telemetry-url must be an absolute http:// or https:// URL"
            )
        args.allowed_telemetry_urls.append(sanitize_url(value)["url"])

    names = [value.strip() for value in args.viewports.split(",") if value.strip()]
    if not names:
        parser.error("at least one viewport is required")
    sizes = {name: viewport_for(name) for name in names}
    unknown = [name for name, size in sizes.items() if size is None]
    if unknown:
        parser.error(
            "Unknown viewport(s): %s. Valid: %s or WxH"
            % (", ".join(unknown), ", ".join(VIEWPORTS))
        )

    os.makedirs(args.out, exist_ok=True)
    report_path = args.report or os.path.join(args.out, "viewport-results.json")
    report = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": iso_now(),
        "settle_policy": {
            "navigation": "domcontentloaded",
            "networkidle_used": False,
            "max_settle_ms": args.settle_ms,
        },
        "requested_urls": requested_safe_urls,
        "url_contexts": [
            {
                "url": safe_url,
                "context": "source" if safe_url == source_url else "local",
                "required": safe_url != source_url,
            }
            for safe_url in requested_safe_urls
        ],
        "source_local_pair": (
            {"source_url": source_url, "local_url": local_paired_url}
            if source_url else None
        ),
        "source_baseline_exceptions": [],
        "allowed_telemetry_urls": sorted(set(args.allowed_telemetry_urls)),
        "allowed_navigation_origins": sorted(set(
            args.allowed_origins + [canonical_origin(url) for url in args.urls]
        )),
        "requested_viewports": names,
        "service_worker_policy": args.service_workers,
        "results": [],
        "summary": {},
    }
    required_url_count = sum(
        1 for safe_url in requested_safe_urls if safe_url != source_url
    )
    base_expected = required_url_count * len(names)
    expected = base_expected * (2 if args.service_workers == "both" else 1)

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        report["fatal_error"] = (
            "playwright not installed; run: python3 -m pip install playwright && "
            "python3 -m playwright install chromium"
        )
        report["summary"] = {
            "expected": expected,
            "produced": 0,
            "passed": 0,
            "failed": expected,
            "complete_matrix": False,
        }
        write_json(report_path, report)
        sys.exit(report["fatal_error"])

    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            for url in args.urls:
                safe_url = sanitize_url(url)["url"]
                context_name = "source" if safe_url == source_url else "local"
                cell_required = context_name == "local"
                for viewport_name in names:
                    modes = []
                    if args.service_workers in ("auto", "allow", "both"):
                        modes.append("allow")
                    if args.service_workers == "block":
                        modes.append("block")
                    if args.service_workers == "both":
                        modes.append("block")

                    primary = capture_case(
                        browser,
                        url,
                        viewport_name,
                        sizes[viewport_name],
                        modes[0],
                        args,
                        context_name=context_name,
                        required=cell_required,
                    )
                    report["results"].append(primary)

                    run_auto_bypass = (
                        args.service_workers == "auto" and sw_is_relevant(primary)
                    )
                    if run_auto_bypass or len(modes) > 1:
                        if run_auto_bypass and cell_required:
                            expected += 1
                        bypassed = capture_case(
                            browser,
                            url,
                            viewport_name,
                            sizes[viewport_name],
                            "block",
                            args,
                            context_name=context_name,
                            required=cell_required,
                        )
                        bypassed["required_reason"] = "service_worker_bypass_comparison"
                        report["results"].append(bypassed)
            browser.close()
    except Exception as exc:
        report["fatal_error"] = safe_error(exc)

    if source_url and local_paired_url:
        report["source_baseline_exceptions"] = apply_source_baseline_exceptions(
            report["results"], source_url, local_paired_url
        )

    for item in report["results"]:
        if item.get("context") == "source":
            label = (
                "SOURCE EVIDENCE COMPLETE"
                if item.get("success") else "SOURCE EVIDENCE INCOMPLETE"
            )
        else:
            label = "PASS" if item.get("success") else "FAIL"
        suffix = (
            " (service workers bypassed)"
            if item.get("service_worker_mode") == "block"
            and item.get("required_reason") == "service_worker_bypass_comparison"
            else ""
        )
        print(
            "%s %s @ %s (%s -> %s)%s"
            % (
                label,
                item.get("requested_url"),
                item.get("viewport_name"),
                item.get("status"),
                item.get("final_url"),
                suffix,
            )
        )

    required_results = [
        item for item in report["results"] if item.get("required")
    ]
    passed = sum(1 for item in required_results if item.get("success"))
    failed = expected - passed
    report["summary"] = {
        "expected": expected,
        "produced": len(required_results),
        "source_evidence_produced": sum(
            1 for item in report["results"] if item.get("context") == "source"
        ),
        "passed": passed,
        "failed": failed,
        "complete_matrix": (
            expected > 0
            and len(required_results) == expected
            and passed == expected
            and not report.get("fatal_error")
        ),
    }
    write_json(report_path, report)
    print("\nViewport evidence: %s" % report_path)
    if report["summary"]["complete_matrix"]:
        print("Matrix: %d/%d passed" % (passed, expected))
    else:
        print(
            "Matrix: INCOMPLETE (%d passed, %d failed, %d/%d cells produced)"
            % (passed, failed, len(required_results), expected)
        )

    if not report["summary"]["complete_matrix"]:
        sys.exit("VALIDATION FAILURE: incomplete URL x viewport matrix")


if __name__ == "__main__":
    main()
