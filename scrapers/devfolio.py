"""
scrapers/devfolio.py — Scraper Devfolio (devfolio.co/hackathons).

Devfolio menggunakan Next.js SSR — konten hackathon ada di HTML awal.
Data terstruktur: nama, tema, status (Open/Ended), lokasi, tanggal mulai.
"""

from __future__ import annotations

import logging
import re

import httpx
from bs4 import BeautifulSoup

from .base import BaseScraper, RawCompetition

logger = logging.getLogger(__name__)


class DevfolioScraper(BaseScraper):
    """Scraper untuk devfolio.co — hackathon global."""

    SOURCE_NAME = "devfolio"
    BASE_URL = "https://devfolio.co/hackathons/open"

    async def scrape(self) -> list[RawCompetition]:
        results: list[RawCompetition] = []
        try:
            async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
                resp = await client.get(self.BASE_URL, headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                })
                resp.raise_for_status()

            soup = BeautifulSoup(resp.text, "lxml")

            # Devfolio listing: <a> cards linking to *.devfolio.co
            links = soup.find_all("a", href=re.compile(r"https://[\w-]+\.devfolio\.co"))
            seen: set[str] = set()

            for link in links:
                try:
                    url = link.get("href", "").split("?")[0]
                    if not url or url in seen:
                        continue
                    seen.add(url)

                    text = link.get_text("\n", strip=True)
                    lines = [l.strip() for l in text.split("\n") if l.strip()]
                    if not lines:
                        continue

                    # Skip jika status "Ended"
                    if "Ended" in text:
                        continue

                    # Judul = h3 dalam card, atau baris pertama
                    h3 = link.find("h3")
                    title = h3.get_text(strip=True) if h3 else lines[0]

                    # Lokasi
                    location_type = "online" if "Online" in text else "onsite"

                    # Deadline dari "Starts DD/MM/YY"
                    deadline_raw = None
                    for line in lines:
                        match = re.search(r"Starts\s+(\d{2}/\d{2}/\d{2})", line)
                        if match:
                            deadline_raw = match.group(1)
                            break

                    results.append(RawCompetition(
                        title=title,
                        url=url,
                        source=self.SOURCE_NAME,
                        description=" ".join(lines),
                        deadline_raw=deadline_raw,
                        deadline=self.parse_deadline(deadline_raw or ""),
                        organizer="Devfolio",
                        location_raw="Online" if location_type == "online" else "Onsite",
                    ))
                except Exception as e:
                    logger.warning("[%s] Skip item: %s", self.SOURCE_NAME, e)
                    continue

        except Exception as e:
            logger.warning("[%s] HTTP error: %s", self.SOURCE_NAME, e)

        logger.info("[%s] Berhasil scrape %d lomba", self.SOURCE_NAME, len(results))
        return results
