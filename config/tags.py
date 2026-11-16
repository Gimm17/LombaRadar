"""
config/tags.py — Definisi tag, keyword mapping, dan data seed.

TAG_KEYWORDS digunakan oleh core/tagger.py untuk auto-tagging.
INITIAL_TAGS digunakan oleh db/migrations.py untuk seed data awal.
"""

from typing import Final

# ── Keyword mapping per tag slug ──────────────────────────────────────────────
# Dipakai oleh core/tagger.py untuk mencocokkan judul + deskripsi lomba
TAG_KEYWORDS: Final[dict[str, list[str]]] = {
    "ai_ml": [
        "artificial intelligence", "machine learning", "deep learning",
        "neural network", "nlp", "computer vision", "llm", "ai", "ml",
        "kecerdasan buatan", "pembelajaran mesin", "data science",
    ],
    "web_dev": [
        "web", "website", "frontend", "backend", "fullstack", "react",
        "vue", "laravel", "django", "api", "rest", "graphql", "javascript",
    ],
    "datathon": [
        "datathon", "data competition", "data challenge", "dataset",
        "analytics", "visualization", "tableau", "power bi", "kaggle",
    ],
    "paper": [
        "call for paper", "cfp", "jurnal", "journal", "publikasi",
        "seminar nasional", "semnas", "konferensi", "conference",
        "proceedings", "artikel ilmiah", "sinta", "scopus", "ieee",
    ],
    "gis": [
        "gis", "geographic information", "pemetaan", "geospasial",
        "remote sensing", "arcgis", "qgis", "mapping", "geografi",
    ],
    "mobile": [
        "mobile", "android", "ios", "flutter", "react native",
        "kotlin", "swift", "aplikasi mobile",
    ],
    "cyber": [
        "cybersecurity", "ctf", "capture the flag", "hacking",
        "penetration testing", "keamanan siber", "forensik digital",
    ],
}

# ── Seed data untuk tabel tags ────────────────────────────────────────────────
# Diinsert ke DB saat pertama kali init via db/migrations.py
INITIAL_TAGS: Final[list[dict[str, str]]] = [
    {"name": "AI/ML",        "slug": "ai_ml",    "color_hex": "#7F77DD", "emoji": "🤖"},
    {"name": "Web Dev",      "slug": "web_dev",  "color_hex": "#1D9E75", "emoji": "🌐"},
    {"name": "Datathon",     "slug": "datathon", "color_hex": "#EF9F27", "emoji": "📊"},
    {"name": "Paper/Jurnal", "slug": "paper",    "color_hex": "#D85A30", "emoji": "📄"},
    {"name": "GIS",          "slug": "gis",      "color_hex": "#378ADD", "emoji": "🗺️"},
    {"name": "Mobile Dev",   "slug": "mobile",   "color_hex": "#D4537E", "emoji": "📱"},
    {"name": "Cybersecurity","slug": "cyber",    "color_hex": "#A32D2D", "emoji": "🔐"},
    {"name": "Umum",         "slug": "umum",     "color_hex": "#888780", "emoji": "🏆"},
]

# ── Source label mapping (untuk display di pesan Telegram) ────────────────────
SOURCE_LABELS: Final[dict[str, str]] = {
    "devpost":       "Devpost",
    "kaggle":        "Kaggle",
    "sinta":         "SINTA Dikti",
    "dicoding":      "Dicoding Events",
    "lomba_info":    "Lomba.info",
    "info_lomba":    "Info Lomba",
    "twitter_x":     "X (Twitter)",
    "devfolio":      "Devfolio",
    "mlh":           "MLH",
    "hackerearth":   "HackerEarth",
    "unstop":        "Unstop",
    "lablab":        "LabLab.ai",
    "sumatranomics": "Sumatranomics",
    "ejavec":        "EJAVEC Forum",
}
