import socket
from queue import Queue
from threading import Thread
from typing import Optional

from shared.logger import Logger
from shared.messaging import Message, MessageRouter

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
        self._is_running = True

        ip, port = connection.socket.getpeername()
        self.client_ip = f"{ip}:{port}"

        Logger.info(f"client: {self.client_ip} connected")

    def handle_message(self, message: Message) -> None:
        if self.msg_queue:
            self.msg_queue.put((self.connection, message))
            return

        self.router.serve(self.connection, message)

    def run(self) -> None:
        while self._is_running:
            try:
                data = self.connection.recv()
            except Exception:
                self.stop()
                break

            message = Message(**data)
            self.handle_message(message)

    def stop(self):
        self.connection.close()
        self._is_running = False
        Logger.info(f"client {self.client_ip} disconnected")


class Server:
    def __init__(
        self,
        addr: str = "localhost",
        port: int = 1337,
        router: MessageRouter = MessageRouter(),
        msg_queue: Optional[Queue[tuple[Connection, Message]]] = None,
        socket_timeout: Optional[float] = None,
    ) -> None:
        self.addr = addr
        self.port = port
        self.router = router
        self.timeout = socket_timeout
        self._running = False
        self.msg_queue = msg_queue
        self.handlers: list[ConnectionHandler] = []
        self.socket: Optional[Connection] = None

    def run(self):
        self._running = True

        server_address = (self.addr, self.port)
        self.socket = Connection.server_connection(server_address, self.timeout)
        if not self.socket:
            Logger.error("oops")
            return

        Logger.info(f"connection server listening on {self.addr}:{self.port}")

        while self._running:
            try:
                sock = self.socket.accept()
            except socket.timeout:
                continue
            except Exception:
                self.stop()
                return

            conn = Connection(sock)
            conn_handler = ConnectionHandler(conn, self.router, self.msg_queue)
            self.handlers.append(conn_handler)
            Thread(target=conn_handler.run).start()

    def stop(self):
        Logger.info("stopping connection server")
        self._running = False
        for h in self.handlers:
            h.stop()

        if not self.socket:
            return

        self.socket.close()
