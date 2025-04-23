from pathlib import Path

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; Scraper/1.0)"}
RETRY = 3
TIMEOUT = 15
RAW_DIR = Path(__file__).resolve().parents[1] / "data" / "raw"

