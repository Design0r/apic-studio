from subprocess import PIPE, Popen

from PySide6.QtCore import QObject, Signal

from shared.logger import Logger


class CmdWorker(QObject):
    finished = Signal()

    def __init__(self, cmd: str, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.cmd: str = cmd

    def run(self):
        with Popen(self.cmd, stdout=PIPE, stderr=PIPE) as process:
            out, err = process.communicate()
            Logger.info(out.decode())
            Logger.info(err.decode())
            process.wait()

        self.finished.emit()
