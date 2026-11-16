"""
scrapers/twitter_x.py — Scraper X (Twitter) menggunakan twscrape.

Mencari tweet berisi info lomba/kompetisi/hackathon berdasarkan
keyword dan hashtag, lalu mengekstrak data terstruktur.
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
from typing import Optional

from twscrape import API, gather

from config.settings import (
    X_USERNAME,
    X_PASSWORD,
    X_EMAIL,
    X_EMAIL_PASSWORD,
)
from .base import BaseScraper, RawCompetition

logger = logging.getLogger(__name__)

# Keyword pencarian tweet yang berisi info lomba
SEARCH_QUERIES: list[str] = [
    "lomba 2026 deadline",
    "hackathon 2026 register",
    "kompetisi mahasiswa 2026",
    "call for paper 2026",
    "datathon 2026",
    "coding competition 2026",
]

# Filter: minimal harus ada salah satu kata ini di tweet
RELEVANCE_KEYWORDS: list[str] = [
    "lomba", "kompetisi", "hackathon", "datathon", "competition",
    "call for paper", "cfp", "challenge", "contest", "register",
    "daftar", "deadline", "pendaftaran", "submission",
]


class TwitterXScraper(BaseScraper):
    """Scraper untuk X (Twitter) — mencari tweet berisi info lomba."""

    SOURCE_NAME = "twitter_x"
    BASE_URL = "https://x.com"

    def __init__(self) -> None:
        super().__init__()
        self._api: Optional[API] = None

    async def _init_api(self) -> Optional[API]:
        """Inisialisasi twscrape API dengan akun dari .env."""
        if not all([X_USERNAME, X_PASSWORD, X_EMAIL]):
            logger.info("[%s] Kredensial X tidak diisi, skip.", self.SOURCE_NAME)
            return None

        try:
            api = API()

            # Cek apakah akun sudah ada di pool
            accounts = await api.pool.accounts_info()
            account_exists = any(
                acc.get("username", "").lower() == X_USERNAME.lower()
                for acc in accounts
            ) if accounts else False

            if not account_exists:
                logger.info("[%s] Menambahkan akun X ke pool ...", self.SOURCE_NAME)
                await api.pool.add_account(
                    X_USERNAME,
                    X_PASSWORD,
                    X_EMAIL,
                    X_EMAIL_PASSWORD or "",
                )
                await api.pool.login_all()

            # Cek apakah ada akun aktif setelah login
            accounts = await api.pool.accounts_info()
            active = [a for a in accounts if a.get("active")]
            if not active:
                logger.warning(
                    "[%s] Login X gagal (kemungkinan diblokir Cloudflare). Skip scraper ini.",
                    self.SOURCE_NAME,
                )
                return None

            logger.info("[%s] Login X berhasil, %d akun aktif.", self.SOURCE_NAME, len(active))
            return api
        except Exception as e:
            logger.warning("[%s] Gagal init API: %s", self.SOURCE_NAME, e)
            return None

    async def scrape(self) -> list[RawCompetition]:
        """Scrape tweet dari X berdasarkan keyword pencarian."""
        results: list[RawCompetition] = []

        api = await self._init_api()
        if not api:
            return results

        seen_urls: set[str] = set()

        for query in SEARCH_QUERIES:
            try:
                tweets = await gather(api.search(query, limit=10))

                for tweet in tweets:
                    try:
                        text = tweet.rawContent or ""

                        # Filter relevansi — harus ada keyword lomba
                        if not self._is_relevant(text):
                            continue

                        # Ekstrak URL dari tweet
                        urls = self._extract_urls(text, tweet)
                        tweet_url = f"https://x.com/{tweet.user.username}/status/{tweet.id}"

                        # Gunakan URL eksternal jika ada, fallback ke URL tweet
                        target_url = urls[0] if urls else tweet_url

                        # Skip duplikat
                        if target_url in seen_urls:
                            continue
                        seen_urls.add(target_url)

                        # Ekstrak judul (baris pertama atau 80 karakter pertama)
                        title = self._extract_title(text)
                        if not title:
                            continue

                        # Coba parse deadline dari teks
                        deadline_raw = self._extract_deadline_text(text)

                        results.append(RawCompetition(
                            title=title,
                            url=target_url,
                            source=self.SOURCE_NAME,
                            description=text[:500],
                            deadline_raw=deadline_raw,
                            deadline=self.parse_deadline(deadline_raw or ""),
                            organizer=f"@{tweet.user.username}",
                            location_raw=text,
                        ))
                    except Exception as e:
                        logger.warning("[%s] Skip tweet: %s", self.SOURCE_NAME, e)
                        continue

                await asyncio.sleep(2)  # rate limit antar query

            except Exception as e:
                logger.warning("[%s] Gagal search '%s': %s", self.SOURCE_NAME, query, e)
                continue

        logger.info("[%s] Berhasil scrape %d lomba", self.SOURCE_NAME, len(results))
        return results

    def _is_relevant(self, text: str) -> bool:
        """Cek apakah tweet relevan dengan topik lomba/kompetisi."""
        lower = text.lower()
        return any(kw in lower for kw in RELEVANCE_KEYWORDS)

    def _extract_title(self, text: str) -> str:
        """Ekstrak judul dari teks tweet."""
        # Hapus URL dari teks
        clean = re.sub(r"https?://\S+", "", text).strip()
        # Hapus hashtag berlebihan di akhir
        clean = re.sub(r"(\s*#\w+){3,}$", "", clean).strip()

        # Ambil baris pertama sebagai judul
        lines = [line.strip() for line in clean.split("\n") if line.strip()]
        if not lines:
            return ""

        title = lines[0]
        # Potong jika terlalu panjang
        if len(title) > 100:
            title = title[:97] + "..."
        return title

    def _extract_urls(self, text: str, tweet) -> list[str]:
        """Ekstrak URL eksternal dari tweet (bukan url twitter)."""
        urls: list[str] = []
        # Dari teks
        found = re.findall(r"https?://\S+", text)
        for url in found:
            # Filter URL twitter/x sendiri
            if "twitter.com" not in url and "x.com" not in url and "t.co" not in url:
                urls.append(url.rstrip(".,;:!?)"))

        # Dari entities tweet jika tersedia
        if hasattr(tweet, "urls") and tweet.urls:
            for u in tweet.urls:
                expanded = getattr(u, "expandedUrl", None) or getattr(u, "url", None)
                if expanded and "twitter.com" not in expanded and "x.com" not in expanded:
                    urls.append(expanded)

        return urls

    def _extract_deadline_text(self, text: str) -> Optional[str]:
        """Coba ekstrak teks deadline dari tweet."""
        lower = text.lower()

        # Pola: "deadline: 15 Juni 2026" atau "deadline 15/06/2026"
        patterns = [
            r"deadline[:\s]+([^\n,]{5,30})",
            r"batas\s+(?:waktu|akhir)[:\s]+([^\n,]{5,30})",
            r"pendaftaran\s+(?:sampai|hingga|s\.?d\.?)[:\s]+([^\n,]{5,30})",
            r"registrasi[:\s]+(?:sampai|hingga)?[:\s]*([^\n,]{5,30})",
        ]

        for pattern in patterns:
            match = re.search(pattern, lower)
            if match:
                return match.group(1).strip()

        return None
