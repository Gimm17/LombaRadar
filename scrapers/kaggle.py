"""
scrapers/kaggle.py — Scraper Kaggle competitions menggunakan httpx + BS4.

Mengambil data kompetisi dari kaggle.com/competitions.
"""

from __future__ import annotations

import asyncio
import logging

import httpx
from bs4 import BeautifulSoup

from .base import BaseScraper, RawCompetition

logger = logging.getLogger(__name__)


class KaggleScraper(BaseScraper):
    """Scraper untuk Kaggle competitions."""

    SOURCE_NAME = "kaggle"
    BASE_URL = "https://www.kaggle.com/competitions"

    async def scrape(self) -> list[RawCompetition]:
        """Scrape halaman listing kompetisi Kaggle."""
        results: list[RawCompetition] = []
        try:
            async with httpx.AsyncClient(
                headers=self.HEADERS, timeout=30.0, follow_redirects=True
            ) as client:
                response = await client.get(self.BASE_URL)
                response.raise_for_status()

                soup = BeautifulSoup(response.text, "lxml")

                # Selector dengan fallback — Kaggle sering pakai JS rendering,
                # jadi static scraping mungkin terbatas
                items = (
                    soup.select("div.competition-item")
                    or soup.select("li.MuiListItem-root")
                    or soup.select("div[data-testid='competition-card']")
                    or soup.select("a.sc-jIZahH")  # fallback generic
                )

                for item in items[:15]:
                    try:
                        title_el = (
                            item.select_one("h4")
                            or item.select_one("h3")
                            or item.select_one(".competition-title")
                            or item.select_one("a")
                        )
                        deadline_el = (
                            item.select_one(".deadline")
                            or item.select_one("time")
                            or item.select_one("span.competition-deadline")
                        )
                        prize_el = (
                            item.select_one(".prize")
                            or item.select_one(".reward")
                        )

                        if not title_el:
                            continue

                        title = title_el.get_text(strip=True)
                        # Ambil URL
                        link_el = item.select_one("a[href]") or title_el
                        url = link_el.get("href", "")
                        if url and not url.startswith("http"):
                            url = f"https://www.kaggle.com{url}"

                        if not title or not url:
                            continue

                        deadline_raw = deadline_el.get_text(strip=True) if deadline_el else None
                        prize = prize_el.get_text(strip=True) if prize_el else None

                        results.append(RawCompetition(
                            title=title,
                            url=url,
                            source=self.SOURCE_NAME,
                            deadline_raw=deadline_raw,
                            deadline=self.parse_deadline(deadline_raw or ""),
                            prize=prize,
                            organizer="Kaggle",
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
