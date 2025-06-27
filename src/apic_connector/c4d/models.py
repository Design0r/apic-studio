from shared.logger import Logger
from shared.messaging import Message, MessageRouter
from shared.network import Connection

from .services import models

models_router = MessageRouter("models.")


@models_router.register("export.selected")
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


@models_router.register("export.all")
def export_all(conn: Connection, msg: Message):
    Logger.debug("exporting all")


@models_router.register("import")
def import_file(conn: Connection, msg: Message):
    if msg.data is None:
        conn.send(Message("error", "No file path provided for import."))
        return
    path = msg.data.get("path", "")
    if not path:
        conn.send(Message("error", "File path is empty."))
        return

    Logger.debug(f"importing models from {path}")
    models.import_file(path)

    conn.send(Message("success"))
