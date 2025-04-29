import sys
from threading import Thread

sys.path.append(r"C:\Users\TheApic\GitHub\apic-studio")
from apic_studio.connector import Message, MessageRouter
from apic_studio.connector.server import ConnectionHandler, Server

router = MessageRouter()


@router.register("hello")
def hello(ctx: ConnectionHandler, msg: Message):
    print("HELLO!")


@router.register("export.selected")
def export_selected(ctx: ConnectionHandler, msg: Message):
    print("exporting")


def main():
    print("hello cinema")
    t = Thread(target=lambda: Server(router=router))
    t.start()


if __name__ == "__main__":
    main()
