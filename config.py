import json
import os
from datetime import timedelta
from pathlib import Path

from sqlalchemy.engine import make_url


BASE_DIR = Path(__file__).resolve().parent.parent
_app_env = os.getenv("APP_ENV", "development").lower()
_database_url = os.getenv("DATABASE_URL", "sqlite:///echoguard.db")
if _database_url.startswith("mysql://"):
    _database_url = _database_url.replace("mysql://", "mysql+pymysql://", 1)
elif _database_url.startswith("postgres://"):
    _database_url = _database_url.replace("postgres://", "postgresql+psycopg://", 1)
elif _database_url.startswith("postgresql://") and "+" not in _database_url.split("://", 1)[0]:
    _database_url = _database_url.replace("postgresql://", "postgresql+psycopg://", 1)

_engine_options: dict[str, object] = {"pool_pre_ping": True}
try:
    _parsed_database_url = make_url(_database_url)
    _ssl_query_value = _parsed_database_url.query.get("ssl")
    if _parsed_database_url.drivername.startswith("mysql+") and _ssl_query_value:
        _database_url = _parsed_database_url.set(query={key: value for key, value in _parsed_database_url.query.items() if key != "ssl"}).render_as_string(hide_password=False)
        try:
            _engine_options["connect_args"] = {"ssl": json.loads(_ssl_query_value)}
        except (TypeError, ValueError):
            _engine_options["connect_args"] = {"ssl": {}}
except (TypeError, ValueError):
    pass


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-only-change-me-before-production")
    SQLALCHEMY_DATABASE_URI = _database_url
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = _engine_options
    AUTO_CREATE_DB = os.getenv("AUTO_CREATE_DB", "true" if _database_url.startswith("sqlite") else "false").lower() == "true"
    SESSION_COOKIE_NAME = "echoguard_session"
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SECURE = os.getenv("COOKIE_SECURE", "true" if _app_env in {"production", "prod", "preview"} else "false").lower() == "true"
    SESSION_COOKIE_SAMESITE = os.getenv("COOKIE_SAMESITE", "None" if _app_env in {"production", "prod", "preview"} else "Lax")
    REMEMBER_COOKIE_SECURE = SESSION_COOKIE_SECURE
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SAMESITE = SESSION_COOKIE_SAMESITE
    PERMANENT_SESSION_LIFETIME = timedelta(hours=int(os.getenv("SESSION_LIFETIME_HOURS", "12")))
    WTF_CSRF_TIME_LIMIT = 3600
    MAX_CONTENT_LENGTH = 2 * 1024 * 1024
    RATELIMIT_HEADERS_ENABLED = True
    RATELIMIT_STORAGE_URI = os.getenv("RATELIMIT_STORAGE_URI", "memory://")
    APP_ENV = _app_env
    DEBUG = APP_ENV == "development"
    TESTING = False
    SMTP_HOST = os.getenv("SMTP_HOST", "")
    SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USERNAME = os.getenv("SMTP_USERNAME", "")
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
    SMTP_USE_TLS = os.getenv("SMTP_USE_TLS", "true").lower() == "true"
    MAIL_FROM = os.getenv("MAIL_FROM", "no-reply@echoguard.local")
    LLM_API_URL = os.getenv("LLM_API_URL", "")
    LLM_API_KEY = os.getenv("LLM_API_KEY", "")
    LLM_MODEL = os.getenv("LLM_MODEL", "")
    MANUS_API_URL = os.getenv("MANUS_API_URL", "")
    MANUS_API_KEY = os.getenv("MANUS_API_KEY", "")


class TestConfig(Config):
    TESTING = True
    APP_ENV = "development"
    WTF_CSRF_ENABLED = False
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}
    SECRET_KEY = "test-secret-key"
    SESSION_COOKIE_SECURE = False
    SESSION_COOKIE_SAMESITE = "Lax"
    REMEMBER_COOKIE_SECURE = False
    REMEMBER_COOKIE_SAMESITE = "Lax"
