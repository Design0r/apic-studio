from shared.logger import Logger
from shared.messaging import Message, MessageRouter
from shared.network import Connection

from .services import core, materials

router = MessageRouter("materials.")


@router.register("list")
def list_materials(conn: Connection, _: Message):
    mtls = materials.get_material_names()
    conn.send(Message("success", data={"materials": mtls}))


@router.register("export")
def export_materials(conn: Connection, msg: Message):
    if not msg.data:
        conn.send(Message("error", data={"message": "expected data"}))
        return

    ok = materials.export_materials(msg.data["materials"], msg.data["path"])
    conn.send(Message("success" if ok else "error"))


@router.register("import")
def import_file(conn: Connection, msg: Message):
    if msg.data is None:
        conn.send(Message("error", "No file path provided for import."))
        return
    path = msg.data.get("path", "")
    if not path:
        conn.send(Message("error", "File path is empty."))
        return

    Logger.debug(f"importing materials from {path}")
    core.import_file(path)

    conn.send(Message("success"))


@router.register("preview.create")
def render_preview(conn: Connection, msg: Message):
    if msg.data is None:
        conn.send(Message("error", "expected message data"))
        return
    path = msg.data.get("path")
    if not path:
        conn.send(Message("error", "file path is empty."))
        return

    mtls = materials.get_materials(msg.data["materials"])
    print(mtls)
    print(msg.data)
    materials.save_material_previews(mtls, path)

    conn.send(Message("success"))
