import logging
import sys
from pathlib import Path

from flask import Flask

# services/shared/ is a sibling of services/dashboard/ (and, in the Docker
# image, of /app) -- not on sys.path by default, so add its parent before
# importing from it. See services/dashboard/Dockerfile and docker-compose.yml
# for how it gets there (COPY services/shared/ /shared/, then bind-mounted
# for local dev the same way /app is).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from shared.security_headers import add_security_headers  # noqa: E402

from .config import Config
from .extensions import db, login_manager
from .minify import MINIFIABLE_MIMETYPES, minify_response
from .oauth import OAUTH_CLIENT_NAME, oauth


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    logging.basicConfig(level=logging.INFO)

    db.init_app(app)

    login_manager.init_app(app)
    login_manager.login_view = "dashboard.login"

    if app.config["AUTH_OAUTH_ENABLED"]:
        oauth.init_app(app)
        oauth.register(
            name=OAUTH_CLIENT_NAME,
            client_id=app.config["OAUTH_CLIENT_ID"],
            client_secret=app.config["OAUTH_CLIENT_SECRET"],
            authorize_url=app.config["OAUTH_AUTHORIZE_URL"],
            access_token_url=app.config["OAUTH_TOKEN_URL"],
            jwks_uri=app.config["OAUTH_JWKS_URL"],
            client_kwargs={"scope": app.config["OAUTH_SCOPE"]},
        )

    from .models import AdminUser, Asset  # noqa: F401 -- Asset registers table
    from .routes import dashboard_bp

    app.register_blueprint(dashboard_bp)

    @login_manager.user_loader
    def load_user(user_id):
        # user_id comes back out of a cryptographically signed session
        # cookie (Flask's SECRET_KEY) -- it can only be a value we put
        # there via login_user() after a real login check, so trusting it
        # here doesn't skip any authorization.
        return AdminUser(user_id)

    @app.get("/healthz")
    def healthz():
        return {"status": "ok"}

    app.after_request(add_security_headers)

    @app.after_request
    def minify(response):
        if (
            response.status_code == 200
            and response.mimetype in MINIFIABLE_MIMETYPES
        ):
            if response.direct_passthrough:
                response.direct_passthrough = False
            text = response.get_data(as_text=True)
            response.set_data(minify_response(response.mimetype, text))
        return response

    return app
