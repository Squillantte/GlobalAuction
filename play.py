#!/usr/bin/env python
"""
play.py
Executa um ou vários plug‑ins de leilões a partir da linha de comando.

Uso:
  python play.py tribunal_sp         # roda apenas tribunal_sp
  python play.py --all               # roda todos os plug‑ins
  python play.py tribunal_sp tj_mg   # roda mais de um

Requisitos: o módulo scraper.fetch_auctions precisa expor a função main().
"""

import sys
from scraper.fetch_auctions import main


def _cli() -> None:
    """
    Encaminha todos os argumentos recebidos para scraper.fetch_auctions.main().
    Se nenhum argumento for passado, mostra a ajuda padrão da função main().
    """
    exit_code: int = main(sys.argv[1:])
    sys.exit(exit_code)


if __name__ == "__main__":
    _cli()
