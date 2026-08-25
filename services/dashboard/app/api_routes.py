import mimetypes
import secrets

from flask import Blueprint, current_app, jsonify, request
from werkzeug.utils import secure_filename

from .asset_ops import hash_bytes, resolve_content_type_explicit, resolve_name
from .extensions import db
from .models import Asset
from .storage import delete_object, get_object, put_object

# A small, token-authenticated JSON API for asset CRUD -- used by machine
# clients (e.g. the Terraform provider in terraform-provider-contentflow/)
# that can't do the dashboard's cookie-session + CSRF login flow. Mirrors
# upload()/edit_asset()/delete_asset() in routes.py exactly, sharing their
# helpers via .asset_ops, but returns JSON instead of redirecting/flashing.
api_bp = Blueprint("api", __name__, url_prefix="/api/v1")

_TRUTHY = {"1", "true", "on", "yes"}


def _truthy(value):
    return (value or "").strip().lower() in _TRUTHY


@api_bp.before_request
def _require_api_token():
    token = current_app.config["DASHBOARD_API_TOKEN"]
    if not token:
        return jsonify(error="The JSON API is not enabled on this server."), 503

    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return jsonify(error="Unauthorized"), 401
    provided = auth[len("Bearer "):]
    if not secrets.compare_digest(provided, token):
        return jsonify(error="Unauthorized"), 401


def _asset_dict(asset):
    return asset.to_dict(current_app.config["API_PUBLIC_URL"])


@api_bp.get("/assets")
def list_assets():
    assets = Asset.query.order_by(Asset.created_at.desc()).all()
    return jsonify([_asset_dict(a) for a in assets])


@api_bp.get("/assets/<asset_id>")
def get_asset(asset_id):
    asset = db.session.get(Asset, asset_id)
    if asset is None:
        return jsonify(error="Asset not found."), 404
    return jsonify(_asset_dict(asset))


@api_bp.post("/assets")
def create_asset():
    upload_file = request.files.get("file")
    if not upload_file or not upload_file.filename:
        return jsonify(error="A file is required."), 400

    data = upload_file.read()
    if not data:
        return jsonify(error="Empty file."), 400

    original_filename = upload_file.filename
    name = resolve_name(request.form.get("name", "").strip(), original_filename)
    if not name:
        return jsonify(error="Could not resolve a valid asset name."), 400

    if Asset.query.filter_by(name=name).first():
        return jsonify(error=f'An asset named "{name}" already exists.'), 409

    default_content_type = (
        mimetypes.guess_type(name)[0]
        or upload_file.mimetype
        or "application/octet-stream"
    )
    content_type, error = resolve_content_type_explicit(
        request.form.get("content_type", "").strip() or None,
        default_content_type,
    )
    if error:
        return jsonify(error=error), 400

    force_download = _truthy(request.form.get("force_download"))
    content_disposition = (
        f'attachment; filename="{name}"' if force_download else None
    )

    put_object(name, data, content_type, content_disposition)
    sha256, sha384_b64 = hash_bytes(data)

    asset = Asset(
        name=name,
        original_filename=secure_filename(original_filename),
        content_type=content_type,
        force_download=force_download,
        size_bytes=len(data),
        sha256=sha256,
        sha384_b64=sha384_b64,
    )
    db.session.add(asset)
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        delete_object(name)
        return jsonify(error=f'An asset named "{name}" already exists.'), 409

    return jsonify(_asset_dict(asset)), 201


@api_bp.patch("/assets/<asset_id>")
def update_asset(asset_id):
    asset = db.session.get(Asset, asset_id)
    if asset is None:
        return jsonify(error="Asset not found."), 404

    replacement = request.files.get("file")
    has_replacement = bool(replacement and replacement.filename)
    original_filename = (
        replacement.filename if has_replacement else asset.original_filename
    )

    requested_name = request.form.get("name")
    if requested_name is not None:
        name = resolve_name(requested_name.strip(), original_filename)
        if not name:
            name = asset.name
    else:
        name = asset.name

    if name != asset.name and Asset.query.filter_by(name=name).first():
        return jsonify(error=f'An asset named "{name}" already exists.'), 409

    if has_replacement:
        data = replacement.read()
        if not data:
            return jsonify(error="Empty file."), 400
        default_content_type = (
            mimetypes.guess_type(name)[0]
            or replacement.mimetype
            or "application/octet-stream"
        )
    else:
        data = get_object(asset.name)
        default_content_type = asset.content_type

    raw_content_type = request.form.get("content_type")
    content_type, error = resolve_content_type_explicit(
        raw_content_type.strip() if raw_content_type else None,
        default_content_type,
    )
    if error:
        return jsonify(error=error), 400

    force_download = (
        _truthy(request.form.get("force_download"))
        if "force_download" in request.form
        else asset.force_download
    )
    content_disposition = (
        f'attachment; filename="{name}"' if force_download else None
    )

    old_name = asset.name
    put_object(name, data, content_type, content_disposition)
    if name != old_name:
        delete_object(old_name)

    asset.name = name
    asset.original_filename = secure_filename(original_filename)
    asset.content_type = content_type
    asset.force_download = force_download
    asset.size_bytes = len(data)
    asset.sha256, asset.sha384_b64 = hash_bytes(data)

    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        return jsonify(error=f'An asset named "{name}" already exists.'), 409

    return jsonify(_asset_dict(asset))


@api_bp.delete("/assets/<asset_id>")
def delete_asset(asset_id):
    asset = db.session.get(Asset, asset_id)
    if asset is None:
        return jsonify(error="Asset not found."), 404

    name = asset.name
    db.session.delete(asset)
    db.session.commit()
    delete_object(name)

    return "", 204
