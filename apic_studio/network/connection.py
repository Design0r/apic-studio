from __future__ import annotations

import json
import socket
from typing import Any, Callable, Self

from apic_studio.core import Logger
from apic_studio.messaging.message import Message


class Connection:
    def __init__(self, socket: socket.socket) -> None:
        self.socket = socket
        self._on_connect: list[Callable[[], None]] = []
        self._on_disconnect: list[Callable[[], None]] = []
        self.is_connected = False

    def send(self, data: bytes) -> Self:
        header = len(data).to_bytes(4, "big")
        self.socket.sendall(header + data)
        return self

    def send_recv(self, data: bytes) -> dict[Any, Any]:
        self.send(data)
        response = self.recv()
        return response

    def recv(self) -> dict[Any, Any]:
        header = self.socket.recv(4)
        body_size = int.from_bytes(header, "big")
        response = self.socket.recv(body_size).decode("utf-8")
        return json.loads(response)

    def close(self) -> None:
        self.socket.close()
        self.is_connected = False

    def status(self) -> bool:
        msg = Message("core.status")

        try:
            res = self.send_recv(msg.as_json())
        except Exception as e:
            Logger.exception(e)
            self.is_connected = False
            return False

        return res["status"] == 200

    def _disconnect(self):
        self.is_connected = False
        for c in self._on_disconnect:
            c()

    def connect(self, adress: tuple[str, int]) -> Self:
        Logger.debug("Connecting to C4D connector...")
        if self.is_connected and self.status():
            return self

        try:
            self.socket.connect(tuple(adress))
        except Exception as e:
            Logger.exception(e)
            self._disconnect()
            return self

        Logger.debug("Connected to C4D connector")
        self.is_connected = True
        for c in self._on_connect:
            c()

        return self

    def on_connect(self, fn: Callable[[], None]) -> None:
        self._on_connect.append(fn)

    def on_disconnect(self, fn: Callable[[], None]) -> None:
        self._on_disconnect.append(fn)

    @classmethod
    def client_connection(cls) -> Connection:
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        return Connection(client_socket)

    @classmethod
    def server_connection(cls, adress: tuple[str, int]) -> Connection:
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.bind(adress)
        server_socket.listen(1)
        server_socket.settimeout(1.0)
        return Connection(server_socket)

    def accept(self) -> socket.socket:
        socket, _ = self.socket.accept()
        return socket
