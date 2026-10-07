from __future__ import annotations

import json
import select
import socket
import threading
from collections.abc import Callable
from typing import Any, Self

from shared.logger import Logger
from shared.messaging.message import Message


class Connection:
    def __init__(
        self,
        socket: socket.socket,
        timeout: float | None = None,
        name: str = "apic studio connector",
    ) -> None:
        self.socket = socket
        self.name = name

        self.timeout = timeout
        self._on_connect: list[Callable[[], None]] = []
        self._on_disconnect: list[Callable[[], None]] = []
        self.is_connected = False

        self._txn_lock = threading.RLock()

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
        with self._txn_lock:
            self.send(data)
            return self.recv()

    def _recv_exactly(self, size: int) -> bytes:
        buffer = bytearray()
        while len(buffer) < size:
            ready, _, _ = select.select([self.socket], [], [], self.timeout)
            if not ready:
                Logger.warning(f"recv() timed out after {self.timeout}s")
                raise TimeoutError(f"no data in {self.timeout}s")

            chunk = self.socket.recv(size - len(buffer))
            if not chunk:
                raise ConnectionError("connection closed while receiving message")

            buffer += chunk

        return bytes(buffer)

    def recv(self) -> dict[str, Any]:
        header = self._recv_exactly(4)
        body_size = int.from_bytes(header, "big")
        if not body_size:
            raise ConnectionError("received an empty message")

        response = self._recv_exactly(body_size).decode("utf-8")

        try:
            rjson = json.loads(response)
        except json.JSONDecodeError:
            Logger.error("failed to decode message")
            raise

        Logger.debug(f"receiving message: {rjson.get('message')}")
        return rjson

    def close(self) -> None:
        self.is_connected = False
        try:
            self.socket.close()
        except Exception as e:
            Logger.exception(e)

    def status(self) -> bool:
        msg = Message("core.status")

        try:
            res = self.send_recv(msg)
        except TimeoutError:
            return False
        except OSError:
            return False

        except Exception as e:
            Logger.exception(e)
            self.is_connected = False
            return False

        data = res.get("data")
        if not data:
            return False
        status = data.get("status")

        return status == 200

    def try_status(self) -> bool | None:

        if not self._txn_lock.acquire(blocking=False):
            return None

        try:
            return self.status()
        finally:
            self._txn_lock.release()

    def _notify(self, callbacks: list[Callable[[], None]]) -> None:
        for c in callbacks:
            try:
                c()
            except Exception as e:
                Logger.exception(e)

    def _disconnect(self):
        self.is_connected = False
        Logger.error(f"lost connection to {self.name}")
        self._notify(self._on_disconnect)

    def connect(self, address: tuple[str, int]) -> Self:
        Logger.info(f"connecting to {self.name}...")
        if self.is_connected and self.status():
            return self

        with self._txn_lock:
            try:
                self.socket.connect(address)
            except ConnectionRefusedError:
                self._disconnect()
                Logger.error(
                    f"connection refused, disconnecting from socket {address}, {self.name} is not available"
                )
                return self
            except OSError as e:
                Logger.exception(e)
                self.close()
                self.socket = self.client_connection(name=self.name).socket
                return self.connect(address)
            except Exception as e:
                Logger.exception(e)
                self._disconnect()
                return self

            Logger.info(f"connected to {self.name}")
            self.is_connected = True

        self._notify(self._on_connect)

        return self

    def on_connect(self, fn: Callable[[], None]) -> None:
        self._on_connect.append(fn)

    def on_disconnect(self, fn: Callable[[], None]) -> None:
        self._on_disconnect.append(fn)

    @classmethod
    def client_connection(
        cls, timeout: float | None = None, name: str = "apic studio connector"
    ) -> Connection:
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        return Connection(client_socket, timeout, name)

    @classmethod
    def server_connection(
        cls, adress: tuple[str, int], timeout: float | None = None
    ) -> Connection | None:
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
