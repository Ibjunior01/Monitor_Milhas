"""
Dashboard Monitor de Milhas — Streamlit
Uso: streamlit run dashboard.py
"""

from datetime import datetime, timedelta, timezone

import altair as alt
import pandas as pd
import streamlit as st

from src.calculations import (
    calcular_milhas_finais,
    calcular_valor_estimado,
)
from src.config import carregar_config, salvar_config
from src.state_sync import sincronizar_estado_remoto
from src.storage import (
    carregar_oportunidades,
    data_ultima_varredura,
)

HORARIO_BRASIL = timezone(timedelta(hours=-3))


def _formatar_data_hora(valor: str | None) -> str:
    """Formata timestamp ISO para horário UTC-3."""
    if not valor:
        return "—"

    try:
        data = datetime.fromisoformat(valor)

        if data.tzinfo is not None:
            data = data.astimezone(HORARIO_BRASIL)

        return data.strftime("%d/%m/%Y %H:%M")

    except (TypeError, ValueError):
        return valor


# ── Configuração da página ──────────────────────────────────────────────────
st.set_page_config(
    page_title="Monitor de Milhas · Esfera",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="auto",
)

# Sincroniza uma vez ao abrir cada sessão do dashboard.
if "estado_remoto_verificado" not in st.session_state:
    st.session_state["resultado_sync"] = sincronizar_estado_remoto()
    st.session_state["estado_remoto_verificado"] = True

# ── CSS personalizado ───────────────────────────────────────────────────────
st.markdown(
    """
<style>
  /* Fonte e fundo */
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
  html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

  /* Grid responsivo dos KPIs */
  .kpi-grid {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 16px;
    margin: 8px 0 24px;
  }

  .kpi-card {
    min-width: 0;
    min-height: 132px;

    background: var(--secondary-background-color);
    border: 1px solid rgba(128, 128, 128, 0.28);

    border-radius: 12px;
    padding: 18px 20px;
    text-align: center;

    color: var(--text-color);

    display: flex;
    flex-direction: column;
    justify-content: center;
  }

  .kpi-label {
    font-size: 0.72rem;
    line-height: 1.35;
    text-transform: uppercase;
    letter-spacing: 0.08rem;

    color: var(--text-color);
    opacity: 0.68;

    margin-bottom: 8px;
  }

  .kpi-value {
    font-size: clamp(1.45rem, 2.3vw, 2rem);
    line-height: 1.15;
    font-weight: 700;

    color: var(--primary-color);

    overflow-wrap: anywhere;
  }

  .kpi-sub {
    font-size: 0.78rem;

    color: var(--text-color);
    opacity: 0.72;

    margin-top: 6px;
  }

  @media (max-width: 1000px) {
    .kpi-grid {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }
  }

  @media (max-width: 640px) {
    .kpi-grid {
      grid-template-columns: 1fr;
      gap: 10px;
    }

    .kpi-card {
      min-height: 108px;
      padding: 14px 16px;
    }
  }

  /* Badge status */
  .badge-aprovada  { background:#00875a; color:#fff; border-radius:4px; padding:2px 8px; font-size:.75rem; }
  .badge-ignorada  { background:#5a5a5a; color:#fff; border-radius:4px; padding:2px 8px; font-size:.75rem; }
  .badge-aguardando { background:#c07c00; color:#fff; border-radius:4px; padding:2px 8px; font-size:.75rem; }
  .badge-abaixo_da_meta { background:#8b1a1a; color:#fff; border-radius:4px; padding:2px 8px; font-size:.75rem; }

  /* Seção */
    .section-title {
    font-size: 1.1rem;
    font-weight: 700;

    color: var(--primary-color);

    margin: 16px 0 8px;
    padding-bottom: 6px;

    border-bottom: 1px solid rgba(128, 128, 128, 0.28);
  }'


  /* Evita esmagamento visual em telas menores */
  [data-testid="stDataFrame"] {
    overflow-x: auto;
  }

</style>
""",
    unsafe_allow_html=True,
)


