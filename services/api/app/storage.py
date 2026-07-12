import mimetypes
from pathlib import Path

import boto3
from botocore.client import Config as BotoConfig
from botocore.exceptions import ClientError
from flask import current_app, g

# Fill in gaps in the stdlib mimetypes DB for common web/media assets, so
# local-storage responses (which have no stored Content-Type) still get the
# right one from the file extension alone.
mimetypes.add_type("image/webp", ".webp")
mimetypes.add_type("image/avif", ".avif")
mimetypes.add_type("image/svg+xml", ".svg")
mimetypes.add_type("image/x-icon", ".ico")
mimetypes.add_type("font/woff", ".woff")
mimetypes.add_type("font/woff2", ".woff2")
mimetypes.add_type("application/javascript", ".js")
mimetypes.add_type("application/javascript", ".mjs")
mimetypes.add_type("text/css", ".css")
mimetypes.add_type("video/mp4", ".mp4")
mimetypes.add_type("video/webm", ".webm")
mimetypes.add_type("audio/mpeg", ".mp3")
mimetypes.add_type("audio/ogg", ".ogg")
mimetypes.add_type("audio/wav", ".wav")


def get_client():
    if "s3_client" not in g:
        g.s3_client = boto3.client(
            "s3",
            endpoint_url=current_app.config["S3_ENDPOINT_URL"],
            aws_access_key_id=current_app.config["S3_ACCESS_KEY"],
            aws_secret_access_key=current_app.config["S3_SECRET_KEY"],
            region_name=current_app.config["S3_REGION"],
            config=BotoConfig(
                signature_version="s3v4",
                s3={"addressing_style": "path"},
            ),
        )
    return g.s3_client


def _resolve_local_path(key):
    root = Path(current_app.config["LOCAL_STORAGE_PATH"]).resolve()
    target = (root / key).resolve()
    if target != root and root not in target.parents:
        return None
    return target


def fetch(key):
    """Look up an asset by its serving name (== storage key).

    Returns (source, content_type), where `source` is a local `Path` when
    serving from disk, or a streaming S3 body otherwise -- callers branch on
    `isinstance(source, Path)`. Returns None if the object doesn't exist.
    """
    if current_app.config["STORAGE_BACKEND"] == "local":
        path = _resolve_local_path(key)
        if not path or not path.is_file():
            return None
        content_type = (
            mimetypes.guess_type(key)[0] or "application/octet-stream"
        )
        return path, content_type

    client = get_client()
    try:
        obj = client.get_object(
            Bucket=current_app.config["S3_BUCKET"], Key=key
        )
    except ClientError:
        return None
    content_type = obj.get("ContentType") or (
        mimetypes.guess_type(key)[0] or "application/octet-stream"
    )
    return obj["Body"], content_type
