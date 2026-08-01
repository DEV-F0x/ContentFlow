import os
from pathlib import Path

from dotenv import find_dotenv, load_dotenv

# Anchor relative SQLITE_PATH/LOCAL_STORAGE_PATH to the directory containing
# .env (the repo root) instead of the process cwd, which varies depending
# on whether the app is launched from the repo root or services/dashboard/.
#
# Under Docker there IS no on-disk .env to anchor to: `env_file: .env` in
# docker-compose.yml injects its variables straight into the container's
# environment without ever copying the file itself in, and the root
# .dockerignore excludes .env/.env.* from the build context too -- so
# find_dotenv() always comes up empty there. Falling back to cwd in that
# case resolves relative paths against /app (the code, from WORKDIR)
# instead of the repo root, so e.g. the shipped LOCAL_STORAGE_PATH=
# ./data/storage would silently write into the container's throwaway layer
# at /app/data/storage instead of the volume docker-compose.yml actually
# mounts at /data -- gone on the next `docker compose up`.
#
# docker-compose.yml only ever bind-mounts the repo root's ./data (not the
# whole repo) into the container, at /data -- so "/" is the right stand-in
# for "the repo root" here: it makes a relative ./data/... path (the only
# relative paths that can persist under Docker at all, since nothing else
# is mounted) resolve to /data/..., matching that mount exactly.
_dotenv_path = find_dotenv()
load_dotenv(_dotenv_path)
_BASE_DIR = Path(_dotenv_path).resolve().parent if _dotenv_path else Path("/")


def _resolve_path(value):
    path = Path(value)
    return path if path.is_absolute() else (_BASE_DIR / path).resolve()


def _database_url(backend):
    if backend == "sqlite":
        path = _resolve_path(os.environ.get("SQLITE_PATH", "/data/dashboard.db"))
        path.parent.mkdir(parents=True, exist_ok=True)
        return f"sqlite:///{path}"

    user = os.environ["POSTGRES_USER"]
    password = os.environ["POSTGRES_PASSWORD"]
    host = os.environ.get("POSTGRES_HOST", "postgres")
    port = os.environ.get("POSTGRES_PORT", "5432")
    db_name = os.environ["POSTGRES_DB"]
    return f"postgresql+psycopg://{user}:{password}@{host}:{port}/{db_name}"


class Config:
    # "postgres" or "sqlite" (a single file at SQLITE_PATH).
    DB_BACKEND = os.environ.get("DB_BACKEND", "postgres").lower()
    # "s3" (MinIO/S3) or "local" (bind-mounted filesystem at LOCAL_STORAGE_PATH).
    STORAGE_BACKEND = os.environ.get("STORAGE_BACKEND", "s3").lower()

    SECRET_KEY = os.environ["DASHBOARD_SECRET_KEY"]
    SQLALCHEMY_DATABASE_URI = _database_url(DB_BACKEND)
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Public host used to build asset links/embed tags; this is the API,
    # which is the only thing that ever serves file bytes.
    API_PUBLIC_URL = os.environ.get(
        "API_PUBLIC_URL", "http://localhost:5000"
    )

    LOCAL_STORAGE_PATH = _resolve_path(
        os.environ.get("LOCAL_STORAGE_PATH", "/data/storage")
    )

    if STORAGE_BACKEND == "s3":
        S3_ENDPOINT_URL = os.environ["S3_ENDPOINT_URL"]
        S3_ACCESS_KEY = os.environ["S3_ACCESS_KEY"]
        S3_SECRET_KEY = os.environ["S3_SECRET_KEY"]
        S3_BUCKET = os.environ["S3_BUCKET"]
        S3_REGION = os.environ.get("S3_REGION", "us-east-1")

    # Unset by default: any asset type/size is accepted. Set MAX_UPLOAD_MB
    # to cap it if needed.
    _max_upload_mb = os.environ.get("MAX_UPLOAD_MB")
    MAX_CONTENT_LENGTH = (
        int(_max_upload_mb) * 1024 * 1024 if _max_upload_mb else None
    )

    # Login methods -- either or both may be on. There is a single admin
    # identity, configured entirely via env vars (no accounts table, no
    # database row -- login is just a string comparison against these).
    # Basic auth checks username+password against
    # ADMIN_USERNAME/ADMIN_PASSWORD below. OAuth (a generic OAuth2 client --
    # any provider that exposes an authorize/token/userinfo endpoint works)
    # only accepts a login whose returned email matches ADMIN_USERNAME, so
    # it only makes sense to enable OAuth if ADMIN_USERNAME is set to that
    # same email address.
    AUTH_BASIC_ENABLED = (
        os.environ.get("AUTH_BASIC_ENABLED", "true").lower() == "true"
    )
    AUTH_OAUTH_ENABLED = (
        os.environ.get("AUTH_OAUTH_ENABLED", "false").lower() == "true"
    )

    if not AUTH_BASIC_ENABLED and not AUTH_OAUTH_ENABLED:
        raise RuntimeError(
            "At least one of AUTH_BASIC_ENABLED / AUTH_OAUTH_ENABLED must "
            "be true, otherwise nobody would be able to log in."
        )

    ADMIN_USERNAME = os.environ["ADMIN_USERNAME"].strip().lower()

    if AUTH_BASIC_ENABLED:
        ADMIN_PASSWORD = os.environ["ADMIN_PASSWORD"]

    if AUTH_OAUTH_ENABLED:
        OAUTH_CLIENT_ID = os.environ["OAUTH_CLIENT_ID"]
        OAUTH_CLIENT_SECRET = os.environ["OAUTH_CLIENT_SECRET"]
        OAUTH_AUTHORIZE_URL = os.environ["OAUTH_AUTHORIZE_URL"]
        OAUTH_TOKEN_URL = os.environ["OAUTH_TOKEN_URL"]
        OAUTH_USERINFO_URL = os.environ["OAUTH_USERINFO_URL"]
        OAUTH_SCOPE = os.environ.get("OAUTH_SCOPE", "openid email profile")
        # Required whenever OAUTH_SCOPE includes "openid": the provider then
        # returns a signed id_token alongside the access token, and Authlib
        # verifies its signature against this JWKS endpoint automatically.
        OAUTH_JWKS_URL = os.environ.get("OAUTH_JWKS_URL")
        # Key in the userinfo JSON response that holds the user's email --
        # providers disagree on this ("email" covers OIDC-compliant ones).
        OAUTH_EMAIL_FIELD = os.environ.get("OAUTH_EMAIL_FIELD", "email")
        # false (default): only a login whose email matches ADMIN_USERNAME
        # is accepted. true: ANY user who successfully authenticates with
        # the OAuth provider is let in -- use this when the provider itself
        # is already the access boundary (e.g. only invited users can even
        # authenticate against your Authentik application in the first
        # place), so there is no separate local allow-list to maintain.
        OAUTH_ALLOW_SIGNUP = (
            os.environ.get("OAUTH_ALLOW_SIGNUP", "false").lower() == "true"
        )
