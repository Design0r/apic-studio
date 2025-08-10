from apic_studio.core import db
from shared.logger import Logger


class TagService:
    def create(self, name: str):
        with db.connection() as conn:
            conn.execute("INSERT INTO tags (name) VALUES(?);", (name,))
            conn.commit()

        Logger.info(f"created tag: {name}")

    def delete(self, name: str):
        with db.connection() as conn:
            conn.execute("DELETE FROM tags WHERE name = ?;", (name,))
            conn.commit()

        Logger.info(f"deleted tag: {name}")

    def exists(self, name: str) -> bool:
        with db.connection() as conn:
            res = conn.execute("SELECT * FROM tags WHERE name = ?;", (name,))
            return len(res.fetchmany()) > 0

    def get_all(self) -> list[str]:
        with db.connection() as conn:
            res = conn.execute("SELECT (name) FROM tags;")
            p = [name[0] for name in res.fetchall()]
            return p
