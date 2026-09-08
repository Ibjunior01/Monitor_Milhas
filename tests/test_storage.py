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


def test_salvar_visto_persiste_links_sem_perder_existentes(
    tmp_path,
    monkeypatch,
):
    vistos_path = tmp_path / "vistos.json"

    monkeypatch.setattr(
        storage,
        "VISTOS_PATH",
        vistos_path,
    )

    storage.salvar_visto("https://example.com/1")
    storage.salvar_visto("https://example.com/2")
    storage.salvar_visto("https://example.com/1")

    assert storage.carregar_vistos() == {
        "https://example.com/1",
        "https://example.com/2",
    }


def test_carregar_vistos_com_json_invalido_retorna_vazio(
    tmp_path,
    monkeypatch,
):
    vistos_path = tmp_path / "vistos.json"
    vistos_path.write_text(
        "{arquivo quebrado",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        storage,
        "VISTOS_PATH",
        vistos_path,
    )

    assert storage.carregar_vistos() == set()


def test_marcar_oportunidade_alertada_atualiza_registro(
    tmp_path,
    monkeypatch,
):
    oportunidades_path = tmp_path / "oportunidades.jsonl"

    oportunidades_path.write_text(
        ('{"id":"OP-1","alertado":false}\n{"id":"OP-2","alertado":false}\n'),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        storage,
        "OPORTUNIDADES_PATH",
        oportunidades_path,
    )

    atualizado = storage.marcar_oportunidade_alertada("OP-2")

    registros = storage.carregar_oportunidades()

    assert atualizado is True
    assert registros[0]["alertado"] is False
    assert registros[1]["alertado"] is True


def test_marcar_oportunidade_alertada_id_inexistente(
    tmp_path,
    monkeypatch,
):
    oportunidades_path = tmp_path / "oportunidades.jsonl"

    oportunidades_path.write_text(
        '{"id":"OP-1","alertado":false}\n',
        encoding="utf-8",
    )

    monkeypatch.setattr(
        storage,
        "OPORTUNIDADES_PATH",
        oportunidades_path,
    )

    atualizado = storage.marcar_oportunidade_alertada("NAO-EXISTE")

    assert atualizado is False
