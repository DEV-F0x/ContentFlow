import uuid
from datetime import datetime, timezone

from flask_login import UserMixin

from .extensions import db
from .tags import IMAGE_EXTS, build_tag, extension_of


def _new_id():
    return str(uuid.uuid4())


def _now():
    return datetime.now(timezone.utc)


class Asset(db.Model):
    __tablename__ = "assets"

    id = db.Column(db.String(36), primary_key=True, default=_new_id)
    # The name an asset is served under: /files/<name>. Also the storage
    # key, so it must be unique and filesystem/S3-key safe.
    name = db.Column(db.String(255), nullable=False, unique=True, index=True)
    original_filename = db.Column(db.String(255), nullable=False)
    content_type = db.Column(db.String(128), nullable=False)
    size_bytes = db.Column(db.Integer, nullable=False)
    sha256 = db.Column(db.String(64), nullable=False, index=True)
    sha384_b64 = db.Column(db.String(128), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=_now)

    def to_dict(self, api_public_url):
        url = f"{api_public_url}/files/{self.name}"
        integrity = f"sha384-{self.sha384_b64}"
        return {
            "id": self.id,
            "name": self.name,
            "original_filename": self.original_filename,
            "content_type": self.content_type,
            "size_bytes": self.size_bytes,
            "sha256": self.sha256,
            "integrity": integrity,
            "url": url,
            "tag": build_tag(self.name, url, integrity),
            "created_at": self.created_at.isoformat(),
            "is_image": extension_of(self.name) in IMAGE_EXTS,
        }


class AdminUser(UserMixin):
    """A logged-in identity -- not a database row. `username` round-trips
    through the signed session cookie (see get_id()/load_user), so whoever
    actually authenticated (basic auth's ADMIN_USERNAME, or an OAuth email)
    stays correct across requests instead of being re-derived from config."""

    def __init__(self, username):
        self.username = username

    def get_id(self):
        return self.username
