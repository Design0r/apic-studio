import logging
import socket
import sys
from pathlib import Path
from typing import Callable

LoggerCallback = Callable[[str, str], None]


class Logger:
    LOGGER_NAME = "apic_studio"

    FORMAT_DEFAULT = "[%(name)s][%(levelname)s] %(message)s"

    LEVEL_DEFAULT = logging.DEBUG
    PROPAGATE_DEFAULT = True

    _logger_obj = None

    _callbacks: list[LoggerCallback] = []

    @classmethod
    def logger_obj(cls):
        if not cls._logger_obj:
            if cls.logger_exists():
                cls._logger_obj = logging.getLogger(cls.LOGGER_NAME)
            else:
                cls._logger_obj = logging.getLogger(cls.LOGGER_NAME)

                cls._logger_obj.setLevel(cls.LEVEL_DEFAULT)
                cls._logger_obj.propagate = cls.PROPAGATE_DEFAULT

                fmt = logging.Formatter(cls.FORMAT_DEFAULT)

                stream_handler = logging.StreamHandler(sys.stdout)
                stream_handler.setFormatter(fmt)
                cls._logger_obj.addHandler(stream_handler)

        return cls._logger_obj

    @classmethod
    def register_callback(cls, func: LoggerCallback) -> None:
        cls._callbacks.append(func)

    @classmethod
    def exec_callbacks(cls, level: str, msg: str) -> None:
        for c in cls._callbacks:
            c(level, f"{level}: {msg}")

    @classmethod
    def logger_exists(cls):
        return cls.LOGGER_NAME in logging.Logger.manager.loggerDict.keys()

    @classmethod
    def set_level(cls, level: str):
        lg = cls.logger_obj()
        lg.setLevel(level)

    @classmethod
    def set_propagate(cls, propagate: bool):
        lg = cls.logger_obj()
        lg.propagate = propagate

    @classmethod
    def debug(cls, msg: str):
        lg = cls.logger_obj()
        lg.debug(msg)

    @classmethod
    def info(cls, msg: str):
        lg = cls.logger_obj()
        lg.info(msg)
        cls.exec_callbacks("Info", msg)

    @classmethod
    def warning(cls, msg: str):
        lg = cls.logger_obj()
        lg.warning(msg)
        cls.exec_callbacks("Warning", msg)

    @classmethod
    def error(cls, msg: str):
        lg = cls.logger_obj()
        lg.error(msg)
        cls.exec_callbacks("Error", msg)

    @classmethod
    def critical(cls, msg: str):
        lg = cls.logger_obj()
        lg.critical(msg)
        cls.exec_callbacks("Critical Error", msg)

    @classmethod
    def log(cls, level, msg: str, *args, **kwargs):
        lg = cls.logger_obj()
        lg.log(level, msg, *args, **kwargs)

    @classmethod
    def exception(cls, msg: Exception):
        lg = cls.logger_obj()
        lg.exception(msg)
        cls.exec_callbacks("Exception", str(msg))

    @classmethod
    def write_to_file(cls, path: Path, level: int = logging.INFO):
        if not path.parent.exists():
            path.parent.mkdir(parents=True, exist_ok=True)

        lg = cls.logger_obj()

        for handler in lg.handlers:
            if (
                isinstance(handler, logging.FileHandler)
                and handler.baseFilename == path
            ):
                return

        file_handler = logging.FileHandler(path)
        file_handler.setLevel(level)

        hostname = socket.gethostname()

        fmt = logging.Formatter(
            fmt=f"[%(asctime)s][{hostname}][%(levelname)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M",
        )
        file_handler.setFormatter(fmt)
        lg.addHandler(file_handler)
