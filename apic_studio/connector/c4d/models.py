from apic_studio.connector import router
from apic_studio.core import Logger
from apic_studio.messaging import Message, MessageRouter
from apic_studio.network import Connection

models_router = MessageRouter("models.")
router.include_router(models_router)


@models_router.register("export.selected")
def export_selected(conn: Connection, msg: Message):
    Logger.debug("exporting selected")


@models_router.register("export.all")
def export_all(conn: Connection, msg: Message):
    Logger.debug("exporting all")
