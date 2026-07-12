import os

from dotenv import load_dotenv

load_dotenv()


class Config:
    # "s3" (MinIO/S3) or "local" (bind-mounted filesystem at LOCAL_STORAGE_PATH).
    STORAGE_BACKEND = os.environ.get("STORAGE_BACKEND", "s3").lower()
    LOCAL_STORAGE_PATH = os.environ.get("LOCAL_STORAGE_PATH", "/data/storage")

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
