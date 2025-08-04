import cProfile
import pstats
import time
from functools import wraps
from typing import Any, Callable

from .settings import SettingsManager

s = SettingsManager()


def benchmark(func: Callable[..., Any]) -> Callable[..., Any]:
    @wraps
    def wrapper(*args, **kwagrs) -> Any:
        start_time = time.perf_counter()
        res = func(*args, **kwargs)
        end_time = time.perf_counter()
        print(f"{func.__name__} finished in {end_time - start_time:.3f}s")
        return res

    return wrapper


def profile(
    *functions: Callable[[], Any],
    filename: str = str(s.ROOT_PATH.parent / "apic_studio.prof"),
):
    with cProfile.Profile() as pr:
        for func in functions:
            func()

    stats = pstats.Stats(pr)
    stats.sort_stats(pstats.SortKey.TIME)
    stats.print_stats()
    stats.dump_stats(filename=filename)
