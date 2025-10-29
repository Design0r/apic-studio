from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from enum import StrEnum
from pathlib import Path
from typing import Generator, NamedTuple, Optional

from shared.logger import Logger

from .settings import SettingsManager

MIGRATIONS = [
    """
CREATE TABLE IF NOT EXISTS materials (
ID INTEGER PRIMARY KEY AUTOINCREMENT,
NAME CHAR(128) NOT NULL,
PATH TEXT NOT NULL);
""",
    """
CREATE TABLE IF NOT EXISTS models(
ID INTEGER PRIMARY KEY AUTOINCREMENT,
NAME CHAR(128) NOT NULL,
PATH TEXT NOT NULL);
""",
    """
CREATE TABLE IF NOT EXISTS hdris(
ID INTEGER PRIMARY KEY AUTOINCREMENT,
NAME CHAR(128) NOT NULL,
PATH TEXT NOT NULL);
""",
    """
CREATE TABLE IF NOT EXISTS lightsets(
ID INTEGER PRIMARY KEY AUTOINCREMENT,
NAME CHAR(128) NOT NULL,
PATH TEXT NOT NULL);
""",
    """
CREATE TABLE IF NOT EXISTS tags (
ID INTEGER PRIMARY KEY AUTOINCREMENT,
NAME CHAR(128) UNIQUE NOT NULL);
""",
    """
CREATE TABLE IF NOT EXISTS apic_models(
ID INTEGER PRIMARY KEY AUTOINCREMENT,
NAME CHAR(128) UNIQUE NOT NULL,
PATH TEXT NOT NULL);
""",
]


class DBSchema(NamedTuple):
    name: str
    path: Path

    @classmethod
    def fields(cls) -> str:
        return f"({','.join([f.upper() for f in cls._fields])})"


class Tables(StrEnum):
    MATERIALS = "materials"
    MODELS = "models"
    HDRIS = "hdris"
    LIGHTSETS = "lightsets"
    TAGS = "tags"
    APIC_MODELS = "apic_models"

    @classmethod
    def members(cls) -> tuple[str, ...]:
        return tuple(cls.__members__)


@contextmanager
def connection() -> Generator[sqlite3.Connection]:
    conn: Optional[sqlite3.Connection] = None
    try:
        conn = _create_connection()
        yield conn
    except Exception as e:
        Logger.exception(e)
    finally:
        if conn:
            _close_connection(conn)


def _create_connection() -> sqlite3.Connection:
    path = SettingsManager().CoreSettings.db_path
    conn = sqlite3.connect(path)
    conn.executescript("""
        PRAGMA synchronous = NORMAL;
        PRAGMA journal_mode = WAL;
        PRAGMA temp_store = MEMORY;
        PRAGMA cache_size = 10000;
    """)

    return conn


def _close_connection(conn: sqlite3.Connection) -> None:
    conn.execute("PRAGMA optimize;")
    conn.close()


def insert(table: Tables, data: DBSchema) -> None:
    with connection() as conn:
        try:
            conn.execute(
                f"INSERT INTO {table.name}{data.fields()} VALUES (?, ?);",
                (data.name, str(data.path)),
            )
            conn.commit()
        except Exception as e:
            Logger.exception(e)


def select(table: Tables) -> dict[str, Path]:
    data = {}
    with connection() as conn:
        try:
            query = f"SELECT name, path FROM {table.name};"
            cursor = conn.execute(query)
            p = {name: Path(path) for name, path in cursor.fetchall()}
            data = dict(sorted(p.items()))
        except Exception as e:
            Logger.exception(e)

    return data


def delete(table: Tables, data: DBSchema) -> None:
    with connection() as conn:
        try:
            conn.execute(f"DELETE FROM {table.name} WHERE name = ?;", (data.name,))
            conn.commit()
        except Exception as e:
            Logger.exception(e)


DBRow = dict[str, Path]


def select_all() -> dict[str, DBRow]:
    data: dict[str, DBRow] = {}
    with connection() as conn:
        try:
            for table in Tables.members():
                cursor = conn.execute(f"SELECT name, path FROM {table}")
                p = {name: Path(path) for name, path in cursor.fetchall()}
                data[table] = dict(sorted(p.items()))

        except Exception as e:
            Logger.exception(e)

    return data


def run_migration(conn: sqlite3.Connection, migration: str) -> None:
    try:
        conn.execute(migration)
    except Exception as e:
        Logger.error("migration Failed:")
        Logger.exception(e)


def init_db():
    Logger.info("initializing DB...")
    path = Path(SettingsManager().CoreSettings.db_path)

    if path.exists():
        Logger.info(f"detected existing DB {path}")
    else:
        Logger.info("creating new DB")

    Logger.info("running migrations...")
    with connection() as conn:
        for i, migration in enumerate(MIGRATIONS, start=1):
            Logger.info(f"migration {i}/{len(MIGRATIONS)}")
            run_migration(conn, migration)
        conn.commit()

    Logger.info("initialized DB")
