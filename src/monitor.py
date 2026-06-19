"""
Orquestrador principal: coleta → parse → cálculo → decisão → storage → alerta.
"""
from datetime import datetime
from src.logger import get_logger
from src.config import carregar_config
from src.sources import coletar_todas_fontes
from src.parser import parsear_item, filtrar_relevantes
from src.calculations import (
    calcular_milhas_finais,
    calcular_valor_estimado,
    avaliar_oportunidade,
)
from src.storage import (
    carregar_vistos,
    salvar_visto,
    salvar_oportunidade,
    criar_oportunidade,
)
from src.telegram_alerts import enviar_alerta
from src.models import StatusOportunidade
from datetime import timedelta

log = get_logger("monitor")

DIAS_MAX_ANTIGUIDADE = 7  # Ignora notícias mais antigas que isso


def _e_recente(item: dict) -> bool:
    """Retorna True se a notícia foi publicada nos últimos DIAS_MAX_ANTIGUIDADE dias."""
    data = item.get("data_publicacao")
    if data is None:
        return True  # Sem data → não descarta, dá benefício da dúvida
    limite = datetime.now() - timedelta(days=DIAS_MAX_ANTIGUIDADE)
    # Remove timezone se existir para comparação simples
    if hasattr(data, "tzinfo") and data.tzinfo is not None:
        data = data.replace(tzinfo=None)
    return data >= limite


def executar_varredura() -> dict:
    """
    Executa ciclo completo de monitoramento.
    Retorna resumo com contagens para log/dashboard.
    """
    log.info("=" * 60)
    log.info(f"Iniciando varredura — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log.info("=" * 60)

    config = carregar_config()
    vistos = carregar_vistos()

    # 1. Coleta
    brutos = coletar_todas_fontes()

    # 2. Deduplica por link (histórico persistido)
    novos = [item for item in brutos if item.get("link") not in vistos]
    log.info(f"Itens novos (não vistos antes): {len(novos)} de {len(brutos)} coletados")

    # 3. Filtra por data (apenas notícias recentes)
    recentes = [item for item in novos if _e_recente(item)]
    descartados_data = len(novos) - len(recentes)
    if descartados_data:
        log.info(f"Descartados por antiguidade (>{DIAS_MAX_ANTIGUIDADE} dias): {descartados_data}")

    # 4. Parse
    parseados = [parsear_item(item) for item in recentes]
    relevantes = filtrar_relevantes(parseados)

    resumo = {
        "total_coletados": len(brutos),
        "novos": len(novos),
        "relevantes": len(relevantes),
        "aprovadas": 0,
        "alertas_enviados": 0,
        "ignoradas": 0,
    }

    # 4. Avaliação + persistência + alertas
    for item in relevantes:
        link = item.get("link", "")
        programa_nome = item.get("programa", "")
        bonus_pct = item.get("bonus_pct")

        # Marca como visto independentemente do resultado
        if link:
            salvar_visto(link)

        # Sem bônus identificado → salva como aguardando para revisão manual
        if bonus_pct is None:
            log.info(f"Sem bônus identificado para {programa_nome}: {item.get('titulo','')[:60]}")
            bonus_pct = 0.0

        programa_cfg = config.programas.get(programa_nome)
        if not programa_cfg:
            log.warning(f"Programa '{programa_nome}' não configurado. Ignorando.")
            continue

        milhas = calcular_milhas_finais(config.pontos_disponiveis, bonus_pct)
        valor = calcular_valor_estimado(milhas, programa_cfg.valor_milheiro)
        status, recomendacao = avaliar_oportunidade(bonus_pct, programa_cfg, config)

        op = criar_oportunidade(
            item=item,
            programa_cfg=programa_cfg,
            config=config,
            status=status,
            recomendacao=recomendacao,
            milhas_finais=milhas,
            valor_estimado=valor,
        )

        salvar_oportunidade(op)

        log.info(
            f"[{status.value.upper()}] {programa_nome} | "
            f"bônus {bonus_pct:.0f}% | "
            f"R$ {valor:,.2f} | {recomendacao[:60]}"
        )

        if status == StatusOportunidade.APROVADA:
            resumo["aprovadas"] += 1
            sucesso = enviar_alerta(op)
            if sucesso:
                resumo["alertas_enviados"] += 1
        else:
            resumo["ignoradas"] += 1

    log.info(
        f"Varredura concluída | "
        f"Aprovadas: {resumo['aprovadas']} | "
        f"Alertas: {resumo['alertas_enviados']} | "
        f"Ignoradas: {resumo['ignoradas']}"
    )
    return resumo