"""
tests/test_tagger.py — Unit tests untuk core/tagger.py.
"""

import unittest
from core.tagger import auto_tag


class TestAutoTag(unittest.TestCase):
    """Test auto-tagging berdasarkan keyword matching."""

    def test_ai_ml_keywords(self) -> None:
        """Test deteksi tag AI/ML dari judul."""
        result = auto_tag("Machine Learning Competition 2026")
        self.assertIn("ai_ml", result)

    def test_web_dev_keywords(self) -> None:
        """Test deteksi tag Web Dev."""
        result = auto_tag("Hackathon Web Development React")
        self.assertIn("web_dev", result)

    def test_datathon_keywords(self) -> None:
        """Test deteksi tag Datathon."""
        result = auto_tag("Kaggle Data Competition Challenge")
        self.assertIn("datathon", result)

    def test_paper_keywords(self) -> None:
        """Test deteksi tag Paper/Jurnal."""
        result = auto_tag("Call for Paper Seminar Nasional")
        self.assertIn("paper", result)

    def test_gis_keywords(self) -> None:
        """Test deteksi tag GIS."""
        result = auto_tag("Kompetisi Pemetaan Geospasial")
        self.assertIn("gis", result)

    def test_mobile_keywords(self) -> None:
        """Test deteksi tag Mobile Dev."""
        result = auto_tag("Flutter Mobile App Competition")
        self.assertIn("mobile", result)

    def test_cyber_keywords(self) -> None:
        """Test deteksi tag Cybersecurity."""
        result = auto_tag("CTF Capture the Flag Hacking")
        self.assertIn("cyber", result)

    def test_default_umum(self) -> None:
        """Test default ke 'umum' jika tidak ada keyword match."""
        result = auto_tag("Lomba Menyanyi Anak-anak")
        self.assertEqual(result, ["umum"])

    def test_max_3_tags(self) -> None:
        """Test jumlah tag maksimal 3."""
        result = auto_tag(
            "AI Machine Learning Web React Mobile Flutter CTF Hacking"
        )
        self.assertLessEqual(len(result), 3)

    def test_description_used(self) -> None:
        """Test bahwa description juga dipakai untuk matching."""
        result = auto_tag("Kompetisi Umum", description="deep learning neural network")
        self.assertIn("ai_ml", result)

    def test_case_insensitive(self) -> None:
        """Test case insensitive matching."""
        result = auto_tag("MACHINE LEARNING COMPETITION")
        self.assertIn("ai_ml", result)

    def test_empty_title(self) -> None:
        """Test dengan judul kosong — harus return umum."""
        result = auto_tag("")
        self.assertEqual(result, ["umum"])


if __name__ == "__main__":
    unittest.main()
