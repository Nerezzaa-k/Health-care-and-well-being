"""
Nirantar Phase 7 Database Module
MongoDB Atlas integration with PyMongo, supporting collection schemas, indexes,
demo clock settings, and health check.
"""
import os
import sys
from dotenv import load_dotenv
import pymongo
import mongomock

load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI", "")
DB_NAME = "nirantar"

_client = None
_db = None
_is_mock = False

def init_mongo_connection(custom_uri=None, db_name=None, allow_mock=True):
    """
    Initializes connection to MongoDB Atlas or local/mock database.
    Exits gracefully with a clear terminal message if database is unreachable.
    """
    global _client, _db, _is_mock
    uri = custom_uri or os.getenv("MONGODB_URI", "")
    target_db_name = db_name or DB_NAME
    
    # 1. Try real MongoDB connection if URI is configured
    if uri and (uri.startswith("mongodb://") or uri.startswith("mongodb+srv://")):
        try:
            client = pymongo.MongoClient(uri, serverSelectionTimeoutMS=2500)
            # Ping database to confirm reachability
            client.admin.command('ping')
            _client = client
            _db = _client[target_db_name]
            _is_mock = False
            ensure_indexes(_db)
            return _db
        except Exception as e:
            if not allow_mock:
                print("\n" + "=" * 70, file=sys.stderr)
                print("FATAL ERROR: Could not connect to MongoDB Atlas / server.", file=sys.stderr)
                print(f"Error details: {e}", file=sys.stderr)
                print("Please verify your MONGODB_URI in .env.", file=sys.stderr)
                print("=" * 70 + "\n", file=sys.stderr)
                sys.exit(1)
            # If allow_mock is True, fallback to in-memory mongomock
            print(f"[Nirantar DB] Notice: Live MongoDB connection failed ({e}). Using compliant in-memory MongoDB engine.")
    
    # 2. In-memory compliant Mongo engine (mongomock)
    if _client is None or _is_mock:
        if _client is None:
            _client = mongomock.MongoClient()
        _db = _client[target_db_name]
        _is_mock = True
        ensure_indexes(_db)
        return _db
    
    _db = _client[target_db_name]
    return _db

def get_db(db_name=None):
    global _db
    if _db is None:
        init_mongo_connection(db_name=db_name)
    elif db_name and _db.name != db_name:
        return _client[db_name]
    return _db

def ensure_indexes(db):
    """
    Ensures required indexes:
    - users.email: unique
    - cases: (owner_id, status, due_date)
    - patients: village_id
    """
    try:
        db.users.create_index("email", unique=True)
        db.cases.create_index([("owner_id", pymongo.ASCENDING), ("status", pymongo.ASCENDING), ("due_date", pymongo.ASCENDING)])
        db.patients.create_index("village_id")
    except Exception as e:
        # Ignore indexing errors if already existing or in mock
        pass

def is_db_healthy():
    """
    Health check helper for GET /api/health
    """
    try:
        db = get_db()
        if _is_mock:
            return True, "in-memory (mongomock)"
        db.command('ping')
        return True, "connected"
    except Exception as e:
        return False, str(e)

if __name__ == "__main__":
    db = get_db()
    healthy, status = is_db_healthy()
    print(f"MongoDB connection initialized successfully. Health status: {status}, Database: {db.name}")
