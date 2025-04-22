from __future__ import annotations

import asyncio
import json
import logging
import importlib
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from types import ModuleType
from typing import Iterable, List

import pandas as pd
from dateutil import parser as date_parser
from tqdm import tqdm

# ---------- Configurações globais ----------
CONCURRENCY = 10           # workers paralelos
MAX_AGE_DAYS = 0           # filtra imóveis já leiloados (0 = somente futuros)
DATA_DIR = Path(__file__).resolve().parents[1] / "data"
PHOTOS_DIR = DATA_DIR / "photos"
SOURCES_PACKAGE = "scraper.sources"

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s | %(name)s | %(message)s"
)
logger = logging.getLogger("fetch_auctions")


# ---------- Modelo de domínio ----------
@dataclass(slots=True, frozen=True)
class Auction:
    source: str
    id: str
    title: str
    auction_date: str          # ISO‑8601
    location: str
    price: str
    photo_path: str
    url: str

    def to_json(self) -> dict:
        return asdict(self)


# ---------- Descoberta dinâmica de plug‑ins ----------
def _discover_sources() -> List[ModuleType]:
    """Importa todos os módulos em scraper/sources/ que tenham fetch() assíncrono."""
    pkg_path = Path(__file__).parent / "sources"
    modules: List[ModuleType] = []

    for file in pkg_path.glob("*.py"):
        if file.name.startswith("_"):
            continue
        module_name = f"{SOURCES_PACKAGE}.{file.stem}"
        module = importlib.import_module(module_name)
        if asyncio.iscoroutinefunction(getattr(module, "fetch", None)):
            modules.append(module)
        else:
            logger.warning("Ignorando %s: não possui fetch() async", module_name)
    return modules


# ---------- Funções auxiliares ----------
def _filter_future_auctions(auctions: Iterable[Auction]) -> List[Auction]:
    today = datetime.utcnow().date()
    keep: List[Auction] = []

    for a in auctions:
        try:
            auction_dt = date_parser.isoparse(a.auction_date).date()
        except ValueError:
            logger.warning("Data inválida para %s – mantendo mesmo assim", a.id)
            keep.append(a)
            continue

        if auction_dt >= today:
            keep.append(a)
    return keep


def _save_to_json(auctions: List[Auction]) -> None:
    DATA_DIR.mkdir(exist_ok=True, parents=True)
    out_file = DATA_DIR / "auctions.json"
    logger.info("Gravando %s com %d registros", out_file, len(auctions))
    out_file.write_text(json.dumps([a.to_json() for a in auctions], indent=2, ensure_ascii=False))


def _save_to_csv(auctions: List[Auction]) -> None:
    df = pd.DataFrame([a.to_json() for a in auctions])
    csv_file = DATA_DIR / "auctions.csv"
    logger.info("Gerando CSV %s", csv_file)
    df.to_csv(csv_file, index=False, encoding="utf-8-sig")


# ---------- Orquestração ----------
async def _collect_from_source(module: ModuleType) -> List[Auction]:
    try:
        logger.info("Coletando %s", module.__name__)
        result: Iterable[Auction] = await module.fetch(PHOTOS_DIR)
        return list(result)
    except Exception as exc:
        logger.exception("Falha em %s: %s", module.__name__, exc)
        return []


async def _gather_all() -> List[Auction]:
    modules = _discover_sources()
    PHOTOS_DIR.mkdir(parents=True, exist_ok=True)

    auctions: List[Auction] = []
    sem = asyncio.Semaphore(CONCURRENCY)

    async def _wrap(m: ModuleType):
        async with sem:
            return await _collect_from_source(m)

    tasks = [_wrap(m) for m in modules]

    for coro in tqdm(asyncio.as_completed(tasks), total=len(tasks), desc="Fontes"):
        auctions.extend(await coro)

    if MAX_AGE_DAYS == 0:
        auctions = _filter_future_auctions(auctions)

    logger.info("Total de registros coletados: %d", len(auctions))
    return auctions


def main() -> None:
    auctions = asyncio.run(_gather_all())
    _save_to_json(auctions)
    _save_to_csv(auctions)


if __name__ == "__main__":
    main()
