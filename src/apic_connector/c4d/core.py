from shared.messaging import Message, MessageRouter
from shared.network import Connection

core_router = MessageRouter("core.")


@core_router.register("status")
def status(conn: Connection, msg: Message):
    response = Message("status", {"status": 200})
    conn.send(response)
