# Site de Pesquisa de Leilões

Este repositório contém:
* **frontend/** – código do site a ser hospedado no Netlify  
* **scraper/** – coletor Python que gera/atualiza `data/auctions.json`  
* GitHub Action (`.github/workflows/update-data.yml`) que:
  1. Executa o scraper diariamente às 02:00 UTC.
  2. Commita o JSON atualizado de volta no branch `main`.
  3. O push dispara um novo build no Netlify, mantendo o site sempre em dia.

## Como testar localmente
```bash
git clone https://github.com/<seu-user>/leiloes-site.git
cd leiloes-site/scraper
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python fetch_auctions.py

3) `netlify.toml` – instrução de build básica (ajuste ao seu stack):

```toml
[build]
  publish = "frontend"
  command = "echo 'Site estático, nada para compilar'"
