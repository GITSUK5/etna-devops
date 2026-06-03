import sqlite3
import threading
import time

from .database import DB_PATH

MODES = [
    "slow_response",
    "high_error_rate",
    "db_lock",
    "cpu_spike",
    "memory_pressure",
]

_state: dict = {"mode": None}
_stop_event = threading.Event()
_threads: list[threading.Thread] = []
_memory_chunks: list[bytes] = []


def get_mode() -> str | None:
    return _state["mode"]


def activate(mode: str) -> str:
    if mode not in MODES:
        raise ValueError(f"unknown mode {mode!r} — valid: {MODES}")
    _cleanup()
    _state["mode"] = mode
    _stop_event.clear()

    if mode == "cpu_spike":
        _start(_cpu_loop)
    elif mode == "memory_pressure":
        _start(_memory_loop)
    elif mode == "db_lock":
        _start(_lock_db)

    return mode


def reset() -> None:
    _cleanup()


def _cleanup() -> None:
    _state["mode"] = None
    _stop_event.set()
    _memory_chunks.clear()
    _threads.clear()


def _start(fn) -> None:
    t = threading.Thread(target=fn, daemon=True)
    t.start()
    _threads.append(t)


def _cpu_loop() -> None:
    while not _stop_event.is_set():
        _ = sum(i * i for i in range(100_000))


def _memory_loop() -> None:
    while not _stop_event.is_set():
        _memory_chunks.append(b"x" * 10 * 1024 * 1024)
        time.sleep(1)


def _lock_db() -> None:
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute("BEGIN EXCLUSIVE")
        _stop_event.wait()
    finally:
        try:
            conn.close()
        except Exception:
            pass
