python -u play.py

"""
Script de uso rápido do seu scraper.

Execute:
    python play.py
"""

from pathlib import Path
from scraper import fetch_auctions


def main() -> None:
    output_dir = Path("data")          # pasta onde será salvo o CSV
    fetch_auctions(output_dir)
    print(f"Leilões coletados com sucesso em '{output_dir}/'")


if __name__ == "__main__":
    main()
