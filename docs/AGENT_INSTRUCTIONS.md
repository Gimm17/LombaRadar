# AGENT_INSTRUCTIONS.md — Instruksi untuk AI Agent

> Baca dokumen ini **pertama kali** sebelum membaca dokumen lain.
> Dokumen ini adalah panduan meta tentang bagaimana AI Agent harus beroperasi.

---

## Kamu adalah siapa?

Kamu adalah AI Agent yang bertugas men-generate **seluruh codebase LombaRadar** dari nol.
LombaRadar adalah Telegram bot Python yang mengagregasi informasi lomba dan mengirim notifikasi otomatis.

---

## Dokumen yang Harus Kamu Baca Sebelum Generate Kode

Baca semua dokumen berikut secara berurutan sebelum mulai menulis satu baris kode pun:

1. `CONTEXT.md` — apa itu LombaRadar, tujuan, dan tech stack
2. `IMPLEMENTATION_PLAN.md` — struktur folder, skema DB, logic, urutan generate
3. `DATABASE_SCHEMA.md` — detail lengkap skema database + query penting
4. `NOTIFICATION_SPEC.md` — format pesan Telegram yang tepat + helper functions
5. `SCRAPER_GUIDE.md` — pola implementasi scraper + base class

---

## Urutan Kerja

**Langkah 1: Baca semua dokumen**
Jangan skip. Setiap dokumen berisi detail yang saling melengkapi.

**Langkah 2: Generate kode sesuai urutan di IMPLEMENTATION_PLAN.md Section 17**
Ikuti urutan Step 1 sampai Step 30 tanpa melewati step.

**Langkah 3: Setelah semua file selesai, buat README.md**
README harus berisi: deskripsi singkat, cara setup, cara run, daftar command bot.

---

## Aturan Wajib (Jangan Dilanggar)

### Tentang Kode

- Gunakan **Python 3.11+** syntax
- Semua fungsi I/O harus **async** (`async def`, `await`)
- Gunakan **type hints** di semua function signature
- Gunakan **dataclass** atau **TypedDict** untuk struktur data, bukan dict mentah
- Setiap file harus punya **docstring** di bagian atas yang menjelaskan tujuan file
- Setiap fungsi harus punya **docstring** minimal satu baris

### Tentang Dependencies

- **Hanya** gunakan library yang ada di `requirements.txt`
- Jangan tambah library baru tanpa konfirmasi
- Jangan gunakan `requests` — gunakan `httpx`
- Jangan gunakan threading — gunakan async/await
- Jangan gunakan PTB versi lama (v13) — kita pakai PTB v21

### Tentang Keamanan

- **Tidak ada hardcode credential** — semua via `.env` dan `config/settings.py`
- Jangan print token atau credential di log
- Gunakan `os.getenv()` dengan default value yang aman

### Tentang Database

- Semua query SQLite menggunakan **parameterized query** (`?` placeholder)
- Jangan pernah string concatenation untuk SQL query (SQL injection risk)
- Selalu close connection setelah selesai, atau gunakan context manager `with`

### Tentang Error Handling

- **Scraper gagal → return `[]`**, bukan raise exception
- **Bot send gagal → log error, retry 1x**, bukan crash
- **Database error → raise**, ini critical
- Semua async job dibungkus `try-except` di level terluar

### Tentang Format Pesan Telegram

- Selalu gunakan `ParseMode.MARKDOWN_V2`
- Selalu escape karakter spesial dengan `escape_md()` sebelum insert ke template
- Jangan gunakan parse_mode lain (Markdown v1 deprecated, HTML berbeda)

---

## Yang Boleh Kamu Improvisasi

- Nama variabel internal (asal deskriptif)
- Komentar kode (dalam Bahasa Indonesia atau Inggris)
- Implementasi detail fungsi `parse_deadline()` selama output tetap YYYY-MM-DD
- Selector CSS fallback di scraper (karena HTML situs bisa berbeda)
- Format log message (asal informatif)

---

## Yang TIDAK Boleh Kamu Improvisasi

- Nama file dan nama folder (harus persis seperti di IMPLEMENTATION_PLAN.md)
- Nama tabel dan kolom database (harus persis seperti di DATABASE_SCHEMA.md)
- Format pesan Telegram (harus sesuai NOTIFICATION_SPEC.md)
- Nama command bot (harus sesuai IMPLEMENTATION_PLAN.md Section 8)
- Nilai enum untuk kolom `status`, `location_type`, `message_type`, `chat_type`
- Nilai slug tag (harus persis seperti di DATABASE_SCHEMA.md)

---

## Checklist Sebelum Selesai

Sebelum menyatakan kode selesai, verifikasi:

- [ ] Semua 30 file di urutan generate sudah dibuat
- [ ] Tidak ada `import` yang gagal karena file tidak ada
- [ ] Tidak ada hardcode credential
- [ ] Semua `async def` sudah benar (tidak ada fungsi sync yang di-await)
- [ ] `requirements.txt` berisi semua dependency yang dipakai
- [ ] `.env.example` berisi semua variable yang dibutuhkan
- [ ] `railway.toml` valid untuk deploy di Railway
- [ ] `README.md` sudah dibuat dengan instruksi setup yang jelas

---

## Jika Menemukan Ambiguitas

Jika ada spesifikasi yang tidak jelas atau konflik antar dokumen:

1. **Prioritas**: `IMPLEMENTATION_PLAN.md` > `DATABASE_SCHEMA.md` > `NOTIFICATION_SPEC.md` > `SCRAPER_GUIDE.md`
2. Untuk hal yang tidak disebutkan di mana pun → pilih implementasi yang paling sederhana dan maintainable
3. Tulis komentar `# NOTE: ...` di kode untuk menandai keputusan implementasi yang kamu buat sendiri
