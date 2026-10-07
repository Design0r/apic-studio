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

            Logger.debug(f"pinging {self._conn.name}...")

            try:
                status = self._conn.try_status()
            except Exception:
                status = False

            if status is None:
                Logger.debug("connection busy, skipping ping")
                time.sleep(self._sleep_duration)
                continue

            if not status:
                if not self.retry():
                    # keep the worker alive, it idles until the next reconnect
                    self._retry_counter = 0
                    self._conn._disconnect()  # type: ignore
                time.sleep(self._sleep_duration)
                continue

            self._retry_counter = 0

            Logger.debug("ping successful")
            time.sleep(self._sleep_duration)

    def retry(self) -> bool:
        if self._retry_counter >= self._retries:
            return False

        self._retry_counter += 1
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
