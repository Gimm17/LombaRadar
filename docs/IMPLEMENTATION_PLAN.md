# IMPLEMENTATION_PLAN.md — LombaRadar v1.0

> Dokumen ini adalah spesifikasi teknis lengkap untuk AI Agent yang akan men-generate kode LombaRadar.
> Ikuti dokumen ini secara ketat. Jangan improvisasi di luar spesifikasi yang tertulis.

---

## 1. Struktur Folder Lengkap

```
lombaradar/
│
├── main.py                        # Entry point: jalankan bot + scheduler
├── .env.example                   # Template environment variables
├── .gitignore
├── requirements.txt
├── railway.toml                   # Konfigurasi deployment Railway
│
├── config/
│   ├── __init__.py
│   ├── settings.py                # Load .env, constants global
│   └── tags.py                    # Definisi tag: nama, warna, keyword
│
├── db/
│   ├── __init__.py
│   ├── database.py                # Koneksi SQLite, init DB
│   ├── models.py                  # Dataclass/TypedDict untuk tiap tabel
│   └── migrations.py              # CREATE TABLE statements
│
├── scrapers/
│   ├── __init__.py
│   ├── base.py                    # Abstract base class BaseScraper
│   ├── devpost.py                 # Scraper Devpost (Playwright)
│   ├── kaggle.py                  # Scraper Kaggle (httpx + BS4)
│   ├── sinta.py                   # Scraper SINTA Dikti (httpx + BS4)
│   ├── dicoding.py                # Scraper Dicoding Events (Playwright)
│   ├── lomba_info.py              # Scraper lomba.info (httpx + BS4)
│   └── info_lomba.py              # Scraper info-lomba.com (httpx + BS4)
│
├── core/
│   ├── __init__.py
│   ├── tagger.py                  # Auto-tagging berdasarkan keyword
│   ├── deduplicator.py            # Hash-based dedup, cek sent_log
│   ├── location_detector.py       # Deteksi online/onsite/hybrid
│   └── competition_manager.py    # Orchestrator: scrape → tag → dedup → save
│
├── notifier/
│   ├── __init__.py
│   ├── formatter.py               # Format pesan Telegram (MarkdownV2)
│   └── sender.py                  # Kirim pesan ke channel/group/private
│
├── bot/
│   ├── __init__.py
│   ├── handlers.py                # Command handlers (/start, /lomba, dll)
│   ├── callbacks.py               # Inline keyboard callback handlers
│   └── keyboards.py               # InlineKeyboardMarkup builders
│
├── scheduler/
│   ├── __init__.py
│   └── jobs.py                    # APScheduler job definitions
│
└── tests/
    ├── __init__.py
    ├── test_tagger.py
    ├── test_deduplicator.py
    ├── test_formatter.py
    └── test_scrapers.py
```

---

## 2. Skema Database Lengkap

### File: `db/migrations.py`

