def test_healthz(client):
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.get_json() == {"status": "ok"}


def test_serve_existing_file(client, stored_file):
    stored_file("style.css", b"body { color: red; }")
    resp = client.get("/files/style.css")
    assert resp.status_code == 200
    assert resp.content_type == "text/css; charset=utf-8"
    assert resp.data == b"body { color: red; }"
    assert "max-age" in resp.headers.get("Cache-Control", "")


def test_serve_missing_file_is_404(client):
    resp = client.get("/files/does-not-exist.png")
    assert resp.status_code == 404


def test_content_type_guessed_from_extension(client, stored_file):
    stored_file("script.js", b"console.log(1);")
    resp = client.get("/files/script.js")
    assert resp.status_code == 200
    assert "javascript" in resp.content_type


def test_path_traversal_outside_storage_root_is_blocked(client, stored_file):
    stored_file("safe.txt", b"safe")
    resp = client.get("/files/../../../../etc/passwd")
    assert resp.status_code in (404, 400)
