import os
import tempfile

import streamlit as st

from visualization.db import get_assets_for_run, get_job_names, get_run_ids
from visualization.graph import build_graph

st.set_page_config(
    page_title="Asset Provenance",
    page_icon="⬡",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
[data-testid="stSidebar"] { background: #0d1117; }
.block-container { padding-top: 1.5rem; }
.meta-label { font-size: 10px; color: #5c6a7a; text-transform: uppercase; letter-spacing: .1em; margin-bottom: 2px; }
.meta-value { font-family: monospace; font-size: 12px; color: #c9d1d9; }
.asset-title { font-family: monospace; font-size: 15px; font-weight: 700; color: #e6a817; margin-bottom: 8px; }
.upstream-chip {
    display: inline-block; padding: 2px 8px; border-radius: 4px;
    background: #161b22; border: 1px solid #30363d;
    font-family: monospace; font-size: 11px; color: #4a9eff; margin: 2px;
}
</style>
""", unsafe_allow_html=True)

# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⬡ provenance")
    st.caption("Dagster asset lineage explorer")
    st.divider()

    try:
        job_names = get_job_names()
    except Exception as e:
        st.error(f"Não foi possível conectar ao banco: {e}")
        st.stop()

    pipeline_filter = st.radio(
        "pipeline",
        ["todos"] + job_names,
        index=0,
        horizontal=True,
    )

    st.divider()

    selected_job = None if pipeline_filter == "todos" else pipeline_filter
    try:
        run_ids = get_run_ids(job_name=selected_job)
    except Exception as e:
        st.error(f"Erro ao buscar runs: {e}")
        st.stop()

    if not run_ids:
        st.warning("Nenhuma execução registrada para este pipeline.")
        st.stop()

    run_options = ["(todos — mais recente por asset)"] + run_ids
    selected_label = st.selectbox("run_id", run_options, index=0)
    run_id = "__all__" if selected_label.startswith("(todos") else selected_label

    st.divider()

# ── Load & filter ─────────────────────────────────────────────────────────────
with st.spinner("carregando proveniência…"):
    assets = get_assets_for_run(run_id)

if pipeline_filter != "todos":
    assets = [a for a in assets if a.get("job_name") == pipeline_filter]

if not assets:
    st.info("Nenhum asset encontrado para esta seleção.")
    st.stop()

# ── Layout ────────────────────────────────────────────────────────────────────
col_graph, col_detail = st.columns([3, 2], gap="medium")

with col_graph:
    st.caption(f"**{len(assets)}** assets · **{sum(1 for a in assets if a['upstream_assets'])}** com dependências upstream")

    net = build_graph(assets)
    with tempfile.NamedTemporaryFile(suffix=".html", delete=False, mode="w", encoding="utf-8") as f:
        net.save_graph(f.name)
        graph_html = open(f.name, encoding="utf-8").read()
    os.unlink(f.name)

    st.components.v1.html(graph_html, height=520, scrolling=False)

    asset_keys = [a["asset_key"] for a in assets]
    selected_key = st.selectbox(
        "inspecionar asset",
        ["— selecione um nó —"] + asset_keys,
        label_visibility="collapsed",
    )

with col_detail:
    if not selected_key or selected_key == "— selecione um nó —":
        st.caption("Selecione um nó acima para ver código-fonte e metadata.")
        st.stop()

    asset = next((a for a in assets if a["asset_key"] == selected_key), None)
    if not asset:
        st.stop()

    st.markdown(f'<div class="asset-title">{asset["asset_key"]}</div>', unsafe_allow_html=True)

    tab_code, tab_meta, tab_output = st.tabs(["source", "meta", "output"])

    with tab_code:
        if asset["asset_code"]:
            st.code(asset["asset_code"], language="python")
        else:
            st.caption("código-fonte não capturado")

    with tab_meta:
        st.markdown('<div class="meta-label">asset_key</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="meta-value">{asset["asset_key"]}</div>', unsafe_allow_html=True)
        st.markdown('<div class="meta-label">run_id</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="meta-value">{asset["run_id"]}</div>', unsafe_allow_html=True)
        st.markdown('<div class="meta-label">return_type</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="meta-value">{asset["return_type"]}</div>', unsafe_allow_html=True)
        st.markdown('<div class="meta-label">finished_at</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="meta-value">{asset["finished_at"]}</div>', unsafe_allow_html=True)

        st.divider()
        if asset["upstream_assets"]:
            st.markdown('<div class="meta-label">upstream_assets</div>', unsafe_allow_html=True)
            chips = "".join(
                f'<span class="upstream-chip">← {up}</span>' for up in asset["upstream_assets"]
            )
            st.markdown(chips, unsafe_allow_html=True)
        else:
            st.caption("asset raiz — sem dependências upstream")

    with tab_output:
        st.caption(f"`return_type`: `{asset['return_type']}`")
        rv = asset["return_value"]
        if rv is None:
            st.caption("NoneType — nenhum valor a exibir")
        elif isinstance(rv, (dict, list)):
            st.json(rv)
        else:
            st.json({"value": rv})
