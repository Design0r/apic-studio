from __future__ import annotations

import json
import socket
from typing import Any, Self

from apic_studio.core import Logger


class Connection:
    def __init__(self, socket: socket.socket) -> None:
        self.socket = socket

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

    def connect(self, adress: tuple[str, int]) -> Self:
        try:
            self.socket.connect(adress)
        except Exception as e:
            Logger.exception(e)
        return self

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
