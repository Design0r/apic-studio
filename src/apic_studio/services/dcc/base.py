from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from subprocess import Popen
from typing import Any, ClassVar, Protocol, Self

from PySide6.QtCore import QObject, QThread

from shared.logger import Logger
from shared.messaging import Message
from shared.network import Connection


class CmdBuilder:
    def __init__(self) -> None:
        self._cmd: list[str] = []

    def add_positional(self, value: str):
        self._cmd.append(f'"{value}"')

    def add_flag(self, flag: str, value: Any | None = None):
        self._cmd.append(flag)
        if value:
            self._cmd.append(f'"{value}"')

    def build(self) -> str:
        return " ".join(self._cmd)

    def build_list(self) -> list[str]:
        return self._cmd


class DCC(Protocol):
    def get_exe(self) -> Path: ...
    def get_py(self) -> Path: ...
    def version(self) -> str: ...
    def run_exe(self, args: list[str]): ...
    def run_py(self, args: list[str]): ...


class RenderThread(QThread):
    def __init__(
        self,
        cmd: str,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self.cmd = cmd

    def run(self):
        with Popen(self.cmd) as p:
            # out, err = p.communicate()
            # try:
            #     Logger.debug(out.decode(errors="ignore"))
            #     Logger.debug(err.decode(errors="ignore"))
            # except UnicodeEncodeError:
            #     pass
            p.wait()


class BaseBridge:
    """
    Talks to the apic studio connector running inside one host app.

    To support another app, subclass this with its key, labels and address plus
    the calls its connector understands, then add it to `DCCBridge`.
    """

    # short id, used to tell the apps apart in the ui
    key: ClassVar[str]
    # full name, shown in tooltips and logs
    label: ClassVar[str]
    # few letters, shown on the connection status button
    short_label: ClassVar[str]

    def __init__(self, ctx: Connection) -> None:
        self.ctx = ctx

    @classmethod
    def create(cls, timeout: float | None = 5) -> Self:
        name = f"{cls.label.lower()} connector"
        return cls(Connection.client_connection(timeout=timeout, name=name))

    def address(self) -> tuple[str, int]:
        raise NotImplementedError()

    @property
    def is_connected(self) -> bool:
        return self.ctx.is_connected

    def is_err(self, msg: Message) -> bool:
        return msg.message == "error"

    def call(self, message: str, data: Any | None = None) -> Message:
        msg = Message(message, data=data)
        res = self.ctx.send_recv(msg)
        return Message.from_dict(res)

    def connect(self) -> None:
        self.ctx.connect(self.address())

    def close(self) -> None:
        self.ctx.close()

    def on_connect(self, fn: Callable[[], None]) -> None:
        self.ctx.on_connect(fn)

    def on_disconnect(self, fn: Callable[[], None]) -> None:
        self.ctx.on_disconnect(fn)

    def file_open(self, path: Path) -> Message:
        res = self.call("core.file.open", {"path": str(path)})
        if self.is_err(res):
            Logger.error(f"failed to open file: {path.name}: {res}")

        return res