```sql
-- Tabel utama lomba
CREATE TABLE IF NOT EXISTS competitions (
    id              TEXT PRIMARY KEY,       -- md5(url)[:12]
    title           TEXT NOT NULL,
    source          TEXT NOT NULL,          -- 'devpost', 'kaggle', 'sinta', dll
    url             TEXT NOT NULL UNIQUE,
    description     TEXT,
    deadline        TEXT,                   -- format: 'YYYY-MM-DD', bisa NULL
    deadline_raw    TEXT,                   -- teks asli dari sumber
    organizer       TEXT,
    prize           TEXT,
    image_url       TEXT,
    eligibility     TEXT,                   -- 'mahasiswa S1/D4/S2', dll
    location_type   TEXT DEFAULT 'online',  -- 'online', 'onsite', 'hybrid'
    location_detail TEXT,                   -- 'Jakarta', 'Universitas Brawijaya', dll
    status          TEXT DEFAULT 'open',    -- 'open', 'closing_soon', 'closed'
    scraped_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Tabel master tag
CREATE TABLE IF NOT EXISTS tags (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL UNIQUE,       -- 'AI/ML', 'Web Dev', 'Datathon', dll
    slug        TEXT NOT NULL UNIQUE,       -- 'ai_ml', 'web_dev', dll (untuk command)
    color_hex   TEXT NOT NULL,             -- '#7F77DD'
    emoji       TEXT                        -- opsional, untuk display
);

-- Relasi many-to-many: lomba ↔ tag
CREATE TABLE IF NOT EXISTS competition_tags (
    competition_id  TEXT NOT NULL,
    tag_id          INTEGER NOT NULL,
    PRIMARY KEY (competition_id, tag_id),
    FOREIGN KEY (competition_id) REFERENCES competitions(id),
    FOREIGN KEY (tag_id) REFERENCES tags(id)
);

-- Tabel subscriber (user/channel/group yang pakai bot)
CREATE TABLE IF NOT EXISTS subscribers (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_chat_id    BIGINT NOT NULL UNIQUE,
    chat_type       TEXT NOT NULL,          -- 'private', 'group', 'channel'
    chat_title      TEXT,                   -- nama group/channel
    is_active       INTEGER DEFAULT 1,      -- 1=aktif, 0=unsubscribe
    joined_at       DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_active_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Preferensi tag per subscriber (kosong = semua tag)
CREATE TABLE IF NOT EXISTS subscriber_tags (
    subscriber_id   INTEGER NOT NULL,
    tag_id          INTEGER NOT NULL,
    PRIMARY KEY (subscriber_id, tag_id),
    FOREIGN KEY (subscriber_id) REFERENCES subscribers(id),
    FOREIGN KEY (tag_id) REFERENCES tags(id)
);

-- Log pesan yang sudah dikirim (anti-duplikat)
CREATE TABLE IF NOT EXISTS sent_log (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    competition_id  TEXT NOT NULL,
    telegram_chat_id    BIGINT NOT NULL,
    message_type    TEXT NOT NULL,          -- 'new', 'reminder_7d', 'reminder_1d', 'digest'
    sent_at         DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(competition_id, telegram_chat_id, message_type),
    FOREIGN KEY (competition_id) REFERENCES competitions(id)
);
```

### Data Seed Tags (diinsert saat init DB)

```python
INITIAL_TAGS = [
    {"name": "AI/ML",       "slug": "ai_ml",    "color_hex": "#7F77DD", "emoji": "🤖"},
    {"name": "Web Dev",     "slug": "web_dev",  "color_hex": "#1D9E75", "emoji": "🌐"},
    {"name": "Datathon",    "slug": "datathon", "color_hex": "#EF9F27", "emoji": "📊"},
    {"name": "Paper/Jurnal","slug": "paper",    "color_hex": "#D85A30", "emoji": "📄"},
    {"name": "GIS",         "slug": "gis",      "color_hex": "#378ADD", "emoji": "🗺️"},
    {"name": "Mobile Dev",  "slug": "mobile",   "color_hex": "#D4537E", "emoji": "📱"},
    {"name": "Cybersecurity","slug": "cyber",   "color_hex": "#A32D2D", "emoji": "🔐"},
    {"name": "Umum",        "slug": "umum",     "color_hex": "#888780", "emoji": "🏆"},
]
```

---

## 3. Konfigurasi & Environment Variables

### File: `.env.example`

```env
# Telegram
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHANNEL_ID=-100xxxxxxxxx       # ID channel publik (opsional)

# Database
DATABASE_PATH=./data/lombaradar.db

# Scheduler
SCRAPE_INTERVAL_HOURS=6                  # Interval scraping dalam jam
DIGEST_TIME_WITA=07:00                   # Jam kirim daily digest (WITA = UTC+8)

# Playwright
PLAYWRIGHT_HEADLESS=true
PLAYWRIGHT_TIMEOUT_MS=30000

# Logging
LOG_LEVEL=INFO
LOG_FILE=./logs/lombaradar.log
```

### File: `config/settings.py`

```python
from dotenv import load_dotenv
import os

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID")
DATABASE_PATH = os.getenv("DATABASE_PATH", "./data/lombaradar.db")
SCRAPE_INTERVAL_HOURS = int(os.getenv("SCRAPE_INTERVAL_HOURS", 6))
DIGEST_HOUR_UTC = 23  # 07.00 WITA = 23.00 UTC hari sebelumnya
PLAYWRIGHT_HEADLESS = os.getenv("PLAYWRIGHT_HEADLESS", "true").lower() == "true"
PLAYWRIGHT_TIMEOUT = int(os.getenv("PLAYWRIGHT_TIMEOUT_MS", 30000))
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
```

---

## 4. Logic: Auto-Tagging

### File: `config/tags.py` — keyword mapping

