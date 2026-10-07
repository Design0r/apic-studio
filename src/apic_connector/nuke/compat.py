"""
Python 2.7 / 3 compatible port of the parts of `shared` the nuke connector needs.

Nuke 12.2 runs on Python 2.7, so this module must not import `shared` and must
stay within the syntax both interpreters understand (no f-strings, annotations,
dataclasses, ...). It speaks the same wire protocol as `shared.network`:
a 4 byte big-endian length header followed by a utf-8 json body of
{"message": str, "data": any}.

Delete this module once nuke runs on Python 3 and import from `shared` instead.
"""

from __future__ import absolute_import

import json
import logging
import socket
import struct
import sys
import threading
from collections import defaultdict

_HEADER = struct.Struct(">I")


class Logger(object):
    LOGGER_NAME = "apic_studio"

    FORMAT_DEFAULT = "[%(name)s][%(levelname)s] %(message)s"

    LEVEL_DEFAULT = logging.DEBUG
    # nuke attaches its own handler to the root logger, propagating would log twice
    PROPAGATE_DEFAULT = False

    _logger_obj = None

    @classmethod
    def logger_obj(cls):
        if not cls._logger_obj:
            exists = cls.LOGGER_NAME in logging.Logger.manager.loggerDict
            cls._logger_obj = logging.getLogger(cls.LOGGER_NAME)

            if not exists:
                cls._logger_obj.setLevel(cls.LEVEL_DEFAULT)
                cls._logger_obj.propagate = cls.PROPAGATE_DEFAULT

                stream_handler = logging.StreamHandler(sys.stdout)
                stream_handler.setFormatter(logging.Formatter(cls.FORMAT_DEFAULT))
                cls._logger_obj.addHandler(stream_handler)

        return cls._logger_obj

    @classmethod
    def debug(cls, msg):
        cls.logger_obj().debug(msg)

    @classmethod
    def info(cls, msg):
        cls.logger_obj().info(msg)

    @classmethod
    def warning(cls, msg):
        cls.logger_obj().warning(msg)

    @classmethod
    def error(cls, msg):
        cls.logger_obj().error(msg)

    @classmethod
    def exception(cls, msg):
        cls.logger_obj().exception(msg)


class Message(object):
    __slots__ = ("data", "message")

    def __init__(self, message, data=None):
        self.message = message
        self.data = data

    def as_json(self, encoding="utf-8"):
        message = {"message": self.message, "data": self.data}
        return json.dumps(message).encode(encoding)

    @staticmethod
    def from_dict(data):
        return Message(message=data["message"], data=data.get("data"))


class Connection(object):
    def __init__(self, sock):
        self.socket = sock

    def send(self, data):
        if isinstance(data, Message):
            Logger.debug("sending message: {}".format(data.message))
            data = data.as_json()
        else:
            Logger.debug("sending message: {} bytes".format(len(data)))

        try:
            self.socket.sendall(_HEADER.pack(len(data)) + data)
        except socket.error:
            Logger.error("failed to send message, socket is already closed")
        except Exception as e:
            Logger.exception(e)

        return self

    def _recv_exactly(self, size):
        buffer = bytearray()
        while len(buffer) < size:
            chunk = self.socket.recv(size - len(buffer))
            if not chunk:
                raise socket.error("connection closed while receiving message")

            buffer += chunk

        return bytes(buffer)

    def recv(self):
        (body_size,) = _HEADER.unpack(self._recv_exactly(_HEADER.size))
        if not body_size:
            raise socket.error("received an empty message")

        response = self._recv_exactly(body_size).decode("utf-8")

        try:
            rjson = json.loads(response)
        except ValueError:
            Logger.error("failed to decode message")
            raise

        Logger.debug("receiving message: {}".format(rjson.get("message")))
        return rjson

    def close(self):
        try:
            self.socket.shutdown(socket.SHUT_RDWR)
        except socket.error:
            pass

        try:
            self.socket.close()
        except Exception as e:
            Logger.exception(e)


class MessageRouter(object):
    def __init__(self, prefix=""):
        self.prefix = prefix
        self.routes = defaultdict(list)

    def serve(self, ctx, message):
        routes = self.routes.get(message.message)
        if not routes:
            ctx.send(Message("unregistered message"))
            return

        for handler in routes:
            handler(ctx, message)

    def register(self, message):
        def decorator(fn):
            self.routes[self.prefix + message].append(fn)
            return fn

        return decorator

    def include_router(self, sub_router):
        for k, v in sub_router.routes.items():
            self.routes[k].extend(v)

        return self


def _call_directly(fn, args):
    fn(*args)


def _start_daemon(target):
    # Thread(daemon=True) is py3 only
    thread = threading.Thread(target=target)
    thread.daemon = True
    thread.start()
    return thread


class ConnectionHandler(object):
    def __init__(self, connection, router, dispatch=_call_directly):
        self.connection = connection
        self.router = router
        self.dispatch = dispatch
        self._is_running = True

        ip, port = connection.socket.getpeername()[:2]
        self.client_ip = "{}:{}".format(ip, port)

        Logger.info("client: {} connected".format(self.client_ip))

    def run(self):
        while self._is_running:
            try:
                data = self.connection.recv()
            except Exception:
                self.stop()
                break

            try:
                message = Message.from_dict(data)
            except (KeyError, TypeError, AttributeError):
                Logger.error("received malformed message")
                continue

            self.dispatch(self.router.serve, (self.connection, message))

    def stop(self):
        if not self._is_running:
            return

        self._is_running = False
        self.connection.close()
        Logger.info("client {} disconnected".format(self.client_ip))


class Server(object):
    """
    `dispatch(fn, args)` decides where handlers run. Pass
    `nuke.executeInMainThread` so handlers can safely use the nuke api;
    the default calls them on the connection's thread.
    """

    def __init__(
        self, addr="localhost", port=1337, router=None, dispatch=_call_directly
    ):
        self.addr = addr
        self.port = port
        self.dispatch = dispatch
        self._running = False
        self.handlers = []
        self.socket = None
        self.router = router or MessageRouter()

    def _bind(self):
        try:
            server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            # SO_REUSEADDR on windows lets a second nuke instance bind the same
            # port and steal connections, so claim it exclusively there
            if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
                opt = socket.SO_EXCLUSIVEADDRUSE
            else:
                opt = socket.SO_REUSEADDR
            server_socket.setsockopt(socket.SOL_SOCKET, opt, 1)
            server_socket.bind((self.addr, self.port))
        except socket.error as e:
            Logger.warning(
                "failed to bind {}:{}, another nuke instance is probably already "
                "serving apic studio: {}".format(self.addr, self.port, e)
            )
            return None

        server_socket.listen(1)
        server_socket.settimeout(1.0)
        return server_socket

    def run(self):
        self._running = True

        self.socket = self._bind()
        if not self.socket:
            return

        Logger.info("connection server listening on {}:{}".format(self.addr, self.port))

        while self._running:
            try:
                sock, _ = self.socket.accept()
            except socket.timeout:
                continue
            except Exception:
                self.stop()
                return

            # on windows py2 the accepted socket inherits the listening socket's
            # non-blocking mode without python knowing, force it back to blocking
            sock.setblocking(True)

            conn_handler = ConnectionHandler(
                Connection(sock), self.router, self.dispatch
            )
            self.handlers.append(conn_handler)
            _start_daemon(conn_handler.run)

    def start(self):
        return _start_daemon(self.run)

    def stop(self):
        Logger.info("stopping connection server")
        self._running = False
        for h in self.handlers:
            h.stop()

        if not self.socket:
            return

        self.socket.close()
