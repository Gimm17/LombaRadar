"""
scrapers/sumatranomics.py — Scraper Sumatranomics.

Sumber: Call for Paper, Call for Opinion, Today's Challenge
dari Bank Indonesia KPw Sumatera Utara.
"""

from __future__ import annotations

import logging

import httpx
from bs4 import BeautifulSoup

from .base import BaseScraper, RawCompetition

logger = logging.getLogger(__name__)


class SumatranomicsScraper(BaseScraper):
    """Scraper untuk sumatranomics.com — kompetisi ekonomi BI Sumut."""

    SOURCE_NAME = "sumatranomics"
    BASE_URL = "https://sumatranomics.com/"

    # Halaman-halaman kompetisi yang diketahui
    COMPETITION_PAGES = [
        {
            "url": "https://sumatranomics.com/call-for-paper/latar-belakang/",
            "title_prefix": "Sumatranomics Call for Paper",
            "tag": "paper",
        },
        {
            "url": "https://sumatranomics.com/call-for-opinion/latar-belakang/",
            "title_prefix": "Sumatranomics Call for Opinion",
            "tag": "paper",
        },
        {
            "url": "https://sumatranomics.com/todays-challenge/latar-belakang/",
            "title_prefix": "Sumatranomics Today's Challenge",
            "tag": "umum",
        },
    ]

    async def scrape(self) -> list[RawCompetition]:
        results: list[RawCompetition] = []
        try:
            async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
                for page_info in self.COMPETITION_PAGES:
                    try:
                        resp = await client.get(page_info["url"], headers={
                            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                        })
                        resp.raise_for_status()

                        soup = BeautifulSoup(resp.text, "lxml")

                        # Cari judul halaman
                        h1 = soup.find("h1")
                        h2 = soup.find("h2")
                        title = page_info["title_prefix"]
                        if h1:
                            sub = h1.get_text(strip=True)
                            if sub and len(sub) > 5:
                                title = f"{page_info['title_prefix']}: {sub}"
                        elif h2:
                            sub = h2.get_text(strip=True)
                            if sub and len(sub) > 5:
                                title = f"{page_info['title_prefix']}: {sub}"

                        # Cari deadline dari halaman timeline
                        timeline_url = page_info["url"].replace("latar-belakang/", "timeline/")
                        deadline_raw = None
                        try:
                            t_resp = await client.get(timeline_url, headers={
                                "User-Agent": "Mozilla/5.0"
                            })
                            if t_resp.status_code == 200:
                                t_soup = BeautifulSoup(t_resp.text, "lxml")
                                body_text = t_soup.get_text()
                                deadline_raw = self._find_deadline_in_text(body_text)
                        except Exception:
                            pass

                        results.append(RawCompetition(
                            title=title,
                            url=page_info["url"],
                            source=self.SOURCE_NAME,
                            description=f"Kompetisi dari Sumatranomics - Bank Indonesia",
                            deadline_raw=deadline_raw,
                            deadline=self.parse_deadline(deadline_raw or ""),
                            organizer="Bank Indonesia KPw Sumut",
                            location_raw="Sumatera Utara",
                        ))
                    except Exception as e:
                        logger.warning("[%s] Skip %s: %s", self.SOURCE_NAME, page_info["url"], e)
                        continue

        except Exception as e:
            logger.warning("[%s] Error: %s", self.SOURCE_NAME, e)

        logger.info("[%s] Berhasil scrape %d lomba", self.SOURCE_NAME, len(results))
        return results

    def _find_deadline_in_text(self, text: str) -> str | None:
        """Cari pola tanggal deadline di teks."""
        import re
        patterns = [
            r"deadline[:\s]+([^\n,]{5,40})",
            r"batas\s+(?:waktu|akhir)[:\s]+([^\n,]{5,40})",
            r"(\d{1,2}\s+(?:Januari|Februari|Maret|April|Mei|Juni|Juli|Agustus|September|Oktober|November|Desember)\s+\d{4})",
        ]
        lower = text.lower()
        for pattern in patterns:
            match = re.search(pattern, lower if "deadline" in pattern.lower() else text)
            if match:
                return match.group(1).strip()
        return None
