from pathlib import Path

import boto3
from botocore.client import Config as BotoConfig
from botocore.exceptions import ClientError
from flask import current_app, g


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


def _local_root():
    root = Path(current_app.config["LOCAL_STORAGE_PATH"])
    root.mkdir(parents=True, exist_ok=True)
    return root


def _is_local():
    return current_app.config["STORAGE_BACKEND"] == "local"


def get_object(key):
    if _is_local():
        return (_local_root() / key).read_bytes()

    client = get_client()
    body = client.get_object(Bucket=current_app.config["S3_BUCKET"], Key=key)
    return body["Body"].read()


def put_object(key, data, content_type):
    if _is_local():
        (_local_root() / key).write_bytes(data)
        return

    client = get_client()
    client.put_object(
        Bucket=current_app.config["S3_BUCKET"],
        Key=key,
        Body=data,
        ContentType=content_type,
    )


def delete_object(key):
    if _is_local():
        (_local_root() / key).unlink(missing_ok=True)
        return

    client = get_client()
    try:
        client.delete_object(Bucket=current_app.config["S3_BUCKET"], Key=key)
    except ClientError:
        pass
