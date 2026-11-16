# DATABASE_SCHEMA.md — LombaRadar

## Overview

LombaRadar menggunakan **SQLite** pada fase v1.0. Database file disimpan di path yang dikonfigurasi via `DATABASE_PATH` di `.env`.

Seluruh DDL ada di `db/migrations.py` dan dijalankan otomatis saat `main.py` start.

---

## Entity Relationship

```
competitions ──< competition_tags >── tags
                                       │
subscribers  ──< subscriber_tags  >───┘
     │
     └──< sent_log >── competitions
```

---

## Tabel: `competitions`

| Kolom | Tipe | Constraint | Keterangan |
|---|---|---|---|
| `id` | TEXT | PK | md5(url)[:12] |
| `title` | TEXT | NOT NULL | Judul lomba |
| `source` | TEXT | NOT NULL | Nama scraper: devpost, kaggle, sinta, dicoding, lomba_info, info_lomba |
| `url` | TEXT | UNIQUE | URL halaman lomba |
| `description` | TEXT | | Deskripsi singkat |
| `deadline` | TEXT | | Format YYYY-MM-DD, NULL jika tidak diketahui |
| `deadline_raw` | TEXT | | Teks deadline asli dari sumber |
| `organizer` | TEXT | | Nama penyelenggara |
| `prize` | TEXT | | Informasi hadiah |
| `image_url` | TEXT | | URL gambar/thumbnail lomba |
| `eligibility` | TEXT | | Kriteria peserta |
| `location_type` | TEXT | DEFAULT 'online' | Nilai: 'online', 'onsite', 'hybrid' |
| `location_detail` | TEXT | | Nama kota/tempat jika onsite/hybrid |
| `status` | TEXT | DEFAULT 'open' | Nilai: 'open', 'closing_soon', 'closed' |
| `scraped_at` | DATETIME | DEFAULT NOW | Waktu pertama kali di-scrape |
| `updated_at` | DATETIME | DEFAULT NOW | Waktu terakhir data diupdate |

### Index yang Direkomendasikan

```sql
CREATE INDEX IF NOT EXISTS idx_competitions_deadline ON competitions(deadline);
CREATE INDEX IF NOT EXISTS idx_competitions_status ON competitions(status);
CREATE INDEX IF NOT EXISTS idx_competitions_source ON competitions(source);
CREATE INDEX IF NOT EXISTS idx_competitions_scraped_at ON competitions(scraped_at DESC);
```

---

## Tabel: `tags`

| Kolom | Tipe | Constraint | Keterangan |
|---|---|---|---|
| `id` | INTEGER | PK AUTOINCREMENT | |
| `name` | TEXT | UNIQUE NOT NULL | Display name: 'AI/ML', 'Web Dev', dll |
| `slug` | TEXT | UNIQUE NOT NULL | Slug untuk command: 'ai_ml', 'web_dev', dll |
| `color_hex` | TEXT | NOT NULL | Hex color untuk badge |
| `emoji` | TEXT | | Emoji opsional untuk display di Telegram |

### Data Seed

| id | name | slug | color_hex | emoji |
|---|---|---|---|---|
| 1 | AI/ML | ai_ml | #7F77DD | 🤖 |
| 2 | Web Dev | web_dev | #1D9E75 | 🌐 |
| 3 | Datathon | datathon | #EF9F27 | 📊 |
| 4 | Paper/Jurnal | paper | #D85A30 | 📄 |
| 5 | GIS | gis | #378ADD | 🗺️ |
| 6 | Mobile Dev | mobile | #D4537E | 📱 |
| 7 | Cybersecurity | cyber | #A32D2D | 🔐 |
| 8 | Umum | umum | #888780 | 🏆 |

---

## Tabel: `competition_tags`

| Kolom | Tipe | Constraint | Keterangan |
|---|---|---|---|
| `competition_id` | TEXT | FK → competitions.id | |
| `tag_id` | INTEGER | FK → tags.id | |
| | | PK(competition_id, tag_id) | Composite PK |

