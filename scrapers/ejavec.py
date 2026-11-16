"""
scrapers/ejavec.py — Scraper EJAVEC Forum (ejavec.org).

East Java Economic Forum — Call for Paper dan Conference.
"""

from __future__ import annotations

import logging

import httpx
from bs4 import BeautifulSoup

from .base import BaseScraper, RawCompetition

logger = logging.getLogger(__name__)


class EjavecScraper(BaseScraper):
    """Scraper untuk ejavec.org — EJAVEC Forum Call for Paper."""

    SOURCE_NAME = "ejavec"
    BASE_URL = "https://ejavec.org/"

    async def scrape(self) -> list[RawCompetition]:
        results: list[RawCompetition] = []
        try:
            async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
                resp = await client.get(self.BASE_URL, headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                })
                resp.raise_for_status()

            soup = BeautifulSoup(resp.text, "lxml")
            body_text = soup.get_text()

            # EJAVEC adalah single-event — ambil info utama
            title = "EJAVEC Forum Call for Paper"

            # Cari tema dari halaman
            h4_tags = soup.find_all("h4")
            for h4 in h4_tags:
                txt = h4.get_text(strip=True)
                if len(txt) > 20 and ("Mengakselerasi" in txt or "Pembangunan" in txt or "Ekonomi" in txt):
                    title = f"EJAVEC: {txt[:80]}"
                    break

            # Cari tahun dari teks
            import re
            year_match = re.search(r"EJAVEC\s+(?:Forum\s+)?(\d{4})", body_text)
            if year_match:
                title = f"EJAVEC Forum {year_match.group(1)} — Call for Paper"

            # Cek news/update untuk artikel terbaru
            news_links = soup.find_all("a", href=lambda h: h and "/berita-update/" not in h and "/20" in str(h))
            for link in news_links[:3]:
                try:
                    href = link.get("href", "")
                    link_text = link.get_text(strip=True)
                    if not link_text or len(link_text) < 10:
                        continue
                    if "recap" in link_text.lower() or "finalis" in link_text.lower():
                        continue  # Skip recap articles

                    url = href if href.startswith("http") else f"https://ejavec.org{href}"

                    results.append(RawCompetition(
                        title=link_text[:100],
                        url=url,
                        source=self.SOURCE_NAME,
                        description="EJAVEC Forum — East Java Economic Forum",
                        deadline_raw=None,
                        deadline=None,
                        organizer="Bank Indonesia KPw Jawa Timur",
                        location_raw="Jawa Timur",
                    ))
                except Exception:
                    continue

            # Tambah main competition page
            results.append(RawCompetition(
                title=title,
                url="https://ejavec.org/call-for-paper/latar-belakang/",
                source=self.SOURCE_NAME,
                description="Kompetisi karya tulis ilmiah — hadiah total Rp 220 juta",
                deadline_raw=None,
                deadline=None,
                organizer="Bank Indonesia KPw Jawa Timur",
                prize="Rp 220.000.000",
                location_raw="Jawa Timur",
            ))

        except Exception as e:
            logger.warning("[%s] Error: %s", self.SOURCE_NAME, e)

        logger.info("[%s] Berhasil scrape %d lomba", self.SOURCE_NAME, len(results))
        return results
