import json
import re
import sqlite3
from copy import deepcopy
from datetime import datetime
from pathlib import Path

from bson import ObjectId
from pymongo import ReturnDocument


class InsertOneResult:
    def __init__(self, inserted_id):
        self.inserted_id = inserted_id


def encode_value(value):
    if isinstance(value, ObjectId):
        return {"__objectid__": str(value)}
    if isinstance(value, datetime):
        return {"__datetime__": value.isoformat()}
    raise TypeError(f"{type(value).__name__} is not JSON serializable")


def decode_value(_key, value):
    if isinstance(value, dict) and "__objectid__" in value:
        return ObjectId(value["__objectid__"])
    if isinstance(value, dict) and "__datetime__" in value:
        return datetime.fromisoformat(value["__datetime__"])
    return value


def dumps(document):
    return json.dumps(document, default=encode_value, separators=(",", ":"))


def loads(payload):
    return json.loads(payload, object_hook=lambda obj: {key: decode_value(key, value) for key, value in obj.items()})


def normalize(value):
    if isinstance(value, ObjectId):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def sort_value(value):
    if isinstance(value, datetime):
        return value.timestamp()
    if value is None:
        return ""
    return str(normalize(value)).lower()


def get_nested(document, dotted):
    value = document
    for part in dotted.split("."):
        if not isinstance(value, dict) or part not in value:
            return None
        value = value[part]
    return value


def set_nested(document, dotted, value):
    target = document
    parts = dotted.split(".")
    for part in parts[:-1]:
        target = target.setdefault(part, {})
    target[parts[-1]] = value


def pull_value(document, dotted, value):
    items = get_nested(document, dotted)
    if isinstance(items, list):
        set_nested(document, dotted, [item for item in items if str(item) != str(value)])


def field_matches(actual, expected):
    if isinstance(expected, dict):
        for operator, operand in expected.items():
            if operator == "$ne" and normalize(actual) == normalize(operand):
                return False
            if operator == "$in":
                choices = {str(item) for item in operand}
                if isinstance(actual, list):
                    if not any(str(item) in choices for item in actual):
                        return False
                elif str(actual) not in choices:
                    return False
            if operator == "$nin":
                choices = {str(item) for item in operand}
                if isinstance(actual, list):
                    if any(str(item) in choices for item in actual):
                        return False
                elif str(actual) in choices:
                    return False
            if operator == "$lte" and not (actual <= operand):
                return False
            if operator == "$gte" and not (actual >= operand):
                return False
            if operator == "$regex":
                flags = re.IGNORECASE if expected.get("$options") == "i" else 0
                if not re.search(operand, str(actual or ""), flags):
                    return False
        return True
    if isinstance(actual, list):
        return str(expected) in {str(item) for item in actual}
    return normalize(actual) == normalize(expected)


def matches_query(document, query):
    for field, expected in (query or {}).items():
        if field == "$or":
            if not any(matches_query(document, candidate) for candidate in expected):
                return False
            continue
        if not field_matches(get_nested(document, field), expected):
            return False
    return True


def apply_projection(document, projection):
    if not projection:
        return deepcopy(document)
    include = {key for key, value in projection.items() if value}
    projected = {"_id": document["_id"]} if "_id" in document else {}
    for key in include:
        if key in document:
            projected[key] = deepcopy(document[key])
    return projected


class SQLiteCursor:
    def __init__(self, rows):
        self.rows = rows

    def sort(self, key_or_list, direction=None):
        sort_keys = key_or_list if isinstance(key_or_list, list) else [(key_or_list, direction)]
        for key, order in reversed(sort_keys):
            self.rows.sort(key=lambda item: sort_value(get_nested(item, key)), reverse=order == -1)
        return self

    def skip(self, count):
        self.rows = self.rows[count:]
        return self

    def limit(self, count):
        self.rows = self.rows[:count]
        return self

    def __iter__(self):
        return iter(self.rows)


