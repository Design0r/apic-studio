from __future__ import annotations

import json
import select
import socket
from typing import Any, Callable, Optional, Self

from shared.logger import Logger
from shared.messaging.message import Message


class Connection:
    def __init__(self, socket: socket.socket, timeout: Optional[float] = None) -> None:
        self.socket = socket

        self.timeout = timeout
        self._on_connect: list[Callable[[], None]] = []
        self._on_disconnect: list[Callable[[], None]] = []
        self.is_connected = False

    def send(self, data: bytes | Message) -> Self:
        if isinstance(data, Message):
            Logger.debug(f"sending message: {data.message}")
            data = data.as_json()
        else:
            Logger.debug(f"sending message: {len(data)} bytes")

        header = len(data).to_bytes(4, "big")
        try:
            self.socket.sendall(header + data)
        except OSError:
            Logger.error("failed to send message, socket is already closed")
        except Exception as e:
            Logger.exception(e)

        return self

    def send_recv(self, data: bytes | Message) -> dict[str, Any]:
        self.send(data)
        response = self.recv()
        return response

    def recv(self) -> dict[str, Any]:
        ready, _, _ = select.select([self.socket], [], [], self.timeout)
        if not ready:
            Logger.warning(f"recv() timed out after {self.timeout}s")
            raise TimeoutError(f"no data in {self.timeout}s")

        header = self.socket.recv(4)
        body_size = int.from_bytes(header, "big")
        response = self.socket.recv(body_size).decode("utf-8")

        try:
            rjson = json.loads(response)
        except json.JSONDecodeError as e:
            Logger.error("failed to decode message")
            raise e
        except TimeoutError:
            Logger.error("message timed out")
            return {}

        Logger.debug(f"receiving message: {rjson.get('message')}")
        return rjson

    def close(self) -> None:
        try:
            self.socket.close()
        except Exception:
            pass
        self.is_connected = False

    def status(self) -> bool:
        msg = Message("core.status")

        try:
            res = self.send_recv(msg)
        except Exception as e:
            Logger.exception(e)
            self.is_connected = False
            return False

        return res.get("status") == 200

    def _disconnect(self):
        self.is_connected = False
        for c in self._on_disconnect:
            c()

    def connect(self, address: tuple[str, int]) -> Self:
        Logger.info("connecting to C4D connector...")
        if self.is_connected and self.status():
            return self

        try:
            self.socket.connect(address)
        except ConnectionRefusedError as e:
            Logger.exception(e)
            self._disconnect()
            Logger.error(
                f"connection refused, disconnecting from socket {address}, apic studio connector is not available"
            )
            return self
        except OSError as e:
            Logger.exception(e)
            self.close()
            self.socket = self.client_connection().socket
            return self.connect(address)
        except Exception as e:
            Logger.exception(e)
            self._disconnect()
            return self

        Logger.info("connected to C4D connector")
        self.is_connected = True
        for c in self._on_connect:
            c()

        return self

    def on_connect(self, fn: Callable[[], None]) -> None:
        self._on_connect.append(fn)

    def on_disconnect(self, fn: Callable[[], None]) -> None:
        self._on_disconnect.append(fn)

    @classmethod
    def client_connection(cls, timeout: Optional[float] = None) -> Connection:
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        return Connection(client_socket, timeout)

    @classmethod
    def server_connection(
        cls, adress: tuple[str, int], timeout: Optional[float] = None
    ) -> Optional[Connection]:
        try:
            server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server_socket.bind(adress)
        except OSError as e:
            Logger.exception(e)
            Logger.error("failed to create server socket")
            return None

        server_socket.listen(1)
        server_socket.settimeout(1.0)
        return Connection(server_socket, timeout=timeout)

    def accept(self) -> socket.socket:
        socket, _ = self.socket.accept()
        return socket
