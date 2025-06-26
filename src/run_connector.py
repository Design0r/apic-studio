import importlib
import sys
from queue import Empty, Queue

import c4d
from c4d.threading import C4DThread

# sys.path.append(r"C:\Users\TheApic\GitHub\apic-studio")
from apic_connector import c4d as routers
from shared.logger import Logger
from shared.messaging import Message, MessageRouter
from shared.network import Connection, Server

thread = None
PLUGIN_ID = 1234567


class ServerThread(C4DThread):
    def __init__(self, server: Server):
        self.server = server

    def Main(self):
        self.server.run()

    def End(self, wait: bool = True):
        self.server.stop()
        super().End(wait)


class TimerMessage(c4d.plugins.MessageData):
    def __init__(self, queue: Queue[tuple[Connection, Message]], router: MessageRouter):
        self.queue = queue
        self.router = router

    def GetTimer(self) -> int:
        return 200

    def CoreMessage(self, id: int, bc: c4d.BaseContainer):
        if id == c4d.MSG_TIMER:
            self.process_queue()

        return True

    def process_queue(self):
        while True:
            try:
                conn, message = self.queue.get_nowait()
            except Empty:
                break

            self.router.serve(conn, message)


def PluginMessage(id: int, _) -> bool:
    global thread

    if thread and (id == c4d.C4DPL_ENDPROGRAM or id == c4d.C4DPL_SHUTDOWNTHREADS):
        thread.End(wait=False)
        thread = None

    if id == c4d.C4DPL_RELOADPYTHONPLUGINS:
        Logger.debug("reloading apic studio connector...")

        import apic_studio

        importlib.reload(apic_studio)
        for name, mod in list(sys.modules.items()):
            if name.startswith("apic_studio."):
                importlib.reload(mod)

        main()

    return True


def main():
    global thread

    if thread is not None:
        return True

    router = MessageRouter()
    router.include_router(routers.core_router)
    router.include_router(routers.models_router)
    queue: Queue[tuple[Connection, Message]] = Queue()

    if not c4d.plugins.FindPlugin(PLUGIN_ID):
        c4d.plugins.RegisterMessagePlugin(
            id=PLUGIN_ID,
            str="Apic Studio Connector",
            info=0,
            dat=TimerMessage(queue, router),
        )

    thread = ServerThread(Server(router=router, msg_queue=queue))
    thread.Start()


if __name__ == "__main__":
    main()
