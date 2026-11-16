"""
scrapers/lomba_info.py — Scraper lomba.info menggunakan httpx + BS4.

Mengambil data lomba/kompetisi umum dari lomba.info.
"""

from __future__ import annotations

import asyncio
import logging

import httpx
from bs4 import BeautifulSoup

from .base import BaseScraper, RawCompetition

logger = logging.getLogger(__name__)


class LombaInfoScraper(BaseScraper):
    """Scraper untuk lomba.info."""

    SOURCE_NAME = "lomba_info"
    BASE_URL = "https://lomba.info"

    async def scrape(self) -> list[RawCompetition]:
        """Scrape halaman utama lomba.info."""
        results: list[RawCompetition] = []
        try:
            async with httpx.AsyncClient(
                headers=self.HEADERS, timeout=30.0, follow_redirects=True
            ) as client:
                response = await client.get(self.BASE_URL)
                response.raise_for_status()

                soup = BeautifulSoup(response.text, "lxml")

                articles = (
                    soup.select("article")
                    or soup.select(".post")
                    or soup.select(".entry")
                    or soup.select(".competition-item")
                )

                for article in articles[:15]:
                    try:
                        title_el = (
                            article.select_one("h2 a")
                            or article.select_one("h3 a")
                            or article.select_one(".entry-title a")
                            or article.select_one("a")
                        )
                        deadline_el = (
                            article.select_one(".deadline")
                            or article.select_one(".date")
                            or article.select_one("time")
                        )
                        desc_el = article.select_one(".entry-summary") or article.select_one("p")
                        img_el = article.select_one("img")

                        if not title_el:
                            continue

                        title = title_el.get_text(strip=True)
                        url = title_el.get("href", "")
                        if not url.startswith("http"):
                            url = self.BASE_URL.rstrip("/") + "/" + url.lstrip("/")
                        if not title:
                            continue

                        results.append(RawCompetition(
                            title=title,
                            url=url,
                            source=self.SOURCE_NAME,
                            description=desc_el.get_text(strip=True) if desc_el else None,
                            deadline_raw=deadline_el.get_text(strip=True) if deadline_el else None,
                            deadline=self.parse_deadline(
                                deadline_el.get_text(strip=True) if deadline_el else ""
                            ),
                            image_url=img_el.get("src") if img_el else None,
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
