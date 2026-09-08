"""Sincronização do estado persistido na branch state do GitHub."""

import json
from datetime import datetime, timezone

import requests

from src import storage
from src.logger import get_logger

log = get_logger("state_sync")

REMOTE_STATE_BASE_URL = (
    "https://raw.githubusercontent.com/Ibjunior01/Monitor_Milhas/state/data"
)

REQUEST_TIMEOUT = 5


def _parse_timestamp(valor: str | None) -> datetime | None:
    if not valor:
        return None

    try:
        data = datetime.fromisoformat(valor)
    except (TypeError, ValueError):
        return None

    # Compatibilidade com os primeiros estados gravados pelo
    # GitHub Actions, que eram UTC mas não continham offset.
    if data.tzinfo is None:
        data = data.replace(tzinfo=timezone.utc)

    return data.astimezone(timezone.utc)


def _baixar_texto(nome_arquivo: str) -> str | None:
    url = f"{REMOTE_STATE_BASE_URL}/{nome_arquivo}"

    response = requests.get(
        url,
        timeout=REQUEST_TIMEOUT,
    )

    if response.status_code == 404:
        return None

    response.raise_for_status()
    return response.text


def _parse_oportunidades(texto: str) -> list[dict]:
    oportunidades = []

    for linha in texto.splitlines():
        linha = linha.strip()

        if not linha:
            continue

        registro = json.loads(linha)

        if not isinstance(registro, dict):
            raise ValueError("Registro inválido em oportunidades.jsonl")

        oportunidades.append(registro)

    return oportunidades


def sincronizar_estado_remoto() -> dict:
    """Atualiza o estado local somente quando o remoto é mais recente."""
    try:
        texto_estado = _baixar_texto("ultima_varredura.json")

        if not texto_estado:
            return {
                "atualizado": False,
                "status": "sem_estado_remoto",
            }

        estado_remoto = json.loads(texto_estado)

        if not isinstance(estado_remoto, dict):
            raise ValueError("Estado remoto inválido")

        data_remota = _parse_timestamp(estado_remoto.get("data_execucao"))

        if data_remota is None:
            raise ValueError("Timestamp remoto inválido")

        # Normaliza também estados antigos gravados sem timezone.
        estado_remoto["data_execucao"] = data_remota.isoformat(
            timespec="seconds"
        )
        
        estado_local = storage.carregar_ultima_varredura()

        data_local = None

        if estado_local:
            data_local = _parse_timestamp(estado_local.get("data_execucao"))

        if data_local is not None and data_local >= data_remota:
            return {
                "atualizado": False,
                "status": "local_atual",
            }

        texto_vistos = _baixar_texto("vistos.json")
        texto_oportunidades = _baixar_texto("oportunidades.jsonl")

        vistos = json.loads(texto_vistos) if texto_vistos else []

        if not isinstance(vistos, list) or not all(
            isinstance(link, str) for link in vistos
        ):
            raise ValueError("vistos.json remoto inválido")

        oportunidades = _parse_oportunidades(texto_oportunidades or "")

        storage.substituir_estado_runtime(
            vistos=set(vistos),
            oportunidades=oportunidades,
            ultima_varredura=estado_remoto,
        )

        log.info(
            "Estado remoto sincronizado: %s",
            estado_remoto.get("data_execucao"),
        )

        return {
            "atualizado": True,
            "status": "atualizado",
        }

    except (
        json.JSONDecodeError,
        OSError,
        requests.RequestException,
        ValueError,
    ) as exc:
        log.warning(
            "Falha ao sincronizar estado remoto: %s",
            type(exc).__name__,
        )

        return {
            "atualizado": False,
            "status": "erro",
        }
