"""
Parser de oportunidades: extrai programa, % de bônus e validade a partir
de texto livre de notícias/títulos.
"""

import re
from datetime import datetime
from typing import Optional

from src.logger import get_logger

log = get_logger("parser")

# Mapeamento de palavras-chave → programa normalizado
PALAVRAS_PROGRAMA: dict[str, str] = {
    "latam": "LATAM",
    "latam pass": "LATAM",
    "tam": "LATAM",
    "smiles": "SMILES",
    "gol": "SMILES",
    "azul": "AZUL",
    "azul fidelidade": "AZUL",
    "tudo azul": "AZUL",
}

# Regex para capturar percentuais de bônus
# Ex: "30% de bônus", "bônus de 50%", "+40%", "50 por cento"
_RE_BONUS = re.compile(
    r"(?:b[oô]nus\s+(?:de\s+)?|\+)(\d{1,3})\s*(?:%|por\s+cento)|"
    r"(\d{1,3})\s*(?:%|por\s+cento)\s+(?:de\s+)?b[oô]nus",
    re.IGNORECASE,
)

# Regex para datas de validade
_RE_VALIDADE = re.compile(
    r"(?:at[eé]\s+|v[aá]lido\s+at[eé]\s+|expira\s+em\s+)"
    r"(\d{1,2})[/\-](\d{1,2})(?:[/\-](\d{2,4}))?",
    re.IGNORECASE,
)


def extrair_programa(texto: str) -> Optional[str]:
    """Identifica o programa de milhas mencionado no texto."""
    texto_lower = texto.lower()
    # Prioriza combinações mais longas primeiro
    for chave in sorted(PALAVRAS_PROGRAMA.keys(), key=len, reverse=True):
        if chave in texto_lower:
            return PALAVRAS_PROGRAMA[chave]
    return None


def extrair_bonus(texto: str) -> Optional[float]:
    """Extrai o percentual de bônus do texto. Retorna None se não encontrar."""
    match = _RE_BONUS.search(texto)
    if match:
        valor = match.group(1) or match.group(2)
        if valor:
            pct = float(valor)
            if 0 < pct <= 500:  # sanidade: bônus acima de 500% é improvável
                return pct
    return None


def extrair_validade(texto: str) -> Optional[datetime]:
    """Tenta extrair data de validade do texto."""
    match = _RE_VALIDADE.search(texto)
    if not match:
        return None
    try:
        dia = int(match.group(1))
        mes = int(match.group(2))
        ano_raw = match.group(3)
        ano = int(ano_raw) if ano_raw else datetime.now().year
        if ano < 100:
            ano += 2000
        return datetime(ano, mes, dia)
    except (ValueError, TypeError):
        return None


def parsear_item(item: dict) -> dict:
    """
    Recebe item bruto (do sources.py) e tenta extrair campos estruturados.
    Retorna o item enriquecido com 'programa', 'bonus_pct', 'data_validade'.
    """
    texto_completo = f"{item.get('titulo', '')} {item.get('resumo', '')}"

    programa = extrair_programa(texto_completo)
    bonus_pct = extrair_bonus(texto_completo)
    data_validade = extrair_validade(texto_completo)

    if programa:
        log.debug(
            f"Identificado: programa={programa}, bonus={bonus_pct}%, link={item.get('link', '')[:60]}"
        )
    else:
        log.debug(f"Sem programa identificado para: {item.get('titulo', '')[:80]}")

    return {
        **item,
        "programa": programa,
        "bonus_pct": bonus_pct,
        "data_validade": data_validade,
    }


def _menciona_esfera(item: dict) -> bool:
    """Indica se título ou resumo mencionam explicitamente a Esfera."""
    texto = (f"{item.get('titulo', '')} {item.get('resumo', '')}").lower()

    return "esfera" in texto


def filtrar_relevantes(itens: list[dict]) -> list[dict]:
    """
    Mantém apenas candidatos relacionados à Esfera e com
    programa aéreo de destino identificado.

    O percentual de bônus não é obrigatório nesta etapa,
    pois uma promoção legítima pode exigir revisão manual
    quando o percentual não estiver presente no título/resumo.
    """
    relevantes = [
        item
        for item in itens
        if item.get("programa")
        and _menciona_esfera(item)
    ]

    ignorados = len(itens) - len(relevantes)

    log.info(
        "Parser: %s relevantes, %s descartados",
        len(relevantes),
        ignorados,
    )

    return relevantes
