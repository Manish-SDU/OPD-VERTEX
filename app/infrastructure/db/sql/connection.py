"""SQLAlchemy engine and session factory.

Mats: this is the DB connection setup. Use get_engine() and get_session()
in your repository implementations.
"""

from __future__ import annotations

from sqlalchemy import create_engine, Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings

_engine: Engine | None = None
_session_factory: sessionmaker[Session] | None = None


def get_mysql_url() -> str:
    s = get_settings()
    return f"mysql+pymysql://{s.mysql_user}:{s.mysql_password}@{s.mysql_host}:{s.mysql_port}/{s.mysql_db}"


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        _engine = create_engine(get_mysql_url(), pool_pre_ping=True)
    return _engine


def get_session() -> Session:
    global _session_factory
    if _session_factory is None:
        _session_factory = sessionmaker(bind=get_engine())
    return _session_factory()
