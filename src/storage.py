"""
Camada de persistência usando arquivos locais (JSON/JSONL).
Interface projetada para substituição futura por banco de dados
sem alterar o restante do código.
"""

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from src.logger import get_logger
from src.models import Oportunidade, StatusOportunidade

log = get_logger("storage")

DATA_DIR = Path(__file__).parent.parent / "data"
OPORTUNIDADES_PATH = DATA_DIR / "oportunidades.jsonl"
VISTOS_PATH = DATA_DIR / "vistos.json"
ULTIMA_VARREDURA_PATH = DATA_DIR / "ultima_varredura.json"


def _serializar(obj) -> str:
    """Converte objetos Python para JSON-safe."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, StatusOportunidade):
        return obj.value
    raise TypeError(f"Tipo não serializável: {type(obj)}")


def _salvar_json_atomico(path: Path, dados) -> None:
    """Grava JSON em arquivo temporário e substitui o destino atomicamente."""
    path.parent.mkdir(parents=True, exist_ok=True)

    temp_path = path.with_suffix(path.suffix + ".tmp")

    try:
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(dados, f, ensure_ascii=False, indent=2)
            f.flush()

        temp_path.replace(path)
    except OSError:
        if temp_path.exists():
            temp_path.unlink(missing_ok=True)
        raise


def carregar_vistos() -> set[str]:
    """Retorna conjunto de links já processados."""
    if not VISTOS_PATH.exists():
        return set()
    try:
        with open(VISTOS_PATH, encoding="utf-8") as f:
            return set(json.load(f))
    except (json.JSONDecodeError, OSError):
        log.warning("Arquivo vistos.json corrompido ou inexistente. Iniciando vazio.")
        return set()


def salvar_visto(link: str) -> None:
    """Adiciona link ao registro de processados."""
    vistos = carregar_vistos()
    vistos.add(link)

    _salvar_json_atomico(
        VISTOS_PATH,
        sorted(vistos),
    )


def salvar_oportunidade(op: Oportunidade) -> None:
    """Appende oportunidade no arquivo JSONL."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    registro = {
        "id": op.id,
        "titulo": op.titulo,
        "resumo": op.resumo,
        "link": op.link,
        "fonte": op.fonte,
        "data_coleta": op.data_coleta,
        "data_publicacao": op.data_publicacao,
        "programa": op.programa,
        "bonus_pct": op.bonus_pct,
        "data_validade": op.data_validade,
        "pontos_considerados": op.pontos_considerados,
        "milhas_finais": op.milhas_finais,
        "valor_milheiro": op.valor_milheiro,
        "valor_estimado": op.valor_estimado,
        "meta_financeira": op.meta_financeira,
        "status": op.status,
        "recomendacao": op.recomendacao,
        "aprovada": op.aprovada,
        "alertado": op.alertado,
    }
    with open(OPORTUNIDADES_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(registro, default=_serializar, ensure_ascii=False) + "\n")
    log.debug(f"Oportunidade salva: {op.id} | {op.programa} | {op.bonus_pct}%")


def carregar_oportunidades() -> list[dict]:
    """Carrega todas as oportunidades do histórico."""
    if not OPORTUNIDADES_PATH.exists():
        return []
    oportunidades = []
    with open(OPORTUNIDADES_PATH, encoding="utf-8") as f:
        for linha in f:
            linha = linha.strip()
            if not linha:
                continue
            try:
                oportunidades.append(json.loads(linha))
            except json.JSONDecodeError as e:
                log.warning(f"Linha inválida no JSONL: {e}")
    return oportunidades


def criar_oportunidade(
    item: dict,
    programa_cfg,
    config,
    status: StatusOportunidade,
    recomendacao: str,
    milhas_finais: float,
    valor_estimado: float,
) -> Oportunidade:
    """Fábrica que monta uma Oportunidade a partir dos dados processados."""
    return Oportunidade(
        id=str(uuid.uuid4())[:8],
        titulo=item.get("titulo", ""),
        resumo=item.get("resumo", ""),
        link=item.get("link", ""),
        fonte=item.get("fonte", ""),
        data_coleta=datetime.now(),
        data_publicacao=item.get("data_publicacao"),
        programa=item.get("programa", ""),
        bonus_pct=item.get("bonus_pct", 0.0),
        data_validade=item.get("data_validade"),
        pontos_considerados=config.pontos_disponiveis,
        milhas_finais=milhas_finais,
        valor_milheiro=programa_cfg.valor_milheiro,
        valor_estimado=valor_estimado,
        meta_financeira=config.meta_financeira_minima,
        status=status,
        recomendacao=recomendacao,
        aprovada=status == StatusOportunidade.APROVADA,
        alertado=False,
    )


def salvar_ultima_varredura(resumo: dict) -> None:
    """Persiste o estado da última varredura concluída."""
    estado = {
        "data_execucao": datetime.now().isoformat(timespec="seconds"),
        "status": "concluida",
        "resumo": resumo,
    }

    _salvar_json_atomico(
        ULTIMA_VARREDURA_PATH,
        estado,
    )


def carregar_ultima_varredura() -> Optional[dict]:
    """Carrega o estado da última varredura concluída."""
    if not ULTIMA_VARREDURA_PATH.exists():
        return None

    try:
        with open(ULTIMA_VARREDURA_PATH, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        log.warning("Arquivo ultima_varredura.json inválido ou inacessível.")
        return None


def data_ultima_varredura() -> Optional[str]:
    """Retorna a data da última varredura concluída, ou None."""
    estado = carregar_ultima_varredura()

    if not estado:
        return None

    return estado.get("data_execucao")


def marcar_oportunidade_alertada(oportunidade_id: str) -> bool:
    """Marca uma oportunidade persistida como alertada.

    Retorna True quando o registro foi encontrado e atualizado.
    """
    if not OPORTUNIDADES_PATH.exists():
        return False

    registros = carregar_oportunidades()
    encontrado = False

    for registro in registros:
        if registro.get("id") == oportunidade_id:
            registro["alertado"] = True
            encontrado = True
            break

    if not encontrado:
        return False

    temp_path = OPORTUNIDADES_PATH.with_suffix(".jsonl.tmp")

    try:
        with open(temp_path, "w", encoding="utf-8") as f:
            for registro in registros:
                f.write(
                    json.dumps(
                        registro,
                        ensure_ascii=False,
                    )
                    + "\n"
                )
            f.flush()

        temp_path.replace(OPORTUNIDADES_PATH)

    except OSError:
        temp_path.unlink(missing_ok=True)
        raise

    log.debug(
        "Oportunidade marcada como alertada: %s",
        oportunidade_id,
    )
    return True
