"""
Executa a ingestão de standings e rounds periodicamente para todas
as séries (A, B, C, D).

Por que um processo separado da API: a API (services/api) só serve
dados já persistidos; quem coleta e atualiza é este processo, rodando
de forma independente (conforme services/data-pipeline na arquitetura
original do projeto).

Uso:
    python scheduler.py
"""

from __future__ import annotations

import sys
from datetime import datetime

from apscheduler.schedulers.blocking import BlockingScheduler

from ingest import ingest_standings, ingest_rounds
from sources.exceptions import BrasileiraoSourceError

SERIES = ["a", "b", "c", "d"]

# Intervalo de execução. Rodadas do Brasileirão não mudam a cada
# minuto — 15 min é frequente o suficiente para capturar atualizações
# de placar ao vivo sem sobrecarregar a fonte (que é scraping de HTML,
# não uma API dedicada).
INTERVAL_MINUTES = 15


def _log(message: str) -> None:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")


def run_ingestion_cycle() -> None:
    """
    Roda standings + rounds para todas as séries. Uma falha numa série
    (ex: fonte fora do ar, fase sem dados disponíveis) não interrompe
    as demais — cada série é isolada em seu próprio try/except.
    """
    _log("Iniciando ciclo de ingestão...")

    for serie in SERIES:
        for resource_name, ingest_fn in (
            ("standings", ingest_standings),
            ("rounds", ingest_rounds),
        ):
            try:
                ingest_fn(serie)
            except BrasileiraoSourceError as exc:
                _log(f"  [{serie}/{resource_name}] erro da fonte: [{exc.code}] {exc}")
            except Exception as exc:  # noqa: BLE001 - isolamento intencional por série/recurso
                _log(f"  [{serie}/{resource_name}] erro inesperado: {exc}")

    _log("Ciclo de ingestão concluído.")


if __name__ == "__main__":
    scheduler = BlockingScheduler()
    scheduler.add_job(
        run_ingestion_cycle,
        "interval",
        minutes=INTERVAL_MINUTES,
        next_run_time=datetime.now(),  # roda imediatamente ao iniciar
    )

    _log(f"Scheduler iniciado. Intervalo: {INTERVAL_MINUTES} minutos.")
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        _log("Scheduler encerrado.")
        sys.exit(0)
