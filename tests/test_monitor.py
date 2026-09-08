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


def test_item_nao_e_marcado_como_visto_se_persistencia_falhar(
    monkeypatch,
):
    """Falha ao persistir não deve fazer o item ser perdido."""
    from types import SimpleNamespace

    import pytest

    link = "https://example.com/promocao"

    item = {
        "link": link,
        "titulo": "Promoção de teste",
        "programa": "Smiles",
        "bonus_pct": 80.0,
        "data_publicacao": None,
    }

    config = SimpleNamespace(
        pontos_disponiveis=100_000,
        programas={
            "Smiles": SimpleNamespace(
                valor_milheiro=20.0,
                ativo=True,
            )
        },
    )

    vistos_salvos = []

    monkeypatch.setattr(
        monitor,
        "carregar_config",
        lambda: config,
    )
    monkeypatch.setattr(
        monitor,
        "carregar_vistos",
        lambda: set(),
    )
    monkeypatch.setattr(
        monitor,
        "coletar_todas_fontes",
        lambda: [item],
    )
    monkeypatch.setattr(
        monitor,
        "parsear_item",
        lambda bruto: bruto,
    )
    monkeypatch.setattr(
        monitor,
        "filtrar_relevantes",
        lambda itens: itens,
    )
    monkeypatch.setattr(
        monitor,
        "calcular_milhas_finais",
        lambda pontos, bonus: 180_000,
    )
    monkeypatch.setattr(
        monitor,
        "calcular_valor_estimado",
        lambda milhas, valor_milheiro: 3_600.0,
    )
    monkeypatch.setattr(
        monitor,
        "avaliar_oportunidade",
        lambda bonus, programa_cfg, cfg: (
            monitor.StatusOportunidade.APROVADA,
            "Oportunidade aprovada",
        ),
    )
    monkeypatch.setattr(
        monitor,
        "criar_oportunidade",
        lambda **kwargs: {"id": "OP-TESTE"},
    )
    monkeypatch.setattr(
        monitor,
        "salvar_visto",
        lambda item_link: vistos_salvos.append(item_link),
    )

    def falhar_ao_salvar(_oportunidade):
        raise RuntimeError("falha ao salvar")

    monkeypatch.setattr(
        monitor,
        "salvar_oportunidade",
        falhar_ao_salvar,
    )

    with pytest.raises(RuntimeError, match="falha ao salvar"):
        monitor.executar_varredura()

    assert vistos_salvos == []


def test_alerta_enviado_atualiza_estado_persistido(monkeypatch):
    """Telegram confirmado deve marcar a oportunidade como alertada."""
    from types import SimpleNamespace

    link = "https://example.com/promocao-alerta"

    item = {
        "link": link,
        "titulo": "Promoção Smiles 80% de bônus",
        "programa": "SMILES",
        "bonus_pct": 80.0,
        "data_publicacao": None,
    }

    config = SimpleNamespace(
        pontos_disponiveis=100_000,
        meta_financeira_minima=900.0,
        programas={
            "SMILES": SimpleNamespace(
                valor_milheiro=20.0,
                ativo=True,
            )
        },
    )

    oportunidade = SimpleNamespace(
        id="OP-ALERTA",
        alertado=False,
    )

    alertados = []

    monkeypatch.setattr(monitor, "carregar_config", lambda: config)
    monkeypatch.setattr(monitor, "carregar_vistos", lambda: set())
    monkeypatch.setattr(monitor, "coletar_todas_fontes", lambda: [item])
    monkeypatch.setattr(monitor, "parsear_item", lambda bruto: bruto)
    monkeypatch.setattr(monitor, "filtrar_relevantes", lambda itens: itens)

    monkeypatch.setattr(
        monitor,
        "calcular_milhas_finais",
        lambda pontos, bonus: 180_000,
    )
    monkeypatch.setattr(
        monitor,
        "calcular_valor_estimado",
        lambda milhas, valor_milheiro: 3_600.0,
    )
    monkeypatch.setattr(
        monitor,
        "avaliar_oportunidade",
        lambda bonus, programa_cfg, cfg: (
            monitor.StatusOportunidade.APROVADA,
            "Oportunidade aprovada",
        ),
    )

    monkeypatch.setattr(
        monitor,
        "criar_oportunidade",
        lambda **kwargs: oportunidade,
    )
    monkeypatch.setattr(
        monitor,
        "salvar_oportunidade",
        lambda op: None,
    )
    monkeypatch.setattr(
        monitor,
        "salvar_visto",
        lambda item_link: None,
    )
    monkeypatch.setattr(
        monitor,
        "enviar_alerta",
        lambda op: True,
    )
    monkeypatch.setattr(
        monitor,
        "marcar_oportunidade_alertada",
        lambda oportunidade_id: alertados.append(oportunidade_id) or True,
    )
    monkeypatch.setattr(
        monitor,
        "salvar_ultima_varredura",
        lambda resumo: None,
    )

    resumo = monitor.executar_varredura()

    assert oportunidade.alertado is True
    assert alertados == ["OP-ALERTA"]
    assert resumo["aprovadas"] == 1
    assert resumo["alertas_enviados"] == 1


