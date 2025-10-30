import time
from threading import Thread

from shared.logger import Logger
from shared.network.connection import Connection


class PingWorker:
    def __init__(self, conn: Connection, sleep_duration: int) -> None:
        self._conn = conn
        self._sleep_duration = sleep_duration

    def run(self):
        while True:
            if not self._conn.is_connected:
                time.sleep(self._sleep_duration)
                continue

            Logger.debug("pinging apic studio connector...")

            try:
                status = self._conn.status()
            except Exception:
                self._conn._disconnect()  # type: ignore
                break

            if not status:
                self._conn._disconnect()  # type: ignore
                break

            Logger.debug("ping successful")
            time.sleep(self._sleep_duration)


class PingService:
    def __init__(self, conn: Connection, sleep_duration: int = 15) -> None:
        self._thread = Thread(target=PingWorker(conn, sleep_duration).run, daemon=True)
        self._thread.start()

    def stop(self):
        self._thread = None
