def test_restrictive_csp_on_every_response(client, stored_file):
    stored_file("a.png", b"\x89PNG")
    for resp in (client.get("/healthz"), client.get("/files/a.png")):
        assert resp.headers.get("Content-Security-Policy") == (
            "default-src 'none'; img-src 'self'; style-src 'self'"
        )


def test_shared_headers_present(client):
    resp = client.get("/healthz")
    assert resp.headers.get("X-Frame-Options") == "SAMEORIGIN"
    assert resp.headers.get("X-Content-Type-Options") == "nosniff"
    assert resp.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
    assert resp.headers.get("Permissions-Policy")


def test_no_seo_robots_header(client):
    resp = client.get("/healthz")
    assert "X-Robots-Tag" not in resp.headers


def test_headers_present_on_404(client):
    resp = client.get("/files/missing.png")
    assert resp.status_code == 404
    assert resp.headers.get("X-Frame-Options") == "SAMEORIGIN"
    assert "Content-Security-Policy" in resp.headers