```python
TAG_KEYWORDS = {
    "ai_ml": [
        "artificial intelligence", "machine learning", "deep learning",
        "neural network", "nlp", "computer vision", "llm", "ai", "ml",
        "kecerdasan buatan", "pembelajaran mesin", "data science"
    ],
    "web_dev": [
        "web", "website", "frontend", "backend", "fullstack", "react",
        "vue", "laravel", "django", "api", "rest", "graphql", "javascript"
    ],
    "datathon": [
        "datathon", "data competition", "data challenge", "dataset",
        "analytics", "visualization", "tableau", "power bi", "kaggle"
    ],
    "paper": [
        "call for paper", "cfp", "jurnal", "journal", "publikasi",
        "seminar nasional", "semnas", "konferensi", "conference",
        "proceedings", "artikel ilmiah", "sinta", "scopus", "ieee"
    ],
    "gis": [
        "gis", "geographic information", "pemetaan", "geospasial",
        "remote sensing", "arcgis", "qgis", "mapping", "geografi"
    ],
    "mobile": [
        "mobile", "android", "ios", "flutter", "react native",
        "kotlin", "swift", "aplikasi mobile"
    ],
    "cyber": [
        "cybersecurity", "ctf", "capture the flag", "hacking",
        "penetration testing", "keamanan siber", "forensik digital"
    ],
}
```

### File: `core/tagger.py` — logic

```python
# Fungsi utama: auto_tag(title, description) -> list[str] (list slug tag)
# 1. Gabungkan title + description jadi satu string lowercase
# 2. Untuk setiap tag di TAG_KEYWORDS, cek apakah ada keyword yang cocok (substring match)
# 3. Return list slug tag yang match
# 4. Jika tidak ada yang match, return ["umum"] sebagai default
# 5. Jumlah tag max 3 per lomba (ambil yang paling relevan berdasarkan jumlah keyword match)
```

---

## 5. Logic: Location Detector

### File: `core/location_detector.py`

```python
ONLINE_KEYWORDS = [
    "online", "daring", "virtual", "zoom", "google meet", "teams",
    "remote", "webinar", "digital", "platform online"
]

ONSITE_KEYWORDS = [
    "onsite", "luring", "offline", "tatap muka", "hadir langsung",
    "jakarta", "bandung", "surabaya", "yogyakarta", "medan", "makassar",
    "universitas", "kampus", "gedung", "hotel", "hall"
]

# Fungsi: detect_location(text) -> tuple[str, str]
# Return: (location_type, location_detail)
# location_type: 'online' | 'onsite' | 'hybrid'
# location_detail: nama kota/tempat jika onsite, '' jika online

# Logic:
# 1. Lowercase semua teks
# 2. Cek online keywords
# 3. Cek onsite keywords
# 4. Jika keduanya ada → 'hybrid'
# 5. Jika hanya online → ('online', '')
# 6. Jika hanya onsite → ('onsite', extracted_location)
# 7. Default → ('online', '')

# Untuk extracted_location: ambil kata setelah keyword kota/universitas
# menggunakan simple regex pattern
```

---

## 6. Logic: Deduplicator

### File: `core/deduplicator.py`

```python
import hashlib

# generate_id(url: str) -> str
# Return: md5(url.strip().lower())[:12]

# is_competition_exists(db, competition_id) -> bool
# Cek apakah id sudah ada di tabel competitions

# is_already_sent(db, competition_id, chat_id, message_type) -> bool
# Cek apakah kombinasi (competition_id, chat_id, message_type) sudah ada di sent_log

# mark_as_sent(db, competition_id, chat_id, message_type)
# Insert ke sent_log

# get_unsent_competitions(db, chat_id, tag_slugs=None) -> list[Competition]
# Return lomba yang belum dikirim ke chat_id ini
# Jika tag_slugs tidak None, filter berdasarkan tag
# Urutkan berdasarkan scraped_at DESC
```

---

## 7. Logic: Notifikasi — Format Pesan

### File: `notifier/formatter.py`

Semua pesan menggunakan **Telegram MarkdownV2**. Karakter spesial MarkdownV2 yang harus di-escape: `_ * [ ] ( ) ~ \` > # + - = | { } . !`

Buat helper function `escape_md(text: str) -> str` yang meng-escape semua karakter spesial.

#### 7.1 Format Pesan `new` (lomba baru)

