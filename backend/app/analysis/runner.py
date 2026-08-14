"""
Repository Intelligence Engine — Analysis Runner
Orchestrates all analysis modules and aggregates results.
"""

from __future__ import annotations

from app.core.logging import get_logger

log = get_logger(__name__)


def run_all_analyses(
    repo_id: str,
    repo_path: str,
    files: list[dict],
    symbols: list[dict],
    imports: list[dict],
    calls: list[dict],
    languages: list[str],
) -> dict:
    """Run all analysis modules and return aggregated results."""
    results = {}

    # Architecture
    try:
        from app.analysis.architecture import analyze_architecture
        results["architecture"] = analyze_architecture(files, symbols, imports, languages)
    except Exception as e:
        log.error("architecture_analysis_failed", error=str(e))
        results["architecture"] = {"error": str(e)}

    # API Discovery
    try:
        from app.analysis.api_discovery import discover_apis
        results["apis"] = discover_apis(files, symbols, imports)
    except Exception as e:
        log.error("api_discovery_failed", error=str(e))
        results["apis"] = {"error": str(e)}

    # Database Intelligence
    try:
        from app.analysis.database_intel import analyze_database
        results["database"] = analyze_database(files, symbols, imports)
    except Exception as e:
        log.error("database_analysis_failed", error=str(e))
        results["database"] = {"error": str(e)}

    # Dependency Intelligence
    try:
        from app.analysis.dependency_intel import analyze_dependencies
        results["dependencies"] = analyze_dependencies(repo_path, files, imports)
    except Exception as e:
        log.error("dependency_analysis_failed", error=str(e))
        results["dependencies"] = {"error": str(e)}

    # Git Intelligence
    try:
        from app.analysis.git_intel import analyze_git
        results["git"] = analyze_git(repo_path)
    except Exception as e:
        log.error("git_analysis_failed", error=str(e))
        results["git"] = {"error": str(e)}

    # Security
    try:
        from app.analysis.security import analyze_security
        results["security"] = analyze_security(repo_path, files, symbols, imports)
    except Exception as e:
        log.error("security_analysis_failed", error=str(e))
        results["security"] = {"error": str(e)}

    # Performance
    try:
        from app.analysis.performance import analyze_performance
        results["performance"] = analyze_performance(files, symbols, calls, imports)
    except Exception as e:
        log.error("performance_analysis_failed", error=str(e))
        results["performance"] = {"error": str(e)}

    # Technical Debt
    try:
        from app.analysis.tech_debt import analyze_tech_debt
        results["tech_debt"] = analyze_tech_debt(files, symbols, calls)
    except Exception as e:
        log.error("tech_debt_analysis_failed", error=str(e))
        results["tech_debt"] = {"error": str(e)}

    log.info("all_analyses_complete", repo_id=repo_id, modules=list(results.keys()))
    return results
