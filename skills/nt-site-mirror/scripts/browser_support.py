#!/usr/bin/env python3
"""Shared, side-effect-limited browser inspection helpers for NT Site Mirror.

The helpers in this module deliberately avoid accepting dialogs, clicking
challenge controls, or altering application state.  They are used by capture
and viewport validation so both tools describe settling, access state, scroll
coverage, and service workers with the same vocabulary.

Playwright is intentionally imported by callers.  Keeping this module free of
that import makes the URL and classification helpers testable with Python's
standard library alone.
"""

import re
import time
from urllib.parse import parse_qsl, urlencode, urljoin, urlsplit, urlunsplit


SENSITIVE_QUERY_RE = re.compile(
    r"(^|[_-])(access[_-]?token|auth|authorization|api[_-]?key|client[_-]?secret|"
    r"code|credential|jwt|key|pass(word|wd)?|policy|saml(response)?|secret|session|"
    r"sig(nature)?|ticket|token)($|[_-])",
    re.IGNORECASE,
)

CHALLENGE_TITLE_MARKERS = (
    "just a moment",
    "checking your browser",
    "verify you are human",
    "security check",
    "attention required",
    "captcha",
)
CHALLENGE_BODY_MARKERS = (
    "verify you are human",
    "checking if the site connection is secure",
    "checking your browser before accessing",
    "performing security verification",
    "complete the security check",
    "enable javascript and cookies to continue",
    "cf-chl-",
    "captcha",
)
CHALLENGE_URL_MARKERS = (
    "/cdn-cgi/challenge",
    "/challenge-platform/",
    "/captcha",
    "recaptcha",
    "hcaptcha",
    "turnstile",
    "verify-you-are-human",
)
LOGIN_MARKERS = (
    "sign in",
    "log in",
    "login",
    "authentication required",
    "authorize access",
)
ERROR_MARKERS = (
    "404 not found",
    "page not found",
    "application error",
    "internal server error",
    "service unavailable",
    "this site can’t be reached",
    "this site can't be reached",
)
EXACT_LOGIN_TITLE_RE = re.compile(
    r"^\s*(?:log[ -]?in|sign[ -]?in|login|authentication required)\s*$",
    re.IGNORECASE,
)
EXACT_CHALLENGE_TITLE_RE = re.compile(
    r"^\s*(?:just a moment(?:\.{1,3})?|checking your browser|"
    r"verify you are human|security check|attention required|captcha)\s*$",
    re.IGNORECASE,
)
EXACT_ACCESS_TITLE_RE = re.compile(
    r"^\s*(?:access denied|request blocked|401(?:\s+unauthorized)?|"
    r"403(?:\s+forbidden)?|unauthorized|forbidden)\s*[.!]?\s*$",
    re.IGNORECASE,
)
EXACT_ERROR_TITLE_RE = re.compile(
    r"^\s*(?:(?:4\d{2}|5\d{2})(?:\s+(?:not found|server error|"
    r"internal server error|service unavailable|bad gateway|gateway timeout))?|"
    r"page not found|not found|server error|application error|"
    r"internal server error|service unavailable|bad gateway|gateway timeout|"
    r"this site can(?:['’]t|not) be reached)\s*[.!]?\s*$",
    re.IGNORECASE,
)


def canonical_origin(url):
    """Return a normalized HTTP(S) origin, excluding default ports."""
    try:
        raw = str(url or "")
        if "\\" in raw or any(ord(char) < 32 or ord(char) == 127 for char in raw):
            return ""
        parts = urlsplit(raw)
        scheme = parts.scheme.lower()
        if (scheme not in ("http", "https") or not parts.hostname
                or parts.username is not None or parts.password is not None):
            return ""
        host = parts.hostname.lower().rstrip(".")
        if ":" in host and not host.startswith("["):
            host = "[%s]" % host
        port = parts.port
        if port and not ((scheme == "http" and port == 80) or
                         (scheme == "https" and port == 443)):
            host = "%s:%d" % (host, port)
        return "%s://%s" % (scheme, host)
    except (TypeError, ValueError):
        return ""


