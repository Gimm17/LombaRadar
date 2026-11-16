"""
core/tagger.py — Auto-tagging lomba berdasarkan keyword matching.

Mencocokkan judul + deskripsi lomba terhadap TAG_KEYWORDS,
mengembalikan list slug tag yang relevan (maks 3, default 'umum').
"""

from __future__ import annotations

import logging
from typing import Optional

from config.tags import TAG_KEYWORDS

logger = logging.getLogger(__name__)


def auto_tag(title: str, description: Optional[str] = None) -> list[str]:
    """
    Auto-tag berdasarkan keyword matching pada title + description.

    Returns:
        List slug tag yang match, maks 3. Default ["umum"] jika tidak ada match.
    """
    text = (title + " " + (description or "")).lower()

    # Hitung jumlah keyword match per tag
    tag_scores: dict[str, int] = {}
    for slug, keywords in TAG_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in text)
        if score > 0:
            tag_scores[slug] = score

    if not tag_scores:
        return ["umum"]

    # Urutkan berdasarkan skor (paling relevan dulu), ambil maks 3
    sorted_tags = sorted(tag_scores, key=lambda s: tag_scores[s], reverse=True)
    return sorted_tags[:3]
