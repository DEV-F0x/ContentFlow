import base64
import hashlib
import re

from werkzeug.utils import secure_filename

from .tags import extension_of

# Presets offered in the dashboard's "Serve as" dropdown -- anything else
# goes through the "Custom MIME type..." field instead. Kept short and to
# the point: these are the cases where the extension-guessed type is wrong
# for what the admin actually wants (e.g. an uploaded .html file that should
# render in the browser instead of the default download-only behavior most
# browsers apply to files linked from another origin).
CONTENT_TYPE_PRESETS = {"text/plain", "text/html", "application/json"}
MIME_TYPE_RE = re.compile(r"^[\w.+-]+/[\w.+-]+(?:\s*;\s*[\w.+-]+=[^\r\n;]+)*$")


def resolve_name(requested_name, original_filename):
    ext = extension_of(original_filename)
    if requested_name:
        name = secure_filename(requested_name)
        if ext and not name.lower().endswith(f".{ext}"):
            name = f"{name}.{ext}"
    else:
        name = secure_filename(original_filename)
    return name


def resolve_content_type_preset(preset, custom, default_content_type):
    """Resolve a Content-Type from the dashboard's preset/custom form
    fields. Returns (content_type, error) -- error is a user-facing message
    when the submitted preset/custom value can't be used."""
    if preset == "custom":
        custom = (custom or "").strip()
        if not custom:
            return None, "Please enter a custom content type, or choose a preset."
        if not MIME_TYPE_RE.match(custom):
            return None, (
                f'"{custom}" doesn\'t look like a valid content type '
                '(expected e.g. "text/html").'
            )
        return custom, None
    if preset in CONTENT_TYPE_PRESETS:
        return preset, None
    return default_content_type, None


def resolve_content_type_explicit(explicit, default_content_type):
    """Resolve a Content-Type from a single raw MIME string (or None/empty,
    meaning "use the default"). Used by the JSON API, which has no
    preset/custom split. Returns (content_type, error)."""
    if not explicit:
        return default_content_type, None
    if not MIME_TYPE_RE.match(explicit):
        return None, (
            f'"{explicit}" doesn\'t look like a valid content type '
            '(expected e.g. "text/html").'
        )
    return explicit, None


def hash_bytes(data):
    """Returns (sha256_hex, sha384_b64) for the given bytes."""
    sha256 = hashlib.sha256(data).hexdigest()
    sha384_b64 = base64.b64encode(hashlib.sha384(data).digest()).decode("ascii")
    return sha256, sha384_b64