def sanitize_url(url):
    """Return a URL safe for reports without losing non-secret query identity.

    Values for credential-like query keys and any URL userinfo are redacted.
    Fragments are discarded because they are not part of an HTTP request.
    Callers must not acquire a URL whose ``redacted`` value is true.
    """
    result = {"url": str(url or ""), "redacted": False,
              "sensitive_query_keys": []}
    try:
        parts = urlsplit(str(url or ""))
        scheme = parts.scheme.lower()
        if scheme not in ("http", "https", "ws", "wss"):
            safe_scheme = re.sub(r"[^a-z0-9+.-]", "", scheme) or "unknown"
            return {
                "url": "%s:<non-network-url-redacted>" % safe_scheme,
                "redacted": True,
                "sensitive_query_keys": [],
                "unsupported_scheme": safe_scheme,
            }
        query = []
        sensitive = []
        for key, value in parse_qsl(parts.query, keep_blank_values=True):
            if SENSITIVE_QUERY_RE.search(key):
                value = "<redacted>"
                sensitive.append(key)
            query.append((key, value))

        hostname = parts.hostname or ""
        netloc = hostname
        if ":" in hostname and not hostname.startswith("["):
            netloc = "[%s]" % hostname
        if parts.port:
            netloc += ":%d" % parts.port
        userinfo_redacted = parts.username is not None or parts.password is not None
        # Preserve byte-for-byte safe query identity.  Re-encoding with
        # parse_qsl/urlencode would turn ``%20`` into ``+`` and can collapse a
        # CDN cache key even when no value required redaction.
        safe_query = urlencode(query, doseq=True) if sensitive else parts.query
        safe = urlunsplit((parts.scheme, netloc, parts.path, safe_query, ""))
        result.update({
            "url": safe,
            "redacted": bool(sensitive or userinfo_redacted),
            "sensitive_query_keys": sorted(set(sensitive)),
        })
        if userinfo_redacted:
            result["userinfo_redacted"] = True
        return result
    except (TypeError, ValueError):
        return {
            "url": "<invalid-url-redacted>",
            "redacted": True,
            "sensitive_query_keys": [],
            "invalid": True,
        }


def redact_error_text(value):
    """Remove credential-like URL values from browser errors before reporting."""
    text = str(value)
    return re.sub(
        r"https?://[^\s'\"]+",
        lambda match: sanitize_url(match.group(0).rstrip(".,)"))["url"],
        text,
    )


def normalize_http_url(value, base_url):
    """Resolve an HTTP(S) reference and strip its fragment."""
    try:
        resolved = urljoin(base_url, value)
        parts = urlsplit(resolved)
        if parts.scheme.lower() not in ("http", "https") or not parts.hostname:
            return ""
        return urlunsplit((parts.scheme, parts.netloc, parts.path, parts.query, ""))
    except (TypeError, ValueError):
        return ""


def navigation_origin_allowed(url, initial_origin, explicitly_allowed=()):
    """Apply the fail-closed top-level navigation policy used by capture.

    The exact requested origin and explicitly named origins are allowed.  A
    same-host HTTP-to-HTTPS upgrade is also allowed.  Host changes (including
    apex-to-www) require an explicit ``--allow-origin`` value.
    """
    candidate = canonical_origin(url)
    if not candidate:
        return False
    allowed = {canonical_origin(item) for item in explicitly_allowed}
    allowed.discard("")
    allowed.add(canonical_origin(initial_origin))
    if candidate in allowed:
        return True
    try:
        source = urlsplit(canonical_origin(initial_origin))
        dest = urlsplit(candidate)
        source_port = source.port or (80 if source.scheme == "http" else 443)
        dest_port = dest.port or (80 if dest.scheme == "http" else 443)
        return (source.hostname == dest.hostname and source.scheme == "http" and
                dest.scheme == "https" and source_port == 80 and dest_port == 443)
    except (TypeError, ValueError):
        return False


def redirect_response_evidence(response, initial_origin, explicitly_allowed=()):
    """Classify a main-document HTTP redirect from its raw Location header.

    Browsers can remove URL userinfo before exposing the next Request URL.  A
    request-only guard would then mistake a credential-bearing redirect for a
    same-origin navigation.  Inspecting the redirect response itself preserves
    the safety decision while ``sanitize_url`` keeps secrets out of reports.
    """
    try:
        status = int(getattr(response, "status", 0) or 0)
        if not 300 <= status < 400:
            return None
        headers = getattr(response, "headers", {}) or {}
        if callable(headers):
            headers = headers()
        headers = {str(key).lower(): str(value) for key, value in headers.items()}
        location = headers.get("location")
        if not location:
            return None
        source = str(getattr(response, "url", "") or "")
        destination = normalize_http_url(location, source)
        safe_source = sanitize_url(source)
        safe_destination = sanitize_url(destination or location)
        authorized = bool(
            destination
            and not safe_destination.get("redacted")
            and navigation_origin_allowed(
                destination, initial_origin, explicitly_allowed
            )
        )
        reason = None
        if not authorized:
            reason = (
                "credential_bearing_redirect"
                if safe_destination.get("userinfo_redacted")
                else "unauthorized_redirect_destination"
            )
        return {
            "from": safe_source["url"],
            "to": safe_destination["url"],
            "status": status,
            "authorized": authorized,
            "destination_redacted": bool(safe_destination.get("redacted")),
            "reason": reason,
            "evidence_source": "response_location_header",
        }
    except Exception:
        return None


