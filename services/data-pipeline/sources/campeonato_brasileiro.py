"""
Wrapper Python para o pacote npm `campeonato-brasileiro-api`.

Motivo: o pacote é uma biblioteca JavaScript que faz scraping de uma
fonte HTML (ge.globo) e normaliza o resultado em JSON. Ele não expõe
um servidor HTTP próprio, então consumimos via subprocess da CLI
empacotada junto ao pacote (binário `campeonato-brasileiro`), usando
a flag --json para obter saída estruturada.

Esta é uma decisão de infraestrutura isolada nesta camada: o resto
do pipeline/analytics/ML não sabe (nem precisa saber) que por baixo
disso existe uma chamada de processo Node. Se no futuro migrarmos
para um microserviço HTTP que implemente a OpenAPI spec do pacote,
só esta função precisa mudar.

Nota importante: se uma competição está agrupada (ex: Série D) é algo
que MUDA ao longo da temporada (fase de grupos -> mata-mata), não é
uma propriedade fixa da série. Por isso não fazemos suposição prévia
de que "serie == d" exige group — deixamos a própria fonte informar
isso via GROUP_REQUIRED quando aplicável.

Referência: https://github.com/ezefranca/campeonato-brasileiro-api
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any, Literal

from .exceptions import BrasileiraoSourceError

Serie = Literal["a", "b", "c", "d"]

_CLI_BIN = (
    Path(__file__).resolve().parent.parent
    / "node_modules"
    / ".bin"
    / "campeonato-brasileiro"
)

_TIMEOUT_SECONDS = 30


def _run_cli(args: list[str]) -> dict[str, Any]:
    if not _CLI_BIN.exists():
        raise BrasileiraoSourceError(
            f"Binário da CLI não encontrado em {_CLI_BIN}. "
            "Rode `npm install` em services/data-pipeline/."
        )

    command = [str(_CLI_BIN), *args, "--json"]

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=_TIMEOUT_SECONDS,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise BrasileiraoSourceError(
            f"Timeout ao executar: {' '.join(command)}"
        ) from exc

    # A CLI pode retornar um JSON de erro estruturado no stdout mesmo
    # com exit code != 0 (ex: GROUP_REQUIRED, GROUP_NOT_FOUND).
    # Tentamos parsear o stdout primeiro para extrair essa informação
    # antes de cair no stderr genérico.
    parsed_stdout: dict[str, Any] | None = None
    if result.stdout.strip():
        try:
            parsed_stdout = json.loads(result.stdout)
        except json.JSONDecodeError:
            parsed_stdout = None

    if result.returncode != 0:
        if parsed_stdout and "error" in parsed_stdout:
            error_info = parsed_stdout["error"]
            raise BrasileiraoSourceError(
                error_info.get("message", "Erro desconhecido retornado pela fonte."),
                code=error_info.get("code"),
                stderr=json.dumps(error_info.get("details")) if error_info.get("details") else None,
            )
        raise BrasileiraoSourceError(
            f"Comando falhou (exit code {result.returncode}): {' '.join(command)}",
            stderr=result.stderr.strip() or None,
        )

    if parsed_stdout is None:
        raise BrasileiraoSourceError(
            "Resposta da CLI não é um JSON válido.",
            stderr=result.stdout[:500],
        )

    return parsed_stdout


def get_standings(serie: Serie, *, group: str | None = None) -> dict[str, Any]:
    """
    Retorna a classificação (e legendas) da série informada.

    `group` é opcional: sem ele, a fonte retorna a(s) tabela(s)
    disponível(is) no momento (pode ser uma tabela geral ou várias
    tabelas de grupo, dependendo da fase atual da competição).
    """
    args = ["standings", serie]
    if group:
        args += ["--group", group]
    return _run_cli(args)


def get_rounds(serie: Serie, *, group: str | None = None, number: int | None = None) -> dict[str, Any]:
    """
    Retorna a rodada atual (com as partidas) da série informada.

    Não assumimos previamente se `group` é obrigatório: isso depende
    da fase atual da competição (ex: Série D em fase de grupos exige
    group; a mesma Série D em mata-mata não tem grupos). Se a fonte
    exigir group e ele não for passado, o erro GROUP_REQUIRED sobe
    naturalmente via BrasileiraoSourceError.
    """
    args = ["rounds", serie]
    if group:
        args += ["--group", group]
    if number is not None:
        args += ["--number", str(number)]
    return _run_cli(args)
