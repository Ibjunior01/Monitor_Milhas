"""Testes das integrações com fontes externas."""

from types import SimpleNamespace

import requests

from src import sources


class FakeResponse:
    def __init__(self, content=b"<rss></rss>"):
        self.content = content

    def raise_for_status(self):
        return None


def test_google_news_usa_timeout_e_user_agent(monkeypatch):
    chamadas = []

    def fake_get(url, headers, timeout):
        chamadas.append(
            {
                "url": url,
                "headers": headers,
                "timeout": timeout,
            }
        )
        return FakeResponse()

    monkeypatch.setattr(sources.requests, "get", fake_get)
    monkeypatch.setattr(
        sources.feedparser,
        "parse",
        lambda _conteudo: SimpleNamespace(
            bozo=False,
            entries=[],
        ),
    )

    resultado = sources.buscar_google_news("Esfera LATAM")

    assert resultado == []
    assert len(chamadas) == 1
    assert chamadas[0]["timeout"] == sources.REQUEST_TIMEOUT
    assert "MonitorMilhasBot" in chamadas[0]["headers"]["User-Agent"]


def test_timeout_faz_retries_e_retorna_lista_vazia(monkeypatch):
    chamadas = []

    def fake_get(*args, **kwargs):
        chamadas.append((args, kwargs))
        raise requests.Timeout("timeout simulado")

    monkeypatch.setattr(sources.requests, "get", fake_get)
    monkeypatch.setattr(sources.time, "sleep", lambda _segundos: None)

    resultado = sources.buscar_google_news("Esfera Smiles")

    assert resultado == []
    assert len(chamadas) == sources.MAX_RETRIES + 1


def test_rss_extra_usa_mesma_camanda_http(monkeypatch):
    chamadas = []

    def fake_get(url, headers, timeout):
        chamadas.append(url)
        return FakeResponse()

    monkeypatch.setattr(sources.requests, "get", fake_get)
    monkeypatch.setattr(
        sources.feedparser,
        "parse",
        lambda _conteudo: SimpleNamespace(
            entries=[],
            feed={},
        ),
    )

    resultado = sources.buscar_rss_extra(
        "https://example.com/feed.xml"
    )

    assert resultado == []
    assert chamadas == ["https://example.com/feed.xml"]