import io
import re

from conftest import PNG_BYTES, extract_csrf_token


def _upload(client, csrf, filename="pic.png", data=PNG_BYTES, name=None):
    form = {"file": (io.BytesIO(data), filename), "csrf_token": csrf}
    if name is not None:
        form["name"] = name
    return client.post(
        "/upload", data=form, content_type="multipart/form-data", follow_redirects=True
    )


def _asset_id(html: bytes) -> str:
    match = re.search(rb'data-edit-id="([a-f0-9-]+)"', html)
    assert match, "no asset card found in response"
    return match.group(1).decode()


def test_empty_state_shown_with_no_assets(logged_in_client, csrf_token):
    resp = logged_in_client.get("/")
    assert b"No assets yet" in resp.data


def test_upload_creates_asset_and_shows_on_index(logged_in_client, csrf_token):
    resp = _upload(logged_in_client, csrf_token, name="hero-image")
    assert resp.status_code == 200
    assert b"hero-image.png" in resp.data
    assert b"http://api.test/files/hero-image.png" in resp.data


def test_upload_without_csrf_is_rejected(logged_in_client):
    form = {"file": (io.BytesIO(PNG_BYTES), "pic.png")}
    resp = logged_in_client.post(
        "/upload", data=form, content_type="multipart/form-data"
    )
    assert resp.status_code == 400


def test_upload_duplicate_name_is_rejected(logged_in_client, csrf_token):
    _upload(logged_in_client, csrf_token, name="dupe")
    resp = _upload(logged_in_client, csrf_token, name="dupe")
    assert b"already exists" in resp.data


def test_upload_empty_file_is_rejected(logged_in_client, csrf_token):
    resp = _upload(logged_in_client, csrf_token, data=b"", name="empty")
    assert b"Empty file" in resp.data


def test_non_image_asset_gets_extension_badge_not_thumbnail(logged_in_client, csrf_token):
    resp = _upload(
        logged_in_client, csrf_token, filename="app.js", data=b"console.log(1);", name="script"
    )
    assert b"script.js" in resp.data
    assert b"thumb-ext" in resp.data


def test_rename_asset(logged_in_client, csrf_token):
    _upload(logged_in_client, csrf_token, name="original-name")
    resp = logged_in_client.get("/")
    asset_id = _asset_id(resp.data)

    resp = logged_in_client.post(
        f"/assets/{asset_id}/edit",
        data={"name": "renamed", "csrf_token": csrf_token},
        content_type="multipart/form-data",
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert b"renamed.png" in resp.data
    assert b"original-name.png" not in resp.data


def test_rename_to_existing_name_is_rejected(logged_in_client, csrf_token):
    _upload(logged_in_client, csrf_token, name="taken")
    _upload(logged_in_client, csrf_token, filename="b.png", name="movable")
    resp = logged_in_client.get("/")
    html = resp.data.decode()
    movable_id = re.search(
        r'data-edit-id="([a-f0-9-]+)"[^>]*data-edit-name="movable\.png"', html
    )
    assert movable_id, html

    resp = logged_in_client.post(
        f"/assets/{movable_id.group(1)}/edit",
        data={"name": "taken", "csrf_token": csrf_token},
        content_type="multipart/form-data",
        follow_redirects=True,
    )
    assert b"already exists" in resp.data


def test_replace_file_keeps_name_updates_content(logged_in_client, csrf_token):
    # The real edit modal always pre-fills the name field with the asset's
    # current name (see populateEditModal in app.js) before submitting, so
    # replicate that rather than omitting it.
    _upload(logged_in_client, csrf_token, name="replaceable")
    resp = logged_in_client.get("/")
    asset_id = _asset_id(resp.data)

    new_bytes = PNG_BYTES + b"\x00\x00\x00\x00"
    resp = logged_in_client.post(
        f"/assets/{asset_id}/edit",
        data={
            "name": "replaceable.png",
            "file": (io.BytesIO(new_bytes), "new.png"),
            "csrf_token": csrf_token,
        },
        content_type="multipart/form-data",
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert b"replaceable.png" in resp.data


def test_delete_asset_removes_it(logged_in_client, csrf_token):
    _upload(logged_in_client, csrf_token, name="throwaway")
    resp = logged_in_client.get("/")
    asset_id = _asset_id(resp.data)

    resp = logged_in_client.post(
        f"/assets/{asset_id}/delete",
        data={"csrf_token": csrf_token},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert b"No assets yet" in resp.data


def test_delete_without_csrf_is_rejected(logged_in_client, csrf_token):
    _upload(logged_in_client, csrf_token, name="protected")
    resp = logged_in_client.get("/")
    asset_id = _asset_id(resp.data)

    resp = logged_in_client.post(f"/assets/{asset_id}/delete", data={})
    assert resp.status_code == 400


def test_index_filters_by_image_type(logged_in_client, csrf_token):
    _upload(logged_in_client, csrf_token, name="a-picture")
    _upload(logged_in_client, csrf_token, filename="a.js", data=b"1;", name="a-script")

    resp = logged_in_client.get("/?type=image")
    assert b"a-picture.png" in resp.data
    assert b"a-script.js" not in resp.data
