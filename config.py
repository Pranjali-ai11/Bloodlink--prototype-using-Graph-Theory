import os


class Config:
    """Base configuration; secrets must be explicitly provided by production."""
    SECRET_KEY = os.environ.get("SECRET_KEY")
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL") or "sqlite:///bloodlink.db"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    DEBUG = False
    TESTING = False


class DevelopmentConfig(Config):
    """Development-only settings."""
    SECRET_KEY = os.environ.get("SECRET_KEY") or "bloodlink-development-only-secret"


class TestingConfig(Config):
    """Isolated in-memory test settings."""
    SECRET_KEY = "bloodlink-testing-only-secret"
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"


class ProductionConfig(Config):
    """Production settings fail closed without a configured session secret."""
    SECRET_KEY = os.environ.get("SECRET_KEY")
    DEBUG = False

    def __init__(self):
        secret_key = os.environ.get("SECRET_KEY")
        if not secret_key:
            raise RuntimeError("SECRET_KEY must be set when FLASK_ENV=production.")
        self.SECRET_KEY = secret_key


config = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
