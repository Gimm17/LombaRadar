"""
tests/test_formatter.py — Unit tests untuk notifier/formatter.py.
"""

import unittest
from notifier.formatter import (
    escape_md,
    format_deadline_display,
    format_deadline_short,
    format_location,
    format_tag_line,
    format_new_competition,
)


class TestEscapeMd(unittest.TestCase):
    """Test escape MarkdownV2."""

    def test_special_chars(self) -> None:
        """Test escape karakter spesial."""
        result = escape_md("Hello_World*Test")
        self.assertIn("\\_", result)
        self.assertIn("\\*", result)

    def test_dots_escaped(self) -> None:
        """Test titik di-escape."""
        result = escape_md("Rp 50.000.000")
        self.assertIn("\\.", result)

    def test_empty_string(self) -> None:
        """Test string kosong."""
        result = escape_md("")
        self.assertEqual(result, "")

    def test_none_input(self) -> None:
        """Test None input."""
        result = escape_md(None)
        self.assertEqual(result, "")

    def test_parentheses(self) -> None:
        """Test tanda kurung di-escape."""
        result = escape_md("(test)")
        self.assertIn("\\(", result)
        self.assertIn("\\)", result)


class TestFormatDeadlineDisplay(unittest.TestCase):
    """Test format deadline display."""

    def test_valid_date(self) -> None:
        """Test format tanggal valid."""
        result = format_deadline_display("2026-06-15")
        self.assertEqual(result, "15 Juni 2026")

    def test_none(self) -> None:
        """Test None deadline."""
        result = format_deadline_display(None)
        self.assertEqual(result, "Tidak diketahui")

    def test_invalid_date(self) -> None:
        """Test format tanggal invalid — fallback ke raw."""
        result = format_deadline_display("invalid-date")
        self.assertEqual(result, "invalid-date")


class TestFormatDeadlineShort(unittest.TestCase):
    """Test format deadline pendek."""

    def test_valid_date(self) -> None:
        """Test format pendek."""
        result = format_deadline_short("2026-06-15")
        self.assertEqual(result, "15 Jun")

    def test_none(self) -> None:
        """Test None."""
        result = format_deadline_short(None)
        self.assertEqual(result, "TBD")


class TestFormatLocation(unittest.TestCase):
    """Test format lokasi."""

    def test_online(self) -> None:
        """Test lokasi online."""
        result = format_location("online")
        self.assertEqual(result, "🌐 Online")

    def test_onsite_with_detail(self) -> None:
        """Test lokasi onsite dengan detail."""
        result = format_location("onsite", "Jakarta")
        self.assertIn("📍 Onsite", result)
        self.assertIn("Jakarta", result)

    def test_hybrid(self) -> None:
        """Test lokasi hybrid."""
        result = format_location("hybrid", "Bandung")
        self.assertIn("🔀 Hybrid", result)

    def test_default_online(self) -> None:
        """Test default ke online."""
        result = format_location("unknown")
        self.assertEqual(result, "🌐 Online")


class TestFormatTagLine(unittest.TestCase):
    """Test format baris tag."""

    def test_single_tag(self) -> None:
        """Test satu tag."""
        tags = [{"name": "AI/ML", "emoji": "🤖"}]
        result = format_tag_line(tags)
        self.assertIn("🤖", result)

    def test_max_3_tags(self) -> None:
        """Test maks 3 tag ditampilkan."""
        tags = [
            {"name": "AI/ML", "emoji": "🤖"},
            {"name": "Web Dev", "emoji": "🌐"},
            {"name": "Datathon", "emoji": "📊"},
            {"name": "Mobile", "emoji": "📱"},
        ]
        result = format_tag_line(tags)
        self.assertNotIn("📱", result)

    def test_empty_tags(self) -> None:
        """Test list tag kosong."""
        result = format_tag_line([])
        self.assertEqual(result, "")


class TestFormatNewCompetition(unittest.TestCase):
    """Test format pesan lomba baru."""

    def test_basic_format(self) -> None:
        """Test format dasar pesan lomba baru."""
        comp = {
            "title": "AI Challenge 2026",
            "organizer": "Dicoding",
            "source": "dicoding",
            "prize": "Rp 50.000.000",
            "deadline": "2026-06-15",
            "eligibility": "Mahasiswa",
            "location_type": "online",
            "location_detail": "",
            "url": "https://example.com",
        }
        tags = [{"name": "AI/ML", "emoji": "🤖"}]
        result = format_new_competition(comp, tags)
        self.assertIn("Lomba Baru Terdeteksi", result)
        self.assertIn("AI Challenge 2026", result)


if __name__ == "__main__":
    unittest.main()
