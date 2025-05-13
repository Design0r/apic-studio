import sys
from queue import Empty, Queue

import c4d
from c4d.threading import C4DThread

sys.path.append(r"C:\Users\TheApic\GitHub\apic-studio")
from apic_studio.connector.router import msg_router
from apic_studio.messaging import Message
from apic_studio.network import Connection, Server

msg_queue: Queue[tuple[Connection, Message]] = Queue()
thread = None


class ServerThread(C4DThread):
    def __init__(self, server: Server):
        self.srv = server

    def Main(self):
        self.srv.run()

    def End(self, wait: bool = True):
        self.srv.stop()
        super().End(wait)

    def TestBreak(self) -> bool:
        print("breaking")
        return super().TestBreak()


class TimerMessage(c4d.plugins.MessageData):
    def __init__(self):
        self.router = msg_router

    def GetTimer(self) -> int:
        return 200

    def CoreMessage(self, id: int, bc: c4d.BaseContainer):
        if id == c4d.MSG_TIMER:
            self.process_queue()

        return True

    def process_queue(self):
        while True:
            try:
                conn, message = msg_queue.get_nowait()
            except Empty:
                break

            self.router.serve(conn, message)


def PluginMessage(id: int, _) -> bool:
    # called during shutdown (before BaseThread system goes away)
    if id == c4d.C4DPL_ENDPROGRAM or id == c4d.C4DPL_SHUTDOWNTHREADS:
        if thread:
            thread.End(wait=False)
    return True


def main():
    global thread

    c4d.plugins.RegisterMessagePlugin(
        id=1234567, str="Apic Studio Connector", info=0, dat=TimerMessage()
    )

    thread = ServerThread(Server(router=msg_router, msg_queue=msg_queue))
    thread.Start()


if __name__ == "__main__":
    main()
