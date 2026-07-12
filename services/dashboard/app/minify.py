import rcssmin
import rjsmin

MINIFIABLE_MIMETYPES = {
    "text/css",
    "application/javascript",
    "text/javascript",
}


def minify_response(mimetype: str, text: str) -> str:
    if mimetype == "text/css":
        return rcssmin.cssmin(text)
    if mimetype in ("application/javascript", "text/javascript"):
        return rjsmin.jsmin(text)
    return text


def maybe_minify_asset(filename: str, data: bytes) -> bytes:
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    try:
        if ext == "css":
            return rcssmin.cssmin(data.decode("utf-8")).encode("utf-8")
        if ext == "js":
            return rjsmin.jsmin(data.decode("utf-8")).encode("utf-8")
    except UnicodeDecodeError:
        pass
    return data
