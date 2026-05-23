"""Copy the local SQLite demo database back into MongoDB.

Run this after approval when the team wants to promote demo data to MongoDB.
It replaces the configured MongoDB collections with the SQLite documents.
"""

from pymongo import MongoClient

from app.config import Config
from app.db import COLLECTIONS
from app.sqlite_store import SQLiteDatabase, loads


def sync():
    client = MongoClient(Config.MONGO_URI, serverSelectionTimeoutMS=15000)
    mongo_db = client[Config.MONGO_DB_NAME]
    sqlite_db = SQLiteDatabase(Config.SQLITE_PATH)
    try:
        for _logical_name, physical_name in COLLECTIONS.items():
            rows = sqlite_db.connection.execute(
                "select doc from documents where collection = ?", (physical_name,)
            ).fetchall()
            documents = [loads(row[0]) for row in rows]
            mongo_db[physical_name].delete_many({})
            if documents:
                mongo_db[physical_name].insert_many(documents)
            print(f"Copied {len(documents)} {physical_name} documents from SQLite to MongoDB.")
    finally:
        sqlite_db.close()
        client.close()


if __name__ == "__main__":
    sync()
