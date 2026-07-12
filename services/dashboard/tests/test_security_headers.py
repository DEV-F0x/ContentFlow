def test_security_headers_present_on_html_response(client):
    resp = client.get("/login")
    assert resp.status_code == 200
    assert resp.headers.get("X-Frame-Options") == "SAMEORIGIN"
    assert resp.headers.get("X-Content-Type-Options") == "nosniff"
    assert resp.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
    assert "max-age" in resp.headers.get("Strict-Transport-Security", "")
    assert resp.headers.get("Permissions-Policy")
    assert "Content-Security-Policy" in resp.headers


def test_security_headers_present_on_redirects_and_errors(client):
    resp = client.get("/", follow_redirects=False)
    assert resp.status_code == 302
    assert resp.headers.get("X-Frame-Options") == "SAMEORIGIN"

    resp = client.get("/this-route-does-not-exist")
    assert resp.status_code == 404
    assert resp.headers.get("X-Frame-Options") == "SAMEORIGIN"


def test_no_seo_robots_header(client):
    resp = client.get("/login")
    assert "X-Robots-Tag" not in resp.headers


def test_csp_not_set_on_json_response(client):
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.content_type.startswith("application/json")
    assert "Content-Security-Policy" not in resp.headers
