import base64
import hashlib
import mimetypes
import re
import secrets
from urllib.parse import urlparse

from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask_login import (
    current_user,
    login_required,
    login_user,
    logout_user,
)
from werkzeug.utils import secure_filename

from .extensions import db
from .minify import maybe_minify_asset
from .models import AdminUser, Asset
from .oauth import OAUTH_CLIENT_NAME, oauth
from .storage import delete_object, get_object, put_object
from .tags import IMAGE_EXTS, extension_of

dashboard_bp = Blueprint("dashboard", __name__)

# Presets offered in the "Serve as" dropdown -- anything else goes through
# the "Custom MIME type..." field instead. Kept short and to the point:
# these are the cases where the extension-guessed type is wrong for what
# the admin actually wants (e.g. an uploaded .html file that should render
# in the browser instead of the default download-only behavior most
# browsers apply to files linked from another origin).
_CONTENT_TYPE_PRESETS = {"text/plain", "text/html", "application/json"}
_MIME_TYPE_RE = re.compile(r"^[\w.+-]+/[\w.+-]+(?:\s*;\s*[\w.+-]+=[^\r\n;]+)*$")


def _resolve_content_type(default_content_type):
    """Resolve the Content-Type to serve an asset with.

    `default_content_type` is what it would be with no override -- the
    extension-guessed type for a new upload/replacement, or the asset's
    existing content_type when just renaming without replacing the file.
    Returns (content_type, error) -- error is a user-facing message when
    the submitted preset/custom value can't be used.
    """
    preset = request.form.get("content_type_preset", "").strip()
    if preset == "custom":
        custom = request.form.get("content_type_custom", "").strip()
        if not custom:
            return None, "Please enter a custom content type, or choose a preset."
        if not _MIME_TYPE_RE.match(custom):
            return None, (
                f'"{custom}" doesn\'t look like a valid content type '
                '(expected e.g. "text/html").'
            )
        return custom, None
    if preset in _CONTENT_TYPE_PRESETS:
        return preset, None
    return default_content_type, None


@dashboard_bp.before_request
def _enforce_csrf():
    if request.method == "POST":
        token = request.form.get("csrf_token")
        if not token or not secrets.compare_digest(
            token, session.get("csrf_token", "")
        ):
            abort(400, description="Invalid or missing CSRF token.")


@dashboard_bp.context_processor
def _inject_csrf_token():
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_urlsafe(32)
    return {"csrf_token": session["csrf_token"]}


def _safe_next(target):
    if not target:
        return None
    parsed = urlparse(target)
    if parsed.scheme or parsed.netloc:
        return None
    return target


def _constant_time_eq(a, b):
    return secrets.compare_digest(a.encode(), b.encode())


@dashboard_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))

    if request.method == "POST":
        if not current_app.config["AUTH_BASIC_ENABLED"]:
            flash("Password login is not enabled.", "error")
            return redirect(url_for("dashboard.login"))

        username = request.form.get("username", "").strip().lower()
        password = request.form.get("password", "")
        admin_username = current_app.config["ADMIN_USERNAME"]
        admin_password = current_app.config["ADMIN_PASSWORD"]
        if not (
            _constant_time_eq(username, admin_username)
            and _constant_time_eq(password, admin_password)
        ):
            flash("Invalid username or password.", "error")
            return redirect(url_for("dashboard.login"))

        login_user(AdminUser(admin_username))
        next_url = _safe_next(request.form.get("next"))
        return redirect(next_url or url_for("dashboard.index"))

    return render_template(
        "login.html",
        basic_enabled=current_app.config["AUTH_BASIC_ENABLED"],
        oauth_enabled=current_app.config["AUTH_OAUTH_ENABLED"],
        next=_safe_next(request.args.get("next")),
    )


@dashboard_bp.post("/logout")
@login_required
def logout():
    logout_user()
    flash("Logged out.", "success")
    return redirect(url_for("dashboard.login"))


@dashboard_bp.get("/login/oauth/start")
def oauth_start():
    if not current_app.config["AUTH_OAUTH_ENABLED"]:
        flash("OAuth login is not enabled.", "error")
        return redirect(url_for("dashboard.login"))

    client = oauth.create_client(OAUTH_CLIENT_NAME)
    redirect_uri = url_for("dashboard.oauth_callback", _external=True)
    return client.authorize_redirect(redirect_uri)


@dashboard_bp.get("/login/oauth/callback")
def oauth_callback():
    if not current_app.config["AUTH_OAUTH_ENABLED"]:
        flash("OAuth login is not enabled.", "error")
        return redirect(url_for("dashboard.login"))

    client = oauth.create_client(OAUTH_CLIENT_NAME)
    token = client.authorize_access_token()
    resp = client.get(current_app.config["OAUTH_USERINFO_URL"], token=token)
    resp.raise_for_status()
    info = resp.json()
    email_field = current_app.config["OAUTH_EMAIL_FIELD"]
    email = (info.get(email_field) or "").strip().lower()
    admin_username = current_app.config["ADMIN_USERNAME"]
    allow_signup = current_app.config["OAUTH_ALLOW_SIGNUP"]

    if not email:
        flash("Your OAuth provider did not return an email address.", "error")
        return redirect(url_for("dashboard.login"))

    if not allow_signup and not _constant_time_eq(email, admin_username):
        flash("This account is not authorized to log in.", "error")
        return redirect(url_for("dashboard.login"))

    login_user(AdminUser(email))
    return redirect(url_for("dashboard.index"))


