"""
scrapers/devpost.py — Scraper Devpost hackathons menggunakan Playwright.

Mengambil data hackathon dari devpost.com/hackathons
dengan JS rendering via Playwright (async).
"""

from __future__ import annotations

import logging

from playwright.async_api import async_playwright, TimeoutError as PWTimeout

from config.settings import PLAYWRIGHT_HEADLESS, PLAYWRIGHT_TIMEOUT
from .base import BaseScraper, RawCompetition

logger = logging.getLogger(__name__)


class DevpostScraper(BaseScraper):
    """Scraper untuk Devpost hackathons."""

    SOURCE_NAME = "devpost"
    BASE_URL = "https://devpost.com/hackathons?challenge_type=all&sort_by=Deadline"

    async def scrape(self) -> list[RawCompetition]:
        """Scrape halaman listing hackathon Devpost."""
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
                        "article.hackathon-tile, div.challenge-listing, "
                        "div.hackathon-card, a.block-wrapper"
                    )

                    for card in cards[:20]:  # max 20 per scrape
                        try:
                            title_el = (
                                await card.query_selector("h2")
                                or await card.query_selector(".challenge-title")
                                or await card.query_selector(".title")
                                or await card.query_selector("h3")
                            )
                            link_el = await card.query_selector("a[href]")
                            deadline_el = (
                                await card.query_selector(".submission-period")
                                or await card.query_selector(".deadline")
                                or await card.query_selector("time")
                            )
                            prize_el = (
                                await card.query_selector(".prize-amount")
                                or await card.query_selector(".prize")
                            )
                            org_el = (
                                await card.query_selector(".host-label")
                                or await card.query_selector(".organizer")
                            )

                            title = await title_el.inner_text() if title_el else None
                            url = await link_el.get_attribute("href") if link_el else None
                            deadline_raw = await deadline_el.inner_text() if deadline_el else None
                            prize = await prize_el.inner_text() if prize_el else None
                            organizer = await org_el.inner_text() if org_el else "Devpost"

                            if not title or not url:
                                continue

                            # Normalisasi URL
                            if url.startswith("/"):
                                url = f"https://devpost.com{url}"

                            results.append(RawCompetition(
                                title=title.strip(),
                                url=url.strip(),
                                source=self.SOURCE_NAME,
                                deadline_raw=deadline_raw,
                                deadline=self.parse_deadline(deadline_raw or ""),
                                prize=prize.strip() if prize else None,
                                organizer=organizer.strip() if organizer else "Devpost",
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
