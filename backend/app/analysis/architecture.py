"""
Repository Intelligence Engine — Architecture Analysis
Detects architectural patterns (MVC, layered, hexagonal, microservices)
by analyzing directory structure, naming conventions, and import patterns.
Generates an Archify-grade interactive system architecture diagram with
tiered boundary subsystems, technology tags, and animated data flows.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import PurePosixPath
from typing import Any

from app.core.logging import get_logger

log = get_logger(__name__)

# Core architectural tiers with modern visual styling tokens
TIER_SPECS = [
    {
        "id": "presentation",
        "name": "Presentation",
        "title": "Presentation & Client Layer",
        "badge": "Client UI",
        "color": "#38bdf8",  # Sky / Cyan
        "bg_color": "rgba(56, 189, 248, 0.08)",
        "border_color": "rgba(56, 189, 248, 0.35)",
        "icon": "globe",
        "subsystems": [
            {
                "id": "ui_views",
                "name": "Views & Dashboard Pages",
                "patterns": ["views", "pages", "screens", "templates", "layouts"],
                "icon": "layout",
                "desc": "User-facing dashboard views, application pages, and route navigation shells",
            },
            {
                "id": "ui_components",
                "name": "UI Component Library",
                "patterns": ["components", "widgets", "elements", "ui"],
                "icon": "component",
                "desc": "Reusable glassmorphic UI controls, interactive cards, charts, and modals",
            },
            {
                "id": "ui_state",
                "name": "Client State & Network",
                "patterns": ["hooks", "contexts", "stores", "state", "lib", "api"],
                "icon": "network",
                "desc": "Client-side state management, custom React hooks, and API/WebSocket clients",
            },
        ],
    },
    {
        "id": "api",
        "name": "Api",
        "title": "Gateway & API Layer",
        "badge": "Ingress & Routers",
        "color": "#818cf8",  # Indigo
        "bg_color": "rgba(129, 140, 248, 0.08)",
        "border_color": "rgba(129, 140, 248, 0.35)",
        "icon": "server",
        "subsystems": [
            {
                "id": "api_endpoints",
                "name": "HTTP Routers & Controllers",
                "patterns": ["api", "routers", "routes", "controllers", "endpoints", "handlers", "rest"],
                "icon": "server",
                "desc": "REST API route declarations, parameter validation, and endpoint handlers",
            },
            {
                "id": "api_realtime",
                "name": "Real-time & WebSockets",
                "patterns": ["websocket", "socket", "events", "stream", "channels"],
                "icon": "radio",
                "desc": "Real-time bidirectional WebSocket broadcast channels and progress streams",
            },
            {
                "id": "api_security",
                "name": "Auth & Middleware",
                "patterns": ["middleware", "security", "auth", "guards", "cors"],
                "icon": "shield",
                "desc": "Authentication tokens, CORS policies, rate limiting, and request interceptors",
            },
        ],
    },
    {
        "id": "service",
        "name": "Service",
        "title": "Domain & Services Layer",
        "badge": "Business Logic",
        "color": "#c084fc",  # Purple
        "bg_color": "rgba(192, 132, 252, 0.08)",
        "border_color": "rgba(192, 132, 252, 0.35)",
        "icon": "cpu",
        "subsystems": [
            {
                "id": "service_pipeline",
                "name": "Execution Pipeline & Tasks",
                "patterns": ["pipeline", "tasks", "runner", "workers", "jobs", "celery", "queue"],
                "icon": "workflow",
                "desc": "Asynchronous background orchestrators, scan jobs, and task runners",
            },
            {
                "id": "service_analysis",
                "name": "Analysis & Intelligence Engine",
                "patterns": ["analysis", "intel", "engine", "heuristics", "metrics", "auditing"],
                "icon": "cpu",
                "desc": "Static code analysis engines: architecture, security, debt, and performance",
            },
            {
                "id": "service_parsing",
                "name": "AST Parsers & Language Adapters",
                "patterns": ["parsing", "parser", "ast", "grammar", "tree_sitter"],
                "icon": "file-code",
                "desc": "Multi-language Tree-sitter parsers and AST symbol extraction adapters",
            },
            {
                "id": "service_ai",
                "name": "AI & Reasoning Engine",
                "patterns": ["ai", "rag", "llm", "chat", "ollama", "reasoning"],
                "icon": "sparkles",
                "desc": "Offline AI reasoning, multi-intent classification, and context synthesis",
            },
        ],
    },
    {
        "id": "data",
        "name": "Data",
        "title": "Data & Persistence Layer",
        "badge": "Storage & Schemas",
        "color": "#34d399",  # Emerald
        "bg_color": "rgba(52, 211, 153, 0.08)",
        "border_color": "rgba(52, 211, 153, 0.35)",
        "icon": "database",
        "subsystems": [
            {
                "id": "data_models",
                "name": "ORM Models & Schemas",
                "patterns": ["models", "schemas", "entities", "types", "dto"],
                "icon": "table",
                "desc": "Declarative database entities, validation schemas, and domain objects",
            },
            {
                "id": "data_storage",
                "name": "Relational & Database Storage",
                "patterns": ["database", "db", "dal", "repositories", "alembic", "migrations", "sql"],
                "icon": "database",
                "desc": "Database connection pools, migrations, session factories, and query managers",
            },
            {
                "id": "data_graph",
                "name": "Knowledge Graph & Topology",
                "patterns": ["graph", "neo4j", "networkx", "vector", "qdrant", "search"],
                "icon": "git-fork",
                "desc": "Graph topology repositories, PageRank centrality, and dependency graphs",
            },
        ],
    },
    {
        "id": "infrastructure",
        "name": "Infrastructure",
        "title": "Infrastructure & Core",
        "badge": "Config & Platform",
        "color": "#fbbf24",  # Amber
        "bg_color": "rgba(251, 191, 36, 0.08)",
        "border_color": "rgba(251, 191, 36, 0.35)",
        "icon": "wrench",
        "subsystems": [
            {
                "id": "infra_config",
                "name": "Environment & Settings",
                "patterns": ["config", "settings", "env", "constants"],
                "icon": "sliders",
                "desc": "Configuration variables, environment settings, and runtime profiles",
            },
            {
                "id": "infra_logging",
                "name": "Structured Logging & Telemetry",
                "patterns": ["logging", "logger", "telemetry", "monitor"],
                "icon": "activity",
                "desc": "Structured log formatters, diagnostic telemetry, and health probes",
            },
            {
                "id": "infra_utils",
                "name": "Utilities & Shared Helpers",
                "patterns": ["utils", "helpers", "shared", "common", "tools"],
                "icon": "wrench",
                "desc": "Shared utility functions, file helpers, and general helpers",
            },
        ],
    },
]

# Patterns suggesting architectural styles
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
    calls: list[dict] | None = None,
) -> dict[str, Any]:
    """
    Detect the architectural pattern and layer composition.
    Builds an Archify-grade interactive system architecture diagram with
    subsystem boundary components, technologies, and animated relationships.
    """
    # Collect all first-level and second-level directory names
    dir_names = set()
    for f in files:
        parts = PurePosixPath(f["path"]).parts
        if len(parts) > 1:
            dir_names.add(parts[0].lower())
        if len(parts) > 2:
            dir_names.add(parts[1].lower())

    # Score each layer based on directory matches
    layer_scores: dict[str, list[str]] = {layer: [] for layer in LAYER_PATTERNS}
    for layer, keywords in LAYER_PATTERNS.items():
        for kw in keywords:
            if kw in dir_names:
                layer_scores[layer].append(kw)

    active_layers_dict = {layer: matches for layer, matches in layer_scores.items() if matches}

    # Classify the primary architectural pattern
    pattern, confidence = _classify_pattern(active_layers_dict, dir_names, files, symbols)

    # Build active architectural tiers and their components
    active_tiers, file_to_subsystem = _classify_subsystems(files, symbols)

    # Format layers list for overview cards and backward compatibility
    layers = []
    for tier in active_tiers:
        component_names = [sub["name"] for sub in tier["subsystems"]]
        total_files = sum(len(sub["files"]) for sub in tier["subsystems"])
        layers.append({
            "name": tier["name"],
            "description": f"{tier['title']} ({', '.join(component_names[:3])})",
            "components": component_names,
            "file_count": total_files,
        })

    # If no tiers were detected (e.g. flat single script repo), provide a sensible fallback tier
    if not layers:
        layers.append({
            "name": "Application",
            "description": "Root Application Module",
            "components": ["Core Module"],
            "file_count": len(files),
        })

    # Build the rich React Flow diagram
    diagram = _build_archify_diagram(active_tiers, file_to_subsystem, imports)

    return {
        "pattern": PATTERN_LABELS.get(pattern, pattern),
        "confidence": confidence,
        "layers": layers,
        "diagram": diagram,
    }


def _classify_subsystems(
    files: list[dict],
    symbols: list[dict],
) -> tuple[list[dict[str, Any]], dict[str, str]]:
    """Group all files and symbols into discrete architectural subsystems."""
    # Pre-index symbols by file path
    symbols_by_file: dict[str, list[dict]] = defaultdict(list)
    for s in symbols:
        fp = s.get("file_path", "")
        if fp:
            symbols_by_file[fp].append(s)

    file_to_subsystem: dict[str, str] = {}
    active_tiers: list[dict[str, Any]] = []

    # Map each file to the most specific subsystem
    for tier_spec in TIER_SPECS:
        tier_subsystems: list[dict[str, Any]] = []

        for sub_spec in tier_spec["subsystems"]:
            sub_id = sub_spec["id"]
            patterns = sub_spec["patterns"]
            matching_files: list[dict] = []

            for f in files:
                fpath = f["path"].lower()
                parts = [p.lower() for p in PurePosixPath(f["path"]).parts]

                # Match if any directory part or filename matches the pattern keywords
                is_match = False
                for pat in patterns:
                    if any(pat == p or pat in p for p in parts[:-1]):
                        # Check tier alignment
                        if tier_spec["id"] == "presentation" and not any(x in fpath for x in ["front", "ui", "view", "page", "comp", "src"]):
                            continue
                        is_match = True
                        break
                    elif pat in parts[-1]:
                        is_match = True
                        break

                if is_match and f["path"] not in file_to_subsystem:
                    matching_files.append(f)
                    file_to_subsystem[f["path"]] = sub_id

            if matching_files:
                # Count symbols
                sub_symbols = []
                for mf in matching_files:
                    sub_symbols.extend(symbols_by_file.get(mf["path"], []))

                # Identify technologies
                exts = {PurePosixPath(mf["path"]).suffix for mf in matching_files}
                techs = []
                if any(e in (".tsx", ".jsx", ".vue", ".svelte") for e in exts):
                    techs.append("React / UI")
                if any(e in (".ts", ".js") for e in exts):
                    techs.append("TypeScript")
                if any(e == ".py" for e in exts):
                    techs.append("Python")
                if any(e == ".java" for e in exts):
                    techs.append("Java")
                if any(e in (".go", ".rs", ".cpp", ".c") for e in exts):
                    techs.append("Native")

                key_files = [mf["path"] for mf in matching_files[:4]]

                tier_subsystems.append({
                    "id": sub_id,
                    "name": sub_spec["name"],
                    "tier_id": tier_spec["id"],
                    "tier_name": tier_spec["name"],
                    "tier_badge": tier_spec["badge"],
                    "color": tier_spec["color"],
                    "bg_color": tier_spec["bg_color"],
                    "border_color": tier_spec["border_color"],
                    "icon": sub_spec["icon"],
                    "desc": sub_spec["desc"],
                    "files": matching_files,
                    "symbols_count": len(sub_symbols),
                    "key_files": key_files,
                    "technologies": techs or ["Module"],
                })

        if tier_subsystems:
            active_tiers.append({
                "id": tier_spec["id"],
                "name": tier_spec["name"],
                "title": tier_spec["title"],
                "badge": tier_spec["badge"],
                "color": tier_spec["color"],
                "bg_color": tier_spec["bg_color"],
                "border_color": tier_spec["border_color"],
                "icon": tier_spec["icon"],
                "subsystems": tier_subsystems,
            })

    # Catch remaining unmapped files into an application fallback subsystem
    unmapped_files = [f for f in files if f["path"] not in file_to_subsystem]
    if unmapped_files and not active_tiers:
        # If everything is unmapped, create a unified application component
        active_tiers.append({
            "id": "app",
            "name": "Application",
            "title": "Application Core",
            "badge": "Core",
            "color": "#818cf8",
            "bg_color": "rgba(129, 140, 248, 0.08)",
            "border_color": "rgba(129, 140, 248, 0.35)",
            "icon": "cpu",
            "subsystems": [{
                "id": "sub_app_core",
                "name": "Application Modules",
                "tier_id": "app",
                "tier_name": "Application",
                "tier_badge": "Core",
                "color": "#818cf8",
                "bg_color": "rgba(129, 140, 248, 0.08)",
                "border_color": "rgba(129, 140, 248, 0.35)",
                "icon": "cpu",
                "desc": "Primary codebase logic and module definitions",
                "files": unmapped_files,
                "symbols_count": sum(len(symbols_by_file.get(f["path"], [])) for f in unmapped_files),
                "key_files": [f["path"] for f in unmapped_files[:4]],
                "technologies": ["Core"],
            }],
        })

    return active_tiers, file_to_subsystem


def _build_archify_diagram(
    active_tiers: list[dict[str, Any]],
    file_to_subsystem: dict[str, str],
    imports: list[dict],
) -> dict[str, Any]:
    """
    Constructs a React Flow diagram formatted like Archify:
    - Tiered swimlanes from top to bottom
    - Modern glassmorphic component cards
    - Directed, animated data-flow edges with custom labels
    """
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []

    # Fixed card dimensions for clean spacing
    card_width = 280
    card_gap = 40
    tier_y_spacing = 240
    start_y = 60

    # Collect all subsystems in order
    all_subsystems_by_id = {}
    tier_order_map = {}

    for t_idx, tier in enumerate(active_tiers):
        tier_id = tier["id"]
        tier_order_map[tier_id] = t_idx
        num_subs = len(tier["subsystems"])
        total_row_width = num_subs * card_width + max(0, num_subs - 1) * card_gap
        start_x = max(60, 600 - (total_row_width // 2))

        y_pos = start_y + t_idx * tier_y_spacing

        for s_idx, sub in enumerate(tier["subsystems"]):
            sub_id = sub["id"]
            all_subsystems_by_id[sub_id] = sub
            x_pos = start_x + s_idx * (card_width + card_gap)

            nodes.append({
                "id": sub_id,
                "type": "componentNode",
                "position": {"x": x_pos, "y": y_pos},
                "data": {
                    "id": sub_id,
                    "label": f"{sub['name']}\n{len(sub['files'])} files",
                    "name": sub["name"],
                    "tier": tier["id"],
                    "tier_name": tier["name"],
                    "tier_badge": tier["badge"],
                    "color": tier["color"],
                    "bg_color": tier["bg_color"],
                    "border_color": tier["border_color"],
                    "icon": sub["icon"],
                    "description": sub["desc"],
                    "file_count": len(sub["files"]),
                    "symbols_count": sub["symbols_count"],
                    "key_files": sub["key_files"],
                    "technologies": sub["technologies"],
                },
                "style": {
                    "width": card_width,
                    "background": tier["bg_color"],
                    "border": f"1px solid {tier['border_color']}",
                    "borderRadius": "14px",
                    "padding": "16px",
                    "color": "#f8fafc",
                },
            })

    # Track cross-subsystem dependencies from AST imports
    import_edge_counts: Counter[tuple[str, str]] = Counter()
    for imp in imports:
        src_file = imp.get("file_path", "")
        module_name = imp.get("module", "")
        src_sub = file_to_subsystem.get(src_file)

        if not src_sub:
            continue

        # Look for target subsystem
        tgt_sub = None
        for target_path, s_id in file_to_subsystem.items():
            clean_tgt = target_path.replace("/", ".").replace("\\", ".")
            if module_name and (module_name in clean_tgt or clean_tgt in module_name):
                if s_id != src_sub:
                    tgt_sub = s_id
                    break

        if tgt_sub:
            import_edge_counts[(src_sub, tgt_sub)] += 1

    created_pairs = set()

    # Add edges found via AST imports
    for (src_id, tgt_id), count in import_edge_counts.most_common(20):
        if (src_id, tgt_id) in created_pairs or src_id not in all_subsystems_by_id or tgt_id not in all_subsystems_by_id:
            continue

        src_sub = all_subsystems_by_id[src_id]
        tgt_sub = all_subsystems_by_id[tgt_id]
        edge_color = src_sub["color"]

        edges.append({
            "id": f"e_{src_id}_{tgt_id}",
            "source": src_id,
            "target": tgt_id,
            "type": "smoothstep",
            "animated": True,
            "label": f"Imports ({count})" if count > 1 else "Imports",
            "style": {
                "stroke": edge_color,
                "strokeWidth": 2,
            },
            "markerEnd": {
                "type": "arrowclosed",
                "color": edge_color,
            },
            "data": {
                "label": f"Imports ({count})",
                "count": count,
            },
        })
        created_pairs.add((src_id, tgt_id))

    # Add natural top-down tier flow edges if missing (Pres -> API -> Service -> Data -> Infra)
    tier_components_map = defaultdict(list)
    for sub_id, sub in all_subsystems_by_id.items():
        tier_components_map[sub["tier_id"]].append(sub_id)

    tier_flow_sequence = [
        ("presentation", "api", "HTTP / REST & WS"),
        ("api", "service", "Dispatches & Invokes"),
        ("service", "data", "Queries & Persists"),
        ("service", "infrastructure", "Config & Telemetry"),
        ("api", "infrastructure", "Config & Auth"),
    ]

    for from_tier, to_tier, flow_label in tier_flow_sequence:
        from_subs = tier_components_map.get(from_tier, [])
        to_subs = tier_components_map.get(to_tier, [])

        if from_subs and to_subs:
            # Check if there is already an edge between these tiers
            has_tier_edge = any(
                (src in from_subs and tgt in to_subs)
                for (src, tgt) in created_pairs
            )
            if not has_tier_edge:
                # Link primary representative components
                src_id = from_subs[0]
                tgt_id = to_subs[0]
                src_sub = all_subsystems_by_id[src_id]
                edge_color = src_sub["color"]

                edges.append({
                    "id": f"flow_{src_id}_{tgt_id}",
                    "source": src_id,
                    "target": tgt_id,
                    "type": "smoothstep",
                    "animated": True,
                    "label": flow_label,
                    "style": {
                        "stroke": edge_color,
                        "strokeWidth": 2,
                    },
                    "markerEnd": {
                        "type": "arrowclosed",
                        "color": edge_color,
                    },
                    "data": {
                        "label": flow_label,
                        "count": 1,
                    },
                })
                created_pairs.add((src_id, tgt_id))

    return {"nodes": nodes, "edges": edges}


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
