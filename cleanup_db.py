"""Cleanup script — hapus lomba SMP/SMA/tahun lama dari DB."""
import sqlite3

db = sqlite3.connect("./data/lombaradar.db")

# Hapus lomba SMP/SMA only
c1 = db.execute("""
    DELETE FROM competitions 
    WHERE (
        LOWER(title) LIKE '%tingkat smp%' 
        OR LOWER(title) LIKE '%tingkat sma%'
        OR LOWER(title) LIKE '%sma sederajat%'
        OR LOWER(title) LIKE '%smp sederajat%'
        OR LOWER(title) LIKE '%siswa sma%'
        OR LOWER(title) LIKE '%siswa smp%'
    )
    AND LOWER(title) NOT LIKE '%mahasiswa%'
    AND LOWER(title) NOT LIKE '%umum%'
""")
print(f"Deleted SMP/SMA: {c1.rowcount}")

# Hapus lomba tahun lama (2023, 2024)
c2 = db.execute("""
    DELETE FROM competitions 
    WHERE (title LIKE '% 2023%' OR title LIKE '% 2024%' OR title LIKE '% 2022%')
    AND title NOT LIKE '% 2026%'
    AND title NOT LIKE '% 2025%'
""")
print(f"Deleted old year: {c2.rowcount}")

# Hapus lomba EJAVEC 2025 (sudah lewat)
c3 = db.execute("""
    DELETE FROM competitions 
    WHERE title LIKE '%EJAVEC%2025%'
""")
print(f"Deleted EJAVEC 2025: {c3.rowcount}")

db.commit()

total = db.execute("SELECT COUNT(*) FROM competitions").fetchone()[0]
print(f"\nRemaining: {total} competitions")

# Show what's left
rows = db.execute("SELECT source, title FROM competitions ORDER BY source, title").fetchall()
for r in rows:
    print(f"  {r[0]:15s} | {r[1][:60]}")

db.close()
