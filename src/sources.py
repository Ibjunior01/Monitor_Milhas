"""
Coleta de fontes públicas de promoções de milhas.
Usa apenas feeds RSS e páginas abertas — sem login, sem CAPTCHA.
"""
import re
import time
import feedparser
import requests
from datetime import datetime
from typing import Optional
from src.logger import get_logger

log = get_logger("sources")

# Termos de busca relevantes para o Esfera
TERMOS_BUSCA = [
    "Esfera LATAM bônus transferência",
    "Esfera Smiles bônus transferência",
    "Esfera Azul bônus transferência",
    "Esfera transferência bonificada",
    "Esfera pontos bônus LATAM Pass",
    "Esfera pontos bônus Smiles",
    "Esfera pontos bônus Azul Fidelidade",
    "promoção Esfera milhas",
]

# Sites especializados em milhas com RSS disponível
RSS_EXTRAS: list[str] = [
    # Adicione aqui outros RSS de blogs de milhas que você acompanha
    # Ex: "https://www.melhoresdestinosdelmundo.com.br/feed/"
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; MonitorMilhasBot/1.0; "
        "+https://github.com/seuusuario/monitor-milhas)"
    )
}


def _gnews_url(termo: str) -> str:
    termo_enc = termo.replace(" ", "+")
    return (
        f"https://news.google.com/rss/search"
        f"?q={termo_enc}&hl=pt-BR&gl=BR&ceid=BR:pt-419"
    )


def buscar_google_news(termo: str) -> list[dict]:
    """Consulta Google News RSS para um termo e retorna lista de itens brutos."""
    url = _gnews_url(termo)
    try:
        feed = feedparser.parse(url)
        if feed.bozo:
            log.warning(f"Feed com erro para '{termo}': {feed.bozo_exception}")
        items = []
        for entry in feed.entries:
            items.append({
                "titulo": entry.get("title", ""),
                "link": entry.get("link", ""),
                "resumo": entry.get("summary", ""),
                "fonte": entry.get("source", {}).get("title", "Google News"),
                "data_publicacao": _parse_data(entry.get("published", "")),
            })
        log.info(f"Google News '{termo}': {len(items)} itens encontrados")
        return items
    except Exception as e:
        log.error(f"Erro ao buscar Google News para '{termo}': {e}")
        return []


def buscar_rss_extra(url: str) -> list[dict]:
    """Busca um feed RSS externo e retorna itens brutos."""
    try:
        feed = feedparser.parse(url)
        items = []
        for entry in feed.entries:
            titulo = entry.get("title", "").lower()
            resumo = entry.get("summary", "").lower()
            # Filtra apenas entradas relacionadas a Esfera ou transferência bonificada
            if any(k in titulo + resumo for k in ["esfera", "transferência bonificada", "bonus transfer"]):
                items.append({
                    "titulo": entry.get("title", ""),
                    "link": entry.get("link", ""),
                    "resumo": entry.get("summary", ""),
                    "fonte": feed.feed.get("title", url),
                    "data_publicacao": _parse_data(entry.get("published", "")),
                })
        log.info(f"RSS extra '{url}': {len(items)} itens relevantes")
        return items
    except Exception as e:
        log.error(f"Erro ao buscar RSS extra '{url}': {e}")
        return []


def coletar_todas_fontes(delay_entre_buscas: float = 1.5) -> list[dict]:
    """
    Agrega resultados de todos os termos e fontes extras.
    delay_entre_buscas evita sobrecarga nos servidores externos.
    """
    resultados: list[dict] = []
    vistos_nesta_rodada: set[str] = set()

    for termo in TERMOS_BUSCA:
        itens = buscar_google_news(termo)
        for item in itens:
            link = item.get("link", "")
            if link and link not in vistos_nesta_rodada:
                vistos_nesta_rodada.add(link)
                resultados.append(item)
        time.sleep(delay_entre_buscas)

    for rss_url in RSS_EXTRAS:
        for item in buscar_rss_extra(rss_url):
            link = item.get("link", "")
            if link and link not in vistos_nesta_rodada:
                vistos_nesta_rodada.add(link)
                resultados.append(item)

    log.info(f"Total coletado (sem deduplicação histórica): {len(resultados)} itens")
    return resultados


def _parse_data(texto: str) -> Optional[datetime]:
    """Tenta converter string de data em datetime."""
    if not texto:
        return None
    import email.utils
    try:
        tupla = email.utils.parsedate(texto)
        if tupla:
            return datetime(*tupla[:6])
    except Exception:
        pass
    for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d %H:%M:%S", "%a, %d %b %Y %H:%M:%S %z"):
        try:
            return datetime.strptime(texto[:25], fmt[:len(texto[:25])])
        except ValueError:
            continue
    return None