def bounded_settle(page, max_ms=5000, sample_ms=250, stable_samples=3):
    """Wait for bounded DOM/resource stability without using ``networkidle``.

    This is intentionally a reported heuristic, not a claim that every
    asynchronous application task has completed.
    """
    max_ms = max(0, int(max_ms))
    sample_ms = max(50, int(sample_ms))
    stable_samples = max(1, int(stable_samples))
    started = time.monotonic()
    previous = None
    consecutive = 0
    samples = 0
    final_sample = None
    errors = []

    while (time.monotonic() - started) * 1000 < max_ms:
        page.wait_for_timeout(sample_ms)
        try:
            sample = page.evaluate(
                """() => {
                    const body = document.body;
                    const root = document.documentElement;
                    const pendingImages = Array.from(document.images || [])
                        .filter(img => !img.complete).length;
                    return {
                        readyState: document.readyState,
                        domNodes: document.getElementsByTagName('*').length,
                        resourceCount: performance.getEntriesByType('resource').length,
                        scrollHeight: Math.max(body ? body.scrollHeight : 0,
                                               root ? root.scrollHeight : 0),
                        pendingImages,
                        fontStatus: document.fonts ? document.fonts.status : 'unsupported'
                    };
                }"""
            )
        except Exception as exc:  # page may navigate or close while settling
            errors.append(redact_error_text(exc).split("\n")[0])
            break
        samples += 1
        final_sample = sample
        fingerprint = (
            sample.get("readyState"), sample.get("domNodes"),
            sample.get("resourceCount"), sample.get("scrollHeight"),
            sample.get("pendingImages"), sample.get("fontStatus"),
        )
        ready = sample.get("readyState") in ("interactive", "complete")
        if ready and fingerprint == previous:
            consecutive += 1
        else:
            consecutive = 1 if ready else 0
        previous = fingerprint
        if consecutive >= stable_samples:
            break

    elapsed_ms = int((time.monotonic() - started) * 1000)
    stable = consecutive >= stable_samples
    return {
        "strategy": "domcontentloaded_plus_bounded_stability",
        "max_ms": max_ms,
        "sample_ms": sample_ms,
        "required_stable_samples": stable_samples,
        "samples": samples,
        "elapsed_ms": elapsed_ms,
        "stable": stable,
        "timed_out": not stable and not errors,
        "final_sample": final_sample,
        "errors": errors,
    }


def scroll_profile(page):
    """Inspect native, internal-container, and likely virtual scroll state."""
    return page.evaluate(
        """() => {
            const marker = 'data-nt-site-mirror-scroll-target';
            document.querySelectorAll('[' + marker + ']').forEach(el =>
                el.removeAttribute(marker));
            const body = document.body, root = document.documentElement;
            const scrollHeight = Math.max(body ? body.scrollHeight : 0,
                                          root ? root.scrollHeight : 0);
            const overflowHidden = [body, root].some(el => {
                if (!el) return false;
                const value = getComputedStyle(el).overflowY;
                return value === 'hidden' || value === 'clip';
            });
            let best = null;
            for (const el of document.querySelectorAll('body *')) {
                const style = getComputedStyle(el);
                if (!['auto', 'scroll'].includes(style.overflowY)) continue;
                if (el.scrollHeight <= el.clientHeight + 40) continue;
                const rect = el.getBoundingClientRect();
                if (rect.width < 120 || rect.height < 120) continue;
                if (rect.bottom <= 0 || rect.top >= innerHeight) continue;
                const score = rect.width * Math.min(rect.height, innerHeight) *
                              (el.scrollHeight - el.clientHeight);
                if (!best || score > best.score) best = {el, score, rect, style};
            }
            let internal = null;
            if (best) {
                best.el.setAttribute(marker, '1');
                internal = {
                    tag: best.el.tagName.toLowerCase(),
                    clientHeight: best.el.clientHeight,
                    scrollHeight: best.el.scrollHeight,
                    scrollTop: best.el.scrollTop,
                    overflowY: best.style.overflowY
                };
            }
            const virtualSignals = [];
            if (overflowHidden && scrollHeight <= innerHeight * 1.1 && !internal)
                virtualSignals.push('root_overflow_hidden_without_native_range');
            if (document.querySelector('[data-scroll-container], [data-lenis-prevent], .smooth-scroll'))
                virtualSignals.push('virtual_scroll_marker');
            return {
                scrollHeight,
                innerHeight,
                windowScrollY: window.scrollY,
                windowRange: Math.max(0, scrollHeight - innerHeight),
                rootOverflowHidden: overflowHidden,
                internalContainer: internal,
                virtualSignals
            };
        }"""
    )


