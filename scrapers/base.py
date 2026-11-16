"""
scrapers/base.py — Abstract base class untuk semua scraper LombaRadar.

Menyediakan RawCompetition dataclass dan BaseScraper ABC
yang harus di-extend oleh setiap scraper per sumber.
"""

from __future__ import annotations

import logging
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)

# Mapping nama bulan (Indonesia & Inggris) ke angka
MONTH_MAP_ID: dict[str, int] = {
    "januari": 1, "februari": 2, "maret": 3, "april": 4,
    "mei": 5, "juni": 6, "juli": 7, "agustus": 8,
    "september": 9, "oktober": 10, "november": 11, "desember": 12,
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
    "january": 1, "february": 2, "march": 3, "april": 4,
    "june": 6, "july": 7, "august": 8,
    "october": 10, "december": 12,
}


@dataclass
class RawCompetition:
    """Data mentah lomba dari scraper, sebelum proses tagging & dedup."""

    title: str
    url: str
    source: str
    description: Optional[str] = None
    deadline_raw: Optional[str] = None     # teks asli deadline dari sumber
    deadline: Optional[str] = None         # format: YYYY-MM-DD setelah parse
    organizer: Optional[str] = None
    prize: Optional[str] = None
    image_url: Optional[str] = None
    eligibility: Optional[str] = None
    location_raw: Optional[str] = None     # teks mentah lokasi dari halaman


class BaseScraper(ABC):
    """Abstract base class yang harus di-extend oleh setiap scraper."""

    SOURCE_NAME: str = ""
    BASE_URL: str = ""

    HEADERS: dict[str, str] = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
    }

    @abstractmethod
    async def scrape(self) -> list[RawCompetition]:
        """Scrape sumber dan return list RawCompetition."""
        pass

    def parse_deadline(self, raw: str) -> Optional[str]:
        """
        Parse berbagai format tanggal ke YYYY-MM-DD.

        Tangani format:
        - ISO: '2026-06-15'
        - DD/MM/YYYY atau DD-MM-YYYY: '15/06/2026'
        - Indonesia: '15 Juni 2026', '15 Jun 2026'
        - English: 'June 15, 2026', 'Jun 15 2026'

        Returns:
            String YYYY-MM-DD atau None jika gagal parse.
        """
        if not raw:
            return None

        raw = raw.strip().lower()

        try:
            # Format ISO: YYYY-MM-DD
            if re.match(r"^\d{4}-\d{2}-\d{2}$", raw):
                return raw

            # Format DD/MM/YYYY atau DD-MM-YYYY
            m = re.match(r"^(\d{1,2})[/\-](\d{1,2})[/\-](\d{4})$", raw)
            if m:
                d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
                return f"{y:04d}-{mo:02d}-{d:02d}"

            # Format "15 Juni 2026" atau "15 Jun 2026"
            m = re.search(r"(\d{1,2})\s+([a-z]+)\s+(\d{4})", raw)
            if m:
                d, month_str, y = int(m.group(1)), m.group(2), int(m.group(3))
                mo = MONTH_MAP_ID.get(month_str)
                if mo:
                    return f"{y:04d}-{mo:02d}-{d:02d}"

            # Format "June 15, 2026" atau "Jun 15 2026"
            m = re.search(r"([a-z]+)\s+(\d{1,2}),?\s+(\d{4})", raw)
            if m:
                month_str, d, y = m.group(1), int(m.group(2)), int(m.group(3))
                mo = MONTH_MAP_ID.get(month_str)
                if mo:
                    return f"{y:04d}-{mo:02d}-{d:02d}"

        except Exception as e:
            logger.warning("[%s] Gagal parse deadline '%s': %s", self.SOURCE_NAME, raw, e)

        return None

    # ── Post-scrape filtering ─────────────────────────────────────────────────

    @staticmethod
    def filter_results(comps: list[RawCompetition]) -> list[RawCompetition]:
        """
        Filter universal — buang lomba yang tidak relevan:
        1. Lomba khusus SMP/SMA (bukan mahasiswa+)
        2. Lomba tahun lalu (2024 dan sebelumnya)
        3. Lomba yang deadline-nya sudah lewat
        """
        from datetime import date

        current_year = date.today().year
        today_str = date.today().isoformat()  # "2026-04-29"
        filtered: list[RawCompetition] = []

        for comp in comps:
            text = f"{comp.title} {comp.description or ''} {comp.eligibility or ''}".lower()

            # 1. Skip lomba KHUSUS SMP/SMA (bukan untuk mahasiswa)
            if _is_smp_sma_only(text):
                logger.debug("Filtered [SMP/SMA]: %s", comp.title)
                continue

            # 2. Skip lomba tahun lalu
            if _is_past_year(text, comp.deadline, current_year):
                logger.debug("Filtered [Past Year]: %s", comp.title)
                continue

            # 3. Skip jika deadline sudah lewat
            if comp.deadline and comp.deadline < today_str:
                logger.debug("Filtered [Expired]: %s (deadline %s)", comp.title, comp.deadline)
                continue

            filtered.append(comp)

        dropped = len(comps) - len(filtered)
        if dropped > 0:
            logger.info("Filter: %d dari %d lomba dibuang (SMP/SMA, expired, past year)", dropped, len(comps))

        return filtered