---

## Tabel: `subscribers`

| Kolom | Tipe | Constraint | Keterangan |
|---|---|---|---|
| `id` | INTEGER | PK AUTOINCREMENT | |
| `telegram_chat_id` | BIGINT | UNIQUE NOT NULL | Chat ID Telegram |
| `chat_type` | TEXT | NOT NULL | Nilai: 'private', 'group', 'channel' |
| `chat_title` | TEXT | | Nama group/channel, NULL untuk private |
| `is_active` | INTEGER | DEFAULT 1 | 1=aktif, 0=unsubscribe |
| `joined_at` | DATETIME | DEFAULT NOW | |
| `last_active_at` | DATETIME | DEFAULT NOW | Update tiap user pakai command |

---

## Tabel: `subscriber_tags`

| Kolom | Tipe | Constraint | Keterangan |
|---|---|---|---|
| `subscriber_id` | INTEGER | FK → subscribers.id | |
| `tag_id` | INTEGER | FK → tags.id | |
| | | PK(subscriber_id, tag_id) | Composite PK |

**Aturan penting**: Jika seorang subscriber tidak punya record di `subscriber_tags`, artinya dia subscribe ke **semua tag** (receive all). Filter per-tag hanya berlaku jika ada minimal 1 record di tabel ini.

---

## Tabel: `sent_log`

| Kolom | Tipe | Constraint | Keterangan |
|---|---|---|---|
| `id` | INTEGER | PK AUTOINCREMENT | |
| `competition_id` | TEXT | FK → competitions.id | |
| `telegram_chat_id` | BIGINT | NOT NULL | |
| `message_type` | TEXT | NOT NULL | Nilai: 'new', 'reminder_7d', 'reminder_1d', 'digest' |
| `sent_at` | DATETIME | DEFAULT NOW | |
| | | UNIQUE(competition_id, telegram_chat_id, message_type) | Anti-duplikat |

### Index

```sql
CREATE INDEX IF NOT EXISTS idx_sent_log_chat ON sent_log(telegram_chat_id);
CREATE INDEX IF NOT EXISTS idx_sent_log_comp ON sent_log(competition_id);
```

---

## Query Penting

### Ambil lomba yang belum dikirim ke subscriber tertentu

```sql
SELECT c.*
FROM competitions c
WHERE c.id NOT IN (
    SELECT competition_id FROM sent_log
    WHERE telegram_chat_id = ? AND message_type = 'new'
)
AND c.status = 'open'
ORDER BY c.scraped_at DESC
LIMIT 10;
```

### Ambil lomba dengan deadline mendekati (untuk reminder)

```sql
-- Deadline 7 hari lagi
SELECT c.*
FROM competitions c
WHERE c.deadline = date('now', '+7 days')
AND c.id NOT IN (
    SELECT competition_id FROM sent_log
    WHERE telegram_chat_id = ? AND message_type = 'reminder_7d'
);

-- Deadline besok
SELECT c.*
FROM competitions c
WHERE c.deadline = date('now', '+1 day')
AND c.id NOT IN (
    SELECT competition_id FROM sent_log
    WHERE telegram_chat_id = ? AND message_type = 'reminder_1d'
);
```

### Ambil lomba berdasarkan tag untuk subscriber

```sql
SELECT DISTINCT c.*
FROM competitions c
JOIN competition_tags ct ON c.id = ct.competition_id
JOIN tags t ON ct.tag_id = t.id
WHERE t.slug = ?
AND c.status = 'open'
ORDER BY c.deadline ASC NULLS LAST;
```

### Update status lomba berdasarkan deadline

```sql
-- Jalankan bersamaan dengan job scheduler harian
UPDATE competitions
SET status = CASE
    WHEN deadline IS NULL THEN 'open'
    WHEN deadline < date('now') THEN 'closed'
    WHEN deadline <= date('now', '+7 days') THEN 'closing_soon'
    ELSE 'open'
END,
updated_at = CURRENT_TIMESTAMP;
```
