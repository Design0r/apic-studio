from pathlib import Path

from shared.messaging import Message, MessageRouter
from shared.network import Connection

from .services import hdris

router = MessageRouter("hdris.")


@router.register("import.domelight")
def import_domelight(conn: Connection, msg: Message):
    if msg.data is None:
        conn.send(Message("error", "No file path provided for import."))
        return
    path = msg.data.get("path", "")
    if not path:
        conn.send(Message("error", "File path is empty."))
        return

    hdris.hdri_import_as_dome(Path(path))
    conn.send(Message("success"))


@router.register("import.arealight")
def import_arealight(conn: Connection, msg: Message):
    if msg.data is None:
        conn.send(Message("error", "No file path provided for import."))
        return
    path = msg.data.get("path", "")
    if not path:
        conn.send(Message("error", "File path is empty."))
        return

    hdris.hdri_import_as_area(Path(path))
    conn.send(Message("success"))
