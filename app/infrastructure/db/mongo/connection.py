"""MongoDB connection helper.

Gabriele and Mats: use get_database() in your repository implementations
to get a pymongo Database handle.
"""

from __future__ import annotations

from pymongo import MongoClient
from pymongo.database import Database

from app.core.config import get_settings

_client: MongoClient | None = None


def get_database() -> Database:
    global _client
    if _client is None:
        s = get_settings()
        _client = MongoClient(s.mongo_uri)
    return _client[get_settings().mongo_db]
