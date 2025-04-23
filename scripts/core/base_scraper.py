from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
import json, logging, time, random, requests

from .settings import HEADERS, RETRY, TIMEOUT, RAW_DIR

log = logging.getLogger(__name__)


class BaseScraper(ABC):
    """Classe base para todos os scrapers."""

    def __init__(self, name: str):
        self.name = name
        self.session = requests.Session()
        self.session.headers.update(HEADERS)

    @abstractmethod
    def fetch(self, **kwargs):
        """Baixa dados crus (HTML/JSON)."""
        raise NotImplementedError

    @abstractmethod
    def parse(self, raw):
        """Transforma dados crus em estrutura limpa."""
        raise NotImplementedError

    def save_raw(self, content: str | bytes, suffix: str = "html") -> Path:
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        path = RAW_DIR / f"{self.name}_{ts}.{suffix}"
        path.parent.mkdir(parents=True, exist_ok=True)
        mode = "wb" if isinstance(content, (bytes, bytearray)) else "w"
        with open(path, mode) as fp:
            fp.write(content)
        log.info("Raw salvo em %s", path)
        return path

    # fluxo padrão
    def run(self, **kwargs):
        for attempt in range(1, RETRY + 1):
            try:
                raw = self.fetch(**kwargs)
                self.save_raw(raw)
                data = self.parse(raw)
                return data
            except Exception as exc:
                log.warning("Tentativa %d/%d falhou: %s",
                            attempt, RETRY, exc, exc_info=False)
                if attempt == RETRY:
                    raise
                time.sleep(random.uniform(1, 3))

