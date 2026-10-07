from __future__ import annotations

import json
import os
from collections.abc import Iterator
from pathlib import Path

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal

from apic_studio.core import db, metadata_path
from shared.logger import Logger


class TagEvents(QObject):
    """App wide notice that a tag was renamed or deleted in every asset."""

    # old name, new name or None when the tag was deleted
    rewritten = Signal(str, object)


tag_events = TagEvents()


class TagRewriter(QObject):
    """Progress of one rename / delete going through every pool's metadata."""

    progress = Signal(int)  # pools done
    finished = Signal(int)  # assets changed

    def __init__(self, old: str, new: str | None, pools: list[Path]):
        super().__init__()
        self.old = old
        self.new = new
        self.pools = pools
        self.pool_count = len(pools)

        # connected to a method of this object, which lives on the GUI thread,
        # so the announcement hops over from the pool thread the task runs on
        self.finished.connect(self._announce)

    def _announce(self, changed: int):
        action = f"renamed to “{self.new}”" if self.new else "deleted"
        Logger.info(f"tag “{self.old}” {action} in {changed} assets")
        tag_events.rewritten.emit(self.old, self.new)
        _running.discard(self)

    def start(self) -> None:
        """Connect to progress / finished first, the task may be quick."""
        _running.add(self)
        QThreadPool.globalInstance().start(_RewriteTask(self, self.pools))


# rewriters stay referenced until their task reports back
_running: set[TagRewriter] = set()


class _RewriteTask(QRunnable):
    def __init__(self, rewriter: TagRewriter, pools: list[Path]):
        super().__init__()
        self.rewriter = rewriter
        self.pools = pools

    def run(self):
        changed = 0
        for i, pool in enumerate(self.pools):
            for meta in _metadata_files(pool):
                try:
                    if _rewrite(meta, self.rewriter.old, self.rewriter.new):
                        changed += 1
                except Exception as e:
                    Logger.exception(e)
            self.rewriter.progress.emit(i + 1)

        self.rewriter.finished.emit(changed)


def _metadata_files(pool: Path) -> Iterator[Path]:
    """Every metadata file a pool may hold, see core.metadata_path."""
    try:
        entries = list(os.scandir(pool))
    except OSError:
        return

    for entry in entries:
        if entry.is_dir():
            # named after the model, which may have drifted from the folder
            yield metadata_path(Path(entry.path))
        elif entry.name.lower().endswith(".json"):
            yield Path(entry.path)


def _rewrite(meta: Path, old: str, new: str | None) -> bool:
    try:
        with open(meta, "r") as f:
            data = json.load(f)
    except OSError, ValueError:
        return False

    tags = data.get("tags") if isinstance(data, dict) else None
    if not isinstance(tags, list) or old not in tags:
        return False

    if new is None:
        tags = [t for t in tags if t != old]
    else:
        tags = [new if t == old else t for t in tags]
    # a rename onto a tag the asset already has would list it twice
    data["tags"] = list(dict.fromkeys(tags))

    # write next to it and swap, a dropped network connection mid write
    # must not leave the asset with half a metadata file
    tmp = meta.with_name(meta.name + ".tmp")
    with open(tmp, "w") as f:
        json.dump(data, f)
    os.replace(tmp, meta)

    return True


def _all_pools() -> list[Path]:
    pools: list[Path] = []
    for table, rows in db.select_all().items():
        if table == db.Tables.TAGS.name:
            continue
        pools.extend(rows.values())

    return list(dict.fromkeys(pools))


class TagService:
    def create(self, name: str):
        with db.connection() as conn:
            conn.execute("INSERT OR IGNORE INTO tags (name) VALUES(?);", (name,))
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
            return sorted(p, key=str.lower)

        return []

    def rename_everywhere(self, old: str, new: str) -> TagRewriter:
        """Rename a tag, merging it into `new` if that tag already exists.

        The tag table changes right away, the assets once the returned
        rewriter is started.
        """
        with db.connection() as conn:
            if conn.execute("SELECT 1 FROM tags WHERE name = ?;", (new,)).fetchone():
                conn.execute("DELETE FROM tags WHERE name = ?;", (old,))
            else:
                conn.execute("UPDATE tags SET name = ? WHERE name = ?;", (new, old))
            conn.commit()

        return self._rewrite_assets(old, new)

    def delete_everywhere(self, name: str) -> TagRewriter:
        """Delete a tag and take it off every asset that carries it."""
        self.delete(name)
        return self._rewrite_assets(name, None)

    def _rewrite_assets(self, old: str, new: str | None) -> TagRewriter:
        return TagRewriter(old, new, _all_pools())
