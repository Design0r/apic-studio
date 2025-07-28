from pathlib import Path
from queue import Empty, Queue
from typing import Optional

from PySide6.QtCore import QObject, QThread, Signal

from .dcc import DCC


class ThumbnailWorker(QObject):
    finished = Signal(object)

    def __init__(self, dcc: DCC, parent: Optional[QObject] = None):
        super().__init__(parent)
        self.dcc = dcc

        self.task_queue: Queue[Path] = Queue()
        self._running = True

    def add_task(self, path: Path) -> None:
        self.task_queue.put(path)

    def stop(self) -> None:
        self._running = False

    def run(self) -> None:
        while self._running:
            try:
                path = self.task_queue.get(timeout=0.2)
            except Empty:
                continue


class ThumbnailRenderer(QObject):
    finished = Signal()

    def __init__(self, dcc: DCC, parent: Optional[QObject] = None):
        super().__init__(parent)
        self.worker = ThumbnailWorker(dcc)
        self.t = QThread()

        self.worker.moveToThread(self.t)
        self.t.started.connect(self.worker.run)
        self.worker.finished.connect(self.on_finish)
        self.t.start()

    def render(self, path: Path):
        self.worker.add_task(path)

    def on_finish(self):
        pass

    def stop(self):
        self.worker.stop()
        self.t.quit()
        self.t.wait()