@dashboard_bp.get("/")
@login_required
def index():
    asset_type = request.args.get("type", "").lower().lstrip(".")
    assets = Asset.query.order_by(Asset.created_at.desc()).all()
    if asset_type == "image":
        assets = [a for a in assets if extension_of(a.name) in IMAGE_EXTS]
    elif asset_type:
        assets = [
            a for a in assets if a.name.lower().endswith(f".{asset_type}")
        ]
    public_url = current_app.config["API_PUBLIC_URL"]
    return render_template(
        "index.html",
        assets=[a.to_dict(public_url) for a in assets],
        asset_type=asset_type,
    )


def _resolve_name(requested_name, original_filename):
    ext = extension_of(original_filename)
    if requested_name:
        name = secure_filename(requested_name)
        if ext and not name.lower().endswith(f".{ext}"):
            name = f"{name}.{ext}"
    else:
        name = secure_filename(original_filename)
    return name


@dashboard_bp.post("/upload")
@login_required
def upload():
    upload_file = request.files.get("file")
    if not upload_file or not upload_file.filename:
        flash("Please choose a file to upload.", "error")
        return redirect(url_for("dashboard.index", upload=1))

    data = upload_file.read()
    if not data:
        flash("Empty file.", "error")
        return redirect(url_for("dashboard.index", upload=1))

    original_filename = upload_file.filename
    data = maybe_minify_asset(original_filename, data)

    name = _resolve_name(request.form.get("name", "").strip(), original_filename)
    if not name:
        flash("Please provide a valid name for this asset.", "error")
        return redirect(url_for("dashboard.index", upload=1))

    if Asset.query.filter_by(name=name).first():
        flash(
            f'An asset named "{name}" already exists. Choose a different name.',
            "error",
        )
        return redirect(url_for("dashboard.index", upload=1))

    sha256 = hashlib.sha256(data).hexdigest()
    sha384_digest = hashlib.sha384(data).digest()
    sha384_b64 = base64.b64encode(sha384_digest).decode("ascii")
    default_content_type = (
        mimetypes.guess_type(name)[0]
        or upload_file.mimetype
        or "application/octet-stream"
    )
    content_type, content_type_error = _resolve_content_type(default_content_type)
    if content_type_error:
        flash(content_type_error, "error")
        return redirect(url_for("dashboard.index", upload=1))

    force_download = request.form.get("force_download") == "on"
    content_disposition = (
        f'attachment; filename="{name}"' if force_download else None
    )

    put_object(name, data, content_type, content_disposition)

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
        flash(
            f'An asset named "{name}" already exists. Choose a different name.',
            "error",
        )
        return redirect(url_for("dashboard.index", upload=1))

    flash("Asset uploaded.", "success")
    return redirect(url_for("dashboard.index"))


@dashboard_bp.post("/assets/<asset_id>/edit")
@login_required
def edit_asset(asset_id):
    asset = db.get_or_404(Asset, asset_id)

    replacement = request.files.get("file")
    has_replacement = bool(replacement and replacement.filename)
    original_filename = (
        replacement.filename if has_replacement else asset.original_filename
    )

    name = _resolve_name(request.form.get("name", "").strip(), original_filename)
    if not name:
        name = asset.name

    if name != asset.name and Asset.query.filter_by(name=name).first():
        flash(
            f'An asset named "{name}" already exists. Choose a different name.',
            "error",
        )
        return redirect(url_for("dashboard.index", edit=asset.id))

    if has_replacement:
        data = replacement.read()
        if not data:
            flash("Empty file.", "error")
            return redirect(url_for("dashboard.index", edit=asset.id))
        data = maybe_minify_asset(original_filename, data)
        default_content_type = (
            mimetypes.guess_type(name)[0]
            or replacement.mimetype
            or "application/octet-stream"
        )
    else:
        data = get_object(asset.name)
        default_content_type = asset.content_type

    content_type, content_type_error = _resolve_content_type(default_content_type)
    if content_type_error:
        flash(content_type_error, "error")
        return redirect(url_for("dashboard.index", edit=asset.id))

    force_download = request.form.get("force_download") == "on"
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
    asset.sha256 = hashlib.sha256(data).hexdigest()
    asset.sha384_b64 = base64.b64encode(
        hashlib.sha384(data).digest()
    ).decode("ascii")

    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        flash(
            f'An asset named "{name}" already exists. Choose a different name.',
            "error",
        )
        return redirect(url_for("dashboard.index", edit=asset.id))

    flash("Asset updated.", "success")
    return redirect(url_for("dashboard.index"))


@dashboard_bp.post("/assets/<asset_id>/delete")
@login_required
def delete_asset(asset_id):
    asset = db.get_or_404(Asset, asset_id)
    name = asset.name

    db.session.delete(asset)
    db.session.commit()
    delete_object(name)

    flash("Asset deleted.", "success")
    return redirect(url_for("dashboard.index"))
