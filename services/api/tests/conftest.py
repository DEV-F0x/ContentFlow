import os
import shutil
import sys
import tempfile
from pathlib import Path

import pytest

_TEST_DIR = Path(tempfile.mkdtemp(prefix="contentflow-api-test-"))

os.environ["STORAGE_BACKEND"] = "local"
os.environ["LOCAL_STORAGE_PATH"] = str(_TEST_DIR / "storage")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import create_app  # noqa: E402

STORAGE_DIR = Path(os.environ["LOCAL_STORAGE_PATH"])


@pytest.fixture()
def app():
    flask_app = create_app()
    flask_app.config.update(TESTING=True)
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    yield flask_app
    shutil.rmtree(STORAGE_DIR, ignore_errors=True)


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def stored_file(app):
    def _write(key: str, data: bytes) -> Path:
        STORAGE_DIR.mkdir(parents=True, exist_ok=True)
        path = STORAGE_DIR / key
        path.write_bytes(data)
        return path

    return _write
