"""Baixa as temporadas históricas de A e B da Highlightly para .cache/ (retomável, ~4 chamadas por série/temporada)."""
import json
from pathlib import Path

from sources.exceptions import BrasileiraoSourceError
from sources.highlightly import get_matches

CACHE = Path(__file__).parent / ".cache"
CACHE.mkdir(exist_ok=True)
SEASONS = [2025, 2024, 2023, 2022, 2021, 2020]

calls = 0
for season in SEASONS:
    for serie in ("a", "b"):
        f = CACHE / f"hl_hist_{serie}_{season}.json"
        if f.exists():
            print(f"{serie.upper()} {season}: já em cache ({len(json.loads(f.read_text()))} jogos)")
            continue
        matches, offset, total = [], 0, 0
        try:
            while True:
                page = get_matches(serie, season, limit=100, offset=offset)
                calls += 1
                data = page.get("data", [])
                total = page.get("pagination", {}).get("totalCount", 0)
                matches += data
                offset += 100
                if not data or offset >= total:
                    break
        except BrasileiraoSourceError as exc:
            if exc.code == "429":
                print(f"Limite diário atingido (429) em {serie.upper()} {season}. Rode de novo amanhã; o que já foi baixado fica.")
                raise SystemExit(0)
            raise
        if len(matches) != total:
            raise SystemExit(f"{serie.upper()} {season}: veio {len(matches)} de {total} jogos. Nada gravado.")
        f.write_text(json.dumps(matches, ensure_ascii=False))
        fin = sum(1 for m in matches if m["state"]["description"] == "Finished")
        print(f"{serie.upper()} {season}: {len(matches)} jogos ({fin} finalizados)")
print(f"Chamadas nesta execução: {calls}")
