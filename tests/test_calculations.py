"""Testes unitários para calculations.py"""
import pytest
from src.calculations import (
    calcular_milhas_finais,
    calcular_valor_estimado,
    avaliar_oportunidade,
    melhor_opcao,
)
from src.models import ConfigPrograma, ConfigUsuario, StatusOportunidade


def _config_padrao():
    return ConfigUsuario(
        pontos_disponiveis=32000,
        meta_financeira_minima=900.0,
        programas={
            "LATAM":  ConfigPrograma("LATAM",  bonus_minimo_pct=20, valor_milheiro=25.0),
            "SMILES": ConfigPrograma("SMILES", bonus_minimo_pct=70, valor_milheiro=16.0),
            "AZUL":   ConfigPrograma("AZUL",   bonus_minimo_pct=80, valor_milheiro=13.0),
        }
    )


class TestCalcularMilhasFinais:
    def test_sem_bonus(self):
        assert calcular_milhas_finais(32000, 0) == 32000.0

    def test_bonus_30pct(self):
        assert calcular_milhas_finais(32000, 30) == pytest.approx(41600.0)

    def test_bonus_100pct(self):
        assert calcular_milhas_finais(10000, 100) == pytest.approx(20000.0)


class TestCalcularValorEstimado:
    def test_latam(self):
        # 41600 milhas × R$ 25 / 1000 = R$ 1040
        assert calcular_valor_estimado(41600, 25.0) == pytest.approx(1040.0)

    def test_smiles(self):
        assert calcular_valor_estimado(32000, 16.0) == pytest.approx(512.0)


class TestAvaliarOportunidade:
    def setup_method(self):
        self.config = _config_padrao()

    def test_aprovada_latam(self):
        """30% bônus LATAM → 41600 milhas → R$ 1040 > meta R$ 900"""
        cfg = self.config.programas["LATAM"]
        status, rec = avaliar_oportunidade(30, cfg, self.config)
        assert status == StatusOportunidade.APROVADA
        assert "Vale analisar" in rec

    def test_abaixo_meta_financeira(self):
        """21% bônus LATAM → ok para % mas vamos simular valor baixo ajustando meta"""
        self.config.meta_financeira_minima = 2000.0
        cfg = self.config.programas["LATAM"]
        status, rec = avaliar_oportunidade(30, cfg, self.config)
        assert status == StatusOportunidade.ABAIXO_META

    def test_bonus_insuficiente(self):
        """10% bônus LATAM (meta é 20%) → ignorada ou aguardando"""
        cfg = self.config.programas["LATAM"]
        status, rec = avaliar_oportunidade(10, cfg, self.config)
        # Pode ser ignorada (valor também abaixo) ou aguardando (valor ok)
        assert status in (StatusOportunidade.IGNORADA, StatusOportunidade.AGUARDANDO)

    def test_smiles_70pct_exato(self):
        """70% bônus Smiles (exatamente na meta)"""
        cfg = self.config.programas["SMILES"]
        status, _ = avaliar_oportunidade(70, cfg, self.config)
        # 32000 × 1.7 = 54400 milhas × 16/1000 = R$ 870,40 < R$ 900
        assert status == StatusOportunidade.ABAIXO_META


class TestMelhorOpcao:
    def test_retorna_programa_com_maior_valor(self):
        config = _config_padrao()
        bonus = {"LATAM": 30, "SMILES": 70, "AZUL": 80}
        resultado = melhor_opcao(config, bonus)
        # LATAM: R$1040, SMILES: R$870, AZUL: R$499 → LATAM vence
        assert resultado == "LATAM"

    def test_sem_programas(self):
        config = _config_padrao()
        resultado = melhor_opcao(config, {})
        assert resultado == "—"
