<div align="center">

# 📡 LombaRadar

### Automated Competition, Hackathon & Call-for-Paper Telegram Aggregator

[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Telegram](https://img.shields.io/badge/Telegram-python--telegram--bot%20v21-26A5E4?style=for-the-badge&logo=telegram&logoColor=white)](https://python-telegram-bot.org/)
[![Playwright](https://img.shields.io/badge/Playwright-Async%20Scraping-2EAD33?style=for-the-badge&logo=playwright&logoColor=white)](https://playwright.dev/)
[![SQLite](https://img.shields.io/badge/SQLite-aiosqlite-003B57?style=for-the-badge&logo=sqlite&logoColor=white)](https://www.sqlite.org/)

*Scrapes trusted competition platforms every 6 hours, classifies opportunities by domain tag, deduplicates entries, and delivers targeted Telegram alerts.*

</div>

---

## ✨ Fitur Utama

- 🔍 **Agregasi Otomatis (6 Sumber)** — Scrape **Devpost**, **Kaggle**, **SINTA Dikti**, **Dicoding**, **lomba.info**, dan **info-lomba.com** setiap 6 jam via APScheduler.
- 🏷️ **Auto-Tagging Cerdas** — Klasifikasi otomatis kategori (`ai_ml`, `web_dev`, `datathon`, `paper`, `gis`, `mobile_dev`, `cyber`, `umum`).
- 📬 **Distribusi Berbasis Preferensi** — Notifikasi hanya dikirim ke subscriber yang berlangganan tag relevan.
- 🔒 **Anti-Duplikat** — Hash deduplication dan `sent_log` memastikan satu lomba hanya dikirim sekali per user per tipe pesan.
- 📋 **Multi-Format Notifikasi** — Info lomba baru, reminder H-7, reminder H-1, dan daily digest.

---

## 🛠 Tech Stack

| Komponen | Teknologi |
| :--- | :--- |
| **Language** | Python 3.11+ |
| **Scraping (JS)** | Playwright (async) |
| **Scraping (Static)** | BeautifulSoup4 + httpx |
| **Telegram Bot** | `python-telegram-bot` v21 |
| **Database** | SQLite (`aiosqlite`) |
| **Scheduler** | APScheduler 3.x |
| **Deployment** | Railway (`railway.toml`) |

---

## 📁 Struktur Proyek

```text
LombaRadar/
├── main.py                    # Entry point
├── config/
│   ├── settings.py            # Environment config
│   └── tags.py                # Tag definitions & keywords
├── db/
│   ├── database.py            # SQLite connection
│   ├── models.py              # Dataclass models
│   └── migrations.py          # DDL & seed data
├── scrapers/
│   ├── base.py                # Abstract base scraper
│   ├── devpost.py             # Devpost (Playwright)
│   ├── kaggle.py              # Kaggle (httpx + BS4)
│   ├── sinta.py               # SINTA Dikti (httpx + BS4)
│   ├── dicoding.py            # Dicoding (Playwright)
│   ├── lomba_info.py          # lomba.info (httpx + BS4)
│   └── info_lomba.py          # info-lomba.com (httpx + BS4)
├── core/
│   ├── tagger.py              # Auto-tagging
│   ├── deduplicator.py        # Hash-based dedup
│   ├── location_detector.py   # Location detection
│   └── competition_manager.py # Orchestrator
├── notifier/
│   ├── formatter.py           # MarkdownV2 formatter
│   └── sender.py              # Telegram sender
├── bot/
│   ├── handlers.py            # Command handlers
│   ├── callbacks.py           # Inline callback handlers
│   └── keyboards.py           # Keyboard builders
├── scheduler/
│   └── jobs.py                # APScheduler jobs
└── tests/
    ├── test_tagger.py
    ├── test_deduplicator.py
    └── test_formatter.py
```

---

## 🚀 Setup & Instalasi

```bash
# 1. Clone repository
git clone https://github.com/Gimm17/LombaRadar.git
cd LombaRadar

# 2. Virtual environment
python -m venv venv
venv\Scripts\activate     # Windows (atau source venv/bin/activate di Linux/Mac)

# 3. Install dependencies & Playwright browser
pip install -r requirements.txt
playwright install chromium

# 4. Konfigurasi environment
cp .env.example .env
# Isi TELEGRAM_BOT_TOKEN (dari @BotFather) & TELEGRAM_CHANNEL_ID (opsional)

# 5. Jalankan bot
python main.py
```

---

## 🤖 Telegram Commands & Kategori

| Command | Deskripsi |
| :--- | :--- |
| `/start` | Registrasi & welcome message |
| `/lomba` | 5 lomba terbaru |
| `/filter [tag]` | Filter lomba berdasarkan kategori (`ai_ml`, `web_dev`, `datathon`, `paper`, `gis`, `mobile_dev`, `cyber`, `umum`) |
| `/subscribe [tag]` | Langganan kategori |
| `/unsubscribe [tag]` | Berhenti langganan |
| `/deadline` | Lomba mendekati deadline |
| `/tags` | Daftar semua kategori |
| `/status` | Status bot & statistik |
| `/help` | Bantuan penggunaan |

---

## 🧪 Testing & Deploy

```bash
python -m pytest tests/ -v
# atau
python -m unittest discover tests/ -v
```

Untuk deploy ke Railway, hubungkan repo `Gimm17/LombaRadar`, atur environment variables dari `.env.example`, dan deploy via `railway.toml`.

---

## 📄 Lisensi

MIT License — Dikembangkan oleh **Gimora Digital** (`Gimm17`).