# ── Helper functions untuk filtering ──────────────────────────────────────────

# Kata kunci yang menandakan lomba KHUSUS untuk SMP/SMA saja
_SMA_ONLY_KEYWORDS = [
    "tingkat smp", "tingkat sma", "tingkat mts", "tingkat ma ",
    "smp sederajat", "sma sederajat", "mts sederajat",
    "siswa smp", "siswa sma", "siswa mts",
    "pelajar smp", "pelajar sma", "pelajar mts",
    "untuk smp", "untuk sma", "untuk mts",
    "khusus smp", "khusus sma",
    "se-smp", "se-sma",
    "jenjang smp", "jenjang sma",
    "high school", "middle school",
    "anak smp", "anak sma",
]

# Kata kunci yang menandakan lomba juga terbuka untuk mahasiswa/umum
_COLLEGE_KEYWORDS = [
    "mahasiswa", "universitas", "perguruan tinggi", "kampus",
    "undergraduate", "college", "university",
    "s1", "s2", "s3", "diploma", "sarjana", "magister", "doktor",
    "umum", "fresh graduate", "profesional", "professional",
    "nasional", "internasional", "hackathon", "datathon",
]


def _is_smp_sma_only(text: str) -> bool:
    """
    Return True jika lomba HANYA untuk SMP/SMA (tidak termasuk mahasiswa).
    
    Jika ada keyword SMA/SMP DAN juga ada keyword mahasiswa/umum,
    maka TIDAK dianggap SMP/SMA only.
    """
    has_sma = any(kw in text for kw in _SMA_ONLY_KEYWORDS)
    if not has_sma:
        return False

    # Cek apakah juga untuk mahasiswa/umum
    has_college = any(kw in text for kw in _COLLEGE_KEYWORDS)
    return not has_college


def _is_past_year(text: str, deadline: Optional[str], current_year: int) -> bool:
    """Return True jika lomba dari tahun lalu (bukan tahun ini atau masa depan)."""
    # Cek dari deadline
    if deadline:
        try:
            year = int(deadline[:4])
            if year < current_year:
                return True
        except (ValueError, IndexError):
            pass

    # Cek tahun lama di judul: "2023", "2024" dll
    past_years = [str(y) for y in range(2018, current_year)]
    for year_str in past_years:
        if year_str in text:
            # Pastikan bukan bagian dari kata lain (misal "2024" di URL)
            # Cek apakah ada tahun current/future juga di teks
            future_years = [str(y) for y in range(current_year, current_year + 3)]
            if any(fy in text for fy in future_years):
                return False  # Ada tahun baru juga, mungkin referensi
            return True

    return False

