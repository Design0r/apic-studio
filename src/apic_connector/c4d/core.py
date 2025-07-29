from shared.messaging import Message, MessageRouter
from shared.network import Connection

from .services import core

router = MessageRouter("core.")


@router.register("status")
def status(conn: Connection, _: Message):
    response = Message("status", {"status": 200})
    conn.send(response)


@router.register("file.open")
def open_file(conn: Connection, msg: Message):
    if msg.data is None:
        conn.send(Message("error", "No file path provided for import."))
        return
    path = msg.data.get("path", "")
    if not path:
        conn.send(Message("error", "File path is empty."))
        return

    core.open_file(path)
    conn.send(Message("success"))
