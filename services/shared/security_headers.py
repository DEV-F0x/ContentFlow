# coding=utf-8
"""
Security response headers applied to every Flask response.

Remove the corresponding middleware from Traefik for this service
and keep the policy in one place here instead.
"""

# ── Content Security Policy ──────────────────────────────────────────────────
# Adjust each directive as CDNs / integrations change.
_CSP_DIRECTIVES = {
    "default-src":  "'self'",
    "script-src": (
        "'self' https://cdn.jsdelivr.net https://mozilla.github.io"
    ),
    "style-src":    "'self' https://cdn.jsdelivr.net",
    "img-src":      "'self' data: https:",
    "font-src":     "'self' https://cdn.jsdelivr.net",
    # Grafana Faro telemetry requires its collector endpoint; cdn.jsdelivr.net
    # is needed so DevTools can fetch source maps for CDN-hosted scripts.
    "connect-src":  (
        "'self' https://faro-collector-prod-eu-west-2.grafana.net "
        "https://cdn.jsdelivr.net"
    ),
    # Allow OpenStreetMap iframes and blob: URLs (PDF preview fallback)
    "frame-src":    "https://www.openstreetmap.org blob:",
    "frame-ancestors": "'self'",
}

_CSP = "; ".join(f"{k} {v}" for k, v in _CSP_DIRECTIVES.items()) + ";"

# ── Permissions Policy ───────────────────────────────────────────────────────
_PERMISSIONS_POLICY = (
    "camera=(), microphone=(), geolocation=(), payment=(), usb=(), "
    "magnetometer=(), gyroscope=(), accelerometer=(), fullscreen=(self)"
)

# ── CORS (mirrors Traefik accessControl* settings) ───────────────────────────
_CORS_ALLOW_METHODS = "GET, OPTIONS, PUT, POST, DELETE"
_CORS_MAX_AGE = "100"

# ── HSTS ─────────────────────────────────────────────────────────────────────
_HSTS = "max-age=31536000; includeSubDomains; preload"


def add_security_headers(response):
    """
    Attach security headers to every outgoing response.

    Register this with ``app.after_request`` in the application factory.
    """
    h = response.headers

    # CSP only makes sense for HTML — XML/JSON responses have no scripts or
    # styles, and applying it to XML causes the browser's built-in XML viewer
    # to fight the policy with its own inline styles.
    if "text/html" in (response.content_type or ""):
        h["Content-Security-Policy"] = _CSP

    # Clickjacking protection
    h["X-Frame-Options"] = "SAMEORIGIN"

    # MIME sniffing protection
    h["X-Content-Type-Options"] = "nosniff"

    # Referrer policy
    h["Referrer-Policy"] = "strict-origin-when-cross-origin"

    # HSTS (only meaningful over HTTPS; harmless over HTTP in dev)
    h["Strict-Transport-Security"] = _HSTS

    # Permissions policy
    h["Permissions-Policy"] = _PERMISSIONS_POLICY

    # XSS filter (legacy browsers)
    h["X-XSS-Protection"] = "1; mode=block"

    # CORS headers
    h["Access-Control-Allow-Methods"] = _CORS_ALLOW_METHODS
    h["Access-Control-Max-Age"] = _CORS_MAX_AGE

    return response
