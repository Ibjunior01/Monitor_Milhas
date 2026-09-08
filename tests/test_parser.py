"""Testes unitários para parser.py"""

import pytest

from src.parser import (
    extrair_bonus,
    extrair_programa,
    extrair_validade,
    filtrar_relevantes,
)


class TestFiltrarRelevantes:
    def test_aceita_esfera_com_programa(self):
        itens = [
            {
                "titulo": ("Esfera oferece bônus na transferência para LATAM Pass"),
                "resumo": "",
                "programa": "LATAM",
                "bonus_pct": None,
            }
        ]

        assert filtrar_relevantes(itens) == itens

    def test_descarta_programa_de_outro_parceiro(self):
        itens = [
            {
                "titulo": ("Livelo oferece 120% de bônus para Azul Fidelidade"),
                "resumo": "",
                "programa": "AZUL",
                "bonus_pct": 120.0,
            }
        ]

        assert filtrar_relevantes(itens) == []

    def test_descarta_clube_smiles_sem_esfera(self):
        itens = [
            {
                "titulo": ("Clube Smiles oferece até 30 mil milhas bônus"),
                "resumo": "",
                "programa": "SMILES",
                "bonus_pct": None,
            }
        ]

        assert filtrar_relevantes(itens) == []


class TestExtrairPrograma:
    def test_latam(self):
        assert extrair_programa("Esfera transfere para LATAM Pass com bônus") == "LATAM"

    def test_smiles(self):
        assert extrair_programa("Promoção Esfera Smiles 80% de bônus") == "SMILES"

    def test_azul(self):
        assert extrair_programa("Azul Fidelidade com bônus de transferência") == "AZUL"

    def test_sem_programa(self):
        assert extrair_programa("Oferta de crédito pessoal do banco") is None

    def test_case_insensitive(self):
        assert extrair_programa("PROMOÇÃO LATAM PASS ESFERA") == "LATAM"


class TestExtrairBonus:
    def test_bonus_percentual_direto(self):
        assert extrair_bonus("Esfera com 30% de bônus para LATAM") == pytest.approx(
            30.0
        )

    def test_bonus_invertido(self):
        assert extrair_bonus("bônus de 70% na transferência") == pytest.approx(70.0)

    def test_mais_percentual(self):
        assert extrair_bonus("+100% bônus Smiles") == pytest.approx(100.0)

    def test_sem_bonus(self):
        assert extrair_bonus("Esfera lança novo cartão de crédito") is None

    def test_bonus_absurdo_ignorado(self):
        # 999% é implausível, deve ser ignorado
        assert extrair_bonus("bônus de 999% incrível") is None


class TestExtrairValidade:
    def test_validade_simples(self):
        dt = extrair_validade("Promoção válida até 31/12/2025")
        assert dt is not None
        assert dt.day == 31
        assert dt.month == 12

    def test_sem_validade(self):
        assert extrair_validade("Esfera com 30% de bônus para LATAM Pass") is None
