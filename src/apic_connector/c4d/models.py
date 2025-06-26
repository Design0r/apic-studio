from shared.logger import Logger
from shared.messaging import Message, MessageRouter
from shared.network import Connection

from .services import models

models_router = MessageRouter("models.")


@models_router.register("export.selected")
def export_selected(conn: Connection, msg: Message):
    models.export_selected()
    conn.send(Message("success"))


@models_router.register("export.all")
def export_all(conn: Connection, msg: Message):
    Logger.debug("exporting all")
