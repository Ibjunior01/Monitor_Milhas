"""Testes do orquestrador de monitoramento."""

from src import monitor


def test_varredura_sem_oportunidades_persiste_estado(monkeypatch):
    """Uma execução válida deve registrar seu estado mesmo sem oportunidades."""
    resumos_salvos = []

    monkeypatch.setattr(monitor, "carregar_config", lambda: object())
    monkeypatch.setattr(monitor, "carregar_vistos", lambda: set())
    monkeypatch.setattr(monitor, "coletar_todas_fontes", lambda: [])

    monkeypatch.setattr(
        monitor,
        "salvar_ultima_varredura",
        lambda resumo: resumos_salvos.append(resumo),
        raising=False,
    )

    resumo = monitor.executar_varredura()

    assert resumo == {
        "total_coletados": 0,
        "novos": 0,
        "relevantes": 0,
        "aprovadas": 0,
        "alertas_enviados": 0,
        "ignoradas": 0,
    }

    assert resumos_salvos == [resumo]