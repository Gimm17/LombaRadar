"""
db/database.py — Koneksi SQLite dan inisialisasi database LombaRadar.

Menyediakan fungsi `init_db()` yang membuat direktori data jika perlu,
membuka koneksi aiosqlite, dan menjalankan migrasi.
Juga menyediakan `get_db()` sebagai context manager untuk koneksi baru.
"""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import aiosqlite

from config.settings import DATABASE_PATH
from db.migrations import run_migrations

logger = logging.getLogger(__name__)


async def init_db() -> None:
    """Inisialisasi database: buat folder, jalankan migrasi."""
    db_dir = os.path.dirname(DATABASE_PATH)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)

    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        await db.execute("PRAGMA journal_mode=WAL;")
        await db.execute("PRAGMA foreign_keys=ON;")
        await run_migrations(db)

    logger.info("Database diinisialisasi di %s", DATABASE_PATH)


@asynccontextmanager
async def get_db() -> AsyncGenerator[aiosqlite.Connection, None]:
    """Context manager untuk mendapatkan koneksi database."""
    db = await aiosqlite.connect(DATABASE_PATH)
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA foreign_keys=ON;")
    try:
        yield db
    finally:
        await db.close()
