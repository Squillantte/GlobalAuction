"""
Plug‑in: Mega Leilões – https://www.megaleiloes.com.br/
Coleta somente lotes de imóveis com leilão futuro.
"""
from __future__ import annotations

import asyncio
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import List

import aiohttp
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential

from scraper.fetch_auctions import Auction

BASE_URL = "https://www.megaleiloes.com.br"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; LeilaoBot/1.0; +https://seusite.com)"
}


@retry(wait=wait_exponential(multiplier=1, min=2, max=30), stop=stop_after_attempt(5))
async def _get(session: aiohttp.ClientSession, url: str) -> str:
    async with session.get(url, headers=HEADERS, timeout=60) as resp:
        resp.raise_for_status()
        return await resp.text()


async def _parse_lot(session: aiohttp.ClientSession, lot_url: str, photos_dir: Path) -> Auction | None:
    html = await _get(session, lot_url)
    soup = BeautifulSoup(html, "lxml")

    title = soup.select_one("h1.product-title")
    date_box = soup.select_one(".date")
    price_box = soup.select_one(".price")
    img_tag = soup.select_one(".fotorama__active img")

    if not all((title, date_box)):
        return None

    # Data no formato "10/05/2025 14:00"
    date_match = re.search(r"\d{2}/\d{2}/\d{4}", date_box.text)
    if not date_match:
        return None
    date_str = datetime.strptime(date_match.group(), "%d/%m/%Y").replace(tzinfo=timezone.utc).isoformat()

    price = price_box.get_text(strip=True) if price_box else "N/A"
    img_url = img_tag["src"] if img_tag else ""

    photo_path = ""
    if img_url:
        photo_path = await _download_photo(session, img_url, photos_dir)

    return Auction(
        source="Mega Leilões",
        id=lot_url.rsplit("/", 1)[-1],
        title=title.get_text(strip=True),
        auction_date=date_str,
        location="",
        price=price,
        photo_path=photo_path,
        url=lot_url,
    )


async def _download_photo(session: aiohttp.ClientSession, url: str, photos_dir: Path) -> str:
    name = url.split("/")[-1].split("?")[0]
    dest = photos_dir / name
    if dest.exists():
        return str(dest.relative_to(photos_dir.parent))
    async with session.get(url, headers=HEADERS, timeout=60) as resp:
        resp.raise_for_status()
        content = await resp.read()
    dest.write_bytes(content)
    return str(dest.relative_to(photos_dir.parent))


async def fetch(photos_dir: Path) -> List[Auction]:
    """
    Retorna uma lista de Auction com imóveis agendados.
    """
    list_url = f"{BASE_URL}/busca?TipoImovel=1"  # imóvel
    auctions: List[Auction] = []

    async with aiohttp.ClientSession() as session:
        html = await _get(session, list_url)
        soup = BeautifulSoup(html, "lxml")
        lot_links = {BASE_URL + tag["href"] for tag in soup.select("a.productLink")}

        tasks = [_parse_lot(session, url, photos_dir) for url in lot_links]
        for coro in asyncio.as_completed(tasks):
            lot = await coro
            if lot:
                auctions.append(lot)

    return auctions