def explore_scroll(page, steps=10, wait_ms=400, wheel_delta=800):
    """Exercise the best available scroll mechanism and report what was used."""
    steps = max(0, int(steps))
    wait_ms = max(0, int(wait_ms))
    wheel_delta = max(1, int(wheel_delta))
    profile = scroll_profile(page)
    if steps == 0:
        return {
            "mechanism": "not_exercised",
            "steps_requested": 0,
            "steps_completed": 0,
            "returned_to_start": True,
            "profile": profile,
            "warnings": ["Scroll exploration was explicitly disabled."],
        }
    mechanism = "none"
    completed = 0
    returned = False
    warnings = []
    observations = {}

    def drive_wheel(fallback_reason=None):
        nonlocal mechanism, completed, returned
        mechanism = "wheel_virtual_scroll"
        completed = 0
        if fallback_reason:
            warnings.append(fallback_reason)
        try:
            if profile.get("internalContainer"):
                page.hover('[data-nt-site-mirror-scroll-target="1"]')
        except Exception:
            warnings.append("Could not focus the internal scroll target before wheel fallback.")
        for _ in range(steps):
            page.mouse.wheel(0, wheel_delta)
            page.wait_for_timeout(wait_ms)
            completed += 1
        page.mouse.wheel(0, -wheel_delta * steps)
        page.wait_for_timeout(min(1200, max(200, wait_ms * 2)))
        returned = False
        warnings.append(
            "Wheel events were exercised, but virtual-scroll coverage and return "
            "to the initial state cannot be proven from document position alone."
        )

    internal = profile.get("internalContainer")
    virtual = bool(profile.get("virtualSignals"))
    if internal:
        mechanism = "internal_container"
        total = max(1, internal["scrollHeight"] - internal["clientHeight"])
        observed_positions = []
        for index in range(1, steps + 1):
            target = int(total * index / steps)
            page.eval_on_selector(
                '[data-nt-site-mirror-scroll-target="1"]',
                "(el, y) => { el.scrollTop = y; }", target,
            )
            page.wait_for_timeout(wait_ms)
            observed_positions.append(page.eval_on_selector(
                '[data-nt-site-mirror-scroll-target="1"]', "el => el.scrollTop"
            ))
            completed += 1
        page.eval_on_selector(
            '[data-nt-site-mirror-scroll-target="1"]',
            "el => { el.scrollTop = 0; }",
        )
        page.wait_for_timeout(min(800, max(100, wait_ms)))
        final_position = page.eval_on_selector(
            '[data-nt-site-mirror-scroll-target="1"]', "el => el.scrollTop"
        )
        observations["internal_scroll_top_max"] = max(observed_positions or [0])
        observations["internal_scroll_top_after_return"] = final_position
        returned = final_position <= 1
        if observations["internal_scroll_top_max"] <= internal.get("scrollTop", 0) + 1:
            drive_wheel(
                "The selected internal container did not move; wheel-driven "
                "virtual-scroll fallback was exercised."
            )
    elif profile.get("windowRange", 0) > 40 and not virtual:
        mechanism = "window_scroll"
        total = profile["windowRange"]
        observed_positions = []
        for index in range(1, steps + 1):
            target = int(total * index / steps)
            page.evaluate("y => window.scrollTo(0, y)", target)
            page.wait_for_timeout(wait_ms)
            observed_positions.append(page.evaluate("() => window.scrollY"))
            completed += 1
        page.evaluate("() => window.scrollTo(0, 0)")
        page.wait_for_timeout(min(800, max(100, wait_ms)))
        final_position = page.evaluate("() => window.scrollY")
        observations["window_scroll_y_max"] = max(observed_positions or [0])
        observations["window_scroll_y_after_return"] = final_position
        returned = final_position <= 1
        if observations["window_scroll_y_max"] <= profile.get("windowScrollY", 0) + 1:
            drive_wheel(
                "Native window scroll did not move; wheel-driven virtual-scroll "
                "fallback was exercised."
            )
    elif virtual:
        drive_wheel()
    else:
        warnings.append("No scrollable range or virtual-scroll signal was detected.")

    try:
        page.evaluate(
            """() => document.querySelectorAll(
                '[data-nt-site-mirror-scroll-target]'
            ).forEach(el => el.removeAttribute('data-nt-site-mirror-scroll-target'))"""
        )
    except Exception:
        warnings.append("Temporary scroll-target marker could not be removed.")

    return {
        "mechanism": mechanism,
        "steps_requested": steps,
        "steps_completed": completed,
        "returned_to_start": returned,
        "profile": profile,
        "observations": observations,
        "warnings": warnings,
    }


