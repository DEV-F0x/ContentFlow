from conftest import ADMIN_PASSWORD, ADMIN_USERNAME, extract_csrf_token


def test_unauthenticated_request_redirects_to_login(client):
    resp = client.get("/", follow_redirects=False)
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]


def test_login_page_loads(client):
    resp = client.get("/login")
    assert resp.status_code == 200
    assert b"Username" in resp.data


def test_wrong_password_is_rejected(client, csrf_token):
    wrong_password = ADMIN_PASSWORD + "-wrong"
    resp = client.post(
        "/login",
        data={
            "username": ADMIN_USERNAME,
            "password": wrong_password,
            "csrf_token": csrf_token,
        },
        follow_redirects=True,
    )
    assert b"Invalid username or password" in resp.data


def test_wrong_username_is_rejected(client, csrf_token):
    resp = client.post(
        "/login",
        data={
            "username": "somebody-else",
            "password": ADMIN_PASSWORD,
            "csrf_token": csrf_token,
        },
        follow_redirects=True,
    )
    assert b"Invalid username or password" in resp.data


def test_login_missing_csrf_token_is_rejected(client):
    resp = client.post(
        "/login",
        data={"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD},
    )
    assert resp.status_code == 400


def test_login_wrong_csrf_token_is_rejected(client, csrf_token):
    resp = client.post(
        "/login",
        data={
            "username": ADMIN_USERNAME,
            "password": ADMIN_PASSWORD,
            "csrf_token": "garbage",
        },
    )
    assert resp.status_code == 400


def test_correct_credentials_log_in_and_reach_index(client, csrf_token):
    resp = client.post(
        "/login",
        data={
            "username": ADMIN_USERNAME,
            "password": ADMIN_PASSWORD,
            "csrf_token": csrf_token,
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert ADMIN_USERNAME.encode() in resp.data


def test_username_matching_is_case_insensitive(client, csrf_token):
    resp = client.post(
        "/login",
        data={
            "username": ADMIN_USERNAME.upper(),
            "password": ADMIN_PASSWORD,
            "csrf_token": csrf_token,
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert ADMIN_USERNAME.encode() in resp.data


def test_logout_requires_login_then_locks_index_again(logged_in_client):
    resp = logged_in_client.get("/")
    csrf = extract_csrf_token(resp.data)

    resp = logged_in_client.post(
        "/logout", data={"csrf_token": csrf}, follow_redirects=True
    )
    assert resp.status_code == 200
    assert b"Log in" in resp.data

    resp = logged_in_client.get("/", follow_redirects=False)
    assert resp.status_code == 302
