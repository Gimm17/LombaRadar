"""
scrapers/unstop.py — Scraper Unstop (unstop.com/hackathons).

Unstop membutuhkan cookies, jadi kita pakai Playwright.
"""

from __future__ import annotations

import logging

from playwright.async_api import async_playwright

from .base import BaseScraper, RawCompetition

logger = logging.getLogger(__name__)


class UnstopScraper(BaseScraper):
    """Scraper untuk unstop.com — kompetisi, hackathon, scholarship."""

    SOURCE_NAME = "unstop"
    BASE_URL = "https://unstop.com/hackathons"

    async def scrape(self) -> list[RawCompetition]:
        results: list[RawCompetition] = []
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                )
                page = await context.new_page()
                await page.goto(self.BASE_URL, wait_until="networkidle", timeout=45000)
                await page.wait_for_timeout(5000)

                # Unstop listing cards
                cards = await page.query_selector_all(
                    ".single_profile, .card, .opp-card, [class*='listing']"
                )
                for card in cards:
                    try:
                        title_el = await card.query_selector(
                            ".opp-title, .single_profile__title, h3, h4, .title"
                        )
                        title = await title_el.inner_text() if title_el else None
                        if not title or len(title.strip()) < 5:
                            continue

                        link_el = await card.query_selector("a[href*='/hackathon']")
                        if not link_el:
                            link_el = await card.query_selector("a[href]")
                        href = await link_el.get_attribute("href") if link_el else None
                        if not href:
                            continue
                        url = href if href.startswith("http") else f"https://unstop.com{href}"

                        # Deadline/date
                        date_el = await card.query_selector(
                            ".opp-deadline, .date, time, .single_profile__date, .end-date"
                        )
                        deadline_raw = await date_el.inner_text() if date_el else None

                        # Prize
                        prize_el = await card.query_selector(".prize, .opp-prize, .worth")
                        prize = await prize_el.inner_text() if prize_el else None

                        results.append(RawCompetition(
                            title=title.strip(),
                            url=url,
                            source=self.SOURCE_NAME,
                            description=f"Unstop: {title.strip()}",
                            deadline_raw=deadline_raw,
                            deadline=self.parse_deadline(deadline_raw or ""),
                            organizer="Unstop",
                            prize=prize,
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
