import os
import sqlite3
from contextlib import contextmanager

DB_PATH = os.getenv("DB_PATH", "orders.db")


def init_db() -> None:
    with get_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS orders (
                id       INTEGER PRIMARY KEY AUTOINCREMENT,
                item     TEXT    NOT NULL,
                quantity INTEGER NOT NULL,
                status   TEXT    NOT NULL DEFAULT 'pending'
            )
            """
        )


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH, timeout=5)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
