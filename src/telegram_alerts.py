"""
Envio de alertas via Telegram Bot API.

Credenciais são lidas exclusivamente de variáveis de ambiente.
"""

import requests

from src.config import telegram_credentials
from src.logger import get_logger
from src.models import Oportunidade

log = get_logger("telegram")

TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"
REQUEST_TIMEOUT = 10


def _formatar_mensagem(op: Oportunidade) -> str:
    data_val = (
        op.data_validade.strftime("%d/%m/%Y") if op.data_validade else "não informada"
    )
    data_pub = op.data_publicacao.strftime("%d/%m/%Y") if op.data_publicacao else "—"

    return (
        f"🎯 *ALERTA DE MILHAS — {op.programa}*\n\n"
        f"📰 *Notícia:* {op.titulo}\n"
        f"📅 Publicado em: {data_pub}\n"
        f"⏳ Validade: {data_val}\n\n"
        f"💡 *Bônus encontrado:* {op.bonus_pct:.0f}%\n"
        f"📦 Pontos considerados: {op.pontos_considerados:,}\n"
        f"✈️ Milhas finais estimadas: {op.milhas_finais:,.0f}\n"
        f"💰 Valor do milheiro ({op.programa}): "
        f"R$ {op.valor_milheiro:.2f}\n"
        f"💵 *Valor total estimado: R$ {op.valor_estimado:,.2f}*\n"
        f"🎯 Meta mínima: R$ {op.meta_financeira:,.2f}\n\n"
        f"📋 *Recomendação:* {op.recomendacao}\n\n"
        f"🔗 [Ver fonte]({op.link})"
    )


def _enviar_payload(payload: dict, contexto: str) -> bool:
    """Envia payload para o Telegram sem expor credenciais em logs."""
    token, chat_id = telegram_credentials()

    if not token or not chat_id:
        log.warning(
            "Telegram ignorado (%s): credenciais ausentes.",
            contexto,
        )
        return False

    url = TELEGRAM_API.format(token=token)

    corpo = {
        "chat_id": chat_id,
        **payload,
    }

    try:
        response = requests.post(
            url,
            json=corpo,
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()

        try:
            resposta = response.json()
        except ValueError:
            log.error(
                "Resposta inválida do Telegram (%s).",
                contexto,
            )
            return False

        if not isinstance(resposta, dict) or resposta.get("ok") is not True:
            log.error(
                "Telegram rejeitou a requisição (%s).",
                contexto,
            )
            return False

        return True

    except requests.exceptions.Timeout:
        log.error(
            "Timeout ao acessar Telegram (%s).",
            contexto,
        )

    except requests.exceptions.HTTPError:
        status = getattr(response, "status_code", "desconhecido")

        log.error(
            "Erro HTTP Telegram (%s): status=%s.",
            contexto,
            status,
        )

    except requests.exceptions.RequestException as exc:
        log.error(
            "Erro de rede Telegram (%s): %s.",
            contexto,
            type(exc).__name__,
        )

    except Exception as exc:
        log.error(
            "Erro inesperado Telegram (%s): %s.",
            contexto,
            type(exc).__name__,
        )

    return False


def enviar_alerta(op: Oportunidade) -> bool:
    """Envia uma oportunidade aprovada para o Telegram."""
    sucesso = _enviar_payload(
        {
            "text": _formatar_mensagem(op),
            "parse_mode": "Markdown",
            "disable_web_page_preview": False,
        },
        contexto="alerta",
    )

    if sucesso:
        log.info(
            "Alerta enviado para Telegram: %s %.0f%%",
            op.programa,
            op.bonus_pct,
        )

    return sucesso


def enviar_resumo_diario(
    oportunidades: list[Oportunidade],
) -> bool:
    """Envia resumo das oportunidades aprovadas do dia."""
    aprovadas = [o for o in oportunidades if o.aprovada]

    if not aprovadas:
        log.info("Nenhuma oportunidade aprovada para resumo diário.")
        return False

    linhas = [(f"📊 *RESUMO DO DIA — {len(aprovadas)} oportunidade(s) aprovada(s)*\n")]

    for op in aprovadas:
        linhas.append(
            f"• *{op.programa}* — "
            f"{op.bonus_pct:.0f}% bônus → "
            f"R$ {op.valor_estimado:,.2f} estimado"
        )

    texto = "\n".join(linhas)

    return _enviar_payload(
        {
            "text": texto,
            "parse_mode": "Markdown",
        },
        contexto="resumo diário",
    )