```
🏆 *Lomba Baru Terdeteksi\!*
━━━━━━━━━━━━━━━━━━
📌 *{title}*
🏢 _{organizer}_ · {source_label}

🏷 {tag_emoji} {tag_name} {tag_emoji2} {tag_name2}
━━━━━━━━━━━━━━━━━━
💰 Hadiah    : {prize}
📅 Deadline  : {deadline_formatted}
👥 Peserta   : {eligibility}
📍 Lokasi    : {location_type_label}{location_detail_suffix}
━━━━━━━━━━━━━━━━━━
🔗 {url}
```

Inline keyboard:
- [Daftar Sekarang] → url
- [Simpan] → callback: `save_{competition_id}`
- [Bagikan] → callback: `share_{competition_id}`

#### 7.2 Format Pesan `reminder_7d`

```
⚠️ *Deadline 7 Hari Lagi\!*
━━━━━━━━━━━━━━━━━━
📌 *{title}*
🏢 _{organizer}_

🏷 {tags}
━━━━━━━━━━━━━━━━━━
📅 Deadline  : *{deadline_formatted}* \(7 hari lagi\)
📍 Lokasi    : {location_type_label}{location_detail_suffix}
━━━━━━━━━━━━━━━━━━
🔗 {url}
```

Inline keyboard:
- [Lihat Detail] → url
- [Submit Sekarang] → url

#### 7.3 Format Pesan `reminder_1d`

```
🚨 *Deadline Besok\!*
━━━━━━━━━━━━━━━━━━
📌 *{title}*
🏢 _{organizer}_

🏷 {tags}
━━━━━━━━━━━━━━━━━━
📅 Deadline  : *{deadline_formatted}* \(BESOK\!\)
📍 Lokasi    : {location_type_label}{location_detail_suffix}
━━━━━━━━━━━━━━━━━━
🔗 {url}
```

Inline keyboard:
- [Daftar Sekarang ⚡] → url

#### 7.4 Format Pesan `digest` (daily digest)

```
📋 *Ringkasan Lomba — {tanggal_hari_ini}*
━━━━━━━━━━━━━━━━━━
✨ *{n} Lomba Baru:*

1\. *{title_1}* — {tag_1} · Deadline: {deadline_1}
2\. *{title_2}* — {tag_2} · Deadline: {deadline_2}
3\. *{title_3}* — {tag_3} · Deadline: {deadline_3}

⏰ *Deadline Minggu Ini:*

\! {title_a} — {n} hari lagi
\! {title_b} — {n} hari lagi

_Gunakan /lomba untuk daftar lengkap_
```

Inline keyboard:
- [Lihat Semua Lomba]  → callback: `list_all`
- [Filter Kategori]    → callback: `show_filter`

#### 7.5 Helper: location label

```python
def format_location(location_type, location_detail):
    if location_type == 'online':
        return '🌐 Online'
    elif location_type == 'onsite':
        detail = f' — {location_detail}' if location_detail else ''
        return f'📍 Onsite{detail}'
    elif location_type == 'hybrid':
        detail = f' — {location_detail}' if location_detail else ''
        return f'🔀 Hybrid{detail}'
    return '🌐 Online'
```

---

## 8. Telegram Bot Commands

### File: `bot/handlers.py`

| Command | Deskripsi | Aksi |
|---|---|---|
| `/start` | Registrasi subscriber | Insert ke `subscribers`, reply welcome message |
| `/lomba` | List 5 lomba terbaru | Query `competitions` ORDER BY scraped_at DESC LIMIT 5 |
| `/filter [tag]` | Filter lomba by tag | Contoh: `/filter ai`, `/filter paper` |
| `/subscribe [tag]` | Subscribe ke tag tertentu | Insert ke `subscriber_tags` |
| `/unsubscribe [tag]` | Unsubscribe dari tag | Delete dari `subscriber_tags` |
| `/deadline` | List lomba deadline < 7 hari | Query dengan filter deadline |
| `/tags` | List semua tag tersedia | Reply daftar tag + slug |
| `/status` | Status bot + jumlah lomba di DB | Info diagnostik |
| `/help` | Bantuan penggunaan bot | Reply daftar command |

### Aturan Handler

- Semua handler async (`async def`)
- Gunakan `context.bot.send_message()` bukan `update.message.reply_text()` untuk fleksibilitas
- Semua teks reply dalam Bahasa Indonesia
- Tangani error dengan try-except dan log ke file

---

## 9. Scheduler Jobs

### File: `scheduler/jobs.py`

