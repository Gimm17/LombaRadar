# SCRAPER_GUIDE.md — Panduan Implementasi Scraper LombaRadar

## Prinsip Dasar

1. **Satu file per sumber** — setiap scraper berdiri sendiri di `scrapers/`
2. **Semua scraper async** — gunakan `async def scrape()` dan `await`
3. **Graceful failure** — jika scraper gagal, log WARNING dan return `[]` (list kosong), jangan raise exception ke atas
4. **User-Agent realistis** — selalu set header `User-Agent` ke browser string yang valid
5. **Rate limiting** — tambah `await asyncio.sleep(2)` antara setiap request ke domain yang sama
6. **Playwright hanya jika perlu** — gunakan httpx+BS4 dulu, Playwright hanya untuk site yang butuh JS rendering

---

## Abstract Base Class

```python
# scrapers/base.py

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional
from datetime import date
import re
import logging

logger = logging.getLogger(__name__)

MONTH_MAP_ID = {
    'januari': 1, 'februari': 2, 'maret': 3, 'april': 4,
    'mei': 5, 'juni': 6, 'juli': 7, 'agustus': 8,
    'september': 9, 'oktober': 10, 'november': 11, 'desember': 12,
    'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
    'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12,
}

@dataclass
class RawCompetition:
    title: str
    url: str
    source: str
    description: Optional[str] = None
    deadline_raw: Optional[str] = None
    deadline: Optional[str] = None        # YYYY-MM-DD
    organizer: Optional[str] = None
    prize: Optional[str] = None
    image_url: Optional[str] = None
    eligibility: Optional[str] = None
    location_raw: Optional[str] = None    # teks mentah lokasi dari halaman

class BaseScraper(ABC):
    SOURCE_NAME: str = ""
    BASE_URL: str = ""

    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
    }

    @abstractmethod
    async def scrape(self) -> list[RawCompetition]:
        pass

    def parse_deadline(self, raw: str) -> Optional[str]:
        """
        Parse berbagai format tanggal ke YYYY-MM-DD.
        Tangani: 'YYYY-MM-DD', '15 Juni 2026', '15 Jun 2026',
                 'June 15, 2026', 'Jun 15 2026', '15/06/2026'
        Return None jika tidak bisa di-parse.
        """
        if not raw:
            return None
        raw = raw.strip().lower()
        try:
            # Format ISO
            if re.match(r'^\d{4}-\d{2}-\d{2}$', raw):
                return raw

            # Format DD/MM/YYYY atau DD-MM-YYYY
            m = re.match(r'^(\d{1,2})[/\-](\d{1,2})[/\-](\d{4})$', raw)
            if m:
                d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
                return f"{y:04d}-{mo:02d}-{d:02d}"

            # Format "15 Juni 2026" atau "15 Jun 2026"
            m = re.search(r'(\d{1,2})\s+([a-z]+)\s+(\d{4})', raw)
            if m:
                d, month_str, y = int(m.group(1)), m.group(2), int(m.group(3))
                mo = MONTH_MAP_ID.get(month_str)
                if mo:
                    return f"{y:04d}-{mo:02d}-{d:02d}"

            # Format "June 15, 2026"
            m = re.search(r'([a-z]+)\s+(\d{1,2}),?\s+(\d{4})', raw)
            if m:
                month_str, d, y = m.group(1), int(m.group(2)), int(m.group(3))
                mo = MONTH_MAP_ID.get(month_str)
                if mo:
                    return f"{y:04d}-{mo:02d}-{d:02d}"

        except Exception as e:
            logger.warning(f"[{self.SOURCE_NAME}] Gagal parse deadline '{raw}': {e}")
        return None
```

---

## Pola Playwright Scraper

Gunakan pola ini untuk scraper yang butuh JS rendering (Devpost, Dicoding):

```python
# scrapers/devpost.py (contoh pola)

import asyncio
import logging
from playwright.async_api import async_playwright, TimeoutError as PWTimeout
from .base import BaseScraper, RawCompetition
from config.settings import PLAYWRIGHT_HEADLESS, PLAYWRIGHT_TIMEOUT

logger = logging.getLogger(__name__)

class DevpostScraper(BaseScraper):
    SOURCE_NAME = "devpost"
    BASE_URL = "https://devpost.com/hackathons"

    async def scrape(self) -> list[RawCompetition]:
        results = []
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=PLAYWRIGHT_HEADLESS)
                page = await browser.new_page()
                await page.set_extra_http_headers(self.HEADERS)

                try:
                    await page.goto(self.BASE_URL, timeout=PLAYWRIGHT_TIMEOUT)
                    await page.wait_for_load_state("networkidle", timeout=PLAYWRIGHT_TIMEOUT)

                    # Ambil semua card lomba
                    cards = await page.query_selector_all("article.hackathon-tile, div.challenge-listing")

                    for card in cards[:20]:  # max 20 per scrape
                        try:
                            title_el = await card.query_selector("h2, .challenge-title, .title")
                            link_el = await card.query_selector("a[href]")
                            deadline_el = await card.query_selector(".submission-period, .deadline, time")
                            prize_el = await card.query_selector(".prize-amount, .prize")

                            title = await title_el.inner_text() if title_el else None
                            url = await link_el.get_attribute("href") if link_el else None
                            deadline_raw = await deadline_el.inner_text() if deadline_el else None
                            prize = await prize_el.inner_text() if prize_el else None

                            if not title or not url:
                                continue

                            # Normalisasi URL
                            if url.startswith('/'):
                                url = f"https://devpost.com{url}"

                            results.append(RawCompetition(
                                title=title.strip(),
                                url=url.strip(),
                                source=self.SOURCE_NAME,
                                deadline_raw=deadline_raw,
                                deadline=self.parse_deadline(deadline_raw or ""),
                                prize=prize.strip() if prize else None,
                                organizer="Devpost",
                            ))
                        except Exception as e:
                            logger.warning(f"[{self.SOURCE_NAME}] Skip card: {e}")
                            continue

                except PWTimeout:
                    logger.warning(f"[{self.SOURCE_NAME}] Timeout saat load halaman")
                finally:
                    await browser.close()

        except Exception as e:
            logger.warning(f"[{self.SOURCE_NAME}] Scraper error: {e}")

        logger.info(f"[{self.SOURCE_NAME}] Berhasil scrape {len(results)} lomba")
        return results
```