# ── Sidebar — Configurações ─────────────────────────────────────────────────
with st.sidebar:
    st.image(
        "https://img.icons8.com/fluency/96/airplane-take-off.png",
        width=64,
    )
    st.title("Monitor de Milhas")
    st.caption("Esfera → LATAM · Smiles · Azul")
    st.divider()

    cfg = carregar_config()

    latam_cfg = cfg.programas["LATAM"]
    smiles_cfg = cfg.programas["SMILES"]
    azul_cfg = cfg.programas["AZUL"]

    st.markdown("### ⚙️ Configurações")

    pontos = st.number_input(
        "Pontos Esfera disponíveis",
        min_value=0,
        step=1000,
        value=int(cfg.pontos_disponiveis),
    )

    meta_fin = st.number_input(
        "Meta financeira mínima (R$)",
        min_value=0.0,
        step=50.0,
        value=float(cfg.meta_financeira_minima),
    )

    # ── Metas de bônus ──────────────────────────────────────────────────────
    with st.expander("🎯 Metas de bônus por programa"):
        meta_latam = st.number_input(
            "LATAM — bônus mínimo (%)",
            min_value=0,
            max_value=500,
            step=5,
            value=int(latam_cfg.bonus_minimo_pct),
            key="meta_latam",
        )

        meta_smiles = st.number_input(
            "Smiles — bônus mínimo (%)",
            min_value=0,
            max_value=500,
            step=5,
            value=int(smiles_cfg.bonus_minimo_pct),
            key="meta_smiles",
        )

        meta_azul = st.number_input(
            "Azul — bônus mínimo (%)",
            min_value=0,
            max_value=500,
            step=5,
            value=int(azul_cfg.bonus_minimo_pct),
            key="meta_azul",
        )

    # ── Valor do milheiro ───────────────────────────────────────────────────
    with st.expander("💰 Valor do milheiro"):
        mil_latam = st.number_input(
            "LATAM (R$ / 1.000 milhas)",
            min_value=0.0,
            step=0.5,
            value=float(latam_cfg.valor_milheiro),
            key="mil_latam",
        )

        mil_smiles = st.number_input(
            "Smiles (R$ / 1.000 milhas)",
            min_value=0.0,
            step=0.5,
            value=float(smiles_cfg.valor_milheiro),
            key="mil_smiles",
        )

        mil_azul = st.number_input(
            "Azul (R$ / 1.000 milhas)",
            min_value=0.0,
            step=0.5,
            value=float(azul_cfg.valor_milheiro),
            key="mil_azul",
        )

    # ── Programas monitorados ───────────────────────────────────────────────
    with st.expander("📡 Programas monitorados"):
        ativo_latam = st.checkbox(
            "Monitorar LATAM",
            value=latam_cfg.ativo,
            key="ativo_latam",
        )

        ativo_smiles = st.checkbox(
            "Monitorar Smiles",
            value=smiles_cfg.ativo,
            key="ativo_smiles",
        )

        ativo_azul = st.checkbox(
            "Monitorar Azul",
            value=azul_cfg.ativo,
            key="ativo_azul",
        )

    # ── Salvar configurações ────────────────────────────────────────────────
    if st.button(
        "💾 Salvar configurações",
        use_container_width=True,
    ):
        cfg.pontos_disponiveis = int(pontos)
        cfg.meta_financeira_minima = float(meta_fin)

        latam_cfg.bonus_minimo_pct = float(meta_latam)
        latam_cfg.valor_milheiro = float(mil_latam)
        latam_cfg.ativo = ativo_latam

        smiles_cfg.bonus_minimo_pct = float(meta_smiles)
        smiles_cfg.valor_milheiro = float(mil_smiles)
        smiles_cfg.ativo = ativo_smiles

        azul_cfg.bonus_minimo_pct = float(meta_azul)
        azul_cfg.valor_milheiro = float(mil_azul)
        azul_cfg.ativo = ativo_azul

        salvar_config(cfg)

        st.success("Configurações salvas!")
        st.rerun()

    # ── Dados e automação ───────────────────────────────────────────────────
    st.caption("Dados e automação")

    if st.button(
        "🔄 Atualizar dados remotos",
        use_container_width=True,
    ):
        resultado_sync = sincronizar_estado_remoto()
        st.session_state["resultado_sync"] = resultado_sync

        if resultado_sync["status"] == "atualizado":
            st.success("Dados remotos atualizados.")

        elif resultado_sync["status"] == "local_atual":
            st.info("Os dados locais já são os mais recentes.")

        elif resultado_sync["status"] == "sem_estado_remoto":
            st.info("Ainda não há estado remoto disponível.")

        else:
            st.warning(
                "Não foi possível sincronizar com o GitHub. "
                "Os dados locais foram mantidos."
            )

    st.divider()

    if st.button(
        "🔍 Executar varredura agora",
        use_container_width=True,
        type="primary",
    ):
        with st.spinner("Executando varredura..."):
            try:
                from src.monitor import executar_varredura

                resumo = executar_varredura()

                st.success(
                    f"Concluído! {resumo['aprovadas']} aprovadas | "
                    f"{resumo['alertas_enviados']} alertas enviados"
                )

                st.rerun()

            except Exception as e:
                st.error(f"Erro: {e}")


# ── Main — KPIs ─────────────────────────────────────────────────────────────
st.title("✈️ Monitor de Milhas · Esfera")