class SQLiteCollection:
    def __init__(self, connection, name):
        self.connection = connection
        self.name = name

    def _all(self):
        rows = self.connection.execute("select doc from documents where collection = ?", (self.name,)).fetchall()
        return [loads(row[0]) for row in rows]

    def _save(self, document):
        doc_id = str(document["_id"])
        self.connection.execute(
            "insert or replace into documents(collection, id, doc) values (?, ?, ?)",
            (self.name, doc_id, dumps(document)),
        )
        self.connection.commit()

    def _delete_all(self):
        self.connection.execute("delete from documents where collection = ?", (self.name,))
        self.connection.commit()

    def find(self, query=None, projection=None):
        rows = [apply_projection(row, projection) for row in self._all() if matches_query(row, query)]
        return SQLiteCursor(rows)

    def find_one(self, query=None, projection=None, sort=None):
        cursor = self.find(query, projection)
        if sort:
            cursor.sort(sort)
        return next(iter(cursor), None)

    def count_documents(self, query=None):
        return sum(1 for row in self._all() if matches_query(row, query))

    def insert_one(self, document):
        doc = deepcopy(document)
        doc.setdefault("_id", ObjectId())
        self._save(doc)
        return InsertOneResult(doc["_id"])

    def update_one(self, query, update, upsert=False):
        document = self.find_one(query)
        if not document and not upsert:
            return None
        if not document:
            document = {key: value for key, value in query.items() if not key.startswith("$") and not isinstance(value, dict)}
            document["_id"] = ObjectId()
            for key, value in update.get("$setOnInsert", {}).items():
                set_nested(document, key, deepcopy(value))
        self._apply_update(document, update, inserting=False)
        self._save(document)
        return None

    def update_many(self, query, update):
        for document in self._all():
            if matches_query(document, query):
                self._apply_update(document, update, inserting=False)
                self._save(document)

    def find_one_and_update(self, query, update, upsert=False, return_document=ReturnDocument.BEFORE):
        document = self.find_one(query)
        inserting = False
        if not document and upsert:
            document = {key: value for key, value in query.items() if not key.startswith("$") and not isinstance(value, dict)}
            document["_id"] = ObjectId()
            inserting = True
        if not document:
            return None
        self._apply_update(document, update, inserting=inserting)
        self._save(document)
        return self.find_one({"_id": document["_id"]}) if return_document == ReturnDocument.AFTER else document

    def _apply_update(self, document, update, inserting=False):
        for key, value in update.get("$set", {}).items():
            set_nested(document, key, deepcopy(value))
        if inserting:
            for key, value in update.get("$setOnInsert", {}).items():
                set_nested(document, key, deepcopy(value))
        for key, value in update.get("$inc", {}).items():
            set_nested(document, key, (get_nested(document, key) or 0) + value)
        for key, value in update.get("$push", {}).items():
            items = get_nested(document, key) or []
            items.append(deepcopy(value))
            set_nested(document, key, items)
        for key, value in update.get("$pull", {}).items():
            pull_value(document, key, value)
        if not any(key.startswith("$") for key in update):
            document.update(deepcopy(update))

    def create_index(self, *_args, **_kwargs):
        return None

    def list_indexes(self):
        return []

    def drop_index(self, *_args, **_kwargs):
        return None


class SQLiteDatabase:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.path)
        self.connection.execute(
            "create table if not exists documents(collection text not null, id text not null, doc text not null, primary key(collection, id))"
        )
        self.connection.commit()

    def __getitem__(self, name):
        return SQLiteCollection(self.connection, name)

    def list_collection_names(self):
        rows = self.connection.execute("select distinct collection from documents").fetchall()
        return [row[0] for row in rows]

    def create_collection(self, name):
        self.connection.execute("insert or ignore into documents(collection, id, doc) values (?, ?, ?)", (name, "__meta__", dumps({"_id": "__meta__"})))
        self.connection.execute("delete from documents where collection = ? and id = ?", (name, "__meta__"))
        self.connection.commit()

    def close(self):
        self.connection.close()
