"""
tests/test_deduplicator.py — Unit tests untuk core/deduplicator.py.
"""

import unittest
from core.deduplicator import generate_id


class TestGenerateId(unittest.TestCase):
    """Test ID generation dari URL."""

    def test_basic_url(self) -> None:
        """Test generate ID dari URL biasa."""
        result = generate_id("https://example.com/competition")
        self.assertIsInstance(result, str)
        self.assertEqual(len(result), 12)

    def test_consistent(self) -> None:
        """Test konsistensi — URL sama harus menghasilkan ID sama."""
        url = "https://devpost.com/hackathon/1234"
        id1 = generate_id(url)
        id2 = generate_id(url)
        self.assertEqual(id1, id2)

    def test_case_insensitive(self) -> None:
        """Test case insensitive — URL beda case harus sama."""
        id1 = generate_id("https://Example.com/Test")
        id2 = generate_id("https://example.com/test")
        self.assertEqual(id1, id2)

    def test_whitespace_stripped(self) -> None:
        """Test whitespace di-strip."""
        id1 = generate_id("https://example.com/test")
        id2 = generate_id("  https://example.com/test  ")
        self.assertEqual(id1, id2)

    def test_different_urls(self) -> None:
        """Test URL berbeda menghasilkan ID berbeda."""
        id1 = generate_id("https://example.com/a")
        id2 = generate_id("https://example.com/b")
        self.assertNotEqual(id1, id2)

    def test_hex_chars_only(self) -> None:
        """Test bahwa ID hanya berisi karakter hex."""
        result = generate_id("https://example.com/test")
        self.assertTrue(all(c in "0123456789abcdef" for c in result))


if __name__ == "__main__":
    unittest.main()