oportunidades = carregar_oportunidades()
total = len(oportunidades)
aprovadas_total = sum(1 for o in oportunidades if o.get("status") == "aprovada")
ignoradas_total = sum(
    1 for o in oportunidades if o.get("status") in ("ignorada", "abaixo_da_meta")
)

ultima = _formatar_data_hora(data_ultima_varredura())

resultado_sync = st.session_state.get(
    "resultado_sync",
    {"status": "local_atual"},
)

status_sync = resultado_sync.get("status")

if status_sync == "atualizado":
    origem_dados = "Sincronizado com GitHub"
elif status_sync == "erro":
    origem_dados = "Dados locais"
elif status_sync == "sem_estado_remoto":
    origem_dados = "Estado local"
else:
    origem_dados = "Dados atualizados"

kpi_html = (
    f'<div class="kpi-grid">'
    f'<div class="kpi-card">'
    f'<div class="kpi-label">Pontos Esfera</div>'
    f'<div class="kpi-value">{pontos:,}</div>'
    f'<div class="kpi-sub">disponíveis</div>'
    f"</div>"
    f'<div class="kpi-card">'
    f'<div class="kpi-label">Oportunidades encontradas</div>'
    f'<div class="kpi-value">{total}</div>'
    f'<div class="kpi-sub">{aprovadas_total} aprovadas</div>'
    f"</div>"
    f'<div class="kpi-card">'
    f'<div class="kpi-label">Meta financeira</div>'
    f'<div class="kpi-value">R$ {meta_fin:,.0f}</div>'
    f'<div class="kpi-sub">por transferência</div>'
    f"</div>"
    f'<div class="kpi-card">'
    f'<div class="kpi-label">Última varredura</div>'
    f'<div class="kpi-value">{ultima}</div>'
    f'<div class="kpi-sub">{origem_dados} · horário local</div>'
    f"</div>"
    f"</div>"
)

st.markdown(kpi_html, unsafe_allow_html=True)


# ── Simulador comparativo ────────────────────────────────────────────────────
st.markdown(
    '<div class="section-title">🔢 Simulador Comparativo</div>', unsafe_allow_html=True
)

with st.container():
    bonus_sim_latam = st.slider(
        "Bônus LATAM (%)",
        0,
        200,
        30,
        key="sim_latam",
    )

    bonus_sim_smiles = st.slider(
        "Bônus Smiles (%)",
        0,
        200,
        80,
        key="sim_smiles",
    )

    bonus_sim_azul = st.slider(
        "Bônus Azul (%)",
        0,
        200,
        100,
        key="sim_azul",
    )

cenarios = [
    {"Programa": "LATAM", "Bônus (%)": bonus_sim_latam, "Milheiro (R$)": mil_latam},
    {"Programa": "Smiles", "Bônus (%)": bonus_sim_smiles, "Milheiro (R$)": mil_smiles},
    {"Programa": "Azul", "Bônus (%)": bonus_sim_azul, "Milheiro (R$)": mil_azul},
]

rows = []
melhor_valor = -1
melhor_prog = ""
melhor_aprovada_valor = -1
melhor_aprovada_prog = ""
for c in cenarios:
    milhas = calcular_milhas_finais(
        pontos,
        c["Bônus (%)"],
    )

    valor = calcular_valor_estimado(
        milhas,
        c["Milheiro (R$)"],
    )
    meta_b = {"LATAM": meta_latam, "Smiles": meta_smiles, "Azul": meta_azul}[
        c["Programa"]
    ]
    bate_bonus = c["Bônus (%)"] >= meta_b
    bate_fin = valor >= meta_fin
    status_sim = (
        "✅ Aprovada"
        if (bate_bonus and bate_fin)
        else ("⚠️ Valor abaixo da meta" if bate_bonus else "❌ Bônus abaixo da meta")
    )
    if bate_bonus and bate_fin and valor > melhor_aprovada_valor:
        melhor_aprovada_valor = valor
        melhor_aprovada_prog = c["Programa"]
    rows.append(
        {
            "Programa": c["Programa"],
            "Bônus (%)": f"{c['Bônus (%)']}%",
            "Milhas Finais": f"{milhas:,.0f}",
            "Milheiro (R$)": f"R$ {c['Milheiro (R$)']:.2f}",
            "Valor Estimado": f"R$ {valor:,.2f}",
            "Meta Bônus": f"{meta_b}%",
            "Status": status_sim,
        }
    )
    if valor > melhor_valor:
        melhor_valor = valor
        melhor_prog = c["Programa"]

df_sim = pd.DataFrame(rows)

st.dataframe(
    df_sim,
    use_container_width=True,
    hide_index=True,
    height=180,
)

