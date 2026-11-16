# CONTEXT.md — LombaRadar Project

## Apa itu LombaRadar?

LombaRadar adalah **Telegram bot otomatis** yang mengagregasi informasi lomba, kompetisi, hackathon, datathon, call for paper, dan publikasi jurnal dari berbagai platform, lalu mendistribusikannya ke pengguna via Telegram secara terjadwal dan real-time.

Bot ini dibangun untuk memecahkan satu masalah nyata: mahasiswa dan peneliti muda Indonesia harus mencari informasi lomba secara manual satu per satu di berbagai platform, yang sangat tidak efisien.

---

## Siapa yang Membangun Ini?

Proyek ini dikembangkan oleh **Gimm** (Nvia), founder dari **Gimora Digital** (gimoradigital.id), sebuah IT agency berbasis di Sulawesi Tengah, Indonesia, yang melayani UMKM, instansi pemerintah, dan klien akademik.

LombaRadar merupakan **micro-product internal Gimora** yang juga berpotensi dikembangkan menjadi layanan publik untuk komunitas mahasiswa Indonesia Timur.

---

## Target Pengguna

- Mahasiswa S1/D4/S2/S3 yang aktif mencari lomba dan kompetisi
- Peneliti muda yang membutuhkan info call for paper dan publikasi jurnal
- Komunitas developer yang mencari hackathon dan datathon
- Dosen/akademisi yang memantau event ilmiah

---

## Tujuan Produk

1. **Agregasi otomatis** — scrape 5–10 sumber lomba terpercaya secara terjadwal
2. **Klasifikasi cerdas** — tagging otomatis berdasarkan kategori (AI/ML, Web, Data, Paper, GIS, dll)
3. **Distribusi tepat sasaran** — kirim notifikasi hanya ke subscriber yang relevan dengan preferensi tag-nya
4. **Anti-duplikat** — sistem `sent_log` memastikan satu lomba hanya dikirim sekali per user per tipe pesan
5. **Multi-format notifikasi** — lomba baru, reminder 7 hari, reminder 1 hari, daily digest

---

## Tech Stack yang Digunakan

| Komponen | Teknologi |
|---|---|
| Language | Python 3.11+ |
| Scraping (JS sites) | Playwright (async) |
| Scraping (static) | BeautifulSoup4 + httpx |
| Telegram Bot | python-telegram-bot v21 (PTB) |
| Database | SQLite (fase awal) → PostgreSQL (scale) |
| Scheduler | APScheduler 3.x |
| Deployment | Railway.app |
| Environment | python-dotenv |

---

## Sumber Data (Target Scraping)

| Sumber | URL | Tipe | Method |
|---|---|---|---|
| Devpost | devpost.com/hackathons | Hackathon | Playwright |
| Kaggle | kaggle.com/competitions | Datathon | httpx + BS4 |
| SINTA Dikti | sinta.kemdikbud.go.id/journals | Paper/Jurnal | httpx + BS4 |
| Dicoding Events | dicoding.com/events | Dev Events | Playwright |
| lomba.info | lomba.info | Umum | httpx + BS4 |
| info-lomba.com | info-lomba.com | Umum | httpx + BS4 |

---

## Batasan & Asumsi

- Fase v1.0 hanya mendukung SQLite, belum PostgreSQL
- Scraping dilakukan tiap **6 jam** via APScheduler
- Daily digest dikirim jam **07.00 WITA** (UTC+8)
- Reminder dikirim jam **07.00 WITA** pada hari H-7 dan H-1 deadline
- Semua teks notifikasi menggunakan **Bahasa Indonesia**
- Bot menggunakan **Telegram MarkdownV2** untuk formatting pesan
- Environment variable wajib di `.env`, tidak ada hardcode credential

---

## Struktur Proyek (Overview)

```
lombaradar/
├── bot/                  # Telegram bot handlers & commands
├── scrapers/             # Scraper per sumber
├── core/                 # Business logic (filter, dedup, tagging)
├── db/                   # Database models & migrations
├── notifier/             # Notification formatter & sender
├── scheduler/            # APScheduler jobs
├── config/               # Settings & constants
├── tests/                # Unit tests
└── main.py               # Entry point
```

Detail lengkap struktur folder ada di `IMPLEMENTATION_PLAN.md`.

---

## Status Proyek

**Fase saat ini: v0.1 — Initial Build**

Belum ada kode yang ditulis. AI Agent bertugas men-generate seluruh codebase dari nol berdasarkan spesifikasi di dokumen ini dan `IMPLEMENTATION_PLAN.md`.
