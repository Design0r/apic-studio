from __future__ import absolute_import

from .compat import Message, MessageRouter
from .services import core

router = MessageRouter("core.")


@router.register("status")
def status(conn, _):
    response = Message("status", {"status": 200})
    conn.send(response)


@router.register("file.open")
def open_file(conn, msg):
    if msg.data is None:
        conn.send(Message("error", "No file path provided for import."))
        return
    path = msg.data.get("path", "")
    if not path:
        conn.send(Message("error", "File path is empty."))
        return

    res = core.open_file(path)
    if res:
        conn.send(Message("success"))
    else:
        conn.send(Message("error"))


@router.register("file.save_as")
def save_file_as(conn, msg):
    if msg.data is None:
        conn.send(Message("error", "No file path provided for import."))
        return
    path = msg.data.get("path", "")
    if not path:
        conn.send(Message("error", "File path is empty."))
        return
    globalize = msg.data.get("globalize_textures", False)

    res = core.save_file_as(path, globalize)
    if res:
        conn.send(Message("success"))
    else:
        conn.send(Message("error"))
