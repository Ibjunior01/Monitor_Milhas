"""
Carrega configurações do arquivo config.json e variáveis de ambiente.
Projetado para migração futura para banco de dados sem alterar o restante do código.
"""
import json
import os
from pathlib import Path
from dotenv import load_dotenv

from src.models import ConfigPrograma, ConfigUsuario
from src.logger import get_logger

load_dotenv()
log = get_logger("config")

DATA_DIR = Path(__file__).parent.parent / "data"
CONFIG_PATH = DATA_DIR / "config.json"
COTACAO_PATH = DATA_DIR / "cotacao_milhas.json"


def carregar_config() -> ConfigUsuario:
    """Lê config.json e cotacao_milhas.json e retorna ConfigUsuario."""
    if not CONFIG_PATH.exists():
        _criar_config_padrao()

    with open(CONFIG_PATH, encoding="utf-8") as f:
        raw = json.load(f)

    with open(COTACAO_PATH, encoding="utf-8") as f:
        cotacoes: dict[str, float] = json.load(f)

    programas: dict[str, ConfigPrograma] = {}
    for nome, cfg in raw["programas"].items():
        programas[nome] = ConfigPrograma(
            nome=nome,
            bonus_minimo_pct=cfg["bonus_minimo_pct"],
            valor_milheiro=cotacoes.get(nome, cfg.get("valor_milheiro_fallback", 20.0)),
            ativo=cfg.get("ativo", True),
        )

    return ConfigUsuario(
        pontos_disponiveis=raw["pontos_disponiveis"],
        meta_financeira_minima=raw["meta_financeira_minima"],
        programas=programas,
    )


def salvar_config(config: ConfigUsuario) -> None:
    """Persiste alterações do usuário (ex: feitas pelo dashboard)."""
    with open(CONFIG_PATH, encoding="utf-8") as f:
        raw = json.load(f)

    raw["pontos_disponiveis"] = config.pontos_disponiveis
    raw["meta_financeira_minima"] = config.meta_financeira_minima

    for nome, prog in config.programas.items():
        if nome in raw["programas"]:
            raw["programas"][nome]["bonus_minimo_pct"] = prog.bonus_minimo_pct

    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(raw, f, ensure_ascii=False, indent=2)

    # Atualiza cotações separadamente
    cotacoes = {nome: prog.valor_milheiro for nome, prog in config.programas.items()}
    with open(COTACAO_PATH, "w", encoding="utf-8") as f:
        json.dump(cotacoes, f, ensure_ascii=False, indent=2)

    log.info("Configurações salvas.")


def _criar_config_padrao() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    config_padrao = {
        "pontos_disponiveis": 32000,
        "meta_financeira_minima": 900.0,
        "programas": {
            "LATAM": {"bonus_minimo_pct": 20, "ativo": True, "valor_milheiro_fallback": 25.0},
            "SMILES": {"bonus_minimo_pct": 70, "ativo": True, "valor_milheiro_fallback": 16.0},
            "AZUL": {"bonus_minimo_pct": 80, "ativo": True, "valor_milheiro_fallback": 13.0},
        },
    }
    cotacao_padrao = {"LATAM": 25.0, "SMILES": 16.0, "AZUL": 13.0}

    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config_padrao, f, ensure_ascii=False, indent=2)

    with open(COTACAO_PATH, "w", encoding="utf-8") as f:
        json.dump(cotacao_padrao, f, ensure_ascii=False, indent=2)

    log.info("Arquivos de configuração padrão criados em data/")


def telegram_credentials() -> tuple[str, str]:
    token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
    if not token or not chat_id:
        log.warning("Credenciais Telegram não configuradas no .env")
    return token, chat_id
