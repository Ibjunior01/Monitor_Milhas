"""Testes das configurações da aplicação."""

import json

from src import config
from src.models import ConfigPrograma, ConfigUsuario


def test_salvar_e_recarregar_config_preserva_campos(
    tmp_path,
    monkeypatch,
):
    config_path = tmp_path / "config.json"
    cotacao_path = tmp_path / "cotacao_milhas.json"

    config_path.write_text(
        json.dumps(
            {
                "pontos_disponiveis": 32000,
                "meta_financeira_minima": 900.0,
                "programas": {
                    "LATAM": {
                        "bonus_minimo_pct": 20,
                        "ativo": True,
                        "valor_milheiro_fallback": 25.0,
                    }
                },
            }
        ),
        encoding="utf-8",
    )

    cotacao_path.write_text(
        json.dumps({"LATAM": 25.0}),
        encoding="utf-8",
    )

    monkeypatch.setattr(config, "CONFIG_PATH", config_path)
    monkeypatch.setattr(config, "COTACAO_PATH", cotacao_path)

    nova_config = ConfigUsuario(
        pontos_disponiveis=50000,
        meta_financeira_minima=1200.0,
        programas={
            "LATAM": ConfigPrograma(
                nome="LATAM",
                bonus_minimo_pct=35,
                valor_milheiro=27.5,
                ativo=False,
            )
        },
    )

    config.salvar_config(nova_config)

    recarregada = config.carregar_config()

    assert recarregada.pontos_disponiveis == 50000
    assert recarregada.meta_financeira_minima == 1200.0
    assert recarregada.programas["LATAM"].bonus_minimo_pct == 35
    assert recarregada.programas["LATAM"].valor_milheiro == 27.5
    assert recarregada.programas["LATAM"].ativo is False