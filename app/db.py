from flask import current_app, g
from pymongo import ASCENDING, DESCENDING, MongoClient

from .sqlite_store import SQLiteDatabase


COLLECTIONS = {
    "users": "users",
    "cycles": "cycles",
    "categories": "categories",
    "ideas": "ideas",
    "evaluations": "evaluations",
    "idea_reactions": "idea_reactions",
    "audit_events": "audit_events",
    "password_reset_requests": "password_reset_requests",
}


class DualWriteCollection:
    def __init__(self, primary, secondary):
        self.primary = primary
        self.secondary = secondary

    def __getattr__(self, name):
        return getattr(self.primary, name)

    def _also(self, method, *args, **kwargs):
        try:
            getattr(self.secondary, method)(*args, **kwargs)
        except Exception:
            current_app.logger.exception("Mongo dual-write failed for %s", method)

    def insert_one(self, document):
        result = self.primary.insert_one(document)
        document.setdefault("_id", result.inserted_id)
        self._also("insert_one", document)
        return result

    def update_one(self, *args, **kwargs):
        result = self.primary.update_one(*args, **kwargs)
        self._also("update_one", *args, **kwargs)
        return result

    def update_many(self, *args, **kwargs):
        result = self.primary.update_many(*args, **kwargs)
        self._also("update_many", *args, **kwargs)
        return result

    def find_one_and_update(self, *args, **kwargs):
        result = self.primary.find_one_and_update(*args, **kwargs)
        self._also("find_one_and_update", *args, **kwargs)
        return result


def get_client():
    if current_app.config.get("USE_SQLITE") and not current_app.config.get("DUAL_WRITE_MONGO"):
        return None
    if "mongo_client" not in g:
        g.mongo_client = MongoClient(
            current_app.config["MONGO_URI"],
            serverSelectionTimeoutMS=8000,
        )
    return g.mongo_client


def get_db():
    if current_app.config.get("USE_SQLITE"):
        if "sqlite_db" not in g:
            g.sqlite_db = SQLiteDatabase(current_app.config["SQLITE_PATH"])
        return g.sqlite_db
    return get_client()[current_app.config["MONGO_DB_NAME"]]


def collection(name):
    primary = get_db()[COLLECTIONS[name]]
    if current_app.config.get("USE_SQLITE") and current_app.config.get("DUAL_WRITE_MONGO"):
        secondary = get_client()[current_app.config["MONGO_DB_NAME"]][COLLECTIONS[name]]
        return DualWriteCollection(primary, secondary)
    return primary


def close_db(_error=None):
    client = g.pop("mongo_client", None)
    if client:
        client.close()
    sqlite_db = g.pop("sqlite_db", None)
    if sqlite_db:
        sqlite_db.close()


def ensure_indexes():
    ensure_collections()
    collection("users").create_index("username", unique=True)
    collection("users").create_index("role")
    collection("cycles").create_index("name", unique=True)
    collection("cycles").create_index([("archived", ASCENDING), ("start_at", DESCENDING)])
    collection("categories").create_index([("cycle_id", ASCENDING), ("slug", ASCENDING)], unique=True)
    collection("ideas").create_index("idea_id", unique=True)
    collection("ideas").create_index([("cycle_id", ASCENDING), ("created_at", DESCENDING)])
    collection("ideas").create_index([("cycle_id", ASCENDING), ("category_ids", ASCENDING)])
    collection("ideas").create_index([("cycle_id", ASCENDING), ("category_ids", ASCENDING), ("created_at", DESCENDING)])
    collection("ideas").create_index([("owner_employee_id", ASCENDING), ("idea_id", ASCENDING)])
    for index in collection("evaluations").list_indexes():
        if list(index["key"].items()) == [("idea_id", 1), ("juror_id", 1)]:
            collection("evaluations").drop_index(index["name"])
    collection("evaluations").create_index(
        [("idea_id", ASCENDING), ("category_id", ASCENDING), ("juror_id", ASCENDING)],
        unique=True,
    )
    collection("evaluations").create_index([("category_id", ASCENDING), ("juror_id", ASCENDING)])
    collection("idea_reactions").create_index([("idea_id", ASCENDING), ("visitor_id", ASCENDING)], unique=True)
    collection("idea_reactions").create_index([("idea_id", ASCENDING), ("sentiment", ASCENDING)])
    collection("password_reset_requests").create_index([("status", ASCENDING), ("created_at", DESCENDING)])
    collection("password_reset_requests").create_index("username")


def ensure_collections():
    db = get_db()
    existing = set(db.list_collection_names())
    for mongo_name in COLLECTIONS.values():
        if mongo_name not in existing:
            db.create_collection(mongo_name)


def init_app(app):
    @app.cli.command("init-db")
    def init_db_command():
        ensure_indexes()
        backend = "SQLite" if current_app.config.get("USE_SQLITE") else "MongoDB"
        print(f"{backend} storage is ready.")
