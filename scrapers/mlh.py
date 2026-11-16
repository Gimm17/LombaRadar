"""
scrapers/mlh.py — Scraper MLH (Major League Hacking).

MLH events page (mlh.io/seasons/2026/events) berisi list hackathon
dengan format: [Lokasi NamaHackathon TANGGAL Lokasi, Negara Tipe].
"""

from __future__ import annotations

import logging
import re

import httpx
from bs4 import BeautifulSoup

from .base import BaseScraper, RawCompetition

logger = logging.getLogger(__name__)


class MlhScraper(BaseScraper):
    """Scraper untuk mlh.io — Major League Hacking events."""

    SOURCE_NAME = "mlh"
    BASE_URL = "https://mlh.io/seasons/2026/events"

    async def scrape(self) -> list[RawCompetition]:
        results: list[RawCompetition] = []
        try:
            async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
                resp = await client.get(self.BASE_URL, headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                })
                resp.raise_for_status()

            soup = BeautifulSoup(resp.text, "lxml")

            # MLH: <a> cards with href to external hackathon sites
            links = soup.find_all("a", href=re.compile(r"https?://(?!mlh\.io)"))
            seen: set[str] = set()

            for link in links:
                try:
                    url = link.get("href", "").split("?")[0]
                    if not url or url in seen:
                        continue

                    text = link.get_text("\n", strip=True)
                    lines = [l.strip() for l in text.split("\n") if l.strip()]
                    if len(lines) < 2:
                        continue

                    # Cari h4 sebagai nama hackathon
                    h4 = link.find("h4")
                    if not h4:
                        # Fallback: cari h4 setelah link
                        next_h4 = link.find_next("h4")
                        if next_h4:
                            title = next_h4.get_text(strip=True)
                        else:
                            continue
                    else:
                        title = h4.get_text(strip=True)

                    if not title or len(title) < 3:
                        continue

                    # Skip link navigasi/footer (bukan hackathon)
                    skip_titles = {
                        "documentation", "status", "guide", "privacy",
                        "terms of service", "contact us", "blog", "partners",
                        "work at mlh", "code of conduct", "prizes & freebies",
                        "branding guidelines", "apply", "fellowship faq",
                        "programs", "mlh logo",
                    }
                    if title.lower().strip() in skip_titles:
                        continue

                    seen.add(url)

                    # Lokasi dari teks
                    location_type = "online"
                    location_detail = ""
                    if "In-Person" in text:
                        location_type = "onsite"
                    elif "Digital" in text:
                        location_type = "online"

                    # Cari tanggal: format "MMM DD - DD" atau "MMM DD"
                    deadline_raw = None
                    date_match = re.search(
                        r"(JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)\s+\d{1,2}",
                        text, re.IGNORECASE
                    )
                    if date_match:
                        deadline_raw = date_match.group(0)

                    # Lokasi detail
                    for line in lines:
                        if any(c in line for c in [", US", ", CA", ", IN", ", MX", ", ES"]):
                            location_detail = line
                            break

                    results.append(RawCompetition(
                        title=title,
                        url=url,
                        source=self.SOURCE_NAME,
                        description=f"MLH Hackathon: {title}",
                        deadline_raw=deadline_raw,
                        deadline=self.parse_deadline(deadline_raw or ""),
                        organizer="Major League Hacking",
                        location_raw=location_detail or ("Online" if location_type == "online" else "Onsite"),
                    ))
                except Exception as e:
                    logger.warning("[%s] Skip item: %s", self.SOURCE_NAME, e)
                    continue

        except Exception as e:
            logger.warning("[%s] HTTP error: %s", self.SOURCE_NAME, e)

        logger.info("[%s] Berhasil scrape %d lomba", self.SOURCE_NAME, len(results))
        return results
