"""
Repository Intelligence Engine — Repository Clone Task
Clones a GitHub repository to local storage and detects basic metadata.
"""

from __future__ import annotations

import os
import re
import shutil
import uuid
from collections import Counter
from pathlib import Path

import git

from app.core.config import settings
from app.core.logging import get_logger

log = get_logger(__name__)

# File extensions → language mapping
EXTENSION_LANGUAGE_MAP: dict[str, str] = {
    ".py": "Python",
    ".js": "JavaScript",
    ".jsx": "JavaScript",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".java": "Java",
    ".kt": "Kotlin",
    ".go": "Go",
    ".rs": "Rust",
    ".rb": "Ruby",
    ".php": "PHP",
    ".cs": "C#",
    ".cpp": "C++",
    ".c": "C",
    ".h": "C",
    ".hpp": "C++",
    ".swift": "Swift",
    ".scala": "Scala",
    ".sql": "SQL",
    ".html": "HTML",
    ".css": "CSS",
    ".scss": "SCSS",
    ".yml": "YAML",
    ".yaml": "YAML",
    ".json": "JSON",
    ".xml": "XML",
    ".md": "Markdown",
    ".sh": "Shell",
    ".bash": "Shell",
    ".r": "R",
    ".dart": "Dart",
    ".lua": "Lua",
    ".ex": "Elixir",
    ".exs": "Elixir",
    ".erl": "Erlang",
    ".hs": "Haskell",
    ".vue": "Vue",
    ".svelte": "Svelte",
}

# Framework detection patterns (file → framework)
FRAMEWORK_INDICATORS: dict[str, str] = {
    "package.json": "_npm",  # further inspected below
    "requirements.txt": "_pip",
    "Pipfile": "_pip",
    "pyproject.toml": "_pip",
    "setup.py": "_pip",
    "pom.xml": "Maven",
    "build.gradle": "Gradle",
    "build.gradle.kts": "Gradle",
    "Cargo.toml": "Cargo",
    "go.mod": "Go Modules",
    "Gemfile": "Bundler",
    "composer.json": "Composer",
    "pubspec.yaml": "Dart Pub",
}

# Package-manager detection file → manager name
PM_FILES: dict[str, str] = {
    "package.json": "npm",
    "package-lock.json": "npm",
    "yarn.lock": "yarn",
    "pnpm-lock.yaml": "pnpm",
    "requirements.txt": "pip",
    "Pipfile": "pipenv",
    "pyproject.toml": "poetry/pip",
    "pom.xml": "maven",
    "build.gradle": "gradle",
    "Cargo.toml": "cargo",
    "go.mod": "go",
    "Gemfile": "bundler",
    "composer.json": "composer",
}

# Directories/files that strongly indicate monorepos
MONOREPO_SIGNALS = [
    "lerna.json",
    "nx.json",
    "pnpm-workspace.yaml",
    "rush.json",
    "packages/",
    "apps/",
    "services/",
    "modules/",
]

# Directories to skip during file enumeration
SKIP_DIRS = {
    ".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build",
    ".next", ".nuxt", "vendor", "target", ".idea", ".vscode", ".gradle",
    ".tox", "egg-info", ".eggs", ".mypy_cache", ".pytest_cache",
    "coverage", ".cache", ".turbo",
}


def validate_safe_repo_url(url: str) -> str:
    """Validate and sanitize git clone URL to prevent argument injection and SSRF."""
    if not url or not isinstance(url, str):
        raise ValueError("Repository URL must be a non-empty string")
    clean = url.strip()
    if clean.startswith("-"):
        raise ValueError("Invalid repository URL: leading hyphens are prohibited (argument injection prevention)")
    if "\x00" in clean:
        raise ValueError("Invalid repository URL: null bytes are prohibited")
    return clean


def clone_repo(github_url: str, repo_id: str) -> Path:
    """
    Clone a repository to local storage with security validation.

    Returns:
        Path to the cloned repository directory.
    """
    safe_url = validate_safe_repo_url(github_url)

    # Sanitize repo_id to prevent directory traversal
    try:
        clean_repo_id = str(uuid.UUID(str(repo_id)))
    except (ValueError, AttributeError):
        clean_repo_id = re.sub(r"[^a-zA-Z0-9_\-]", "", str(repo_id))
        if not clean_repo_id:
            raise ValueError("Invalid repository ID")

    clone_dir = settings.effective_clone_dir / clean_repo_id
    if clone_dir.exists():
        log.info("repo_already_cloned", path=str(clone_dir))
        return clone_dir

    clone_dir.parent.mkdir(parents=True, exist_ok=True)

    log.info("cloning_repo", url=safe_url, dest=str(clone_dir))
    git.Repo.clone_from(
        safe_url,
        str(clone_dir),
        depth=500,  # Shallow clone for performance, deep enough for git history
        no_single_branch=True,
    )
    log.info("clone_complete", url=safe_url, dest=str(clone_dir))
    return clone_dir


def detect_default_branch(repo_path: Path) -> str:
    """Detect the default branch name."""
    try:
        repo = git.Repo(str(repo_path))
        return repo.active_branch.name
    except Exception:
        return "main"


