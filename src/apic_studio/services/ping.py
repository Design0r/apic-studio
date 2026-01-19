import time
from threading import Thread

from shared.logger import Logger
from shared.network.connection import Connection


class PingWorker:
    def __init__(self, conn: Connection, sleep_duration: int, retries: int) -> None:
        self._conn = conn
        self._sleep_duration = sleep_duration
        self._retries: int = retries
        self._retry_counter = 0

    def run(self):
        status = None
        while True:
            if not self._conn.is_connected:
                time.sleep(self._sleep_duration)
                continue

            Logger.debug("pinging apic studio connector...")

            try:
                status = self._conn.status()
            except Exception:
                if self.retry():
                    continue
                else:
                    self._conn._disconnect()  # type: ignore
                    break

            if not status and not self.retry():
                self._conn._disconnect()  # type: ignore
                break

            if self._retry_counter > 0:
                self._retry_counter = 0

            Logger.debug("ping successful")
            time.sleep(self._sleep_duration)

    def retry(self) -> bool:
        if self._retry_counter == self._retries:
            return False

        self._retries += 1
        return True


class PingService:
    def __init__(
        self, conn: Connection, sleep_duration: int = 15, retries: int = 3
    ) -> None:
        self._thread = Thread(
            target=PingWorker(conn, sleep_duration, retries).run, daemon=True
        )
        self._thread.start()

    def stop(self):
        self._thread = None