def detect_access_state(page, response_status=None, final_url=None):
    """Detect access/challenge/error interstitials without interacting with them."""
    final_url = final_url or getattr(page, "url", "")
    safe_final = sanitize_url(final_url)
    try:
        observed = page.evaluate(
            """markers => {
                const visible = el => {
                    if (!el) return false;
                    const style = getComputedStyle(el);
                    const rect = el.getBoundingClientRect();
                    return style.display !== 'none' && style.visibility !== 'hidden' &&
                           rect.width > 0 && rect.height > 0;
                };
                const title = document.title || '';
                const bodyText = (document.body ? document.body.innerText : '').toLowerCase();
                const lowerTitle = title.toLowerCase();
                const selectorMap = {
                    cloudflare_challenge: '#challenge-form, .cf-challenge, [class*="cf-turnstile"]',
                    captcha: 'iframe[src*="captcha"], [class*="h-captcha"], .g-recaptcha',
                    access_wall: '[id="access-denied" i], [id="request-blocked" i], [data-access-wall]',
                    password_field: 'input[type="password"]'
                };
                const selectorHits = [];
                let visiblePasswordFields = 0;
                for (const [name, selector] of Object.entries(selectorMap)) {
                    const matches = Array.from(document.querySelectorAll(selector)).filter(visible);
                    if (matches.length) selectorHits.push(name);
                    if (name === 'password_field') visiblePasswordFields = matches.length;
                }
                let consentCoverage = 0;
                const consentSelectors = [
                    '[id*="consent" i]', '[class*="consent" i]',
                    '[id*="cookie" i]', '[class*="cookie" i]',
                    '[aria-label*="consent" i]'
                ];
                for (const selector of consentSelectors) {
                    for (const el of document.querySelectorAll(selector)) {
                        if (!visible(el)) continue;
                        const rect = el.getBoundingClientRect();
                        consentCoverage = Math.max(consentCoverage,
                            Math.min(1, (rect.width * rect.height) / (innerWidth * innerHeight)));
                    }
                }
                return {
                    title,
                    titleChallengeMarkers: markers.challengeTitles.filter(m => lowerTitle.includes(m)),
                    bodyChallengeMarkers: markers.challengeBodies.filter(m => bodyText.includes(m)),
                    titleLoginMarkers: markers.login.filter(m => lowerTitle.includes(m)),
                    bodyLoginMarkers: markers.login.filter(m => bodyText.includes(m)),
                    titleErrorMarkers: markers.errors.filter(m => lowerTitle.includes(m)),
                    bodyErrorMarkers: markers.errors.filter(m => bodyText.includes(m)),
                    selectorHits,
                    visiblePasswordFields,
                    consentOverlayCoverage: Number(consentCoverage.toFixed(3)),
                    rootOverflowLocked: [document.body, document.documentElement].some(el => {
                        if (!el) return false;
                        const y = getComputedStyle(el).overflowY;
                        return y === 'hidden' || y === 'clip';
                    })
                };
            }""",
            {
                "challengeTitles": list(CHALLENGE_TITLE_MARKERS),
                "challengeBodies": list(CHALLENGE_BODY_MARKERS),
                "login": list(LOGIN_MARKERS),
                "errors": list(ERROR_MARKERS),
            },
        )
    except Exception as exc:
        return {
            "state": "inspection_error",
            "blocked": True,
            "title": "",
            "final_url": safe_final["url"],
            "evidence": {"inspection_error": redact_error_text(exc).split("\n")[0]},
        }

    lower_url = safe_final["url"].lower()
    path = urlsplit(lower_url).path
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
    status = int(response_status) if response_status is not None else None
    selector_hits = observed["selectorHits"]
    challenge_textual = bool(
        observed["titleChallengeMarkers"] or observed["bodyChallengeMarkers"]
    )
    challenge_score = (
        int(challenge_textual) + len(url_challenge) +
        int("cloudflare_challenge" in selector_hits) * 2 +
        int("captcha" in selector_hits) * 2
    )
    exact_challenge_title = bool(EXACT_CHALLENGE_TITLE_RE.match(observed["title"]))
    exact_access_title = bool(EXACT_ACCESS_TITLE_RE.match(observed["title"]))
    exact_error_title = bool(EXACT_ERROR_TITLE_RE.match(observed["title"]))
    login_textual = bool(observed["titleLoginMarkers"] or
                         observed["bodyLoginMarkers"])
    login_route = bool(url_login)
    login_blocking = (
        bool(EXACT_LOGIN_TITLE_RE.match(observed["title"])) or
        (observed["visiblePasswordFields"] > 0 and (login_textual or login_route)) or
        (login_route and login_textual)
    )
    consent_blocking = (
        observed["consentOverlayCoverage"] >= 0.75 and observed["rootOverflowLocked"]
    )

    if exact_challenge_title or challenge_score >= 2:
        state, blocked = "blocked_by_challenge", True
    elif status in (401, 403):
        state, blocked = "blocked_by_access", True
    elif login_blocking:
        state, blocked = "blocked_by_login", True
    elif status is not None and status >= 400:
        state, blocked = "http_error", True
    elif exact_access_title or "access_wall" in selector_hits:
        state, blocked = "blocked_by_access", True
    elif exact_error_title:
        state, blocked = "error_document", True
    elif consent_blocking:
        state, blocked = "blocked_by_consent", True
    elif observed["consentOverlayCoverage"] > 0:
        state, blocked = "consent_present", False
    else:
        state, blocked = "ok", False

    return {
        "state": state,
        "blocked": blocked,
        "title": observed["title"],
        "final_url": safe_final["url"],
        "evidence": {
            "http_status": status,
            "url_challenge_markers": url_challenge,
            "title_challenge_markers": observed["titleChallengeMarkers"],
            "body_challenge_markers": observed["bodyChallengeMarkers"],
            "selector_markers": selector_hits,
            "url_login_markers": url_login,
            "title_login_markers": observed["titleLoginMarkers"],
            "body_login_markers": observed["bodyLoginMarkers"],
            "visible_password_fields": observed["visiblePasswordFields"],
            "title_error_markers": observed["titleErrorMarkers"],
            "body_error_markers": observed["bodyErrorMarkers"],
            "consent_overlay_coverage": observed["consentOverlayCoverage"],
            "root_overflow_locked": observed["rootOverflowLocked"],
        },
    }


