"""
config/settings.py — Konfigurasi global LombaRadar.

Load environment variables dari .env dan expose sebagai konstanta.
Semua modul lain import setting dari sini, bukan langsung os.getenv().
"""

from dotenv import load_dotenv
import os

load_dotenv()

# ── Telegram ──────────────────────────────────────────────────────────────────
TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHANNEL_ID: str | None = os.getenv("TELEGRAM_CHANNEL_ID")
OWNER_CHAT_ID: int | None = int(os.getenv("OWNER_CHAT_ID", "0")) or None

# ── Database ──────────────────────────────────────────────────────────────────
DATABASE_PATH: str = os.getenv("DATABASE_PATH", "./data/lombaradar.db")

# ── Scheduler ─────────────────────────────────────────────────────────────────
SCRAPE_INTERVAL_HOURS: int = int(os.getenv("SCRAPE_INTERVAL_HOURS", "6"))
DIGEST_HOUR_UTC: int = 23  # 07.00 WITA = 23.00 UTC hari sebelumnya

# ── Playwright ────────────────────────────────────────────────────────────────
PLAYWRIGHT_HEADLESS: bool = os.getenv("PLAYWRIGHT_HEADLESS", "true").lower() == "true"
PLAYWRIGHT_TIMEOUT: int = int(os.getenv("PLAYWRIGHT_TIMEOUT_MS", "30000"))

# ── Logging ───────────────────────────────────────────────────────────────────
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE: str = os.getenv("LOG_FILE", "./logs/lombaradar.log")

# ── X (Twitter) ───────────────────────────────────────────────────────────────
X_USERNAME: str = os.getenv("X_USERNAME", "")
X_PASSWORD: str = os.getenv("X_PASSWORD", "")
X_EMAIL: str = os.getenv("X_EMAIL", "")
X_EMAIL_PASSWORD: str = os.getenv("X_EMAIL_PASSWORD", "")