def test_falha_telegram_mantem_alertado_false(monkeypatch):
    """Falha no Telegram não deve apagar nem marcar a oportunidade."""
    from types import SimpleNamespace

    item = {
        "link": "https://example.com/promocao-sem-alerta",
        "titulo": "Promoção Smiles 80% de bônus",
        "programa": "SMILES",
        "bonus_pct": 80.0,
        "data_publicacao": None,
    }

    config = SimpleNamespace(
        pontos_disponiveis=100_000,
        meta_financeira_minima=900.0,
        programas={
            "SMILES": SimpleNamespace(
                valor_milheiro=20.0,
                ativo=True,
            )
        },
    )

    oportunidade = SimpleNamespace(
        id="OP-SEM-ALERTA",
        alertado=False,
    )

    persistidas = []
    alertados = []

    monkeypatch.setattr(monitor, "carregar_config", lambda: config)
    monkeypatch.setattr(monitor, "carregar_vistos", lambda: set())
    monkeypatch.setattr(monitor, "coletar_todas_fontes", lambda: [item])
    monkeypatch.setattr(monitor, "parsear_item", lambda bruto: bruto)
    monkeypatch.setattr(monitor, "filtrar_relevantes", lambda itens: itens)

    monkeypatch.setattr(
        monitor,
        "calcular_milhas_finais",
        lambda pontos, bonus: 180_000,
    )
    monkeypatch.setattr(
        monitor,
        "calcular_valor_estimado",
        lambda milhas, valor_milheiro: 3_600.0,
    )
    monkeypatch.setattr(
        monitor,
        "avaliar_oportunidade",
        lambda bonus, programa_cfg, cfg: (
            monitor.StatusOportunidade.APROVADA,
            "Oportunidade aprovada",
        ),
    )
    monkeypatch.setattr(
        monitor,
        "criar_oportunidade",
        lambda **kwargs: oportunidade,
    )
    monkeypatch.setattr(
        monitor,
        "salvar_oportunidade",
        lambda op: persistidas.append(op),
    )
    monkeypatch.setattr(
        monitor,
        "salvar_visto",
        lambda item_link: None,
    )
    monkeypatch.setattr(
        monitor,
        "enviar_alerta",
        lambda op: False,
    )
    monkeypatch.setattr(
        monitor,
        "marcar_oportunidade_alertada",
        lambda oportunidade_id: alertados.append(oportunidade_id) or True,
    )
    monkeypatch.setattr(
        monitor,
        "salvar_ultima_varredura",
        lambda resumo: None,
    )

    resumo = monitor.executar_varredura()

    assert persistidas == [oportunidade]
    assert oportunidade.alertado is False
    assert alertados == []
    assert resumo["aprovadas"] == 1
    assert resumo["alertas_enviados"] == 0
