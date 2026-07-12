import mimetypes

IMAGE_EXTS = {"png", "jpg", "jpeg", "gif", "webp", "svg", "avif", "ico", "bmp"}
VIDEO_EXTS = {"mp4", "webm", "ogv", "mov"}
AUDIO_EXTS = {"mp3", "wav", "ogg", "m4a", "flac"}
FONT_EXTS = {"woff", "woff2", "ttf", "otf", "eot"}

# Fill in gaps in the stdlib mimetypes DB for common web/media assets, so
# uploads get a correct Content-Type regardless of the browser-supplied one.
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


def extension_of(name: str) -> str:
    return name.rsplit(".", 1)[-1].lower() if "." in name else ""


def build_tag(name: str, url: str, integrity: str) -> str:
    ext = extension_of(name)

    if ext == "js":
        return (
            f'<script src="{url}" integrity="{integrity}" '
            f'crossorigin="anonymous"></script>'
        )
    if ext == "css":
        return (
            f'<link rel="stylesheet" href="{url}" '
            f'integrity="{integrity}" crossorigin="anonymous">'
        )
    if ext in IMAGE_EXTS:
        return f'<img src="{url}" alt="{name}">'
    if ext in VIDEO_EXTS:
        return f'<video src="{url}" controls></video>'
    if ext in AUDIO_EXTS:
        return f'<audio src="{url}" controls></audio>'
    if ext in FONT_EXTS:
        return (
            f'<link rel="preload" href="{url}" as="font" '
            f'type="font/{ext}" crossorigin>'
        )
    return f'<a href="{url}">{name}</a>'
