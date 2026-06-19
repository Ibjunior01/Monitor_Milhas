"""
Dashboard Monitor de Milhas — Streamlit
Uso: streamlit run dashboard.py
"""
import json
from pathlib import Path
from datetime import datetime

import streamlit as st
import pandas as pd

# ── Configuração da página ──────────────────────────────────────────────────
st.set_page_config(
    page_title="Monitor de Milhas · Esfera",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS personalizado ───────────────────────────────────────────────────────
st.markdown("""
<style>
  /* Fonte e fundo */
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
  html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

  /* Cards KPI */
  .kpi-card {
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
    border: 1px solid #0f3460;
    border-radius: 12px;
    padding: 20px 24px;
    text-align: center;
    color: #e0e0e0;
  }
  .kpi-label { font-size: 0.75rem; text-transform: uppercase; letter-spacing: 1px; color: #888; margin-bottom: 6px; }
  .kpi-value { font-size: 2rem; font-weight: 700; color: #00d4ff; }
  .kpi-sub   { font-size: 0.8rem; color: #aaa; margin-top: 4px; }

  /* Badge status */
  .badge-aprovada  { background:#00875a; color:#fff; border-radius:4px; padding:2px 8px; font-size:.75rem; }
  .badge-ignorada  { background:#5a5a5a; color:#fff; border-radius:4px; padding:2px 8px; font-size:.75rem; }
  .badge-aguardando { background:#c07c00; color:#fff; border-radius:4px; padding:2px 8px; font-size:.75rem; }
  .badge-abaixo_da_meta { background:#8b1a1a; color:#fff; border-radius:4px; padding:2px 8px; font-size:.75rem; }

  /* Seção */
  .section-title { font-size:1.1rem; font-weight:700; color:#00d4ff; margin:16px 0 8px; border-bottom:1px solid #0f3460; padding-bottom:4px; }
</style>
""", unsafe_allow_html=True)

# ── Paths ───────────────────────────────────────────────────────────────────
DATA_DIR = Path("data")
CONFIG_PATH = DATA_DIR / "config.json"
COTACAO_PATH = DATA_DIR / "cotacao_milhas.json"
OPORTUNIDADES_PATH = DATA_DIR / "oportunidades.jsonl"


# ── Helpers ─────────────────────────────────────────────────────────────────
def _load_json(path: Path, default):
    if not path.exists():
        return default
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def _save_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _load_oportunidades() -> list[dict]:
    if not OPORTUNIDADES_PATH.exists():
        return []
    ops = []
    with open(OPORTUNIDADES_PATH, encoding="utf-8") as f:
        for linha in f:
            linha = linha.strip()
            if linha:
                try:
                    ops.append(json.loads(linha))
                except Exception:
                    pass
    return ops


def _calcular(pontos: int, bonus_pct: float, milheiro: float) -> tuple[float, float]:
    milhas = pontos * (1 + bonus_pct / 100)
    valor = (milhas / 1000) * milheiro
    return milhas, valor


# ── Sidebar — Configurações ─────────────────────────────────────────────────
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/airplane-take-off.png", width=64)
    st.title("Monitor de Milhas")
    st.caption("Esfera → LATAM · Smiles · Azul")
    st.divider()

    cfg_raw = _load_json(CONFIG_PATH, {
        "pontos_disponiveis": 32000,
        "meta_financeira_minima": 900.0,
        "programas": {
            "LATAM": {"bonus_minimo_pct": 20, "ativo": True},
            "SMILES": {"bonus_minimo_pct": 70, "ativo": True},
            "AZUL":   {"bonus_minimo_pct": 80, "ativo": True},
        }
    })
    cotacoes = _load_json(COTACAO_PATH, {"LATAM": 25.0, "SMILES": 16.0, "AZUL": 13.0})

    st.markdown("### ⚙️ Configurações")
    pontos = st.number_input(
        "Pontos Esfera disponíveis", min_value=0, step=1000,
        value=cfg_raw.get("pontos_disponiveis", 32000)
    )
    meta_fin = st.number_input(
        "Meta financeira mínima (R$)", min_value=0.0, step=50.0,
        value=float(cfg_raw.get("meta_financeira_minima", 900.0))
    )

    st.markdown("#### Metas de bônus por programa")
    programas_cfg = cfg_raw.get("programas", {})
    meta_latam  = st.number_input("LATAM — bônus mínimo (%)",  min_value=0, max_value=500, step=5,
                                   value=int(programas_cfg.get("LATAM", {}).get("bonus_minimo_pct", 20)))
    meta_smiles = st.number_input("Smiles — bônus mínimo (%)", min_value=0, max_value=500, step=5,
                                   value=int(programas_cfg.get("SMILES", {}).get("bonus_minimo_pct", 70)))
    meta_azul   = st.number_input("Azul — bônus mínimo (%)",   min_value=0, max_value=500, step=5,
                                   value=int(programas_cfg.get("AZUL", {}).get("bonus_minimo_pct", 80)))

    st.markdown("#### Valor do milheiro (R$ / 1.000 milhas)")
    mil_latam  = st.number_input("LATAM",  min_value=0.0, step=0.5, value=float(cotacoes.get("LATAM",  25.0)))
    mil_smiles = st.number_input("Smiles", min_value=0.0, step=0.5, value=float(cotacoes.get("SMILES", 16.0)))
    mil_azul   = st.number_input("Azul",   min_value=0.0, step=0.5, value=float(cotacoes.get("AZUL",   13.0)))

    if st.button("💾 Salvar configurações", use_container_width=True):
        novo_cfg = {
            "pontos_disponiveis": pontos,
            "meta_financeira_minima": meta_fin,
            "programas": {
                "LATAM":   {"bonus_minimo_pct": meta_latam,  "ativo": True, "valor_milheiro_fallback": mil_latam},
                "SMILES":  {"bonus_minimo_pct": meta_smiles, "ativo": True, "valor_milheiro_fallback": mil_smiles},
                "AZUL":    {"bonus_minimo_pct": meta_azul,   "ativo": True, "valor_milheiro_fallback": mil_azul},
            }
        }
        nova_cotacao = {"LATAM": mil_latam, "SMILES": mil_smiles, "AZUL": mil_azul}
        _save_json(CONFIG_PATH, novo_cfg)
        _save_json(COTACAO_PATH, nova_cotacao)
        st.success("Configurações salvas!")
        st.rerun()

    st.divider()
    if st.button("🔍 Executar varredura agora", use_container_width=True, type="primary"):
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

oportunidades = _load_oportunidades()
total = len(oportunidades)
aprovadas_total = sum(1 for o in oportunidades if o.get("status") == "aprovada")
ignoradas_total = sum(1 for o in oportunidades if o.get("status") in ("ignorada", "abaixo_da_meta"))
ultima = max((o.get("data_coleta", "") for o in oportunidades), default="—")
if ultima != "—":
    try:
        ultima = datetime.fromisoformat(ultima).strftime("%d/%m/%Y %H:%M")
    except Exception:
        pass

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.markdown(f"""
    <div class="kpi-card">
      <div class="kpi-label">Pontos Esfera</div>
      <div class="kpi-value">{pontos:,}</div>
      <div class="kpi-sub">disponíveis</div>
    </div>""", unsafe_allow_html=True)

with col2:
    st.markdown(f"""
    <div class="kpi-card">
      <div class="kpi-label">Oportunidades encontradas</div>
      <div class="kpi-value">{total}</div>
      <div class="kpi-sub">{aprovadas_total} aprovadas</div>
    </div>""", unsafe_allow_html=True)

with col3:
    st.markdown(f"""
    <div class="kpi-card">
      <div class="kpi-label">Meta financeira</div>
      <div class="kpi-value">R$ {meta_fin:,.0f}</div>
      <div class="kpi-sub">por transferência</div>
    </div>""", unsafe_allow_html=True)

with col4:
    st.markdown(f"""
    <div class="kpi-card">
      <div class="kpi-label">Última varredura</div>
      <div class="kpi-value" style="font-size:1.1rem">{ultima}</div>
      <div class="kpi-sub">&nbsp;</div>
    </div>""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── Simulador comparativo ────────────────────────────────────────────────────
st.markdown('<div class="section-title">🔢 Simulador Comparativo</div>', unsafe_allow_html=True)

col_sim1, col_sim2, col_sim3 = st.columns(3)
with col_sim1:
    bonus_sim_latam  = st.slider("Bônus LATAM (%)",  0, 200, 30, key="sim_latam")
with col_sim2:
    bonus_sim_smiles = st.slider("Bônus Smiles (%)", 0, 200, 80, key="sim_smiles")
with col_sim3:
    bonus_sim_azul   = st.slider("Bônus Azul (%)",   0, 200, 100, key="sim_azul")

cenarios = [
    {"Programa": "LATAM",  "Bônus (%)": bonus_sim_latam,  "Milheiro (R$)": mil_latam},
    {"Programa": "Smiles", "Bônus (%)": bonus_sim_smiles, "Milheiro (R$)": mil_smiles},
    {"Programa": "Azul",   "Bônus (%)": bonus_sim_azul,   "Milheiro (R$)": mil_azul},
]

rows = []
melhor_valor = -1
melhor_prog = ""
for c in cenarios:
    milhas, valor = _calcular(pontos, c["Bônus (%)"], c["Milheiro (R$)"])
    meta_b = {"LATAM": meta_latam, "Smiles": meta_smiles, "Azul": meta_azul}[c["Programa"]]
    bate_bonus = c["Bônus (%)"] >= meta_b
    bate_fin   = valor >= meta_fin
    status_sim = "✅ Aprovada" if (bate_bonus and bate_fin) else ("⚠️ Bônus ok" if bate_bonus else "❌ Abaixo")
    rows.append({
        "Programa": c["Programa"],
        "Bônus (%)": f"{c['Bônus (%)']}%",
        "Milhas Finais": f"{milhas:,.0f}",
        "Milheiro (R$)": f"R$ {c['Milheiro (R$)']:.2f}",
        "Valor Estimado": f"R$ {valor:,.2f}",
        "Meta Bônus": f"{meta_b}%",
        "Status": status_sim,
    })
    if valor > melhor_valor:
        melhor_valor = valor
        melhor_prog = c["Programa"]

df_sim = pd.DataFrame(rows)
st.dataframe(df_sim, use_container_width=True, hide_index=True)
st.info(f"🏆 **Melhor opção atual no simulador:** {melhor_prog} — R$ {melhor_valor:,.2f} estimado")

# ── Gráfico de barras ────────────────────────────────────────────────────────
st.markdown('<div class="section-title">📊 Comparativo de Valor Estimado</div>', unsafe_allow_html=True)

chart_data = {}
for c in cenarios:
    _, valor = _calcular(pontos, c["Bônus (%)"], c["Milheiro (R$)"])
    chart_data[c["Programa"]] = round(valor, 2)

df_chart = pd.DataFrame.from_dict(
    {"Valor Estimado (R$)": chart_data}, orient="index"
).T
st.bar_chart(df_chart)

# ── Histórico de oportunidades ───────────────────────────────────────────────
st.markdown('<div class="section-title">📋 Histórico de Oportunidades</div>', unsafe_allow_html=True)

if not oportunidades:
    st.info("Nenhuma oportunidade encontrada ainda. Execute uma varredura para começar.")
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
        o for o in reversed(oportunidades)
        if o.get("status") in filtro_status
        and o.get("programa") in filtro_programa
    ]

    if not filtradas:
        st.warning("Nenhuma oportunidade com os filtros selecionados.")
    else:
        for op in filtradas[:50]:  # Limita a 50 para performance
            with st.expander(
                f"[{op.get('programa','?')}] {op.get('bonus_pct', 0):.0f}% bônus | "
                f"R$ {op.get('valor_estimado', 0):,.2f} | {op.get('titulo','')[:60]}"
            ):
                col_a, col_b = st.columns(2)
                with col_a:
                    st.write(f"**Programa:** {op.get('programa','—')}")
                    st.write(f"**Bônus:** {op.get('bonus_pct', 0):.0f}%")
                    st.write(f"**Pontos:** {op.get('pontos_considerados', 0):,}")
                    st.write(f"**Milhas finais:** {op.get('milhas_finais', 0):,.0f}")
                with col_b:
                    st.write(f"**Valor estimado:** R$ {op.get('valor_estimado', 0):,.2f}")
                    st.write(f"**Meta:** R$ {op.get('meta_financeira', 0):,.2f}")
                    st.write(f"**Status:** {op.get('status','—')}")
                    data_c = op.get("data_coleta", "—")
                    if data_c != "—":
                        try:
                            data_c = datetime.fromisoformat(data_c).strftime("%d/%m/%Y %H:%M")
                        except Exception:
                            pass
                    st.write(f"**Coletado:** {data_c}")

                st.write(f"**Recomendação:** {op.get('recomendacao', '—')}")
                if op.get("link"):
                    st.markdown(f"[🔗 Ver fonte]({op.get('link')})")

st.divider()
st.caption("Monitor de Milhas · Esfera · MVP v1.0 — Dados para análise manual. Não transfere pontos automaticamente.")
