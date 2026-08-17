from __future__ import annotations

import json
import select
import socket
import threading
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

        # Guards a request/response pair, nothing else. On the studio side more
        # than one thread talks over this socket (the GUI thread for every DCC
        # call, the ping thread every few seconds), and the wire is a stream of
        # length prefixed frames with no request ids, so an interleaved pair
        # leaves each thread holding the other's reply and both ends desync.
        #
        # Deliberately NOT taken by send() or recv() on their own: the connector
        # parks a reader thread in recv() until the next message arrives, while
        # replies are sent from C4D's main thread. A lock spanning that read
        # would block the host UI until the client disconnects.
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
        # TCP is a stream: a single recv() can return a short read, so keep
        # pulling until the full frame is here.
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
        except json.JSONDecodeError as e:
            Logger.error("failed to decode message")
            raise e

        Logger.debug(f"receiving message: {rjson.get('message')}")
        return rjson

    def close(self) -> None:
        self.is_connected = False
        try:
            self.socket.close()
        except Exception:
            pass

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

    def try_status(self) -> Optional[bool]:
        """status(), but never queues behind an in flight call.

        Returns None when another thread holds the line. A DCC operation can run
        for far longer than the ping timeout, so waiting for it would both delay
        that operation and report a healthy connector as dead.
        """
        if not self._txn_lock.acquire(blocking=False):
            return None

        try:
            return self.status()
        finally:
            self._txn_lock.release()

    def _notify(self, callbacks: list[Callable[[], None]]) -> None:
        # These run on whatever thread noticed the state change, so a listener
        # that has gone away must not take that thread down with it.
        for c in callbacks:
            try:
                c()
            except Exception as e:
                Logger.exception(e)

    def _disconnect(self):
        self.is_connected = False
        Logger.error("lost connection to apic studio connector")
        self._notify(self._on_disconnect)

    def connect(self, address: tuple[str, int]) -> Self:
        Logger.info("connecting to apic studio connector...")
        if self.is_connected and self.status():
            return self

        # client side only, the connector never dials out: holding the lock
        # keeps a DCC call from racing the socket being rebound below
        with self._txn_lock:
            try:
                self.socket.connect(address)
            except ConnectionRefusedError:
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

            Logger.info("connected to apic studio connector")
            self.is_connected = True

        self._notify(self._on_connect)

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
