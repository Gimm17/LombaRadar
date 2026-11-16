# NOTIFICATION_SPEC.md — Format Notifikasi LombaRadar

## Aturan Umum

- Semua pesan menggunakan **Telegram MarkdownV2** (bukan Markdown biasa)
- Semua teks dalam **Bahasa Indonesia**
- Karakter yang wajib di-escape di MarkdownV2: `_ * [ ] ( ) ~ \` > # + - = | { } . !`
- Implementasikan helper `escape_md(text: str) -> str` untuk semua input dinamis
- Gunakan `parse_mode=ParseMode.MARKDOWN_V2` di semua `send_message()` call
- Inline keyboard menggunakan `InlineKeyboardMarkup` dari PTB v21

---

## Tipe Pesan & Trigger

| Tipe | Trigger | Waktu Kirim |
|---|---|---|
| `new` | Lomba baru ditemukan scraper | Real-time saat scrape berjalan |
| `reminder_7d` | deadline lomba = hari ini + 7 | 07.00 WITA setiap hari |
| `reminder_1d` | deadline lomba = hari ini + 1 | 07.00 WITA setiap hari |
| `digest` | Harian | 07.00 WITA setiap hari |

---

## Tipe 1: `new` — Lomba Baru

### Template

```
🏆 *Lomba Baru Terdeteksi\!*
━━━━━━━━━━━━━━━━━━
📌 *{title}*
🏢 _{organizer}_ · {source_label}

🏷 {tag_line}
━━━━━━━━━━━━━━━━━━
💰 Hadiah   : {prize}
📅 Deadline : {deadline_display}
👥 Peserta  : {eligibility}
📍 Lokasi   : {location_display}
━━━━━━━━━━━━━━━━━━
```

### Inline Keyboard

```python
[
    [InlineKeyboardButton("Daftar Sekarang 🔗", url=competition.url)],
    [
        InlineKeyboardButton("Simpan 🔖", callback_data=f"save_{competition.id}"),
        InlineKeyboardButton("Bagikan 📤", callback_data=f"share_{competition.id}"),
    ]
]
```

### Contoh Output Final

```
🏆 *Lomba Baru Terdeteksi\!*
━━━━━━━━━━━━━━━━━━
📌 *AI Innovation Challenge 2026*
🏢 _Dicoding_ · Dicoding Events

🏷 🤖 AI/ML  📊 Datathon
━━━━━━━━━━━━━━━━━━
💰 Hadiah   : Rp 50\.000\.000 \+ sertifikat
📅 Deadline : 15 Juni 2026
👥 Peserta  : Mahasiswa S1/D4/S2
📍 Lokasi   : 🌐 Online
━━━━━━━━━━━━━━━━━━
```

---

## Tipe 2: `reminder_7d` — Reminder 7 Hari

### Template

```
⚠️ *Deadline 7 Hari Lagi\!*
━━━━━━━━━━━━━━━━━━
📌 *{title}*
🏢 _{organizer}_

🏷 {tag_line}
━━━━━━━━━━━━━━━━━━
📅 Deadline : *{deadline_display}* \(7 hari lagi\)
📍 Lokasi   : {location_display}
━━━━━━━━━━━━━━━━━━
```

### Inline Keyboard

```python
[
    [InlineKeyboardButton("Lihat Detail 👀", url=competition.url)],
    [InlineKeyboardButton("Submit Sekarang ✅", url=competition.url)],
]
```

---

## Tipe 3: `reminder_1d` — Reminder Besok

### Template

```
🚨 *Deadline Besok\!*
━━━━━━━━━━━━━━━━━━
📌 *{title}*
🏢 _{organizer}_

🏷 {tag_line}
━━━━━━━━━━━━━━━━━━
📅 Deadline : *{deadline_display}* \(BESOK\!\)
📍 Lokasi   : {location_display}
━━━━━━━━━━━━━━━━━━
```

### Inline Keyboard

```python
[
    [InlineKeyboardButton("Daftar Sekarang ⚡", url=competition.url)],
]
```

---

## Tipe 4: `digest` — Daily Digest

### Template

```
📋 *Ringkasan Lomba — {tanggal}*
━━━━━━━━━━━━━━━━━━
✨ *{n} Lomba Baru:*

{nomor}\. *{title}* — {tag_singkat} · {deadline_singkat}
{nomor}\. *{title}* — {tag_singkat} · {deadline_singkat}
\.\.\. (max 5 item)

⏰ *Deadline Minggu Ini:*

‼️ {title} — {n} hari lagi
‼️ {title} — {n} hari lagi
\.\.\. (max 3 item)

_Gunakan /lomba untuk daftar lengkap_
```

### Inline Keyboard

