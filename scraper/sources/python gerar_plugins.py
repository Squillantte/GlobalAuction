#!/usr/bin/env python3
# python gerar_plugins.py
from pathlib import Path

estados = [
    "AC","AL","AM","AP","BA","CE","DF","ES","GO","MA","MG","MS","MT",
    "PA","PB","PE","PI","PR","RJ","RN","RO","RR","RS","SC","SE","SP","TO"
]

def criar(uf: str, modelo: Path):
    txt = modelo.read_text().replace("{{UF}}", uf)
    destino = modelo.with_name(f"{modelo.stem.split('_')[0]}_{uf.lower()}.py")
    destino.write_text(txt)

root = Path(__file__).parent
tribunal_tpl = root / "tribunal_template.py"
junta_tpl    = root / "junta_template.py"

for uf in estados:
    criar(uf, tribunal_tpl)
    criar(uf, junta_tpl)

print("Pronto! 54 arquivos gerados.")
