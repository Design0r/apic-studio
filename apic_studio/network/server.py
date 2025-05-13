import socket
from queue import Queue
from threading import Thread
from typing import Optional

from apic_studio.core import Logger
from apic_studio.messaging import Message, MessageRouter

from . import Connection


class ConnectionHandler:
    def __init__(
        self,
        connection: Connection,
        router: MessageRouter,
        msg_queue: Optional[Queue[tuple[Connection, Message]]] = None,
    ) -> None:
        self.connection = connection
        self.router = router
        self.msg_queue = msg_queue

        ip, port = connection.socket.getpeername()
        self.client_ip = f"{ip}:{port}"

        Logger.info(f"client: {self.client_ip} connected")

    def handle_message(self, message: Message) -> None:
        self.router.serve(self.connection, message)
        if self.msg_queue:
            self.msg_queue.put((self.connection, message))

    def run(self) -> None:
        while True:
            try:
                data = self.connection.recv()
                message = Message(**data)
                self.handle_message(message)
            except Exception as e:
                Logger.exception(e)
                break

        Logger.info(f"client {self.client_ip} disconnected")
        self.connection.close()


class Server:
    def __init__(
        self,
        addr: str = "localhost",
        port: int = 65432,
        router: MessageRouter = MessageRouter(),
        msg_queue: Optional[Queue[tuple[Connection, Message]]] = None,
    ) -> None:
        self.addr = addr
        self.port = port
        self.router = router
        self._running = False
        self.msg_queue = msg_queue

        self.run()
        self.stop()

    def run(self):
        self._running = True

        server_address = (self.addr, self.port)
        server_socket = Connection.server_connection(server_address)
        Logger.info(f"connection server listening on {self.addr}:{self.port}")

        while self._running:
            try:
                sock = server_socket.accept()
                conn_handler = ConnectionHandler(
                    Connection(sock), self.router, msg_queue=self.msg_queue
                )
                conn_handler.run()
                Thread(target=conn_handler.run).start()
            except socket.timeout:
                continue

    def stop(self):
        self._running = False
        Logger.info("stopping connection server")
