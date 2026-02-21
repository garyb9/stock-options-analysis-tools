"""Shared helpers: timer, date parsing."""

import os
from datetime import datetime

import psutil
from dateutil.parser import parse as dateutil_parse


def start_timer() -> datetime:
    """Return current time for elapsed measurement."""
    return datetime.now()


def get_timer(start: datetime) -> str:
    """Return elapsed time since start as string."""
    return str(datetime.now() - start)


def print_time(start: datetime) -> None:
    """Print runtime in seconds."""
    print("Runtime in seconds => " + str(datetime.now() - start))


def print_mem() -> None:
    """Print process memory usage in MB."""
    process = psutil.Process(os.getpid())
    print("MB used => " + str(process.memory_info().rss / 10**6))


def print_run_data(start: datetime) -> None:
    """Print memory and runtime."""
    print_mem()
    print_time(start)


def is_date(string: str, fuzzy: bool = False) -> bool:
    """Return whether the string can be interpreted as a date."""
    try:
        dateutil_parse(string, fuzzy=fuzzy)
        return True
    except (ValueError, TypeError):
        return False