---

## Pola httpx + BS4 Scraper

Gunakan untuk situs statis (Kaggle, SINTA, lomba.info, info-lomba.com):

```python
# scrapers/lomba_info.py (contoh pola)

import httpx
import asyncio
import logging
from bs4 import BeautifulSoup
from .base import BaseScraper, RawCompetition

logger = logging.getLogger(__name__)

class LombaInfoScraper(BaseScraper):
    SOURCE_NAME = "lomba_info"
    BASE_URL = "https://lomba.info"

    async def scrape(self) -> list[RawCompetition]:
        results = []
        try:
            async with httpx.AsyncClient(headers=self.HEADERS, timeout=30.0, follow_redirects=True) as client:
                response = await client.get(self.BASE_URL)
                response.raise_for_status()

                soup = BeautifulSoup(response.text, 'lxml')

                # Sesuaikan selector dengan struktur HTML aktual saat implementasi
                articles = soup.select("article, .post, .entry, .competition-item")

                for article in articles[:15]:
                    try:
                        title_el = article.select_one("h2 a, h3 a, .entry-title a, .title a")
                        deadline_el = article.select_one(".deadline, .date, time, .closing-date")

                        if not title_el:
                            continue

                        title = title_el.get_text(strip=True)
                        url = title_el.get('href', '')
                        deadline_raw = deadline_el.get_text(strip=True) if deadline_el else None

                        if not url.startswith('http'):
                            url = self.BASE_URL.rstrip('/') + '/' + url.lstrip('/')

                        results.append(RawCompetition(
                            title=title,
                            url=url,
                            source=self.SOURCE_NAME,
                            deadline_raw=deadline_raw,
                            deadline=self.parse_deadline(deadline_raw or ""),
                        ))

                        await asyncio.sleep(0.5)  # gentle rate limit

                    except Exception as e:
                        logger.warning(f"[{self.SOURCE_NAME}] Skip item: {e}")
                        continue

        except httpx.HTTPError as e:
            logger.warning(f"[{self.SOURCE_NAME}] HTTP error: {e}")
        except Exception as e:
            logger.warning(f"[{self.SOURCE_NAME}] Scraper error: {e}")

        logger.info(f"[{self.SOURCE_NAME}] Berhasil scrape {len(results)} lomba")
        return results
```

---

## Daftar Scraper & Method

| File | Class | Method | URL Target |
|---|---|---|---|
| `scrapers/devpost.py` | `DevpostScraper` | Playwright | `devpost.com/hackathons` |
| `scrapers/kaggle.py` | `KaggleScraper` | httpx+BS4 | `kaggle.com/competitions` |
| `scrapers/sinta.py` | `SintaScraper` | httpx+BS4 | `sinta.kemdikbud.go.id/journals` |
| `scrapers/dicoding.py` | `DicodingScraper` | Playwright | `dicoding.com/events/all` |
| `scrapers/lomba_info.py` | `LombaInfoScraper` | httpx+BS4 | `lomba.info` |
| `scrapers/info_lomba.py` | `InfoLombaScraper` | httpx+BS4 | `info-lomba.com` |

---

## Registrasi Semua Scraper

Di `scrapers/__init__.py`:

```python
from .devpost import DevpostScraper
from .kaggle import KaggleScraper
from .sinta import SintaScraper
from .dicoding import DicodingScraper
from .lomba_info import LombaInfoScraper
from .info_lomba import InfoLombaScraper

ALL_SCRAPERS = [
    DevpostScraper,
    KaggleScraper,
    SintaScraper,
    DicodingScraper,
    LombaInfoScraper,
    InfoLombaScraper,
]
```

Di `core/competition_manager.py`, loop semua scraper:

```python
from scrapers import ALL_SCRAPERS

async def run_all_scrapers() -> list[RawCompetition]:
    all_results = []
    for ScraperClass in ALL_SCRAPERS:
        scraper = ScraperClass()
        results = await scraper.scrape()
        all_results.extend(results)
        await asyncio.sleep(3)  # jeda antar scraper
    return all_results
```

---

## Catatan Penting untuk AI Agent

Saat mengimplementasikan scraper, **selector CSS di atas adalah estimasi**. Karena HTML situs bisa berubah, implementasikan dengan pola defensif berikut:

```python
# Selalu gunakan pola ini:
title_el = (
    article.select_one(".judul-utama") or      # selector primer
    article.select_one("h2 a") or              # fallback 1
    article.select_one("h3 a") or              # fallback 2
    article.select_one("a.title")              # fallback 3
)
```

Jika semua selector gagal, skip item tersebut dengan `continue`, log WARNING, dan lanjutkan ke item berikutnya.
