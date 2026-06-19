"""
Cálculos financeiros do Monitor de Milhas.
Funções puras — sem I/O, fáceis de testar unitariamente.
"""
from src.models import ConfigPrograma, ConfigUsuario, StatusOportunidade


def calcular_milhas_finais(pontos: int, bonus_pct: float) -> float:
    """Aplica o percentual de bônus sobre os pontos disponíveis."""
    return pontos * (1 + bonus_pct / 100)


def calcular_valor_estimado(milhas: float, valor_milheiro: float) -> float:
    """
    Converte milhas em reais.
    valor_milheiro = R$ por 1.000 milhas.
    """
    return (milhas / 1000) * valor_milheiro


def avaliar_oportunidade(
    bonus_pct: float,
    programa_cfg: ConfigPrograma,
    config: ConfigUsuario,
) -> tuple[StatusOportunidade, str]:
    """
    Decide o status e recomendação de uma oportunidade.
    Retorna (StatusOportunidade, recomendacao_texto).
    """
    pontos = config.pontos_disponiveis
    milhas = calcular_milhas_finais(pontos, bonus_pct)
    valor = calcular_valor_estimado(milhas, programa_cfg.valor_milheiro)
    meta_bonus = programa_cfg.bonus_minimo_pct
    meta_financeira = config.meta_financeira_minima

    bonus_ok = bonus_pct >= meta_bonus
    financeiro_ok = valor >= meta_financeira

    if bonus_ok and financeiro_ok:
        status = StatusOportunidade.APROVADA
        recomendacao = "✅ Vale analisar — bônus e valor financeiro atingem as metas."
    elif bonus_ok and not financeiro_ok:
        status = StatusOportunidade.ABAIXO_META
        diff = meta_financeira - valor
        recomendacao = (
            f"⚠️ Bônus bom ({bonus_pct:.0f}%), mas valor estimado R$ {valor:.0f} "
            f"está R$ {diff:.0f} abaixo da meta."
        )
    elif not bonus_ok and financeiro_ok:
        status = StatusOportunidade.AGUARDANDO
        recomendacao = (
            f"⏳ Valor financeiro ok (R$ {valor:.0f}), mas bônus "
            f"{bonus_pct:.0f}% abaixo da meta de {meta_bonus:.0f}%."
        )
    else:
        status = StatusOportunidade.IGNORADA
        recomendacao = (
            f"❌ Aguardar promoção melhor. Bônus {bonus_pct:.0f}% "
            f"(meta {meta_bonus:.0f}%) e valor R$ {valor:.0f} "
            f"(meta R$ {meta_financeira:.0f}) abaixo do esperado."
        )

    return status, recomendacao


def resumo_simulacao(
    pontos: int, bonus_pct: float, programa_cfg: ConfigPrograma
) -> dict:
    """Retorna dict completo para exibir no dashboard ou no alerta."""
    milhas = calcular_milhas_finais(pontos, bonus_pct)
    valor = calcular_valor_estimado(milhas, programa_cfg.valor_milheiro)
    return {
        "programa": programa_cfg.nome,
        "pontos": pontos,
        "bonus_pct": bonus_pct,
        "milhas_finais": milhas,
        "valor_milheiro": programa_cfg.valor_milheiro,
        "valor_estimado": valor,
    }


def melhor_opcao(config: ConfigUsuario, bonus_por_programa: dict[str, float]) -> str:
    """Dado um dict {programa: bonus_pct}, retorna qual programa dá maior valor."""
    melhor = None
    melhor_valor = -1.0
    for prog_nome, bonus in bonus_por_programa.items():
        cfg = config.programas.get(prog_nome)
        if not cfg:
            continue
        valor = calcular_valor_estimado(
            calcular_milhas_finais(config.pontos_disponiveis, bonus),
            cfg.valor_milheiro,
        )
        if valor > melhor_valor:
            melhor_valor = valor
            melhor = prog_nome
    return melhor or "—"
