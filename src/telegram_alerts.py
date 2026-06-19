"""
Envio de alertas via Telegram Bot API.
Credenciais lidas exclusivamente de variáveis de ambiente.
"""
import requests
from src.models import Oportunidade
from src.config import telegram_credentials
from src.logger import get_logger

log = get_logger("telegram")

TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"


def _formatar_mensagem(op: Oportunidade) -> str:
    data_val = op.data_validade.strftime("%d/%m/%Y") if op.data_validade else "não informada"
    data_pub = op.data_publicacao.strftime("%d/%m/%Y") if op.data_publicacao else "—"
    return (
        f"🎯 *ALERTA DE MILHAS — {op.programa}*\n\n"
        f"📰 *Notícia:* {op.titulo}\n"
        f"📅 Publicado em: {data_pub}\n"
        f"⏳ Validade: {data_val}\n\n"
        f"💡 *Bônus encontrado:* {op.bonus_pct:.0f}%\n"
        f"📦 Pontos considerados: {op.pontos_considerados:,}\n"
        f"✈️ Milhas finais estimadas: {op.milhas_finais:,.0f}\n"
        f"💰 Valor do milheiro ({op.programa}): R$ {op.valor_milheiro:.2f}\n"
        f"💵 *Valor total estimado: R$ {op.valor_estimado:,.2f}*\n"
        f"🎯 Meta mínima: R$ {op.meta_financeira:,.2f}\n\n"
        f"📋 *Recomendação:* {op.recomendacao}\n\n"
        f"🔗 [Ver fonte]({op.link})"
    )


def enviar_alerta(op: Oportunidade) -> bool:
    """
    Envia mensagem no Telegram.
    Retorna True se enviou com sucesso.
    """
    token, chat_id = telegram_credentials()
    if not token or not chat_id:
        log.warning("Alerta Telegram ignorado: credenciais ausentes.")
        return False

    url = TELEGRAM_API.format(token=token)
    payload = {
        "chat_id": chat_id,
        "text": _formatar_mensagem(op),
        "parse_mode": "Markdown",
        "disable_web_page_preview": False,
    }

    try:
        resp = requests.post(url, json=payload, timeout=10)
        resp.raise_for_status()
        log.info(f"Alerta enviado para Telegram: {op.programa} {op.bonus_pct}%")
        return True
    except requests.exceptions.Timeout:
        log.error("Timeout ao enviar alerta Telegram.")
    except requests.exceptions.HTTPError as e:
        log.error(f"Erro HTTP Telegram: {e} | Body: {resp.text[:200]}")
    except Exception as e:
        log.error(f"Erro inesperado ao enviar alerta Telegram: {e}")
    return False


def enviar_resumo_diario(oportunidades: list[Oportunidade]) -> bool:
    """Envia resumo com todas as oportunidades aprovadas do dia."""
    token, chat_id = telegram_credentials()
    if not token or not chat_id:
        return False

    aprovadas = [o for o in oportunidades if o.aprovada]
    if not aprovadas:
        log.info("Nenhuma oportunidade aprovada para resumo diário.")
        return False

    linhas = [f"📊 *RESUMO DO DIA — {len(aprovadas)} oportunidade(s) aprovada(s)*\n"]
    for op in aprovadas:
        linhas.append(
            f"• *{op.programa}* — {op.bonus_pct:.0f}% bônus → "
            f"R$ {op.valor_estimado:,.2f} estimado"
        )

    texto = "\n".join(linhas)
    url = TELEGRAM_API.format(token=token)
    try:
        resp = requests.post(
            url,
            json={"chat_id": chat_id, "text": texto, "parse_mode": "Markdown"},
            timeout=10,
        )
        resp.raise_for_status()
        return True
    except Exception as e:
        log.error(f"Erro ao enviar resumo diário: {e}")
        return False
