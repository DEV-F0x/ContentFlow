from sqlalchemy import inspect, text

from app import create_app
from app.extensions import db

app = create_app()
with app.app_context():
    db.create_all()

    # db.create_all() only creates missing tables, not missing columns on
    # tables that already exist -- there's no migration framework here, so
    # patch in columns added after an install's first run by hand. Guarded
    # by the inspector check so this stays a no-op once the column exists.
    inspector = inspect(db.engine)
    if "assets" in inspector.get_table_names():
        columns = {col["name"] for col in inspector.get_columns("assets")}
        if "force_download" not in columns:
            db.session.execute(
                text(
                    "ALTER TABLE assets ADD COLUMN force_download "
                    "BOOLEAN NOT NULL DEFAULT FALSE"
                )
            )
            db.session.commit()
