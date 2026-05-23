"""Copy MongoDB GRIT documents into the local SQLite demo database.

Use this when MongoDB is available and you want the offline demo database to
start from the current cloud data. The app itself chooses SQLite or Mongo with
config.ini.
"""

from pymongo import MongoClient

from app.config import Config
from app.db import COLLECTIONS
from app.sqlite_store import SQLiteDatabase, dumps


def sync():
    client = MongoClient(Config.MONGO_URI, serverSelectionTimeoutMS=15000)
    mongo_db = client[Config.MONGO_DB_NAME]
    sqlite_db = SQLiteDatabase(Config.SQLITE_PATH)
    try:
        for logical_name, physical_name in COLLECTIONS.items():
            sqlite_db.connection.execute("delete from documents where collection = ?", (physical_name,))
            for document in mongo_db[physical_name].find():
                sqlite_db.connection.execute(
                    "insert or replace into documents(collection, id, doc) values (?, ?, ?)",
                    (physical_name, str(document["_id"]), dumps(document)),
                )
            sqlite_db.connection.commit()
            print(f"Copied {physical_name} from MongoDB to SQLite.")
    finally:
        sqlite_db.close()
        client.close()


if __name__ == "__main__":
    sync()
