import logging
import sys
from pathlib import Path

from flask import Flask, Response, abort, send_file

# services/shared/ is a sibling of services/api/ (and, in the Docker image,
# of /app) -- not on sys.path by default, so add its parent before importing
# from it. See services/api/Dockerfile and docker-compose.yml for how it
# gets there (COPY services/shared/ /shared/, then bind-mounted for local
# dev the same way /app is).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from shared.security_headers import add_security_headers  # noqa: E402

from .config import Config
from .storage import fetch


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    logging.basicConfig(level=logging.INFO)

    @app.after_request
    def set_security_headers(response):
        add_security_headers(response)
        # Overrides the shared module's HTML-oriented CSP: this service
        # only ever streams raw file bytes, so it needs its own minimal,
        # restrictive policy instead (see CSP_POLICY in config.py).
        response.headers["Content-Security-Policy"] = app.config[
            "CSP_POLICY"
        ]
        return response

    @app.get("/healthz")
    def healthz():
        return {"status": "ok"}

    @app.get("/files/<path:object_key>")
    def serve_file(object_key):
        result = fetch(object_key)
        if result is None:
            abort(404)
        source, content_type = result

        if isinstance(source, Path):
            return send_file(
                source,
                mimetype=content_type,
                conditional=True,
                max_age=31536000,
            )

        return Response(
            source.iter_chunks(chunk_size=65536),
            mimetype=content_type,
            headers={
                "Cache-Control": "public, max-age=31536000, immutable",
            },
        )

    return app
