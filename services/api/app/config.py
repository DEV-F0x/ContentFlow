import os
from pathlib import Path

from dotenv import find_dotenv, load_dotenv

# See the matching comment in services/dashboard/app/config.py: under
# Docker there's no on-disk .env for find_dotenv() to locate (env_file:
# injects variables directly, and .dockerignore excludes the file itself),
# so a relative LOCAL_STORAGE_PATH would otherwise silently resolve against
# the process cwd (/app, the code, from WORKDIR) instead of the repo root.
# docker-compose.yml only bind-mounts the repo root's ./data/storage (not
# the whole repo) into the container, at /data/storage -- so "/" stands in
# for "the repo root" here: it makes the shipped LOCAL_STORAGE_PATH=
# ./data/storage resolve to /data/storage, matching that mount.
_dotenv_path = find_dotenv()
load_dotenv(_dotenv_path)
_BASE_DIR = Path(_dotenv_path).resolve().parent if _dotenv_path else Path("/")


def _resolve_path(value):
    path = Path(value)
    return path if path.is_absolute() else (_BASE_DIR / path).resolve()


class Config:
    # "s3" (MinIO/S3) or "local" (bind-mounted filesystem at
    # LOCAL_STORAGE_PATH).
    STORAGE_BACKEND = os.environ.get("STORAGE_BACKEND", "s3").lower()
    LOCAL_STORAGE_PATH = _resolve_path(
        os.environ.get("LOCAL_STORAGE_PATH", "/data/storage")
    )

    if STORAGE_BACKEND == "s3":
        S3_ENDPOINT_URL = os.environ["S3_ENDPOINT_URL"]
        S3_ACCESS_KEY = os.environ["S3_ACCESS_KEY"]
        S3_SECRET_KEY = os.environ["S3_SECRET_KEY"]
        S3_BUCKET = os.environ["S3_BUCKET"]
        S3_REGION = os.environ.get("S3_REGION", "us-east-1")

    CSP_POLICY = os.environ.get(
        "CSP_POLICY",
        "default-src 'none'; img-src 'self'; style-src 'self'",
    )
