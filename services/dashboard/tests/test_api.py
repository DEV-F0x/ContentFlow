import io

from conftest import PNG_BYTES


def _create(
    client, headers, filename="pic.png", data=PNG_BYTES, name=None, **extra
):
    form = {"file": (io.BytesIO(data), filename), **extra}
    if name is not None:
        form["name"] = name
    return client.post(
        "/api/v1/assets",
        data=form,
        headers=headers,
        content_type="multipart/form-data",
    )


def test_create_requires_auth_header(client):
    resp = _create(client, {}, name="no-auth")
    assert resp.status_code == 401


def test_create_rejects_wrong_token(client):
    resp = _create(client, {"Authorization": "Bearer wrong"}, name="bad-token")
    assert resp.status_code == 401


def test_api_disabled_without_token_configured(app):
    app.config["DASHBOARD_API_TOKEN"] = None
    resp = app.test_client().get("/api/v1/assets")
    assert resp.status_code == 503


def test_create_asset_returns_real_url(client, api_headers):
    resp = _create(client, api_headers, name="hero-image")
    assert resp.status_code == 201
    body = resp.get_json()
    assert body["name"] == "hero-image.png"
    assert body["url"] == "http://api.test/files/hero-image.png"
    assert body["sha256"]
    assert body["integrity"].startswith("sha384-")
    assert body["id"]


def test_create_duplicate_name_conflicts(client, api_headers):
    _create(client, api_headers, name="dupe")
    resp = _create(client, api_headers, name="dupe")
    assert resp.status_code == 409


def test_create_empty_file_rejected(client, api_headers):
    resp = _create(client, api_headers, data=b"", name="empty")
    assert resp.status_code == 400


def test_create_invalid_content_type_rejected(client, api_headers):
    resp = _create(
        client, api_headers, name="bad-ct", content_type="not-a-mime-type"
    )
    assert resp.status_code == 400


def test_list_and_get_asset(client, api_headers):
    created = _create(client, api_headers, name="listed").get_json()

    resp = client.get("/api/v1/assets", headers=api_headers)
    assert resp.status_code == 200
    assert any(a["id"] == created["id"] for a in resp.get_json())

    resp = client.get(f"/api/v1/assets/{created['id']}", headers=api_headers)
    assert resp.status_code == 200
    assert resp.get_json()["name"] == "listed.png"


def test_get_missing_asset_404s(client, api_headers):
    resp = client.get("/api/v1/assets/does-not-exist", headers=api_headers)
    assert resp.status_code == 404


def test_patch_renames_asset(client, api_headers):
    created = _create(client, api_headers, name="original").get_json()

    resp = client.patch(
        f"/api/v1/assets/{created['id']}",
        data={"name": "renamed"},
        headers=api_headers,
        content_type="multipart/form-data",
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["name"] == "renamed.png"
    assert body["url"] == "http://api.test/files/renamed.png"

    assert client.get(
        "/api/v1/assets/does-not-exist", headers=api_headers
    ).status_code == 404


def test_patch_replaces_file_content(client, api_headers):
    created = _create(client, api_headers, name="replaceable").get_json()
    new_bytes = PNG_BYTES + b"\x00\x00\x00\x00"

    resp = client.patch(
        f"/api/v1/assets/{created['id']}",
        data={"file": (io.BytesIO(new_bytes), "new.png")},
        headers=api_headers,
        content_type="multipart/form-data",
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["size_bytes"] == len(new_bytes)
    assert body["sha256"] != created["sha256"]


def test_patch_toggles_force_download(client, api_headers):
    created = _create(client, api_headers, name="dl").get_json()
    assert created["force_download"] is False

    resp = client.patch(
        f"/api/v1/assets/{created['id']}",
        data={"force_download": "true"},
        headers=api_headers,
        content_type="multipart/form-data",
    )
    assert resp.status_code == 200
    assert resp.get_json()["force_download"] is True


def test_patch_missing_asset_404s(client, api_headers):
    resp = client.patch(
        "/api/v1/assets/does-not-exist",
        data={"name": "x"},
        headers=api_headers,
        content_type="multipart/form-data",
    )
    assert resp.status_code == 404


def test_delete_asset_removes_it(client, api_headers):
    created = _create(client, api_headers, name="throwaway").get_json()

    resp = client.delete(
        f"/api/v1/assets/{created['id']}", headers=api_headers
    )
    assert resp.status_code == 204

    resp = client.get(f"/api/v1/assets/{created['id']}", headers=api_headers)
    assert resp.status_code == 404


def test_delete_missing_asset_404s(client, api_headers):
    resp = client.delete("/api/v1/assets/does-not-exist", headers=api_headers)
    assert resp.status_code == 404
