"""
Datenbankzugriff über SQLAlchemy.

SQLAlchemy ist eine Schicht zwischen Python und der Datenbank. Der restliche
Code spricht nur mit SQLAlchemy-Objekten; ob dahinter SQLite oder PostgreSQL
steckt, entscheidet allein die Verbindungs-URL in config.py.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import settings


class Base(DeclarativeBase):
    """Basisklasse für alle Tabellen (siehe models.py)."""


def _make_engine():
    url = settings.db_url
    if url.startswith("sqlite"):
        settings.data_dir.mkdir(parents=True, exist_ok=True)
        engine = create_engine(url, connect_args={"check_same_thread": False})

        # WAL-Modus: Lesen und Schreiben blockieren sich weniger gegenseitig.
        @event.listens_for(engine, "connect")
        def _sqlite_pragmas(dbapi_conn, _record):
            cur = dbapi_conn.cursor()
            cur.execute("PRAGMA journal_mode=WAL")
            cur.execute("PRAGMA synchronous=NORMAL")
            cur.close()

        return engine
    return create_engine(url, pool_pre_ping=True)


engine = _make_engine()
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


@contextmanager
def session_scope() -> Iterator[Session]:
    """Öffnet eine Sitzung und schreibt am Ende alles in die Datenbank."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_db() -> None:
    """Legt fehlende Tabellen an (für einen Prototyp reicht das statt Migrationen)."""
    from . import models  # noqa: F401  (registriert die Tabellen)

    Base.metadata.create_all(engine)
