"""
scrapers/hackerearth.py — Scraper HackerEarth challenges.

HackerEarth challenges page is JS-heavy, so we use Playwright.
"""

from __future__ import annotations

import logging

from playwright.async_api import async_playwright

from .base import BaseScraper, RawCompetition

logger = logging.getLogger(__name__)


class HackerEarthScraper(BaseScraper):
    """Scraper untuk hackerearth.com — coding challenges & hackathons."""

    SOURCE_NAME = "hackerearth"
    BASE_URL = "https://www.hackerearth.com/challenges/"

    async def scrape(self) -> list[RawCompetition]:
        results: list[RawCompetition] = []
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                await page.goto(self.BASE_URL, wait_until="networkidle", timeout=30000)
                await page.wait_for_timeout(3000)

                # Challenge cards
                cards = await page.query_selector_all(".challenge-card-modern, .challenge-card, .upcoming")
                for card in cards:
                    try:
                        # Title
                        title_el = await card.query_selector(".challenge-name, .challenge-list-title, h4, h3")
                        title = await title_el.inner_text() if title_el else None
                        if not title:
                            continue

                        # URL
                        link_el = await card.query_selector("a[href]")
                        href = await link_el.get_attribute("href") if link_el else None
                        if not href:
                            continue
                        url = href if href.startswith("http") else f"https://www.hackerearth.com{href}"

                        # Deadline
                        time_el = await card.query_selector(".challenge-type, .date, time, .card-time-details")
                        deadline_raw = await time_el.inner_text() if time_el else None

                        results.append(RawCompetition(
                            title=title.strip(),
                            url=url,
                            source=self.SOURCE_NAME,
                            description=f"HackerEarth: {title.strip()}",
                            deadline_raw=deadline_raw,
                            deadline=self.parse_deadline(deadline_raw or ""),
                            organizer="HackerEarth",
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
