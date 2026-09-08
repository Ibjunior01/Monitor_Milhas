"""Testes da integração com Telegram sem acesso à internet."""

from types import SimpleNamespace

import requests

from src import telegram_alerts


def _oportunidade():
    return SimpleNamespace(
        programa="SMILES",
        titulo="Promoção de teste",
        data_validade=None,
        data_publicacao=None,
        bonus_pct=80.0,
        pontos_considerados=100_000,
        milhas_finais=180_000,
        valor_milheiro=20.0,
        valor_estimado=3_600.0,
        meta_financeira=900.0,
        recomendacao="Oportunidade aprovada",
        link="https://example.com/promocao",
        aprovada=True,
    )


class FakeResponse:
    status_code = 200

    def raise_for_status(self):
        return None

    def json(self):
        return {"ok": True}


def test_credenciais_ausentes_nao_fazem_request(monkeypatch):
    monkeypatch.setattr(
        telegram_alerts,
        "telegram_credentials",
        lambda: ("", ""),
    )

    def request_nao_deveria_ocorrer(*args, **kwargs):
        raise AssertionError("requests.post não deveria ser chamado")

    monkeypatch.setattr(
        telegram_alerts.requests,
        "post",
        request_nao_deveria_ocorrer,
    )

    assert telegram_alerts.enviar_alerta(_oportunidade()) is False


def test_alerta_usa_timeout_e_credenciais(monkeypatch):
    chamadas = []

    monkeypatch.setattr(
        telegram_alerts,
        "telegram_credentials",
        lambda: ("TOKEN-TESTE", "CHAT-TESTE"),
    )

    def fake_post(url, json, timeout):
        chamadas.append(
            {
                "url": url,
                "json": json,
                "timeout": timeout,
            }
        )
        return FakeResponse()

    monkeypatch.setattr(
        telegram_alerts.requests,
        "post",
        fake_post,
    )

    assert telegram_alerts.enviar_alerta(_oportunidade()) is True

    assert len(chamadas) == 1
    assert chamadas[0]["timeout"] == telegram_alerts.REQUEST_TIMEOUT
    assert chamadas[0]["json"]["chat_id"] == "CHAT-TESTE"


def test_timeout_retorna_false(monkeypatch):
    monkeypatch.setattr(
        telegram_alerts,
        "telegram_credentials",
        lambda: ("TOKEN-TESTE", "CHAT-TESTE"),
    )

    def fake_post(*args, **kwargs):
        raise requests.Timeout("timeout simulado")

    monkeypatch.setattr(
        telegram_alerts.requests,
        "post",
        fake_post,
    )

    assert telegram_alerts.enviar_alerta(_oportunidade()) is False


def test_erro_http_nao_expoe_token_no_log(monkeypatch):
    token = "TOKEN-SUPER-SECRETO"
    mensagens = []

    monkeypatch.setattr(
        telegram_alerts,
        "telegram_credentials",
        lambda: (token, "CHAT-TESTE"),
    )

    class FakeLogger:
        def info(self, msg, *args):
            mensagens.append(msg % args if args else msg)

        def warning(self, msg, *args):
            mensagens.append(msg % args if args else msg)

        def error(self, msg, *args):
            mensagens.append(msg % args if args else msg)

    monkeypatch.setattr(
        telegram_alerts,
        "log",
        FakeLogger(),
    )

    class ErrorResponse:
        status_code = 401

        def raise_for_status(self):
            raise requests.HTTPError(
                f"401 Client Error for URL "
                f"https://api.telegram.org/bot{token}/sendMessage"
            )

        def json(self):
            return {"ok": False}

    monkeypatch.setattr(
        telegram_alerts.requests,
        "post",
        lambda *args, **kwargs: ErrorResponse(),
    )

    assert telegram_alerts.enviar_alerta(_oportunidade()) is False

    log_completo = "\n".join(mensagens)

    assert token not in log_completo


def test_resposta_invalida_retorna_false(monkeypatch):
    monkeypatch.setattr(
        telegram_alerts,
        "telegram_credentials",
        lambda: ("TOKEN-TESTE", "CHAT-TESTE"),
    )

    class InvalidResponse:
        status_code = 200

        def raise_for_status(self):
            return None

        def json(self):
            raise ValueError("JSON inválido")

    monkeypatch.setattr(
        telegram_alerts.requests,
        "post",
        lambda *args, **kwargs: InvalidResponse(),
    )

    assert telegram_alerts.enviar_alerta(_oportunidade()) is False