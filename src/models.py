"""
Modelos de domínio do Monitor de Milhas.
Separados do banco/persistência para facilitar migração futura.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from enum import Enum


class StatusOportunidade(str, Enum):
    APROVADA = "aprovada"
    IGNORADA = "ignorada"
    AGUARDANDO = "aguardando"
    ABAIXO_META = "abaixo_da_meta"


class ProgramaMilhas(str, Enum):
    LATAM = "LATAM"
    SMILES = "SMILES"
    AZUL = "AZUL"
    OUTRO = "OUTRO"


@dataclass
class ConfigPrograma:
    nome: str
    bonus_minimo_pct: float       # % mínimo de bônus para alertar
    valor_milheiro: float         # R$ por 1.000 milhas
    ativo: bool = True


@dataclass
class ConfigUsuario:
    pontos_disponiveis: int
    meta_financeira_minima: float
    programas: dict[str, ConfigPrograma]


@dataclass
class Oportunidade:
    id: str
    titulo: str
    resumo: str
    link: str
    fonte: str
    data_coleta: datetime
    data_publicacao: Optional[datetime]
    programa: str
    bonus_pct: float
    data_validade: Optional[datetime]
    pontos_considerados: int
    milhas_finais: float
    valor_milheiro: float
    valor_estimado: float
    meta_financeira: float
    status: StatusOportunidade
    recomendacao: str
    aprovada: bool = False
    alertado: bool = False
