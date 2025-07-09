from pathlib import Path
from typing import Any, Callable, Optional

from shared.logger import Logger
from shared.messaging import Message
from shared.network import Connection


class DCCBridge:
    def __init__(self, ctx: Connection) -> None:
        self.ctx = ctx

    def is_err(self, msg: Message) -> bool:
        if msg.message == "error":
            return False

        return True

    def call(self, message: str, data: Optional[Any] = None) -> Message:
        msg = Message(message, data=data)
        res = self.ctx.send_recv(msg)
        return Message.from_dict(res)

    def connect(self, address: tuple[str, int]) -> None:
        self.ctx.connect(address)

    def on_connect(self, fn: Callable[[], None]) -> None:
        self.ctx.on_connect(fn)

    def on_disconnect(self, fn: Callable[[], None]) -> None:
        self.ctx.on_disconnect(fn)

    def models_export_selected(self, path: Path) -> Message:
        res = self.call("models.export.selected", {"path": str(path)})
        if self.is_err(res):
            Logger.error(
                f"failed to export asset: {path.name} to {path}: {res.message} {res.data}"
            )
        return res

    def models_import(self, path: Path) -> Message:
        res = self.call("models.import", {"path": str(path)})
        if self.is_err(res):
            Logger.error(
                f"failed to import asset: {path.name} to {path}: {res.message} {res.data}"
            )

        return res

    def save_as(self, path: Path) -> Message:
        res = self.call("core.save.as", {"path": str(path)})
        if self.is_err(res):
            Logger.error(
                f"failed to save as: {path.name} to {path}: {res.message} {res.data}"
            )

        return res

    def copy_textures(self, path: Path) -> Message:
        res = self.call("textures.export", {"path": str(path)})
        if self.is_err(res):
            Logger.error(
                f"failed to export textures: {path.name} to {path}: {res.message} {res.data}"
            )

        return res

    def materials_list(self) -> Message:
        res = self.call("materials.list")
        if self.is_err(res):
            Logger.error(f"failed to list materials: {res.message} {res.data}")

        return res
