import os
import configparser
from datetime import timedelta
from pathlib import Path


def load_env_file():
    env_path = Path(".env")
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        if not line or line.lstrip().startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


load_env_file()


def load_ini():
    parser = configparser.ConfigParser()
    parser.read("config.ini", encoding="utf-8")
    return parser


INI = load_ini()


class Config:
    APP_NAME = "GRIT"
    DEBUG = os.getenv("FLASK_DEBUG", "0") == "1"
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-only-girt-secret")
    MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
    MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "girt")
    USE_SQLITE = INI.getboolean("database", "sqlite", fallback=False)
    SQLITE_PATH = INI.get("database", "sqlite_path", fallback="data/grit.sqlite3")
    DUAL_WRITE_MONGO = INI.getboolean("sync", "dual_write_mongo", fallback=False)
    GIRT_BOOTSTRAP_CORE_USERNAME = os.getenv("GIRT_BOOTSTRAP_CORE_USERNAME")
    GIRT_BOOTSTRAP_CORE_PASSWORD = os.getenv("GIRT_BOOTSTRAP_CORE_PASSWORD")
    GIRT_BOOTSTRAP_CORE_NAME = os.getenv("GIRT_BOOTSTRAP_CORE_NAME", "Core Administrator")
    UPLOAD_FOLDER = os.getenv("GIRT_UPLOAD_FOLDER", "app/static/uploads")
    MAX_CONTENT_LENGTH = 12 * 1024 * 1024
    MAX_BSON_BYTES = 15 * 1024 * 1024
    PER_PAGE = 10
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    PERMANENT_SESSION_LIFETIME = timedelta(hours=12)
    DEFAULT_CATEGORIES = [
        "Unique Idea",
        "Solution Re-use",
        "Process Improvement",
        "DevOps",
        "Data Architecture",
        "Automation",
        "Technical Debt",
    ]
    INDIA_REGIONS = [
        "North India",
        "South India",
        "East India",
        "West India",
        "Central India",
        "North-East India",
    ]