def inspect_service_workers(page):
    """Inventory registrations, controller state, cache names, and cache keys."""
    try:
        result = page.evaluate(
            """async () => {
                const out = {
                    apiAvailable: 'serviceWorker' in navigator,
                    controller: null,
                    registrations: [],
                    cacheNames: [],
                    precacheResources: [],
                    precacheTruncated: false,
                    errors: []
                };
                if ('serviceWorker' in navigator) {
                    try {
                        const regs = await navigator.serviceWorker.getRegistrations();
                        out.controller = navigator.serviceWorker.controller ? {
                            scriptURL: navigator.serviceWorker.controller.scriptURL,
                            state: navigator.serviceWorker.controller.state
                        } : null;
                        out.registrations = regs.map(reg => ({
                            scope: reg.scope,
                            updateViaCache: reg.updateViaCache,
                            installing: reg.installing ? {
                                scriptURL: reg.installing.scriptURL, state: reg.installing.state
                            } : null,
                            waiting: reg.waiting ? {
                                scriptURL: reg.waiting.scriptURL, state: reg.waiting.state
                            } : null,
                            active: reg.active ? {
                                scriptURL: reg.active.scriptURL, state: reg.active.state
                            } : null
                        }));
                    } catch (err) { out.errors.push('serviceWorker: ' + String(err)); }
                }
                if ('caches' in self) {
                    try {
                        out.cacheNames = await caches.keys();
                        for (const name of out.cacheNames) {
                            const cache = await caches.open(name);
                            const requests = await cache.keys();
                            for (const request of requests) {
                                if (out.precacheResources.length >= 500) {
                                    out.precacheTruncated = true;
                                    break;
                                }
                                out.precacheResources.push(request.url);
                            }
                            if (out.precacheTruncated) break;
                        }
                    } catch (err) { out.errors.push('cacheStorage: ' + String(err)); }
                }
                return out;
            }"""
        )
    except Exception as exc:
        return {
            "api_available": False,
            "controller": None,
            "registrations": [],
            "cache_names": [],
            "precache_resources": [],
            "precache_truncated": False,
            "errors": [redact_error_text(exc).split("\n")[0]],
        }

    def safe_worker(worker):
        if not worker:
            return None
        copy = dict(worker)
        copy["script_url"] = sanitize_url(copy.pop("scriptURL", ""))["url"]
        return copy

    registrations = []
    for registration in result.get("registrations", []):
        registrations.append({
            "scope": sanitize_url(registration.get("scope", ""))["url"],
            "update_via_cache": registration.get("updateViaCache"),
            "installing": safe_worker(registration.get("installing")),
            "waiting": safe_worker(registration.get("waiting")),
            "active": safe_worker(registration.get("active")),
        })
    controller = safe_worker(result.get("controller"))
    resources = [sanitize_url(url)["url"]
                 for url in result.get("precacheResources", [])]
    return {
        "api_available": bool(result.get("apiAvailable")),
        "controller": controller,
        "registrations": registrations,
        "cache_names": list(result.get("cacheNames", [])),
        "precache_resources": resources,
        "precache_truncated": bool(result.get("precacheTruncated")),
        "errors": [redact_error_text(value).split("\n")[0]
                   for value in result.get("errors", [])],
    }


