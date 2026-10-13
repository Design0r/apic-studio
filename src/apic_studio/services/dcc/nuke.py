from pathlib import Path

from apic_studio.core.settings import SettingsManager
from shared.logger import Logger
from shared.messaging import Message

from .base import BaseBridge


class NukeBridge(BaseBridge):
    key = "nuke"
    label = "Nuke"
    short_label = "NK"

    def address(self) -> tuple[str, int]:
        return SettingsManager().CoreSettings.nuke_address

    def file_open_in_place(self, path: Path) -> Message:
        """Clears the current comp, discarding unsaved changes, then opens path."""
        res = self.call("core.file.open_in_place", {"path": str(path)})
        if self.is_err(res):
            Logger.error(f"failed to open file in place: {path.name}: {res}")

        return res

    def file_export(self, path: Path) -> Message:
        res = self.call("core.file.export", {"path": str(path)})
        if self.is_err(res):
            Logger.error(f"failed to export file: {path.name}: {res}")

        return res

    def file_import(self, path: Path) -> Message:
        res = self.call("core.file.import", {"path": str(path)})
        if self.is_err(res):
            Logger.error(f"failed to import file: {path.name}: {res}")

        return res
