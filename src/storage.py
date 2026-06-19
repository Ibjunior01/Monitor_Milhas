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

from src.models import Oportunidade, StatusOportunidade
from src.logger import get_logger

log = get_logger("storage")

DATA_DIR = Path(__file__).parent.parent / "data"
OPORTUNIDADES_PATH = DATA_DIR / "oportunidades.jsonl"
VISTOS_PATH = DATA_DIR / "vistos.json"


def _serializar(obj) -> str:
    """Converte objetos Python para JSON-safe."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, StatusOportunidade):
        return obj.value
    raise TypeError(f"Tipo não serializável: {type(obj)}")


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
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(VISTOS_PATH, "w", encoding="utf-8") as f:
        json.dump(list(vistos), f, ensure_ascii=False)


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


def data_ultima_varredura() -> Optional[str]:
    """Retorna a data da coleta mais recente, ou None."""
    ops = carregar_oportunidades()
    if not ops:
        return None
    datas = [o.get("data_coleta", "") for o in ops if o.get("data_coleta")]
    return max(datas) if datas else None
