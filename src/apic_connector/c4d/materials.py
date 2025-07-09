from shared.logger import Logger
from shared.messaging import Message, MessageRouter
from shared.network import Connection

from .services import materials

material_router = MessageRouter("materials.")


@material_router.register("list")
def list_materials(conn: Connection, msg: Message):
    Logger.debug("listing materials")
    mtls = materials.get_materials()
    conn.send(Message("success", data={"materials": mtls}))
