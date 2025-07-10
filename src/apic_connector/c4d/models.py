import c4d
from shared.logger import Logger
from shared.messaging import Message, MessageRouter
from shared.network import Connection

from .services import core, models

router = MessageRouter("models.")


@router.register("export.selected")
def export_selected(conn: Connection, msg: Message):
    if msg.data is None:
        conn.send(Message("error", "No file path provided for export."))
        return
    path = msg.data.get("path", "")
    if not path:
        conn.send(Message("error", "File path is empty."))
        return

    Logger.debug(f"exporting selected models to {path}")
    models.export_selected(path)

    conn.send(Message("success"))


@router.register("export.all")
def export_all(conn: Connection, msg: Message):
    Logger.debug("exporting all")


@router.register("import")
def import_file(conn: Connection, msg: Message):
    if msg.data is None:
        conn.send(Message("error", "No file path provided for import."))
        return
    path = msg.data.get("path", "")
    if not path:
        conn.send(Message("error", "File path is empty."))
        return

    Logger.debug(f"importing models from {path}")
    core.import_file(c4d.documents.GetActiveDocument(), path)

    conn.send(Message("success"))