def enumerate_files(repo_path: Path) -> list[dict]:
    """
    Walk the repository and collect metadata for every source file.
    Includes symlink traversal protection to prevent escaping the repository root.

    Returns:
        List of dicts: {path, extension, language, lines, size_bytes}
    """
    files: list[dict] = []
    canonical_root = repo_path.resolve()

    for root, dirs, filenames in os.walk(repo_path):
        # Skip ignored directories in-place
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]

        for filename in filenames:
            abs_path = (Path(root) / filename).resolve()

            # Security: ensure file resolves within repository boundary (prevent symlink traversal)
            try:
                rel_path = abs_path.relative_to(canonical_root).as_posix()
            except ValueError:
                log.warning("symlink_escape_detected", file=str(abs_path), root=str(canonical_root))
                continue

            ext = abs_path.suffix.lower()
            language = EXTENSION_LANGUAGE_MAP.get(ext)

            size_bytes = abs_path.stat().st_size
            lines = 0
            if language and size_bytes < 2_000_000:  # Skip huge files
                try:
                    with open(abs_path, "r", encoding="utf-8", errors="replace") as f:
                        lines = sum(1 for _ in f)
                except Exception:
                    pass

            files.append({
                "path": rel_path,
                "extension": ext,
                "language": language,
                "lines": lines,
                "size_bytes": size_bytes,
            })
    return files


def detect_languages(files: list[dict]) -> list[str]:
    """Detect primary languages from file counts."""
    lang_counts: Counter[str] = Counter()
    for f in files:
        if f["language"]:
            lang_counts[f["language"]] += 1
    # Return languages sorted by frequency
    return [lang for lang, _ in lang_counts.most_common()]


def detect_frameworks(repo_path: Path, files: list[dict]) -> list[str]:
    """Detect frameworks by inspecting project files."""
    frameworks: set[str] = set()
    file_paths = {f["path"] for f in files}
    basenames = {Path(f["path"]).name for f in files}

    # Check framework indicator files
    for indicator, framework in FRAMEWORK_INDICATORS.items():
        if indicator in basenames:
            if not framework.startswith("_"):
                frameworks.add(framework)

    # Inspect package.json for JS frameworks
    pkg_json = repo_path / "package.json"
    if pkg_json.exists():
        try:
            import json
            with open(pkg_json) as f:
                pkg = json.load(f)
            all_deps = {}
            all_deps.update(pkg.get("dependencies", {}))
            all_deps.update(pkg.get("devDependencies", {}))
            js_fw_map = {
                "react": "React",
                "next": "Next.js",
                "vue": "Vue",
                "nuxt": "Nuxt",
                "@angular/core": "Angular",
                "svelte": "Svelte",
                "express": "Express",
                "fastify": "Fastify",
                "nestjs": "NestJS",
                "@nestjs/core": "NestJS",
            }
            for dep_name, fw_name in js_fw_map.items():
                if dep_name in all_deps:
                    frameworks.add(fw_name)
        except Exception:
            pass

    # Inspect requirements.txt for Python frameworks
    req_path = repo_path / "requirements.txt"
    if req_path.exists():
        try:
            content = req_path.read_text(encoding="utf-8", errors="replace").lower()
            py_fw_map = {
                "django": "Django",
                "flask": "Flask",
                "fastapi": "FastAPI",
                "tornado": "Tornado",
                "starlette": "Starlette",
                "celery": "Celery",
                "sqlalchemy": "SQLAlchemy",
            }
            for keyword, fw_name in py_fw_map.items():
                if keyword in content:
                    frameworks.add(fw_name)
        except Exception:
            pass

    # Check for Docker
    if "Dockerfile" in basenames or "docker-compose.yml" in basenames:
        frameworks.add("Docker")

    return sorted(frameworks)


def detect_package_managers(basenames: set[str]) -> list[str]:
    """Detect package managers from project files."""
    managers: set[str] = set()
    for filename, manager in PM_FILES.items():
        if filename in basenames:
            managers.add(manager)
    return sorted(managers)


def detect_monorepo(repo_path: Path, basenames: set[str]) -> bool:
    """Check if the repository is a monorepo."""
    for signal in MONOREPO_SIGNALS:
        if signal.endswith("/"):
            if (repo_path / signal.rstrip("/")).is_dir():
                return True
        else:
            if signal in basenames:
                return True
    return False


def extract_repo_name(github_url: str) -> str:
    """Extract owner/repo from a GitHub URL."""
    match = re.search(r"github\.com[/:]([^/]+/[^/.]+)", github_url)
    if match:
        return match.group(1)
    return github_url.split("/")[-1].replace(".git", "")


def analyze_clone(github_url: str, repo_id: str) -> dict:
    """
    Full clone + metadata extraction pipeline.

    Returns a dict with all detected metadata:
        name, default_branch, languages, frameworks, package_managers,
        is_monorepo, total_files, total_lines, files (for further parsing)
    """
    # Clone
    repo_path = clone_repo(github_url, repo_id)

    # Enumerate files
    files = enumerate_files(repo_path)

    # Extract metadata
    basenames = {Path(f["path"]).name for f in files}
    languages = detect_languages(files)
    frameworks = detect_frameworks(repo_path, files)
    package_managers = detect_package_managers(basenames)
    is_monorepo = detect_monorepo(repo_path, basenames)
    default_branch = detect_default_branch(repo_path)
    name = extract_repo_name(github_url)

    total_files = len(files)
    total_lines = sum(f["lines"] for f in files)

    log.info(
        "clone_analysis_complete",
        repo_id=repo_id,
        name=name,
        languages=languages[:5],
        frameworks=frameworks,
        total_files=total_files,
        total_lines=total_lines,
    )

    return {
        "repo_path": str(repo_path),
        "name": name,
        "default_branch": default_branch,
        "languages": languages,
        "frameworks": frameworks,
        "package_managers": package_managers,
        "is_monorepo": is_monorepo,
        "total_files": total_files,
        "total_lines": total_lines,
        "files": files,
    }