if melhor_aprovada_prog:
    st.success(
        f"🏆 **Melhor opção que atende às metas:** "
        f"{melhor_aprovada_prog} — "
        f"R$ {melhor_aprovada_valor:,.2f} estimado"
    )
else:
    st.warning(
        "⚠️ **Nenhum cenário atende simultaneamente às metas "
        "de bônus e valor financeiro.** "
        f"O maior valor estimado no momento é {melhor_prog} — "
        f"R$ {melhor_valor:,.2f}."
    )

# ── Gráfico de barras ────────────────────────────────────────────────────────
st.markdown(
    '<div class="section-title">📊 Comparativo de Valor Estimado</div>',
    unsafe_allow_html=True,
)

chart_data = {}
for c in cenarios:
    milhas = calcular_milhas_finais(
        pontos,
        c["Bônus (%)"],
    )
    valor = calcular_valor_estimado(
        milhas,
        c["Milheiro (R$)"],
    )
    chart_data[c["Programa"]] = round(valor, 2)

df_chart = pd.DataFrame(
    [
        {
            "Programa": programa,
            "Valor Estimado (R$)": valor,
        }
        for programa, valor in chart_data.items()
    ]
)

valor_maximo = max(chart_data.values(), default=0)
limite_superior = max(valor_maximo * 1.15, 100)

grafico = (
    alt.Chart(df_chart)
    .mark_bar()
    .encode(
        x=alt.X(
            "Programa:N",
            sort=["LATAM", "Smiles", "Azul"],
            title=None,
        ),
        y=alt.Y(
            "Valor Estimado (R$):Q",
            scale=alt.Scale(
                domain=[0, limite_superior],
                nice=False,
            ),
            title="Valor estimado (R$)",
        ),
        tooltip=[
            alt.Tooltip(
                "Programa:N",
                title="Programa",
            ),
            alt.Tooltip(
                "Valor Estimado (R$):Q",
                title="Valor estimado",
                format=",.2f",
            ),
        ],
    )
    .properties(
        height=320,
    )
)

st.altair_chart(
    grafico,
    use_container_width=True,
)

# ── Histórico de oportunidades ───────────────────────────────────────────────
st.markdown(
    '<div class="section-title">📋 Histórico de Oportunidades</div>',
    unsafe_allow_html=True,
)

if not oportunidades:
    st.info(
        "Nenhuma oportunidade Esfera encontrada no período monitorado. "
        "O sistema continua acompanhando LATAM, Smiles e Azul "
        "de acordo com as metas configuradas."
    )
else:
    filtro_status = st.multiselect(
        "Filtrar por status",
        options=["aprovada", "ignorada", "aguardando", "abaixo_da_meta"],
        default=["aprovada", "aguardando", "abaixo_da_meta"],
    )
    filtro_programa = st.multiselect(
        "Filtrar por programa",
        options=["LATAM", "SMILES", "AZUL"],
        default=["LATAM", "SMILES", "AZUL"],
    )

    filtradas = [
        o
        for o in reversed(oportunidades)
        if o.get("status") in filtro_status and o.get("programa") in filtro_programa
    ]

    if not filtradas:
        st.warning("Nenhuma oportunidade com os filtros selecionados.")
    else:
        for op in filtradas[:50]:  # Limita a 50 para performance
            with st.expander(
                f"[{op.get('programa', '?')}] {op.get('bonus_pct', 0):.0f}% bônus | "
                f"R$ {op.get('valor_estimado', 0):,.2f} | {op.get('titulo', '')[:60]}"
            ):
                col_a, col_b = st.columns(2)
                with col_a:
                    st.write(f"**Programa:** {op.get('programa', '—')}")
                    st.write(f"**Bônus:** {op.get('bonus_pct', 0):.0f}%")
                    st.write(f"**Pontos:** {op.get('pontos_considerados', 0):,}")
                    st.write(f"**Milhas finais:** {op.get('milhas_finais', 0):,.0f}")
                with col_b:
                    st.write(
                        f"**Valor estimado:** R$ {op.get('valor_estimado', 0):,.2f}"
                    )
                    st.write(f"**Meta:** R$ {op.get('meta_financeira', 0):,.2f}")
                    st.write(f"**Status:** {op.get('status', '—')}")
                    data_c = _formatar_data_hora(op.get("data_coleta"))
                    st.write(f"**Coletado:** {data_c}")

                st.write(f"**Recomendação:** {op.get('recomendacao', '—')}")
                if op.get("link"):
                    st.markdown(f"[🔗 Ver fonte]({op.get('link')})")

st.divider()
st.caption(
    "Monitor de Milhas · Esfera · MVP v1.0 — Dados para análise manual. Não transfere pontos automaticamente."
)
