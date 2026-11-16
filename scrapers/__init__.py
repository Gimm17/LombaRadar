"""Modul scraper LombaRadar — registrasi semua scraper."""

from .devpost import DevpostScraper
from .kaggle import KaggleScraper
from .sinta import SintaScraper
from .dicoding import DicodingScraper
from .lomba_info import LombaInfoScraper
from .info_lomba import InfoLombaScraper
from .twitter_x import TwitterXScraper
from .devfolio import DevfolioScraper
from .mlh import MlhScraper
from .hackerearth import HackerEarthScraper
from .unstop import UnstopScraper
from .lablab import LablabScraper
from .sumatranomics import SumatranomicsScraper
from .ejavec import EjavecScraper

ALL_SCRAPERS = [
    DevpostScraper,
    KaggleScraper,
    SintaScraper,
    DicodingScraper,
    LombaInfoScraper,
    InfoLombaScraper,
    TwitterXScraper,
    DevfolioScraper,
    MlhScraper,
    HackerEarthScraper,
    UnstopScraper,
    LablabScraper,
    SumatranomicsScraper,
    EjavecScraper,
]
