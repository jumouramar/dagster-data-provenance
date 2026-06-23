import json

from pyvis.network import Network

_COLORS = {
    "weather":    {"border": "#4a9eff", "background": "#161b22", "highlight": {"border": "#74b9ff", "background": "#1c2230"}},
    "calculator": {"border": "#e6a817", "background": "#161b22", "highlight": {"border": "#fdcb6e", "background": "#251f0d"}},
    "default":    {"border": "#8b949e", "background": "#161b22", "highlight": {"border": "#c9d1d9", "background": "#21262d"}},
}

_PYVIS_OPTIONS = {
    "nodes": {
        "shape": "box",
        "font": {"face": "monospace", "size": 13, "color": "#c9d1d9"},
        "borderWidth": 1,
        "borderWidthSelected": 2,
        "margin": {"top": 8, "right": 12, "bottom": 8, "left": 12},
    },
    "edges": {
        "arrows": {"to": {"enabled": True, "scaleFactor": 0.6}},
        "color": {"color": "#30363d", "highlight": "#4a9eff"},
        "smooth": {"type": "cubicBezier", "forceDirection": "vertical", "roundness": 0.5},
        "width": 1.5,
    },
    "layout": {
        "hierarchical": {
            "enabled": True,
            "direction": "UD",
            "sortMethod": "directed",
            "levelSeparation": 90,
            "nodeSpacing": 230,
        }
    },
    "interaction": {"hover": True, "tooltipDelay": 100, "navigationButtons": False},
    "physics": {"enabled": False},
}


def _pipeline_color(asset_key: str) -> dict:
    if "weather" in asset_key:
        return _COLORS["weather"]
    if "mean" in asset_key or "random" in asset_key or "numbers" in asset_key:
        return _COLORS["calculator"]
    return _COLORS["default"]


def build_graph(assets: list[dict], height: str = "500px") -> Network:
    net = Network(
        height=height,
        width="100%",
        bgcolor="#0d1117",
        font_color="#c9d1d9",
        directed=True,
        notebook=False,
    )
    net.set_options(json.dumps(_PYVIS_OPTIONS))

    for asset in assets:
        key = asset["asset_key"]
        tooltip = (
            f"{key}\n"
            f"type: {asset['return_type']}\n"
            f"run: {asset['run_id'][:12]}…\n"
            f"at: {asset['finished_at']}"
        )
        net.add_node(
            key,
            label=key,
            title=tooltip,
            color=_pipeline_color(key),
        )

    node_ids = set(net.get_nodes())
    seen_edges: set[tuple] = set()
    for asset in assets:
        for upstream in asset["upstream_assets"]:
            if upstream not in node_ids:
                continue
            edge = (upstream, asset["asset_key"])
            if edge not in seen_edges:
                net.add_edge(upstream, asset["asset_key"])
                seen_edges.add(edge)

    return net
