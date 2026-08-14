"""
Repository Intelligence Engine — Architecture Analysis
Detects architectural patterns (MVC, layered, hexagonal, microservices)
by analyzing directory structure, naming conventions, and import patterns.
"""

from __future__ import annotations

from collections import Counter
from pathlib import PurePosixPath

from app.core.logging import get_logger

log = get_logger(__name__)

# Directory patterns that suggest architectural layers
LAYER_PATTERNS = {
    "presentation": ["views", "templates", "pages", "components", "ui", "frontend", "screens", "layouts"],
    "api": ["api", "routes", "routers", "controllers", "endpoints", "handlers", "rest", "graphql"],
    "service": ["services", "usecases", "use_cases", "application", "business", "domain", "interactors"],
    "data": ["models", "repositories", "dal", "dao", "database", "db", "entities", "schemas", "orm"],
    "infrastructure": ["infra", "infrastructure", "config", "core", "utils", "helpers", "lib", "shared", "common"],
}

PATTERN_LABELS = {
    "layered": "Layered Architecture",
    "mvc": "MVC (Model-View-Controller)",
    "hexagonal": "Hexagonal / Ports & Adapters",
    "microservices": "Microservices",
    "monolith": "Monolith",
    "modular": "Modular Monolith",
    "unknown": "Undetermined",
}


def analyze_architecture(
    files: list[dict],
    symbols: list[dict],
    imports: list[dict],
    languages: list[str],
) -> dict:
    """Detect the architectural pattern and layer composition."""
    # Collect all first-level directory names
    dir_names = set()
    dir_file_counts: Counter[str] = Counter()
    for f in files:
        parts = PurePosixPath(f["path"]).parts
        if len(parts) > 1:
            dir_names.add(parts[0].lower())
            dir_file_counts[parts[0].lower()] += 1
        if len(parts) > 2:
            dir_names.add(parts[1].lower())
            dir_file_counts[parts[1].lower()] += 1

    # Score each layer based on directory matches
    layer_scores: dict[str, list[str]] = {layer: [] for layer in LAYER_PATTERNS}
    for layer, keywords in LAYER_PATTERNS.items():
        for kw in keywords:
            if kw in dir_names:
                layer_scores[layer].append(kw)

    # Count how many layers are present
    active_layers = {layer: matches for layer, matches in layer_scores.items() if matches}
    num_layers = len(active_layers)

    # Detect pattern
    pattern, confidence = _classify_pattern(active_layers, dir_names, files, symbols)

    # Build layer details
    layers = []
    for layer_name, matches in active_layers.items():
        layer_files = []
        for f in files:
            parts = PurePosixPath(f["path"]).parts
            if any(m in [p.lower() for p in parts] for m in matches):
                layer_files.append(f["path"])
        layers.append({
            "name": layer_name.capitalize(),
            "description": f"Detected from directories: {', '.join(matches)}",
            "components": matches,
            "file_count": len(layer_files),
        })

    # Build React Flow diagram
    diagram = _build_diagram(layers)

    return {
        "pattern": PATTERN_LABELS.get(pattern, pattern),
        "confidence": confidence,
        "layers": layers,
        "diagram": diagram,
    }


def _classify_pattern(
    active_layers: dict[str, list[str]],
    dir_names: set[str],
    files: list[dict],
    symbols: list[dict],
) -> tuple[str, float]:
    """Classify the architecture pattern."""
    num_layers = len(active_layers)

    # Microservices indicators
    microservice_signals = sum(1 for d in dir_names if d in ("services", "apps", "microservices", "functions"))
    has_docker_compose = any(f["path"].endswith("docker-compose.yml") for f in files)
    has_k8s = any("k8s" in f["path"] or "kubernetes" in f["path"] for f in files)

    if microservice_signals >= 2 or (has_docker_compose and has_k8s):
        return "microservices", 0.75

    # Hexagonal indicators
    hex_dirs = {"ports", "adapters", "domain", "application", "infrastructure"}
    hex_match = len(hex_dirs & dir_names)
    if hex_match >= 3:
        return "hexagonal", 0.80

    # MVC indicators
    mvc_dirs = {"models", "views", "controllers"}
    mvc_match = len(mvc_dirs & dir_names)
    if mvc_match >= 2:
        return "mvc", 0.85

    # Layered architecture
    if num_layers >= 3:
        return "layered", min(0.5 + num_layers * 0.1, 0.90)

    # Modular monolith
    if num_layers >= 2:
        return "modular", 0.60

    if num_layers == 1:
        return "monolith", 0.50

    return "unknown", 0.30


def _build_diagram(layers: list[dict]) -> dict:
    """Build a React Flow compatible diagram."""
    nodes = []
    edges = []
    y_offset = 50

    colors = {
        "Presentation": "rgba(99, 102, 241, 0.15)",
        "Api": "rgba(6, 182, 212, 0.15)",
        "Service": "rgba(168, 85, 247, 0.15)",
        "Data": "rgba(16, 185, 129, 0.15)",
        "Infrastructure": "rgba(245, 158, 11, 0.15)",
    }

    for i, layer in enumerate(layers):
        node_id = f"layer_{i}"
        color = colors.get(layer["name"], "rgba(100,100,100,0.15)")
        nodes.append({
            "id": node_id,
            "position": {"x": 300, "y": y_offset + i * 150},
            "data": {
                "label": f"{layer['name']} Layer\n{layer['file_count']} files",
            },
            "style": {
                "background": color,
                "border": f"1px solid {color.replace('0.15', '0.4')}",
                "borderRadius": "12px",
                "padding": "16px",
                "width": 260,
                "textAlign": "center",
            },
        })

        if i > 0:
            edges.append({
                "id": f"e{i - 1}_{i}",
                "source": f"layer_{i - 1}",
                "target": node_id,
                "animated": True,
            })

    return {"nodes": nodes, "edges": edges}
