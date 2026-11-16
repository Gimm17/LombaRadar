"""
scrapers/dicoding.py — Scraper Dicoding Events menggunakan Playwright.

Mengambil data event (competition, hackathon) dari dicoding.com/events/all.
"""

from __future__ import annotations

import logging

from playwright.async_api import async_playwright, TimeoutError as PWTimeout

from config.settings import PLAYWRIGHT_HEADLESS, PLAYWRIGHT_TIMEOUT
from .base import BaseScraper, RawCompetition

logger = logging.getLogger(__name__)


class DicodingScraper(BaseScraper):
    """Scraper untuk Dicoding Events."""

    SOURCE_NAME = "dicoding"
    BASE_URL = "https://www.dicoding.com/events/all"

    async def scrape(self) -> list[RawCompetition]:
        """Scrape halaman event listing Dicoding."""
        results: list[RawCompetition] = []
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=PLAYWRIGHT_HEADLESS)
                page = await browser.new_page()
                await page.set_extra_http_headers(self.HEADERS)

                try:
                    await page.goto(self.BASE_URL, timeout=PLAYWRIGHT_TIMEOUT)
                    await page.wait_for_load_state("networkidle", timeout=PLAYWRIGHT_TIMEOUT)

                    # Selector dengan fallback
                    cards = await page.query_selector_all(
                        "div.event-card, div.card-event, "
                        "div.event-item, article.event"
                    )

                    for card in cards[:20]:
                        try:
                            title_el = (
                                await card.query_selector("h3")
                                or await card.query_selector("h2")
                                or await card.query_selector(".event-title")
                                or await card.query_selector(".title")
                            )
                            link_el = await card.query_selector("a[href]")
                            deadline_el = (
                                await card.query_selector(".event-date")
                                or await card.query_selector("time")
                                or await card.query_selector(".date")
                            )
                            desc_el = (
                                await card.query_selector(".event-desc")
                                or await card.query_selector("p")
                            )
                            img_el = await card.query_selector("img")

                            title = await title_el.inner_text() if title_el else None
                            url = await link_el.get_attribute("href") if link_el else None
                            deadline_raw = await deadline_el.inner_text() if deadline_el else None
                            description = await desc_el.inner_text() if desc_el else None
                            image_url = await img_el.get_attribute("src") if img_el else None

                            if not title or not url:
                                continue

                            # Normalisasi URL
                            if url.startswith("/"):
                                url = f"https://www.dicoding.com{url}"

                            results.append(RawCompetition(
                                title=title.strip(),
                                url=url.strip(),
                                source=self.SOURCE_NAME,
                                description=description.strip() if description else None,
                                deadline_raw=deadline_raw,
                                deadline=self.parse_deadline(deadline_raw or ""),
                                organizer="Dicoding",
                                image_url=image_url,
                            ))
                        except Exception as e:
                            logger.warning("[%s] Skip card: %s", self.SOURCE_NAME, e)
                            continue

                except PWTimeout:
                    logger.warning("[%s] Timeout saat load halaman", self.SOURCE_NAME)
                finally:
                    await browser.close()

        except Exception as e:
            logger.warning("[%s] Scraper error: %s", self.SOURCE_NAME, e)

        logger.info("[%s] Berhasil scrape %d lomba", self.SOURCE_NAME, len(results))
        return results
