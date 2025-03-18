import socket
from threading import Thread

from .connection import Connection
from .router import Message, MessageRouter


class ClientHandler:
    def __init__(self, connection: Connection, router: MessageRouter) -> None:
        self.connection = connection
        self.router = router

        ip, port = connection.socket.getpeername()
        self.client_ip = f"{ip}:{port}"

        print(f"client: {self.client_ip} connected")

    def handle_message(self, message: Message) -> None:
        print(f"MSG: {message}")
        self.router.serve(self, message)

    def send(self, data: bytes):
        self.connection.send(data)

    def run(self) -> None:
        while True:
            try:
                data = self.connection.recv()
                message = Message(**data)
                self.handle_message(message)
            except Exception as e:
                print(e)
                break

        print(f"client {self.client_ip} disconnected")
        self.connection.close()


class Server:
    def __init__(
        self,
        addr: str = "localhost",
        port: int = 65432,
        router: MessageRouter = MessageRouter(),
    ) -> None:
        self.addr = addr
        self.port = port
        self.router = router
        self._running = False

    def run(self):
        self._running = True

        server_address = (self.addr, self.port)
        server_socket = Connection.server_connection(server_address)
        print("apic studio server listening on", server_address)

        while self._running:
            try:
                sock = server_socket.accept()
                client_handler = ClientHandler(Connection(sock), self.router)
                thread = Thread(target=client_handler.run)
                thread.start()
            except socket.timeout:
                continue

    def stop(self):
        self._running = False
