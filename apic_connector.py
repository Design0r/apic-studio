import sys
from queue import Empty, Queue

import c4d
from c4d.threading import C4DThread

sys.path.append(r"C:\Users\TheApic\GitHub\apic-studio")
from apic_studio.connector.router import msg_router
from apic_studio.messaging import Message
from apic_studio.network import Connection, Server

msg_queue: Queue[tuple[Connection, Message]] = Queue()


class ServerThread(C4DThread):
    def Main(self):
        Server(router=msg_router, msg_queue=msg_queue)


class TimerMessage(c4d.plugins.MessageData):
    def __init__(self):
        self.router = msg_router

    def GetTimer(self) -> int:
        return 100

    def CoreMessage(self, id: int, bc: c4d.BaseContainer):
        if id == c4d.MSG_TIMER:
            self.ProcessQueue()

        return True

    def ProcessQueue(self):
        while True:
            try:
                conn, message = msg_queue.get_nowait()
            except Empty:
                break

            self.router.serve(conn, message)


if __name__ == "__main__":
    c4d.plugins.RegisterMessagePlugin(id=1234567, str="", info=0, dat=TimerMessage())
    thread = ServerThread()
    thread.Start()
