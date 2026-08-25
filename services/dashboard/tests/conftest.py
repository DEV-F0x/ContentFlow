import os
import re
import shutil
import sys
import tempfile
from pathlib import Path

import pytest

# All of this has to run before `from app import create_app` -- Config reads
# every env var exactly once, at first import, so tests never touch a real
# Postgres/MinIO/OAuth provider and never write into the dev data/ dir.
_TEST_DIR = Path(tempfile.mkdtemp(prefix="contentflow-dashboard-test-"))

os.environ["DASHBOARD_SECRET_KEY"] = "test-secret-key"
os.environ["DB_BACKEND"] = "sqlite"
os.environ["SQLITE_PATH"] = str(_TEST_DIR / "test.db")
os.environ["STORAGE_BACKEND"] = "local"
os.environ["LOCAL_STORAGE_PATH"] = str(_TEST_DIR / "storage")
os.environ["API_PUBLIC_URL"] = "http://api.test"
os.environ["AUTH_BASIC_ENABLED"] = "true"
os.environ["AUTH_OAUTH_ENABLED"] = "false"
os.environ["ADMIN_USERNAME"] = "testadmin"
os.environ["ADMIN_PASSWORD"] = "test-password-123"
os.environ["DASHBOARD_API_TOKEN"] = "test-api-token"

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import create_app  # noqa: E402
from app.extensions import db  # noqa: E402

ADMIN_USERNAME = os.environ["ADMIN_USERNAME"]
ADMIN_PASSWORD = os.environ["ADMIN_PASSWORD"]
API_TOKEN = os.environ["DASHBOARD_API_TOKEN"]

# 1x1 transparent PNG -- small enough to inline, real enough to exercise the
# "is this an image" thumbnail/tag logic.
PNG_BYTES = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108020000009077"
    "53de0000000c4944415408d763f8ffff3f0005fe02fea1e5e9560000000049454e44ae426082"
)


def _teardown_test_dir():
    shutil.rmtree(_TEST_DIR, ignore_errors=True)
    _TEST_DIR.mkdir(parents=True, exist_ok=True)
    (_TEST_DIR / "storage").mkdir(parents=True, exist_ok=True)


@pytest.fixture()
def app():
    flask_app = create_app()
    flask_app.config.update(TESTING=True)
    with flask_app.app_context():
        db.create_all()
        yield flask_app
        db.session.remove()
        db.drop_all()
    _teardown_test_dir()


@pytest.fixture()
def client(app):
    return app.test_client()


def extract_csrf_token(html: bytes) -> str:
    match = re.search(rb'name="csrf_token"[^>]*value="([^"]+)"', html)
    assert match, "csrf_token input not found in response"
    return match.group(1).decode()


@pytest.fixture()
def csrf_token(client):
    resp = client.get("/login")
    return extract_csrf_token(resp.data)


@pytest.fixture()
def api_headers():
    return {"Authorization": f"Bearer {API_TOKEN}"}


@pytest.fixture()
def logged_in_client(client, csrf_token):
    resp = client.post(
        "/login",
        data={
            "username": ADMIN_USERNAME,
            "password": ADMIN_PASSWORD,
            "csrf_token": csrf_token,
        },
    )
    assert resp.status_code == 302
    return client
