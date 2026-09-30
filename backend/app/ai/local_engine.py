"""
Repository Intelligence Engine — Local AI & Code Reasoning Engine
100% offline, deterministic code reasoning engine that generates grounded,
structured answers with exact file and graph citations.
Requires zero external API keys (no OpenAI, Anthropic, NVIDIA, or Ollama).
Outputs clean, simple, readable text with no raw '#' or '*' markdown symbols.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import re
from typing import Any, Dict, List, Optional

from app.core.config import settings
from app.core.logging import get_logger
from app.graph import get_graph_repository
from app.models.schemas import ChatMessage, ChatResponse, Citation

log = get_logger(__name__)


def _clean_text(text: str) -> str:
    """
    Format output cleanly and strip all '#' and '*' characters.
    Headers become capitalized section labels with colons.
    Bold and italic markers are removed.
    Bullet points remain clean using standard '-' dashes.
    """
    if not text:
        return ""

    # 1. Transform markdown headings into clean Section Titles with colons
    def _heading_repl(match):
        header_text = match.group(2).strip()
        if not header_text.endswith(":"):
            header_text = f"{header_text}:"
        return f"{header_text}\n"

    cleaned = re.sub(r"^(#{1,6})\s+(.+)$", _heading_repl, text, flags=re.MULTILINE)

    # 2. Remove markdown bold and italic: **text** -> text, *text* -> text
    cleaned = re.sub(r"\*\*([^*]+)\*\*", r"\1", cleaned)
    cleaned = re.sub(r"\*([^*]+)\*", r"\1", cleaned)

    # 3. Remove any remaining stray '#' and '*' characters
    cleaned = cleaned.replace("#", "").replace("*", "")

    # 4. Clean up any double colons
    cleaned = re.sub(r"::\s*", ": ", cleaned)

    # 5. Normalize multiple consecutive blank lines
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)

    return cleaned.strip()


class LocalReasoningEngine:
    """
    Offline code intelligence engine.
    Analyzes user queries, traverses the knowledge graph, scans README documentation,
    and constructs precise, professional responses with zero external API dependencies.
    """

    def __init__(self) -> None:
        pass

    async def answer(
        self,
        query: str,
        history: List[ChatMessage],
        repo_id: str,
        results_summary: Optional[Dict[str, Any]] = None,
        repo_info: Optional[Dict[str, Any]] = None,
    ) -> ChatResponse:
        """Analyze the query intent and synthesize a grounded, cited response."""
        summary = results_summary or {}
        info = repo_info or {}
        q = query.lower().strip()

        readme_data = self._load_readme_context(repo_id, info.get("clone_path"))

        # Intent 1: What is this repository / Explain the project
        if any(phrase in q for phrase in [
            "explain what this", "what is this", "about this repo", "what does this",
            "tell me about", "project about", "overview of", "summary of", "explain repository",
            "what is nexusgrid", "what is this project", "who is it for", "purpose",
        ]):
            res = await self._handle_explain_project_query(query, summary, info, readme_data)
            return self._format_response(res)

        # Intent 2: How to run / Install / Setup / Getting Started
        if any(phrase in q for phrase in [
            "how to run", "how to install", "how to start", "getting started", "setup",
            "prerequisites", "run instructions", "start the server", "run command",
            "build the project", "how do i run",
        ]):
            res = await self._handle_run_and_setup_query(query, summary, info, readme_data)
            return self._format_response(res)

        # Intent 3: Entry points & Main execution flow
        if any(phrase in q for phrase in [
            "entry point", "main file", "where to start", "execution start", "how it starts",
            "index file", "main entry",
        ]):
            res = await self._handle_entry_points_query(query, summary, info, repo_id)
            return self._format_response(res)

        # Intent 4: Tech Stack & Languages
        if any(phrase in q for phrase in [
            "tech stack", "technology", "technologies", "what language", "framework", "libraries",
        ]):
            res = await self._handle_tech_stack_query(query, summary, info)
            return self._format_response(res)

        # Intent 5: Health Score & Quality
        if any(phrase in q for phrase in [
            "health score", "code quality", "why is the score", "score breakdown", "how healthy",
        ]):
            res = await self._handle_health_score_query(query, summary, info)
            return self._format_response(res)

        # Intent 6: Security & Vulnerabilities
        if any(w in q for w in ["security", "vulnerabilit", "cve", "secret", "password", "token", "injection", "owasp"]):
            res = await self._handle_security_query(query, summary, repo_id)
            return self._format_response(res)

        # Intent 7: Architecture & Patterns
        if any(w in q for w in ["architecture", "pattern", "structure", "layer", "design", "monolith", "mvc", "hexagonal"]):
            res = await self._handle_architecture_query(query, summary, repo_id)
            return self._format_response(res)

        # Intent 8: Performance & Bottlenecks
        if any(w in q for w in ["performance", "bottleneck", "n+1", "speed", "slow", "latency", "memory"]):
            res = await self._handle_performance_query(query, summary, repo_id)
            return self._format_response(res)

        # Intent 9: Dependencies & Cycles
        if any(w in q for w in ["dependenc", "circular", "cycle", "import", "package", "library"]):
            res = await self._handle_dependency_query(query, summary, repo_id)
            return self._format_response(res)

        # Intent 10: APIs & Endpoints
        if any(w in q for w in ["api", "endpoint", "route", "http", "rest", "graphql", "handler"]):
            res = await self._handle_api_query(query, summary, repo_id)
            return self._format_response(res)

        # Intent 11: Database & Schemas
        if any(w in q for w in ["database", "table", "schema", "model", "migration", "entity", "sql", "orm"]):
            res = await self._handle_database_query(query, summary, repo_id)
            return self._format_response(res)

        # Intent 12: Technical Debt & Smells
        if any(w in q for w in ["debt", "quality", "complexity", "refactor", "cleanup", "smell"]):
            res = await self._handle_tech_debt_query(query, summary, repo_id)
            return self._format_response(res)

        # Intent 13: Git & Contributors
        if any(w in q for w in ["git", "commit", "author", "contributor", "churn", "hotspot"]):
            res = await self._handle_git_query(query, summary, repo_id)
            return self._format_response(res)

        # Intent 14: Specific Symbol or File search
        symbol_match = await self._search_symbol_or_file(query, repo_id)
        if symbol_match:
            return self._format_response(symbol_match)

        # Default: Grounded Repository Overview
        res = await self._handle_overview_query(query, summary, info, readme_data)
        return self._format_response(res)

    def _format_response(self, resp: ChatResponse) -> ChatResponse:
        """Sanitize response to remove any raw '#' and '*' symbols."""
        resp.answer = _clean_text(resp.answer)
        return resp

    # ── Context Extraction from Files / README ────────────────

    def _load_readme_context(self, repo_id: str, clone_path: Optional[str] = None) -> Dict[str, Any]:
        """Search clone path and storage directory for README documentation and package files."""
        candidate_paths = []
        if clone_path:
            candidate_paths.append(Path(clone_path))
        candidate_paths.append(Path(r"\app\repos") / repo_id)
        candidate_paths.append(Path.home() / ".rie" / "repos" / repo_id)

        context: Dict[str, Any] = {
            "title": "",
            "description": "",
            "features": [],
            "audience": [],
            "how_to_run": [],
            "raw_summary": "",
            "source_file": "",
        }

        found_dir = None
        for p in candidate_paths:
            if p.exists() and p.is_dir():
                found_dir = p
                break

        if not found_dir:
            return context

        # Check Documentation/README.md first (often richer), then root README
        doc_candidates = [
            found_dir / "Documentation" / "README.md",
            found_dir / "Documentation" / "DEVELOPER_README.md",
            found_dir / "README.md",
            found_dir / "readme.md",
            found_dir / "README.rst",
            found_dir / "README.txt",
        ]

        text_content = ""
        for doc_file in doc_candidates:
            if doc_file.exists():
                try:
                    txt = doc_file.read_text(encoding="utf-8", errors="replace")
                    if len(txt.strip()) > 50:
                        text_content += f"\n\n--- Source: {doc_file.name} ---\n" + txt
                        if not context["source_file"]:
                            context["source_file"] = str(doc_file.relative_to(found_dir))
                except Exception:
                    pass

        if not text_content:
            # Try reading package.json or pyproject.toml
            pkg_file = found_dir / "package.json"
            if pkg_file.exists():
                try:
                    data = json.loads(pkg_file.read_text(encoding="utf-8", errors="replace"))
                    context["title"] = data.get("name", "")
                    context["description"] = data.get("description", "")
                    if "scripts" in data:
                        context["how_to_run"] = [f"npm run {k}: {v}" for k, v in list(data["scripts"].items())[:6]]
                except Exception:
                    pass
            return context

        # Parse text content
        lines = [line.strip() for line in text_content.splitlines()]
        paragraphs = []
        current_para = []

        for line in lines:
            if not line:
                if current_para:
                    paragraphs.append(" ".join(current_para))
                    current_para = []
            elif not line.startswith(("#", "---", "```", "![", "[!")):
                current_para.append(line)
        if current_para:
            paragraphs.append(" ".join(current_para))

        # First meaningful paragraphs usually explain the project
        meaningful_paras = [p for p in paragraphs if len(p) > 60 and not p.startswith(("|", "http", "Copyright"))]
        if meaningful_paras:
            context["description"] = "\n\n".join(meaningful_paras[:3])

        # Extract features (bullet points)
        for line in lines:
            if line.startswith(("- ", "* ")) and len(line) > 15:
                bullet = line.lstrip("-* ").strip()
                if not any(x in bullet for x in ["http", "license", "badge", "npm install"]):
                    context["features"].append(bullet)
                    if len(context["features"]) >= 8:
                        break

        # Extract setup / run snippets
        run_cmds = []
        in_code_block = False
        current_block = []
        for line in lines:
            if line.startswith("```"):
                if in_code_block:
                    block_text = "\n".join(current_block)
                    if any(k in block_text for k in ["npm ", "python ", "pip ", "yarn ", "docker", "manage.py"]):
                        run_cmds.append(block_text)
                    current_block = []
                    in_code_block = False
                else:
                    in_code_block = True
            elif in_code_block:
                current_block.append(line)
        if run_cmds:
            context["how_to_run"] = run_cmds[:3]

        return context

    # ── Specialized Intent Handlers ─────────────────────────

    async def _handle_explain_project_query(
        self,
        query: str,
        summary: Dict[str, Any],
        info: Dict[str, Any],
        readme: Dict[str, Any],
    ) -> ChatResponse:
        repo_name = info.get("name") or "This repository"
        arch = summary.get("architecture") or {}
        pattern = arch.get("pattern", "Modular Architecture")
        langs = info.get("languages") or []
        lang_str = ", ".join(langs) if langs else "Python / TypeScript"

        citations: List[Citation] = []
        if readme.get("source_file"):
            citations.append(
                Citation(
                    type="file",
                    reference=readme["source_file"],
                    snippet=f"Project Documentation: {repo_name}",
                    relevance_score=0.99,
                )
            )

        lines = [
            f"Repository Overview: {repo_name}\n",
        ]

        if readme.get("description"):
            lines.append(readme["description"])
        else:
            lines.append(
                f"{repo_name} is a software platform engineered using a {pattern} design, primarily built with {lang_str}."
            )

        lines.append("")

        if readme.get("features"):
            lines.append("Key Capabilities and Features:")
            for f in readme["features"][:6]:
                lines.append(f"- {f}")
            lines.append("")

        lines.append("Technical Architecture:")
        lines.append(f"- Architecture Pattern: {pattern}")
        lines.append(f"- Primary Languages: {lang_str}")
        if info.get("total_files"):
            lines.append(f"- Codebase Scope: {info.get('total_files'):,} files, {info.get('total_lines', 0):,} lines of code")
        if info.get("health_score") is not None:
            lines.append(f"- Health Score: {round(info.get('health_score'))}/100")

        return ChatResponse(
            answer="\n".join(lines),
            citations=citations,
            model_used="RIE Local Intelligence Engine (Offline / Deterministic)",
            reasoning_type="general",
        )

    async def _handle_run_and_setup_query(
        self,
        query: str,
        summary: Dict[str, Any],
        info: Dict[str, Any],
        readme: Dict[str, Any],
    ) -> ChatResponse:
        repo_name = info.get("name", "Project")
        lines = [
            f"How to Run and Setup {repo_name}:\n",
        ]

        if readme.get("how_to_run"):
            lines.append("Commands and Setup Instructions from Documentation:")
            for cmd in readme["how_to_run"]:
                lines.append(cmd)
                lines.append("")
        else:
            langs = info.get("languages", [])
            fws = info.get("frameworks", [])
            lines.append("Standard Execution Commands:")
            if "Python" in langs:
                lines.append("- Python Virtual Environment: python -m venv venv")
                lines.append("- Install Dependencies: pip install -r requirements.txt")
                if "Django" in fws:
                    lines.append("- Run Database Migrations: python manage.py migrate")
                    lines.append("- Start Django Server: python manage.py runserver")
                elif "FastAPI" in fws:
                    lines.append("- Start FastAPI Server: uvicorn app.main:app --reload")
            if "TypeScript" in langs or "JavaScript" in langs:
                lines.append("- Install Node Packages: npm install")
                lines.append("- Start Development Server: npm run dev")
                lines.append("- Build for Production: npm run build")

        return ChatResponse(
            answer="\n".join(lines),
            citations=[],
            model_used="RIE Local Intelligence Engine (Offline / Deterministic)",
            reasoning_type="code",
        )

    async def _handle_entry_points_query(
        self,
        query: str,
        summary: Dict[str, Any],
        info: Dict[str, Any],
        repo_id: str,
    ) -> ChatResponse:
        lines = [
            "Application Entry Points and Execution Flow:\n",
        ]

        graph_repo = await get_graph_repository()
        subgraph = await graph_repo.get_subgraph(repo_id, node_types=["File"], limit=200)

        entry_files = []
        for node in subgraph.nodes:
            path = node.properties.get("path", "").lower()
            if any(path.endswith(s) for s in [
                "main.py", "manage.py", "app.py", "server.py", "wsgi.py", "asgi.py",
                "index.ts", "index.tsx", "index.js", "app.tsx", "main.ts", "vite.config.ts"
            ]):
                entry_files.append(node.properties.get("path"))

        citations = []
        if entry_files:
            lines.append("Primary Execution Entry Points:")
            for f in sorted(entry_files)[:8]:
                lines.append(f"- {f}")
                citations.append(Citation(type="file", reference=f, snippet="Entry Point", relevance_score=0.95))
        else:
            lines.append("- Root entry points can be found in the project root directory (e.g. manage.py, main.py, or index.ts).")

        return ChatResponse(
            answer="\n".join(lines),
            citations=citations,
            model_used="RIE Local Intelligence Engine (Offline / Deterministic)",
            reasoning_type="code",
        )

    async def _handle_tech_stack_query(
        self,
        query: str,
        summary: Dict[str, Any],
        info: Dict[str, Any],
    ) -> ChatResponse:
        langs = info.get("languages") or []
        fws = info.get("frameworks") or []
        pms = info.get("package_managers") or []
        apis = summary.get("apis") or {}
        db = summary.get("database") or {}

        lines = [
            "Codebase Technology Stack:\n",
            f"- Primary Languages: {', '.join(langs) if langs else 'Python, TypeScript, JavaScript'}",
            f"- Frameworks: {', '.join(fws) if fws else 'Web Frameworks, React, Django / FastAPI'}",
            f"- Package Managers: {', '.join(pms) if pms else 'npm, pip'}",
            f"- API Endpoints Detected: {len(apis.get('endpoints', []))} public endpoints",
            f"- Database Entities: {len(db.get('tables', []))} tables / models detected",
        ]

        return ChatResponse(
            answer="\n".join(lines),
            citations=[],
            model_used="RIE Local Intelligence Engine (Offline / Deterministic)",
            reasoning_type="general",
        )

    async def _handle_health_score_query(
        self,
        query: str,
        summary: Dict[str, Any],
        info: Dict[str, Any],
    ) -> ChatResponse:
        score = info.get("health_score")
        score_val = round(score, 1) if score is not None else "Pending"
        sec = summary.get("security") or {}
        td = summary.get("tech_debt") or {}
        perf = summary.get("performance") or {}

        sec_findings = len(sec.get("findings", []))
        sec_risk = sec.get("risk_score", 0.0)
        debt_score = td.get("debt_score", 0.0)
        perf_findings = len(perf.get("findings", []))

        sec_deduction = min(sec_risk, 50.0)
        debt_deduction = min(debt_score, 30.0)
        perf_deduction = min(perf_findings * 2, 20.0)

        lines = [
            f"Codebase Health Score Breakdown: {score_val}/100\n",
            "Calculation Formula:",
            "- Base Health Score: 100.0",
            f"- Security Risk Deduction: -{round(sec_deduction, 1)} pts ({sec_findings} vulnerabilities detected)",
            f"- Technical Debt Deduction: -{round(debt_deduction, 1)} pts (debt score: {debt_score}/100)",
            f"- Performance Antipattern Deduction: -{round(perf_deduction, 1)} pts ({perf_findings} findings detected)",
            f"- Final Calculated Score: {score_val}/100\n",
            "Key Recommendations to Improve Health:",
            "1. Resolve critical and high security findings to recover up to 50 health points.",
            "2. Refactor high-complexity modules and god classes to decrease technical debt.",
            "3. Eliminate N+1 loop queries and add pagination on heavy database calls.",
        ]

        return ChatResponse(
            answer="\n".join(lines),
            citations=[],
            model_used="RIE Local Intelligence Engine (Offline / Deterministic)",
            reasoning_type="quality",
        )

    async def _handle_security_query(
        self, query: str, summary: Dict[str, Any], repo_id: str
    ) -> ChatResponse:
        sec = summary.get("security") or {}
        findings = sec.get("findings", [])
        risk_score = sec.get("risk_score", 0.0)

        citations: List[Citation] = []
        for f in findings[:6]:
            fp = f.get("file_path", "")
            ls = f.get("line_start")
            ref = f"{fp}:{ls}" if ls else fp
            citations.append(
                Citation(
                    type="file",
                    reference=ref,
                    snippet=f.get("title"),
                    relevance_score=0.95,
                )
            )

        if not findings:
            lines = [
                "Security Audit Overview:\n",
                "No critical security vulnerabilities or hardcoded secrets were detected by the static rule analyzer.",
                "- Risk Score: 0.0 / 100.0 (Clean)",
                "- Analyzed Rules: OWASP Top 10, Hardcoded API keys, Database URLs, Private keys, and SQL injection sinks.",
                "- Recommendation: Continue maintaining automated dependency audits and pre-commit secret scanning.",
            ]
        else:
            by_severity: Dict[str, List[dict]] = {"critical": [], "high": [], "medium": [], "low": [], "info": []}
            for f in findings:
                sev = f.get("severity", "info").lower()
                by_severity.setdefault(sev, []).append(f)

            lines = [
                "Security Audit Findings:\n",
                f"The static security rule engine identified {len(findings)} security findings with an aggregate risk score of {risk_score}/100.\n",
                "Severity Distribution:",
                f"- Critical: {len(by_severity.get('critical', []))}",
                f"- High: {len(by_severity.get('high', []))}",
                f"- Medium: {len(by_severity.get('medium', []))}",
                f"- Low / Info: {len(by_severity.get('low', [])) + len(by_severity.get('info', []))}\n",
                "Top Vulnerabilities and Hardcoded Secrets:",
            ]

            for f in findings[:8]:
                fp = f.get("file_path", "unknown")
                ls = f.get("line_start", "")
                loc = f"{fp}:{ls}" if ls else f"{fp}"
                lines.append(f"- [{f.get('severity', 'INFO').upper()}] {f.get('title')} at {loc}")
                if f.get("recommendation"):
                    lines.append(f"  Remediation: {f.get('recommendation')}")

            lines.append("\nRemediation Guidance:")
            lines.append("1. Extract all hardcoded credentials into environment variables or secrets management services.")
            lines.append("2. Replace raw SQL concatenation with parameterized ORM queries.")
            lines.append("3. Ensure cryptographic hashing uses modern algorithms (Argon2, bcrypt, or SHA-256) instead of MD5.")

        return ChatResponse(
            answer="\n".join(lines),
            citations=citations,
            model_used="RIE Local Intelligence Engine (Offline / Deterministic)",
            reasoning_type="security",
        )

    async def _handle_architecture_query(
        self, query: str, summary: Dict[str, Any], repo_id: str
    ) -> ChatResponse:
        arch = summary.get("architecture") or {}
        pattern = arch.get("pattern", "Modular Architecture")
        confidence = arch.get("confidence", 0.8)
        layers = arch.get("layers", [])

        citations: List[Citation] = []
        for lay in layers[:4]:
            comps = lay.get("components", [])
            for c in comps[:2]:
                citations.append(
                    Citation(
                        type="file",
                        reference=c,
                        snippet=f"{lay.get('name')} Layer component",
                        relevance_score=0.9,
                    )
                )

        lines = [
            "Architectural Analysis & Pattern Classification:\n",
            f"- Classified Pattern: {pattern}",
            f"- Detection Confidence: {round(confidence * 100)}%\n",
            "Identified Architectural Layers:",
        ]

        for lay in layers:
            name = lay.get("name", "Layer")
            desc = lay.get("description", "")
            fc = lay.get("file_count", 0)
            lines.append(f"- {name} Layer ({fc} files): {desc}")

        lines.append("\nStructural Summary:")
        lines.append(f"The codebase is organized according to {pattern} conventions, with separation across {len(layers)} functional layers.")

        return ChatResponse(
            answer="\n".join(lines),
            citations=citations,
            model_used="RIE Local Intelligence Engine (Offline / Deterministic)",
            reasoning_type="architecture",
        )

    async def _handle_performance_query(
        self, query: str, summary: Dict[str, Any], repo_id: str
    ) -> ChatResponse:
        perf = summary.get("performance") or {}
        findings = perf.get("findings", [])

        citations: List[Citation] = []
        for f in findings[:6]:
            fp = f.get("file_path", "")
            ln = f.get("line_number")
            ref = f"{fp}:{ln}" if ln else fp
            citations.append(
                Citation(
                    type="file",
                    reference=ref,
                    snippet=f.get("title"),
                    relevance_score=0.92,
                )
            )

        lines = [
            "Performance Analysis & Antipattern Detection:\n",
            f"- Total Performance Findings: {len(findings)}\n",
        ]

        if findings:
            lines.append("Detected Performance Antipatterns:")
            for f in findings[:8]:
                fp = f.get("file_path", "unknown")
                ln = f.get("line_number", "")
                loc = f"{fp}:{ln}" if ln else f"{fp}"
                lines.append(f"- [{f.get('type', 'antipattern').upper()}] {f.get('title')} at {loc}")
                if f.get("recommendation"):
                    lines.append(f"  Fix: {f.get('recommendation')}")

            lines.append("\nOptimization Recommendations:")
            lines.append("1. Preload relational queries using select_related / prefetch_related to eliminate N+1 overhead.")
            lines.append("2. Add limit and offset pagination parameters to endpoint result sets.")
            lines.append("3. Offload intensive I/O tasks to background worker routines.")
        else:
            lines.append("No critical performance bottlenecks or loop query antipatterns were identified.")

        return ChatResponse(
            answer="\n".join(lines),
            citations=citations,
            model_used="RIE Local Intelligence Engine (Offline / Deterministic)",
            reasoning_type="performance",
        )

    async def _handle_dependency_query(
        self, query: str, summary: Dict[str, Any], repo_id: str
    ) -> ChatResponse:
        deps = summary.get("dependencies") or {}
        packages = deps.get("packages", [])
        cycles = deps.get("circular_dependencies", [])

        citations: List[Citation] = []
        if cycles:
            citations.append(
                Citation(
                    type="graph",
                    reference=" -> ".join(cycles[0][:3]),
                    snippet="Circular Dependency Cycle",
                    relevance_score=0.95,
                )
            )

        lines = [
            "Dependency & Circular Import Analysis:\n",
            f"- Total External Packages: {len(packages)}",
            f"- Circular Dependency Cycles: {len(cycles)}\n",
        ]

        if cycles:
            lines.append("Detected Circular Dependency Loops:")
            for cyc in cycles[:5]:
                chain = " -> ".join(cyc)
                lines.append(f"- Cycle: {chain}")
            lines.append("\nResolution: Decouple shared abstractions into a common module to break the import cycle.")
        else:
            lines.append("No circular dependency loops were detected. The dependency graph forms a clean directed acyclic graph.")

        if packages:
            lines.append("\nTop Detected Packages:")
            for p in packages[:10]:
                lines.append(f"- {p.get('name')} ({p.get('type', 'runtime')} dependency)")

        return ChatResponse(
            answer="\n".join(lines),
            citations=citations,
            model_used="RIE Local Intelligence Engine (Offline / Deterministic)",
            reasoning_type="architecture",
        )

    async def _handle_api_query(
        self, query: str, summary: Dict[str, Any], repo_id: str
    ) -> ChatResponse:
        apis = summary.get("apis") or {}
        endpoints = apis.get("endpoints", [])
        frameworks = apis.get("frameworks_detected", [])

        citations: List[Citation] = []
        for ep in endpoints[:5]:
            citations.append(
                Citation(
                    type="file",
                    reference=f"{ep.get('file_path')}:{ep.get('line_start')}",
                    snippet=f"{ep.get('method')} {ep.get('path')}",
                    relevance_score=0.9,
                )
            )

        lines = [
            "API and Route Discovery:\n",
            f"- Total Endpoints Detected: {len(endpoints)}",
            f"- Frameworks: {', '.join(frameworks) if frameworks else 'Standard REST / Web'}\n",
        ]

        if endpoints:
            lines.append("Discovered Endpoints:")
            for ep in endpoints[:15]:
                method = ep.get("method", "GET").upper()
                path = ep.get("path", "/")
                handler = ep.get("handler_name", "")
                fp = ep.get("file_path", "")
                lines.append(f"- {method} {path} -> {handler}() in {fp}")
        else:
            lines.append("No public REST/GraphQL endpoint declarations were detected in this codebase.")

        return ChatResponse(
            answer="\n".join(lines),
            citations=citations,
            model_used="RIE Local Intelligence Engine (Offline / Deterministic)",
            reasoning_type="code",
        )

    async def _handle_database_query(
        self, query: str, summary: Dict[str, Any], repo_id: str
    ) -> ChatResponse:
        db_data = summary.get("database") or {}
        tables = db_data.get("tables", [])
        relationships = db_data.get("relationships", [])

        citations: List[Citation] = []
        for t in tables[:5]:
            citations.append(
                Citation(
                    type="file",
                    reference=t.get("file_path", "models.py"),
                    snippet=f"Table: {t.get('name')}",
                    relevance_score=0.9,
                )
            )

        lines = [
            "Database Schema and Models:\n",
            f"- Entities / Tables: {len(tables)}",
            f"- Relationships: {len(relationships)}\n",
        ]

        if tables:
            lines.append("Database Entities:")
            for t in tables[:10]:
                cols = ", ".join(c.get("name") for c in t.get("columns", [])[:5])
                lines.append(f"- {t.get('name')}: Columns: {cols} (in {t.get('file_path')})")
        else:
            lines.append("No explicit ORM entity or SQL schema declarations were found.")

        return ChatResponse(
            answer="\n".join(lines),
            citations=citations,
            model_used="RIE Local Intelligence Engine (Offline / Deterministic)",
            reasoning_type="code",
        )

    async def _handle_tech_debt_query(
        self, query: str, summary: Dict[str, Any], repo_id: str
    ) -> ChatResponse:
        td = summary.get("tech_debt") or {}
        score = td.get("debt_score", 0.0)
        items = td.get("items", [])

        citations = []
        for it in items[:4]:
            citations.append(
                Citation(
                    type="file",
                    reference=f"{it.get('file_path')}:{it.get('line_number', 1)}",
                    snippet=it.get("title"),
                    relevance_score=0.85,
                )
            )

        lines = [
            "Technical Debt and Code Health:\n",
            f"- Technical Debt Score: {score}/100",
            f"- Identified Maintenance Items: {len(items)}\n",
        ]

        if items:
            lines.append("Priority Code Smells and Maintenance Items:")
            for it in items[:8]:
                lines.append(f"- {it.get('title')} in {it.get('file_path')}: {it.get('description')}")
        else:
            lines.append("The codebase demonstrates high cohesion and minimal structural technical debt.")

        return ChatResponse(
            answer="\n".join(lines),
            citations=citations,
            model_used="RIE Local Intelligence Engine (Offline / Deterministic)",
            reasoning_type="code",
        )

    async def _handle_git_query(
        self, query: str, summary: Dict[str, Any], repo_id: str
    ) -> ChatResponse:
        git_data = summary.get("git") or {}
        commits = git_data.get("total_commits", 0)
        contribs = git_data.get("contributors", [])
        hotspots = git_data.get("hotspot_files", [])

        citations = [
            Citation(
                type="file",
                reference=h.get("path", ""),
                snippet=f"Hotspot with {h.get('revisions', 0)} revisions",
                relevance_score=0.9,
            )
            for h in hotspots[:4]
        ]

        lines = [
            "Git Insights and Code Churn:\n",
            f"- Total Commits Analyzed: {commits}",
            f"- Contributors: {len(contribs)}\n",
        ]

        if hotspots:
            lines.append("High-Churn Hotspot Files:")
            for h in hotspots[:6]:
                lines.append(f"- {h.get('path')}: {h.get('revisions')} modifications")

        return ChatResponse(
            answer="\n".join(lines),
            citations=citations,
            model_used="RIE Local Intelligence Engine (Offline / Deterministic)",
            reasoning_type="general",
        )

    async def _search_symbol_or_file(self, query: str, repo_id: str) -> Optional[ChatResponse]:
        """Search in-memory graph for specific classes, functions, or files mentioned in query."""
        try:
            graph_repo = await get_graph_repository()
            subgraph = await graph_repo.get_subgraph(repo_id, limit=300)

            tokens = set(re.findall(r"\b[A-Za-z0-9_]{3,}\b", query))
            matches = []

            for node in subgraph.nodes:
                props = node.properties
                name = props.get("name", "")
                if name and any(tok.lower() == name.lower() for tok in tokens):
                    matches.append(node)

            if not matches:
                return None

            citations = []
            lines = ["Symbol and Component Lookup:\n"]

            for m in matches[:6]:
                props = m.properties
                label = m.labels[0] if m.labels else "Symbol"
                fp = props.get("file_path", props.get("path", "unknown"))
                ls = props.get("line_start")
                ref = f"{fp}:{ls}" if ls else fp

                citations.append(
                    Citation(
                        type="file",
                        reference=ref,
                        snippet=f"{label}: {props.get('name')}",
                        relevance_score=0.98,
                    )
                )

                lines.append(f"- {label} {props.get('name')} defined in {ref}")
                if props.get("signature"):
                    lines.append(f"  Signature: {props.get('signature')}")
                if props.get("docstring"):
                    lines.append(f"  Description: {props.get('docstring')[:200]}")

            return ChatResponse(
                answer="\n".join(lines),
                citations=citations,
                model_used="RIE Local Intelligence Engine (Offline / Deterministic)",
                reasoning_type="code",
            )
        except Exception:
            return None

    async def _handle_overview_query(
        self,
        query: str,
        summary: Dict[str, Any],
        info: Dict[str, Any],
        readme: Dict[str, Any],
    ) -> ChatResponse:
        repo_name = info.get("name") or "This repository"
        arch = summary.get("architecture") or {}
        sec = summary.get("security") or {}
        pattern = arch.get("pattern", "Modular Software Platform")
        sec_count = len(sec.get("findings", []))

        lines = [
            f"Codebase Intelligence Summary: {repo_name}\n",
        ]

        if readme.get("description"):
            lines.append(readme["description"])
            lines.append("")

        lines.extend([
            f"- Architectural Classification: {pattern}",
            f"- Security Findings: {sec_count} issues detected",
            "- Status: Grounded knowledge graph and local symbol index are active.\n",
            "You can ask specific questions about:",
            "- Project Purpose: 'Explain what this repository is about'",
            "- Setup and Run: 'How do I run or install this project?'",
            "- Architecture: 'What architectural pattern is used?'",
            "- Security: 'Show me security vulnerabilities or hardcoded secrets'",
            "- Dependencies: 'Are there any circular dependency loops?'",
            "- APIs: 'List all discovered API endpoints'",
            "- Database: 'What database tables or schemas exist?'",
            "- Health Score: 'Why is the health score what it is?'",
        ])

        return ChatResponse(
            answer="\n".join(lines),
            citations=[],
            model_used="RIE Local Intelligence Engine (Offline / Deterministic)",
            reasoning_type="general",
        )


local_reasoning_engine = LocalReasoningEngine()
