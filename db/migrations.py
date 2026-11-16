"""
db/migrations.py — DDL dan seed data untuk database LombaRadar.

Berisi semua CREATE TABLE, CREATE INDEX, dan INSERT seed tags.
Dipanggil oleh db/database.py saat pertama kali init.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import aiosqlite

from config.tags import INITIAL_TAGS

logger = logging.getLogger(__name__)

# ── DDL Statements ────────────────────────────────────────────────────────────

SQL_CREATE_COMPETITIONS = """
CREATE TABLE IF NOT EXISTS competitions (
    id              TEXT PRIMARY KEY,
    title           TEXT NOT NULL,
    source          TEXT NOT NULL,
    url             TEXT NOT NULL UNIQUE,
    description     TEXT,
    deadline        TEXT,
    deadline_raw    TEXT,
    organizer       TEXT,
    prize           TEXT,
    image_url       TEXT,
    eligibility     TEXT,
    location_type   TEXT DEFAULT 'online',
    location_detail TEXT,
    status          TEXT DEFAULT 'open',
    scraped_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);
"""

SQL_CREATE_TAGS = """
CREATE TABLE IF NOT EXISTS tags (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL UNIQUE,
    slug        TEXT NOT NULL UNIQUE,
    color_hex   TEXT NOT NULL,
    emoji       TEXT
);
"""

SQL_CREATE_COMPETITION_TAGS = """
CREATE TABLE IF NOT EXISTS competition_tags (
    competition_id  TEXT NOT NULL,
    tag_id          INTEGER NOT NULL,
    PRIMARY KEY (competition_id, tag_id),
    FOREIGN KEY (competition_id) REFERENCES competitions(id),
    FOREIGN KEY (tag_id) REFERENCES tags(id)
);
"""

SQL_CREATE_SUBSCRIBERS = """
CREATE TABLE IF NOT EXISTS subscribers (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_chat_id    BIGINT NOT NULL UNIQUE,
    chat_type           TEXT NOT NULL,
    chat_title          TEXT,
    is_active           INTEGER DEFAULT 1,
    joined_at           DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_active_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);
"""

SQL_CREATE_SUBSCRIBER_TAGS = """
CREATE TABLE IF NOT EXISTS subscriber_tags (
    subscriber_id   INTEGER NOT NULL,
    tag_id          INTEGER NOT NULL,
    PRIMARY KEY (subscriber_id, tag_id),
    FOREIGN KEY (subscriber_id) REFERENCES subscribers(id),
    FOREIGN KEY (tag_id) REFERENCES tags(id)
);
"""

SQL_CREATE_SENT_LOG = """
CREATE TABLE IF NOT EXISTS sent_log (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    competition_id      TEXT NOT NULL,
    telegram_chat_id    BIGINT NOT NULL,
    message_type        TEXT NOT NULL,
    sent_at             DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(competition_id, telegram_chat_id, message_type),
    FOREIGN KEY (competition_id) REFERENCES competitions(id)
);
"""

# ── Index Statements ──────────────────────────────────────────────────────────

SQL_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_competitions_deadline ON competitions(deadline);",
    "CREATE INDEX IF NOT EXISTS idx_competitions_status ON competitions(status);",
    "CREATE INDEX IF NOT EXISTS idx_competitions_source ON competitions(source);",
    "CREATE INDEX IF NOT EXISTS idx_competitions_scraped_at ON competitions(scraped_at DESC);",
    "CREATE INDEX IF NOT EXISTS idx_sent_log_chat ON sent_log(telegram_chat_id);",
    "CREATE INDEX IF NOT EXISTS idx_sent_log_comp ON sent_log(competition_id);",
]

# ── Migration Runner ──────────────────────────────────────────────────────────


async def run_migrations(db: "aiosqlite.Connection") -> None:
    """Jalankan semua CREATE TABLE, index, dan seed data awal."""
    logger.info("Menjalankan migrasi database ...")

    # Buat tabel
    await db.execute(SQL_CREATE_COMPETITIONS)
    await db.execute(SQL_CREATE_TAGS)
    await db.execute(SQL_CREATE_COMPETITION_TAGS)
    await db.execute(SQL_CREATE_SUBSCRIBERS)
    await db.execute(SQL_CREATE_SUBSCRIBER_TAGS)
    await db.execute(SQL_CREATE_SENT_LOG)

    # Buat index
    for idx_sql in SQL_INDEXES:
        await db.execute(idx_sql)

    # Seed tags
    for tag in INITIAL_TAGS:
        await db.execute(
            """
            INSERT OR IGNORE INTO tags (name, slug, color_hex, emoji)
            VALUES (?, ?, ?, ?)
            """,
            (tag["name"], tag["slug"], tag["color_hex"], tag["emoji"]),
        )

    await db.commit()
    logger.info("Migrasi database selesai.")
