from pathlib import Path

from sqlalchemy.engine import make_url


def database_location(app):
    """Return a safe, resolved database target without exposing credentials."""
    url = make_url(app.config["SQLALCHEMY_DATABASE_URI"])
    if url.get_backend_name() == "sqlite":
        if not url.database or url.database == ":memory:":
            return "SQLite in-memory database"
        path = Path(url.database)
        if not path.is_absolute():
            path = Path(app.instance_path) / path
        return str(path.resolve())
    return f"{url.get_backend_name()} database {url.database or '(default)'}"
