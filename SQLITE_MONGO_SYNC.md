# GRIT SQLite And MongoDB Sync

GRIT currently runs in local SQLite demo mode for approval.

Backend selection is in `config.ini`:

```ini
[database]
sqlite = yes
sqlite_path = data/grit.sqlite3

[sync]
dual_write_mongo = no
```

## Demo Mode

- Keep `sqlite = yes`.
- Start with `python start_grit.py`.
- Data is stored in `data/grit.sqlite3`.
- Data is retained after restart.
- MongoDB code is still present in `app/db.py` and can be enabled later.

## Copy MongoDB To SQLite

When MongoDB access is available and you want the local demo DB to mirror Mongo:

```powershell
python sync_mongo_to_sqlite.py
```

This replaces local SQLite documents with MongoDB documents for the GRIT logical collections.

## Copy SQLite To MongoDB

After approval, when you want to push demo data back to Mongo:

```powershell
python sync_sqlite_to_mongo.py
```

This replaces the configured MongoDB collections with documents from `data/grit.sqlite3`.

## Optional Dual Write

Set this only when MongoDB access is stable:

```ini
[sync]
dual_write_mongo = yes
```

With dual write enabled, the app reads from SQLite and also attempts to write changes to MongoDB. Keep it disabled for offline company demos.
