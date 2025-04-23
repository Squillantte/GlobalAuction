import argparse, importlib
from pathlib import Path
import json

def main():
    parser = argparse.ArgumentParser(description="Runner unificado")
    parser.add_argument("target", help="caminho do módulo ex: br.juntas_comerciais.junta_sp")
    parser.add_argument("--out", default="stdout", help="arquivo de saída ou stdout")
    args = parser.parse_args()

    mod = importlib.import_module(f"scripts.{args.target}")
    scraper_cls = getattr(mod, "Scraper")
    result = scraper_cls().run()

    if args.out == "stdout":
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        Path(args.out).write_text(json.dumps(result, ensure_ascii=False))
        print(f"Dados salvos em {args.out}")

if __name__ == "__main__":
    main()

