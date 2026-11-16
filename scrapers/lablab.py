"""
scrapers/lablab.py — Scraper LabLab.ai (AI Hackathons).

LabLab.ai memblok httpx (403), jadi pakai Playwright.
Ini sumber utama untuk AI hackathon global.
"""

from __future__ import annotations

import logging

from playwright.async_api import async_playwright

from .base import BaseScraper, RawCompetition

logger = logging.getLogger(__name__)


class LablabScraper(BaseScraper):
    """Scraper untuk lablab.ai — AI hackathon global."""

    SOURCE_NAME = "lablab"
    BASE_URL = "https://lablab.ai/ai-hackathons"

    async def scrape(self) -> list[RawCompetition]:
        results: list[RawCompetition] = []
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                )
                await page.goto(self.BASE_URL, wait_until="networkidle", timeout=45000)
                await page.wait_for_timeout(5000)

                # LabLab hackathon cards — biasanya div/a cards dengan judul
                cards = await page.query_selector_all(
                    "a[href*='/event/'], a[href*='/hackathon/'], "
                    "[class*='hackathon'], [class*='event-card'], "
                    "[class*='Card'], [class*='card']"
                )

                seen: set[str] = set()
                for card in cards:
                    try:
                        # Ambil URL
                        href = await card.get_attribute("href")
                        if not href:
                            link = await card.query_selector("a[href]")
                            href = await link.get_attribute("href") if link else None
                        if not href or href in seen:
                            continue

                        url = href if href.startswith("http") else f"https://lablab.ai{href}"

                        # Skip non-event URLs
                        if "/event/" not in url and "/hackathon/" not in url:
                            continue

                        seen.add(url)

                        # Title
                        title_el = await card.query_selector("h2, h3, h4, [class*='title'], [class*='Title']")
                        if title_el:
                            title = await title_el.inner_text()
                        else:
                            title = await card.inner_text()
                            title = title.split("\n")[0] if title else None

                        if not title or len(title.strip()) < 5:
                            continue

                        # Date
                        date_el = await card.query_selector(
                            "time, [class*='date'], [class*='Date'], [class*='time']"
                        )
                        deadline_raw = await date_el.inner_text() if date_el else None

                        results.append(RawCompetition(
                            title=title.strip()[:100],
                            url=url,
                            source=self.SOURCE_NAME,
                            description=f"LabLab AI Hackathon: {title.strip()}",
                            deadline_raw=deadline_raw,
                            deadline=self.parse_deadline(deadline_raw or ""),
                            organizer="LabLab.ai",
                            location_raw="Online",
                        ))
                    except Exception as e:
                        logger.warning("[%s] Skip card: %s", self.SOURCE_NAME, e)
                        continue

                await browser.close()

        except Exception as e:
            logger.warning("[%s] Error: %s", self.SOURCE_NAME, e)

        logger.info("[%s] Berhasil scrape %d lomba", self.SOURCE_NAME, len(results))
        return results
