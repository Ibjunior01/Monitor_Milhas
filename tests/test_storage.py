"""Testes da camada de persistência."""

from src import storage


def test_ultima_varredura_independe_de_oportunidades(tmp_path, monkeypatch):
    """
    Uma varredura concluída deve possuir estado próprio,
    mesmo quando nenhuma oportunidade foi encontrada.
    """
    estado_path = tmp_path / "ultima_varredura.json"
    oportunidades_path = tmp_path / "oportunidades.jsonl"

    monkeypatch.setattr(
        storage,
        "ULTIMA_VARREDURA_PATH",
        estado_path,
        raising=False,
    )
    monkeypatch.setattr(
        storage,
        "OPORTUNIDADES_PATH",
        oportunidades_path,
    )

    resumo = {
        "total_coletados": 10,
        "novos": 0,
        "relevantes": 0,
        "aprovadas": 0,
        "alertas_enviados": 0,
        "ignoradas": 0,
    }

    storage.salvar_ultima_varredura(resumo)

    assert not oportunidades_path.exists()

    estado = storage.carregar_ultima_varredura()

    assert estado is not None
    assert estado["status"] == "concluida"
    assert estado["resumo"] == resumo
    assert storage.data_ultima_varredura() == estado["data_execucao"]
