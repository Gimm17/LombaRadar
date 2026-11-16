"""
scrapers/sinta.py — Scraper SINTA Dikti journals/call for papers menggunakan httpx + BS4.

Mengambil data jurnal dan call for paper dari sinta.kemdikbud.go.id.
"""

from __future__ import annotations

import asyncio
import logging

import httpx
from bs4 import BeautifulSoup

from .base import BaseScraper, RawCompetition

logger = logging.getLogger(__name__)


class SintaScraper(BaseScraper):
    """Scraper untuk SINTA Dikti — jurnal & call for paper."""

    SOURCE_NAME = "sinta"
    BASE_URL = "https://sinta.kemdikbud.go.id/journals"

    async def scrape(self) -> list[RawCompetition]:
        """Scrape halaman journal listing SINTA."""
        results: list[RawCompetition] = []
        try:
            async with httpx.AsyncClient(
                headers=self.HEADERS, timeout=30.0, follow_redirects=True
            ) as client:
                response = await client.get(self.BASE_URL)
                response.raise_for_status()

                soup = BeautifulSoup(response.text, "lxml")

                # SINTA journal listing — selector dengan fallback
                items = (
                    soup.select("div.journal-item")
                    or soup.select("div.ar-list-item")
                    or soup.select("table tbody tr")
                    or soup.select("div.content-list div.row")
                )

                for item in items[:15]:
                    try:
                        title_el = (
                            item.select_one("a.journal-title")
                            or item.select_one("h3 a")
                            or item.select_one("a")
                        )
                        desc_el = (
                            item.select_one(".journal-desc")
                            or item.select_one("p")
                        )

                        if not title_el:
                            continue

                        title = title_el.get_text(strip=True)
                        url = title_el.get("href", "")
                        if url and not url.startswith("http"):
                            url = f"https://sinta.kemdikbud.go.id{url}"

                        if not title or not url:
                            continue

                        description = desc_el.get_text(strip=True) if desc_el else None

                        results.append(RawCompetition(
                            title=title,
                            url=url,
                            source=self.SOURCE_NAME,
                            description=description,
                            organizer="Kemdikbud",
                            # Jurnal biasanya open terus, deadline jarang ada
                            deadline_raw=None,
                            deadline=None,
                        ))

                        await asyncio.sleep(0.5)

                    except Exception as e:
                        logger.warning("[%s] Skip item: %s", self.SOURCE_NAME, e)
                        continue

        except httpx.HTTPError as e:
            logger.warning("[%s] HTTP error: %s", self.SOURCE_NAME, e)
        except Exception as e:
            logger.warning("[%s] Scraper error: %s", self.SOURCE_NAME, e)

        logger.info("[%s] Berhasil scrape %d lomba", self.SOURCE_NAME, len(results))
        return results
