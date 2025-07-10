from shared.messaging import Message, MessageRouter
from shared.network import Connection

router = MessageRouter("core.")


@router.register("status")
def status(conn: Connection, msg: Message):
    response = Message("status", {"status": 200})
    conn.send(response)
