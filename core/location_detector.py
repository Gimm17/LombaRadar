"""
core/location_detector.py — Deteksi tipe lokasi lomba (online/onsite/hybrid).

Menganalisis teks deskripsi/lokasi mentah dan menentukan apakah
acara bersifat online, onsite, atau hybrid beserta detail lokasinya.
"""

from __future__ import annotations

import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)

ONLINE_KEYWORDS: list[str] = [
    "online", "daring", "virtual", "zoom", "google meet", "teams",
    "remote", "webinar", "digital", "platform online",
]

ONSITE_KEYWORDS: list[str] = [
    "onsite", "luring", "offline", "tatap muka", "hadir langsung",
    "jakarta", "bandung", "surabaya", "yogyakarta", "medan", "makassar",
    "universitas", "kampus", "gedung", "hotel", "hall",
]

# Nama kota untuk ekstraksi location_detail
_CITY_NAMES: list[str] = [
    "jakarta", "bandung", "surabaya", "yogyakarta", "semarang",
    "medan", "makassar", "denpasar", "malang", "solo",
    "palembang", "pekanbaru", "manado", "pontianak", "balikpapan",
    "palu", "kendari", "jayapura", "mataram", "kupang",
]


def detect_location(text: Optional[str] = None) -> tuple[str, str]:
    """
    Deteksi tipe lokasi dari teks.

    Args:
        text: Teks deskripsi / lokasi mentah dari scraper.

    Returns:
        Tuple (location_type, location_detail).
        location_type: 'online' | 'onsite' | 'hybrid'
        location_detail: nama kota/tempat jika onsite/hybrid, '' jika online.
    """
    if not text:
        return ("online", "")

    lower_text = text.lower()

    has_online = any(kw in lower_text for kw in ONLINE_KEYWORDS)
    has_onsite = any(kw in lower_text for kw in ONSITE_KEYWORDS)

    # Ekstrak nama kota
    detail = _extract_location_detail(lower_text)

    if has_online and has_onsite:
        return ("hybrid", detail)
    elif has_onsite:
        return ("onsite", detail)
    else:
        # Default ke online (termasuk jika hanya has_online)
        return ("online", "")


def _extract_location_detail(text: str) -> str:
    """Ekstrak nama kota atau tempat dari teks."""
    # Cek nama kota yang dikenal
    for city in _CITY_NAMES:
        if city in text:
            return city.title()

    # Coba ekstrak pola "Universitas ..." atau "Kampus ..."
    match = re.search(r'(universitas|kampus|gedung|hotel)\s+([a-zA-Z\s]{3,30})', text)
    if match:
        return match.group(0).strip().title()

    return ""