def extract_metadata_references(page, include_manifest_icons=True):
    """Inventory page metadata URLs without retaining JSON-LD payloads.

    Same-origin web manifests are read only when ``include_manifest_icons`` is
    true.  Their icon URLs are inventoried; no icon body is fetched here.
    """
    raw = page.evaluate(
        """async includeManifestIcons => {
            const refs = [];
            const add = (value, kind, source, probe = null, base = document.baseURI) => {
                if (!value || typeof value !== 'string') return;
                try { refs.push({url: new URL(value, base).href,
                                 kind, source, probe}); } catch (_) {}
            };
            for (const meta of document.querySelectorAll('meta[property], meta[name]')) {
                const key = (meta.getAttribute('property') || meta.getAttribute('name') || '')
                    .toLowerCase();
                if (['og:image', 'og:image:url', 'og:image:secure_url'].includes(key))
                    add(meta.content, 'open_graph_image', 'meta[' + key + ']');
                if (['twitter:image', 'twitter:image:src'].includes(key))
                    add(meta.content, 'twitter_image', 'meta[' + key + ']');
            }
            const manifests = [];
            for (const link of document.querySelectorAll('link[href]')) {
                const rel = (link.rel || '').toLowerCase().split(/\\s+/);
                if (rel.includes('manifest')) {
                    add(link.href, 'web_manifest', 'link[rel=manifest]');
                    manifests.push(link.href);
                }
                if (rel.some(value => ['icon', 'shortcut', 'apple-touch-icon',
                                        'mask-icon'].includes(value)))
                    add(link.href, 'favicon', 'link[rel=' + rel.join(' ') + ']');
            }
            const walk = (value, trail = []) => {
                if (!value) return;
                if (Array.isArray(value)) {
                    value.forEach((item, index) => walk(item, trail.concat(String(index))));
                } else if (typeof value === 'object') {
                    for (const [key, child] of Object.entries(value)) {
                        const lower = key.toLowerCase();
                        if (lower === 'image' || lower === 'logo') {
                            const kind = lower === 'logo' ? 'json_ld_logo' : 'json_ld_image';
                            if (typeof child === 'string') add(child, kind, 'json-ld:' + trail.concat(key).join('.'));
                            else if (child && typeof child === 'object') {
                                if (typeof child.url === 'string') add(child.url, kind, 'json-ld:' + trail.concat(key, 'url').join('.'));
                                if (typeof child.contentUrl === 'string') add(child.contentUrl, kind, 'json-ld:' + trail.concat(key, 'contentUrl').join('.'));
                            }
                        }
                        walk(child, trail.concat(key));
                    }
                }
            };
            for (const script of document.querySelectorAll('script[type="application/ld+json"]')) {
                try { walk(JSON.parse(script.textContent || '')); } catch (_) {}
            }
            if (includeManifestIcons) {
                for (const manifestUrl of manifests) {
                    try {
                        const resolved = new URL(manifestUrl, document.baseURI);
                        if (resolved.origin !== location.origin) continue;
                        const response = await fetch(resolved.href, {
                            credentials: 'same-origin', redirect: 'manual'
                        });
                        const declaredLength = Number(
                            response.headers.get('content-length') || 0
                        );
                        const probe = {
                            status: response.status, finalUrl: response.url,
                            contentType: response.headers.get('content-type') || '',
                            responseType: response.type,
                            redirected: response.redirected,
                            redirectMode: 'manual',
                            declaredLength: declaredLength || null,
                            actualBytes: null,
                            skippedReason: null
                        };
                        const manifestRef = refs.find(item => item.kind === 'web_manifest' &&
                                                       item.url === resolved.href);
                        if (manifestRef) manifestRef.probe = probe;
                        // A manual cross-origin redirect is exposed as an
                        // opaque redirect (status 0). Never follow or parse it.
                        if (response.type === 'opaqueredirect' ||
                            (response.status >= 300 && response.status < 400)) {
                            probe.skippedReason = 'manual_redirect_not_followed';
                            continue;
                        }
                        if (!response.ok) {
                            probe.skippedReason = 'non_success_status';
                            continue;
                        }
                        const maxBytes = 1024 * 1024;
                        if (declaredLength > maxBytes) {
                            probe.skippedReason = 'manifest_body_too_large_declared';
                            continue;
                        }
                        if (!response.body || !response.body.getReader) {
                            probe.skippedReason = 'bounded_stream_reader_unavailable';
                            continue;
                        }
                        const reader = response.body.getReader();
                        const chunks = [];
                        let actualBytes = 0, tooLarge = false;
                        while (true) {
                            const {done, value} = await reader.read();
                            if (done) break;
                            actualBytes += value.byteLength;
                            if (actualBytes > maxBytes) {
                                tooLarge = true;
                                await reader.cancel();
                                break;
                            }
                            chunks.push(value);
                        }
                        probe.actualBytes = actualBytes;
                        if (tooLarge) {
                            probe.skippedReason = 'manifest_body_too_large_actual';
                            continue;
                        }
                        const combined = new Uint8Array(actualBytes);
                        let offset = 0;
                        for (const chunk of chunks) {
                            combined.set(chunk, offset); offset += chunk.byteLength;
                        }
                        let data;
                        try { data = JSON.parse(new TextDecoder().decode(combined)); }
                        catch (_) { probe.skippedReason = 'invalid_manifest_json'; continue; }
                        for (const icon of (Array.isArray(data.icons) ? data.icons : []))
                            // Manifest members resolve against the manifest URL,
                            // not document.baseURI.  Reading the manifest probes
                            // only the manifest; icons remain Observed-only.
                            add(icon && icon.src, 'manifest_icon',
                                'web-manifest:icons', null, resolved.href);
                    } catch (_) {}
                }
            }
            return refs;
        }""",
        bool(include_manifest_icons),
    )

    deduped = {}
    for item in raw or []:
        normalized = normalize_http_url(item.get("url", ""), getattr(page, "url", ""))
        if not normalized:
            continue
        safe = sanitize_url(normalized)
        key = (item.get("kind", "unknown"), safe["url"], item.get("source", ""))
        probe = item.get("probe")
        if probe:
            probe = {
                "status": probe.get("status"),
                "content_type": probe.get("contentType", ""),
                "final_url": sanitize_url(probe.get("finalUrl", normalized))["url"],
                "method": "GET",
                "metadata_only": True,
                "response_type": probe.get("responseType"),
                "redirected": probe.get("redirected"),
                "redirect_mode": probe.get("redirectMode"),
                "declared_length": probe.get("declaredLength"),
                "actual_bytes": probe.get("actualBytes"),
                "skipped_reason": probe.get("skippedReason"),
            }
        deduped[key] = {
            "url": safe["url"],
            "url_redacted": safe["redacted"],
            "sensitive_query_keys": safe["sensitive_query_keys"],
            "kind": item.get("kind", "unknown"),
            "source": item.get("source", ""),
            "observed": True,
            "probed": bool(probe),
            "captured": False,
            "states": ["Observed"] + (["Probed"] if probe else []),
            "probe": probe,
        }
    return list(deduped.values())
