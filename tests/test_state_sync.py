"""Testes da sincronização do estado remoto."""

import json

import requests

from src import state_sync, storage


class FakeResponse:
    def __init__(self, text, status_code=200):
        self.text = text
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}")


def _configurar_paths(tmp_path, monkeypatch):
    monkeypatch.setattr(
        storage,
        "VISTOS_PATH",
        tmp_path / "vistos.json",
    )
    monkeypatch.setattr(
        storage,
        "OPORTUNIDADES_PATH",
        tmp_path / "oportunidades.jsonl",
    )
    monkeypatch.setattr(
        storage,
        "ULTIMA_VARREDURA_PATH",
        tmp_path / "ultima_varredura.json",
    )


def test_remoto_mais_novo_atualiza_estado(
    tmp_path,
    monkeypatch,
):
    _configurar_paths(tmp_path, monkeypatch)

    storage.ULTIMA_VARREDURA_PATH.write_text(
        json.dumps(
            {
                "data_execucao": "2026-09-08T10:00:00+00:00",
                "status": "concluida",
                "resumo": {},
            }
        ),
        encoding="utf-8",
    )

    respostas = {
        "ultima_varredura.json": json.dumps(
            {
                "data_execucao": "2026-09-08T17:00:00",
                "status": "concluida",
                "resumo": {"total_coletados": 10},
            }
        ),
        "vistos.json": json.dumps(["https://example.com/1"]),
        "oportunidades.jsonl": ('{"id":"OP-1","alertado":false}\n'),
    }

    def fake_get(url, timeout):
        nome = url.rsplit("/", 1)[-1]
        return FakeResponse(respostas[nome])

    monkeypatch.setattr(
        state_sync.requests,
        "get",
        fake_get,
    )

    resultado = state_sync.sincronizar_estado_remoto()

    assert resultado["atualizado"] is True

    assert storage.carregar_vistos() == {"https://example.com/1"}

    oportunidades = storage.carregar_oportunidades()

    assert oportunidades == [
        {
            "id": "OP-1",
            "alertado": False,
        }
    ]

    assert storage.data_ultima_varredura() == "2026-09-08T17:00:00+00:00"


def test_local_mais_novo_nao_e_sobrescrito(
    tmp_path,
    monkeypatch,
):
    _configurar_paths(tmp_path, monkeypatch)

    storage.ULTIMA_VARREDURA_PATH.write_text(
        json.dumps(
            {
                "data_execucao": "2026-09-08T18:00:00+00:00",
                "status": "concluida",
                "resumo": {},
            }
        ),
        encoding="utf-8",
    )

    remoto = json.dumps(
        {
            "data_execucao": "2026-09-08T17:00:00+00:00",
            "status": "concluida",
            "resumo": {},
        }
    )

    chamadas = []

    def fake_get(url, timeout):
        chamadas.append(url)
        return FakeResponse(remoto)

    monkeypatch.setattr(
        state_sync.requests,
        "get",
        fake_get,
    )

    resultado = state_sync.sincronizar_estado_remoto()

    assert resultado == {
        "atualizado": False,
        "status": "local_atual",
    }

    # Apenas ultima_varredura.json deve ter sido consultado.
    assert len(chamadas) == 1


def test_falha_de_rede_preserva_estado_local(
    tmp_path,
    monkeypatch,
):
    _configurar_paths(tmp_path, monkeypatch)

    estado_local = {
        "data_execucao": "2026-09-08T15:00:00+00:00",
        "status": "concluida",
        "resumo": {},
    }

    storage.ULTIMA_VARREDURA_PATH.write_text(
        json.dumps(estado_local),
        encoding="utf-8",
    )

    def fake_get(*args, **kwargs):
        raise requests.Timeout("timeout simulado")

    monkeypatch.setattr(
        state_sync.requests,
        "get",
        fake_get,
    )

    resultado = state_sync.sincronizar_estado_remoto()

    assert resultado == {
        "atualizado": False,
        "status": "erro",
    }

    assert storage.carregar_ultima_varredura() == estado_local
