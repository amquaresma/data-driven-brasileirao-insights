"""Lista os rótulos de rodada que a Highlightly devolve para uma série (usa cache, ~3 chamadas)."""
import json
import sys
from collections import Counter
from pathlib import Path

from sources.highlightly import paginate_matches

serie = sys.argv[1] if len(sys.argv) > 1 else "c"
cache = Path(__file__).parent / ".cache" / f"hl_matches_{serie}.json"
cache.parent.mkdir(exist_ok=True)

if cache.exists():
    matches = json.loads(cache.read_text())
else:
    matches = list(paginate_matches(serie, 2026))
    cache.write_text(json.dumps(matches, ensure_ascii=False))

labels = Counter(m["round"] for m in matches)
print(f"{len(matches)} jogos")
for label, n in sorted(labels.items()):
    states = Counter(m["state"]["description"] for m in matches if m["round"] == label)
    print(f"  {label!r}: {n} jogos {dict(states)}")
