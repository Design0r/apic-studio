import shutil
import subprocess
import sys
from pathlib import Path
from typing import Union

from shared.logger import Logger


def create_dir(path: Union[str, Path]) -> None:
    if not path:
        Logger.error(f"can't create directory, path: {path} is invalid")
        return

    if isinstance(path, str):
        path = Path(path)

    if path.exists():
        Logger.error(f"can't create directory, path: {path} already exists")
        return

    try:
        path.mkdir(parents=True)
    except Exception as e:
        Logger.exception(e)

    return


def remove_dir(path: Union[str, Path]) -> None:
    if not path:
        Logger.error(f"can't delete directory, path: {path} is invalid")
        return

    if isinstance(path, str):
        path = Path(path)

    if not path.exists():
        Logger.error(f"can't delete directory, path: {path} does not exist")
        return

    try:
        shutil.rmtree(path)
    except Exception as e:
        Logger.exception(e)

    return


def open_dir(path: Union[str, Path]) -> None:
    if not path:
        Logger.error(f"can't open path, {path} does not exist")

    if isinstance(path, str):
        path = Path(path)

    if not path.exists():
        Logger.error(f"can't open path, {path} does not exist")
        return

    if sys.platform == "darwin":
        subprocess.run(["open", path])
    elif sys.platform == "win32":
        subprocess.run(["explorer", path])
    else:
        Logger.error(f"unsupported os {sys.platform}")