```python
# Job 1: scrape_all_sources()
# Interval: setiap SCRAPE_INTERVAL_HOURS jam
# Aksi:
#   1. Jalankan semua scraper secara sequential (bukan concurrent, hindari ban)
#   2. Untuk setiap lomba baru yang ditemukan:
#      a. Generate id = md5(url)[:12]
#      b. Auto-tag dengan tagger.auto_tag()
#      c. Detect location dengan location_detector.detect_location()
#      d. Cek dedup: jika sudah ada di DB, skip
#      e. Insert ke competitions + competition_tags
#      f. Kirim notif 'new' ke semua subscriber yang relevan

# Job 2: send_daily_digest()
# Waktu: 23:00 UTC setiap hari (= 07:00 WITA)
# Aksi:
#   1. Ambil semua subscriber aktif
#   2. Untuk setiap subscriber:
#      a. Ambil lomba baru (belum di-digest ke subscriber ini)
#      b. Ambil lomba dengan deadline < 7 hari
#      c. Format digest message
#      d. Kirim & catat di sent_log dengan type='digest'

# Job 3: check_deadlines()
# Waktu: 23:00 UTC setiap hari (bersamaan dengan digest)
# Aksi:
#   1. Ambil lomba dengan deadline = hari_ini + 7 hari
#   2. Kirim reminder_7d ke subscriber yang belum menerima
#   3. Ambil lomba dengan deadline = hari_ini + 1 hari
#   4. Kirim reminder_1d ke subscriber yang belum menerima
```

---

## 10. Abstract Base Scraper

### File: `scrapers/base.py`

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

@dataclass
class RawCompetition:
    title: str
    url: str
    source: str
    description: Optional[str] = None
    deadline_raw: Optional[str] = None      # teks asli deadline dari sumber
    deadline: Optional[str] = None          # format: 'YYYY-MM-DD' setelah parse
    organizer: Optional[str] = None
    prize: Optional[str] = None
    image_url: Optional[str] = None
    eligibility: Optional[str] = None
    location_raw: Optional[str] = None     # teks asli lokasi dari sumber

class BaseScraper(ABC):
    SOURCE_NAME: str = ""

    @abstractmethod
    async def scrape(self) -> list[RawCompetition]:
        """Scrape sumber dan return list RawCompetition"""
        pass

    def parse_deadline(self, raw: str) -> Optional[str]:
        """
        Parse teks deadline ke format YYYY-MM-DD.
        Tangani format Indonesia: '15 Juni 2026', '15 Jun 2026', '2026-06-15'
        Return None jika tidak bisa di-parse.
        """
        pass
```

---

## 11. Implementasi Scraper Per Sumber

### `scrapers/devpost.py` — Playwright

```
URL: https://devpost.com/hackathons?challenge_type=all&sort_by=Deadline
Selector target:
  - Judul: h2.challenge-title atau a.challenge-title
  - URL: href dari card link
  - Deadline: span.submission-period atau div.deadline
  - Hadiah: div.prize-amount
  - Organizer: span.host-label
Pagination: ambil halaman 1 saja (max 20 lomba)
```

### `scrapers/kaggle.py` — httpx + BS4

```
URL: https://www.kaggle.com/competitions
Method: httpx GET dengan headers User-Agent browser
Selector: div.competition-item atau via JSON API endpoint jika tersedia
Target field: title, url, deadline, prize, description
```

### `scrapers/sinta.py` — httpx + BS4

```
URL: https://sinta.kemdikbud.go.id/journals
Fokus: Call for Paper yang aktif
Note: Site ini relatif stabil, gunakan httpx + BS4 cukup
```

### `scrapers/dicoding.py` — Playwright

```
URL: https://www.dicoding.com/events/all
Filter: ambil yang tipe 'competition' atau 'hackathon'
Selector: div.event-card atau sejenisnya
```

### `scrapers/lomba_info.py` — httpx + BS4

```
URL: https://lomba.info
Selector: div.entry-header atau artikel utama di homepage
Ambil 10 entry terbaru
```

### `scrapers/info_lomba.py` — httpx + BS4

```
URL: https://info-lomba.com
Struktur mirip blog/listing, ambil post terbaru
```

> **Catatan untuk AI Agent**: Selector CSS/XPath di atas adalah estimasi. Saat generate kode, implementasikan dengan mekanisme fallback: coba selector utama, jika gagal coba selector alternatif, jika tetap gagal log warning dan lanjutkan ke sumber berikutnya. Jangan crash seluruh proses karena satu scraper gagal.

---

## 12. Entry Point

### File: `main.py`

```python
# Urutan inisialisasi:
# 1. Load settings dari .env
# 2. Setup logging (ke file + stdout)
# 3. Init database (buat tabel jika belum ada, seed tags)
# 4. Init Telegram bot application (PTB)
# 5. Register semua handlers dari bot/handlers.py
# 6. Register semua callback handlers dari bot/callbacks.py
# 7. Init APScheduler
# 8. Register jobs dari scheduler/jobs.py
# 9. Start scheduler
# 10. Start bot polling (bot.run_polling())
```

---

## 13. Dependencies

### File: `requirements.txt`

```
python-telegram-bot==21.6
playwright==1.44.0
httpx==0.27.0
beautifulsoup4==4.12.3
apscheduler==3.10.4
python-dotenv==1.0.1
lxml==5.2.2
```

### Instalasi Playwright browsers

```bash
playwright install chromium
playwright install-deps chromium
```

---

## 14. Deployment: Railway

### File: `railway.toml`

```toml
[build]
builder = "nixpacks"
buildCommand = "pip install -r requirements.txt && playwright install chromium && playwright install-deps chromium"

