from apic_studio.messaging import Message, MessageRouter
from apic_studio.network import Connection

core_router = MessageRouter("core.")


@core_router.register("status")
def status(conn: Connection, msg: Message):
    response = Message("status", {"status": 200})
    conn.send(response)