```python
[
    [
        InlineKeyboardButton("Lihat Semua 📋", callback_data="list_all"),
        InlineKeyboardButton("Filter Kategori 🏷", callback_data="show_filter"),
    ]
]
```

### Aturan Digest

- Maksimal 5 lomba baru ditampilkan dalam digest
- Maksimal 3 lomba deadline minggu ini ditampilkan
- Jika tidak ada lomba baru → tidak kirim digest (skip)
- Jika tidak ada deadline minggu ini → hapus bagian "Deadline Minggu Ini"
- Format `deadline_singkat`: "15 Jun" (bukan full date)
- Format `tanggal` di header: "Rabu, 29 Apr 2026"

---

## Helper: `format_location()`

```python
def format_location(location_type: str, location_detail: str = "") -> str:
    """
    Return string lokasi yang sudah siap untuk ditampilkan di pesan.
    Output sudah di-escape untuk MarkdownV2.
    """
    if location_type == 'online':
        return '🌐 Online'
    elif location_type == 'onsite':
        detail = f' — {escape_md(location_detail)}' if location_detail else ''
        return f'📍 Onsite{detail}'
    elif location_type == 'hybrid':
        detail = f' — {escape_md(location_detail)}' if location_detail else ''
        return f'🔀 Hybrid{detail}'
    return '🌐 Online'
```

---

## Helper: `format_tag_line()`

```python
def format_tag_line(tags: list[dict]) -> str:
    """
    tags = list of {'name': 'AI/ML', 'emoji': '🤖'}
    Return: '🤖 AI/ML  📊 Datathon'
    Max 3 tag ditampilkan.
    """
    return '  '.join(f"{t['emoji']} {escape_md(t['name'])}" for t in tags[:3])
```

---

## Helper: `format_deadline_display()`

```python
def format_deadline_display(deadline: str | None) -> str:
    """
    deadline: 'YYYY-MM-DD' atau None
    Return: '15 Juni 2026' atau 'Tidak diketahui'
    """
    MONTH_ID = {
        1: 'Januari', 2: 'Februari', 3: 'Maret', 4: 'April',
        5: 'Mei', 6: 'Juni', 7: 'Juli', 8: 'Agustus',
        9: 'September', 10: 'Oktober', 11: 'November', 12: 'Desember'
    }
    if not deadline:
        return 'Tidak diketahui'
    try:
        from datetime import date
        d = date.fromisoformat(deadline)
        return f"{d.day} {MONTH_ID[d.month]} {d.year}"
    except:
        return deadline  # fallback ke raw jika parse gagal
```

---

## Helper: `escape_md()`

```python
import re

def escape_md(text: str) -> str:
    """
    Escape semua karakter spesial MarkdownV2 Telegram.
    Wajib digunakan untuk SEMUA input dinamis sebelum disisipkan ke template.
    """
    if not text:
        return ''
    escape_chars = r'\_*[]()~`>#+-=|{}.!'
    return re.sub(f'([{re.escape(escape_chars)}])', r'\\\1', str(text))
```

---

## Source Label Mapping

```python
SOURCE_LABELS = {
    'devpost':    'Devpost',
    'kaggle':     'Kaggle',
    'sinta':      'SINTA Dikti',
    'dicoding':   'Dicoding Events',
    'lomba_info': 'Lomba\.info',
    'info_lomba': 'Info Lomba',
}
```

---

## Bot Reply Messages (Command Responses)

### `/start`

```
Halo\! 👋 Selamat datang di *LombaRadar*\!

Saya akan membantu kamu menemukan lomba, hackathon, datathon, dan call for paper terbaru\.

*Command yang tersedia:*
/lomba — 5 lomba terbaru
/filter \[tag\] — filter by kategori
/subscribe \[tag\] — langganan kategori
/unsubscribe \[tag\] — berhenti langganan
/deadline — lomba mendekati deadline
/tags — daftar semua kategori
/help — bantuan lengkap
```

### `/tags`

```
*Kategori Lomba Tersedia:*
━━━━━━━━━━━━━━━━━━
🤖 AI/ML → /filter ai\_ml
🌐 Web Dev → /filter web\_dev
📊 Datathon → /filter datathon
📄 Paper/Jurnal → /filter paper
🗺️ GIS → /filter gis
📱 Mobile Dev → /filter mobile
🔐 Cybersecurity → /filter cyber
🏆 Umum → /filter umum
━━━━━━━━━━━━━━━━━━
_Gunakan /subscribe \[tag\] untuk langganan kategori tertentu_
```

### Jika tidak ada lomba ditemukan

```
Belum ada lomba baru untuk kategori ini\.
Coba lagi nanti atau gunakan /lomba untuk semua kategori\.
```