[deploy]
startCommand = "python main.py"
restartPolicyType = "always"
```

### Environment Variables di Railway Dashboard

Set semua variabel dari `.env.example` di Railway dashboard. Khusus `DATABASE_PATH`, gunakan Railway persistent volume atau ganti ke SQLite di `/data/` yang di-mount.

---

## 15. Logging

### Konfigurasi logging di `main.py`

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.FileHandler('./logs/lombaradar.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
```

Log setiap event penting:
- Scraper mulai/selesai + jumlah lomba ditemukan
- Lomba baru berhasil disimpan
- Notifikasi berhasil dikirim
- Error pada scraper (WARNING, jangan ERROR agar tidak stop proses)
- Error pada bot (ERROR)

---

## 16. Error Handling — Aturan Wajib

1. **Scraper error → log WARNING, lanjutkan ke scraper berikutnya**. Satu scraper gagal tidak boleh menghentikan seluruh proses.
2. **Bot send error → log ERROR + retry 1x setelah 5 detik**. Jika masih gagal, catat di log dan lanjutkan.
3. **Database error → log ERROR + raise Exception** (ini critical, harus ditangani).
4. **Playwright timeout → log WARNING + return empty list** (bukan crash).
5. Semua fungsi async wajib dibungkus `try-except` minimal di level job scheduler.

---

## 17. Urutan Generate Kode oleh AI Agent

Ikuti urutan ini agar tidak ada circular import atau missing dependency:

```
Step 1:  config/settings.py
Step 2:  config/tags.py
Step 3:  db/models.py
Step 4:  db/migrations.py
Step 5:  db/database.py
Step 6:  core/tagger.py
Step 7:  core/location_detector.py
Step 8:  core/deduplicator.py
Step 9:  scrapers/base.py
Step 10: scrapers/devpost.py
Step 11: scrapers/kaggle.py
Step 12: scrapers/sinta.py
Step 13: scrapers/dicoding.py
Step 14: scrapers/lomba_info.py
Step 15: scrapers/info_lomba.py
Step 16: core/competition_manager.py
Step 17: notifier/formatter.py
Step 18: notifier/sender.py
Step 19: bot/keyboards.py
Step 20: bot/callbacks.py
Step 21: bot/handlers.py
Step 22: scheduler/jobs.py
Step 23: main.py
Step 24: requirements.txt
Step 25: railway.toml
Step 26: .env.example
Step 27: .gitignore
Step 28: tests/test_tagger.py
Step 29: tests/test_deduplicator.py
Step 30: tests/test_formatter.py
```

---

## 18. Hal yang DILARANG (Anti-Halusinasi)

- **DILARANG** menggunakan library selain yang ada di `requirements.txt`
- **DILARANG** hardcode bot token, chat ID, atau credential apapun
- **DILARANG** menggunakan `asyncio.run()` di dalam fungsi async (gunakan `await`)
- **DILARANG** membuat file diluar struktur folder yang sudah ditentukan
- **DILARANG** menggunakan `threading` — semua concurrency via `async/await`
- **DILARANG** menggunakan deprecated API PTB v13 (kita pakai PTB v21)
- **DILARANG** menyimpan state di memory global — semua state di database
- **DILARANG** menggunakan `requests` library — gunakan `httpx` (async)
