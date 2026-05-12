import sqlite3
from contextlib import contextmanager
from typing import Iterator

from app.core.config import DB_PATH, ensure_storage_dirs


def get_connection() -> sqlite3.Connection:
    ensure_storage_dirs()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def db_session() -> Iterator[sqlite3.Connection]:
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    with db_session() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY,
                original_filenames TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                amount_total REAL NOT NULL DEFAULT 0,
                tax_total REAL NOT NULL DEFAULT 0,
                error_message TEXT
            );

            CREATE TABLE IF NOT EXISTS image_files (
                id TEXT PRIMARY KEY,
                job_id TEXT NOT NULL,
                original_name TEXT NOT NULL,
                stored_path TEXT NOT NULL,
                width INTEGER NOT NULL DEFAULT 0,
                height INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS groups (
                id TEXT PRIMARY KEY,
                job_id TEXT NOT NULL,
                group_index INTEGER NOT NULL,
                display_name TEXT NOT NULL,
                color_hex TEXT NOT NULL,
                amount_total REAL NOT NULL DEFAULT 0,
                tax_total REAL NOT NULL DEFAULT 0,
                formula_amount TEXT NOT NULL DEFAULT '',
                formula_tax TEXT NOT NULL DEFAULT '',
                FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS items (
                id TEXT PRIMARY KEY,
                job_id TEXT NOT NULL,
                group_id TEXT NOT NULL,
                image_file_id TEXT,
                raw_text TEXT NOT NULL DEFAULT '',
                amount REAL NOT NULL DEFAULT 0,
                tax REAL NOT NULL DEFAULT 0,
                bbox_x INTEGER,
                bbox_y INTEGER,
                bbox_w INTEGER,
                bbox_h INTEGER,
                ocr_confidence REAL,
                is_manual INTEGER NOT NULL DEFAULT 0,
                is_corrected INTEGER NOT NULL DEFAULT 0,
                sort_order INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE,
                FOREIGN KEY (group_id) REFERENCES groups(id) ON DELETE CASCADE,
                FOREIGN KEY (image_file_id) REFERENCES image_files(id) ON DELETE SET NULL
            );

            CREATE TABLE IF NOT EXISTS exports (
                id TEXT PRIMARY KEY,
                job_id TEXT NOT NULL,
                filename TEXT NOT NULL,
                stored_path TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE
            );
            """
        )
