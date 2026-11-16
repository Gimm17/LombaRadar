"""
core/competition_manager.py — Orchestrator: scrape → tag → dedup → save → notify.

Mengkoordinasikan seluruh pipeline dari scraping sampai penyimpanan ke database.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Optional

import aiosqlite

from scrapers import ALL_SCRAPERS
from scrapers.base import RawCompetition
from core.tagger import auto_tag
from core.location_detector import detect_location
from core.deduplicator import generate_id, is_competition_exists
from db.database import get_db

logger = logging.getLogger(__name__)


async def run_all_scrapers() -> list[RawCompetition]:
    """Jalankan semua scraper secara sequential dan gabungkan hasilnya."""
    from scrapers.base import BaseScraper

    all_results: list[RawCompetition] = []
    for ScraperClass in ALL_SCRAPERS:
        scraper = ScraperClass()
        logger.info("Menjalankan scraper: %s", scraper.SOURCE_NAME)
        try:
            results = await scraper.scrape()
            # Filter: buang SMP/SMA, tahun lalu, expired
            results = BaseScraper.filter_results(results)
            all_results.extend(results)
            logger.info("[%s] Ditemukan %d lomba (setelah filter)", scraper.SOURCE_NAME, len(results))
        except Exception as e:
            logger.warning("[%s] Gagal scrape: %s", scraper.SOURCE_NAME, e)
        await asyncio.sleep(3)  # jeda antar scraper
    return all_results


async def process_and_save(raw_competitions: list[RawCompetition]) -> list[str]:
    """
    Proses lomba mentah: tag, detect location, dedup, dan simpan ke DB.

    Returns:
        List competition_id yang baru disimpan (untuk notifikasi).
    """
    new_ids: list[str] = []

    async with get_db() as db:
        for raw in raw_competitions:
            try:
                comp_id = generate_id(raw.url)

                # Skip jika sudah ada
                if await is_competition_exists(db, comp_id):
                    continue

                # Auto-tagging
                tag_slugs = auto_tag(raw.title, raw.description)

                # Detect location
                location_text = raw.location_raw or raw.description or ""
                location_type, location_detail = detect_location(location_text)

                # Insert ke competitions
                await db.execute(
                    """
                    INSERT INTO competitions
                        (id, title, source, url, description, deadline, deadline_raw,
                         organizer, prize, image_url, eligibility,
                         location_type, location_detail, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'open')
                    """,
                    (
                        comp_id, raw.title, raw.source, raw.url,
                        raw.description, raw.deadline, raw.deadline_raw,
                        raw.organizer, raw.prize, raw.image_url,
                        raw.eligibility, location_type, location_detail,
                    ),
                )

                # Insert competition_tags
                for slug in tag_slugs:
                    await db.execute(
                        """
                        INSERT OR IGNORE INTO competition_tags (competition_id, tag_id)
                        SELECT ?, id FROM tags WHERE slug = ?
                        """,
                        (comp_id, slug),
                    )

                new_ids.append(comp_id)
                logger.info("Lomba baru disimpan: %s — %s", comp_id, raw.title)

            except Exception as e:
                logger.warning("Gagal proses lomba '%s': %s", raw.title, e)
                continue

        await db.commit()

    logger.info("Total lomba baru disimpan: %d", len(new_ids))
    return new_ids


async def update_competition_statuses() -> None:
    """Update status lomba berdasarkan deadline (open → closing_soon → closed)."""
    async with get_db() as db:
        await db.execute(
            """
            UPDATE competitions
            SET status = CASE
                WHEN deadline IS NULL THEN 'open'
                WHEN deadline < date('now') THEN 'closed'
                WHEN deadline <= date('now', '+7 days') THEN 'closing_soon'
                ELSE 'open'
            END,
            updated_at = CURRENT_TIMESTAMP
            """
        )
        await db.commit()
    logger.info("Status lomba diperbarui berdasarkan deadline.")


async def get_competitions_by_tag(
    tag_slug: str, limit: int = 10
) -> list[dict]:
    """Ambil lomba berdasarkan tag slug."""
    async with get_db() as db:
        cursor = await db.execute(
            """
            SELECT DISTINCT c.*, t.name AS tag_name, t.emoji AS tag_emoji
            FROM competitions c
            JOIN competition_tags ct ON c.id = ct.competition_id
            JOIN tags t ON ct.tag_id = t.id
            WHERE t.slug = ?
            AND c.status IN ('open', 'closing_soon')
            ORDER BY c.deadline ASC NULLS LAST
            LIMIT ?
            """,
            (tag_slug, limit),
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def get_latest_competitions(limit: int = 5) -> list[dict]:
    """Ambil lomba terbaru."""
    async with get_db() as db:
        cursor = await db.execute(
            """
            SELECT c.*
            FROM competitions c
            WHERE c.status IN ('open', 'closing_soon')
            ORDER BY c.scraped_at DESC
            LIMIT ?
            """,
            (limit,),
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def get_deadline_competitions(days: int = 7) -> list[dict]:
    """Ambil lomba dengan deadline dalam N hari ke depan."""
    async with get_db() as db:
        cursor = await db.execute(
            """
            SELECT c.*
            FROM competitions c
            WHERE c.deadline IS NOT NULL
            AND c.deadline BETWEEN date('now') AND date('now', ? || ' days')
            AND c.status IN ('open', 'closing_soon')
            ORDER BY c.deadline ASC
            """,
            (str(days),),
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def get_competition_tags(competition_id: str) -> list[dict]:
    """Ambil tags untuk satu competition."""
    async with get_db() as db:
        cursor = await db.execute(
            """
            SELECT t.* FROM tags t
            JOIN competition_tags ct ON t.id = ct.tag_id
            WHERE ct.competition_id = ?
            """,
            (competition_id,),
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def get_competition_count() -> int:
    """Hitung total lomba di database."""
    async with get_db() as db:
        cursor = await db.execute("SELECT COUNT(*) as cnt FROM competitions")
        row = await cursor.fetchone()
        return row["cnt"] if row else 0
