from __future__ import annotations

import sqlite3
from enum import StrEnum
from pathlib import Path
from typing import NamedTuple

from shared.logger import Logger

from .settings import SettingsManager


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

    @classmethod
    def members(cls) -> tuple[str, ...]:
        return tuple(cls.__members__)


def create_connection() -> sqlite3.Connection:
    path = SettingsManager.DB_PATH

    conn = sqlite3.connect(path)

    conn.executescript("""
        PRAGMA synchronous = NORMAL;
        PRAGMA journal_mode = WAL;
        PRAGMA temp_store = MEMORY;
        PRAGMA cache_size = 10000;
    """)

    return conn


def close_connection(conn: sqlite3.Connection) -> None:
    conn.execute("PRAGMA optimize;")
    conn.close()


def insert(table: Tables, data: DBSchema) -> None:
    conn = create_connection()
    try:
        conn.execute(
            f"INSERT INTO {table.name}{data.fields()} VALUES (?, ?);",
            (data.name, str(data.path)),
        )
        conn.commit()
    except Exception as e:
        Logger.exception(e)
    finally:
        close_connection(conn)


def select(table: Tables) -> dict[str, Path]:
    data = {}
    conn = create_connection()
    try:
        cursor = conn.execute(f"SELECT name, path FROM {table.name};")
        p = {name: Path(path) for name, path in cursor.fetchall()}
        data = dict(sorted(p.items()))
    except Exception as e:
        Logger.exception(e)
    finally:
        close_connection(conn)

    return data


def delete(table: Tables, data: DBSchema) -> None:
    conn = create_connection()
    try:
        conn.execute(f"DELETE FROM {table.name} WHERE NAME = ?;", (data.name,))
        conn.commit()
    except Exception as e:
        Logger.exception(e)
    finally:
        close_connection(conn)


DBRow = dict[str, Path]


def select_all() -> dict[str, DBRow]:
    data: dict[str, DBRow] = {}
    conn = create_connection()
    try:
        for table in Tables.members():
            cursor = conn.execute(f"SELECT name, path FROM {table}")
            p = {name: Path(path) for name, path in cursor.fetchall()}
            data[table] = dict(sorted(p.items()))

    except Exception as e:
        Logger.exception(e)
    finally:
        close_connection(conn)

    return data


def run_migration(data: dict[str, dict[str, str]]) -> None:
    for pool, entrys in data.items():
        for name, path in entrys.items():
            schema = DBSchema(name, Path(path))
            insert(Tables(pool), schema)


def init_db():
    path = SettingsManager.DB_PATH
    if path.exists():
        Logger.info("database already exists. skipping initialization")
        return

    path.parent.mkdir(parents=True, exist_ok=True)

    conn = create_connection()
    try:
        tables = Tables.members()
        for table in tables:
            conn.execute(
                f"""CREATE TABLE IF NOT EXISTS {table}
                (ID INTEGER PRIMARY KEY AUTOINCREMENT,
                NAME CHAR(128) NOT NULL,
                PATH TEXT NOT NULL);"""
            )

        conn.commit()

        Logger.debug(f"created database {path.stem}")
    except Exception as e:
        Logger.exception(e)
    finally:
        close_connection(conn)

    """
    with open(Path(__file__).parent / "sql.json") as file:
        data = json.load(file)
        run_migration(data)
    """
