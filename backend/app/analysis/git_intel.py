"""
Repository Intelligence Engine — Git Intelligence
Analyzes git history for contributor stats, hotspot files, change coupling,
commit frequency, and code ownership using GitPython.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import git

from app.core.logging import get_logger

log = get_logger(__name__)


def analyze_git(repo_path: str) -> dict:
    """Run full git intelligence analysis."""
    try:
        repo = git.Repo(repo_path)
    except Exception as e:
        log.error("git_open_failed", path=repo_path, error=str(e))
        return {"error": str(e)}

    commits = list(repo.iter_commits(max_count=500))
    if not commits:
        return {
            "total_commits": 0,
            "total_contributors": 0,
            "contributors": [],
            "hotspot_files": [],
            "change_coupling": [],
            "commit_frequency": {},
        }

    contributors = _analyze_contributors(commits, repo)
    hotspots = _analyze_hotspots(commits)
    coupling = _analyze_change_coupling(commits)
    frequency = _analyze_commit_frequency(commits)

    return {
        "total_commits": len(commits),
        "total_contributors": len(contributors),
        "contributors": contributors,
        "hotspot_files": hotspots[:30],
        "change_coupling": coupling[:20],
        "commit_frequency": frequency,
    }


def _analyze_contributors(commits: list, repo: git.Repo) -> list[dict]:
    """Analyze contributor statistics."""
    contributors: dict[str, dict] = {}

    for commit in commits:
        email = commit.author.email or "unknown"
        name = commit.author.name or "unknown"

        if email not in contributors:
            contributors[email] = {
                "name": name,
                "email": email,
                "commits": 0,
                "lines_added": 0,
                "lines_deleted": 0,
                "first_commit": commit.committed_datetime.isoformat(),
                "last_commit": commit.committed_datetime.isoformat(),
                "files_touched": Counter(),
            }

        c = contributors[email]
        c["commits"] += 1

        # Update first/last commit timestamps
        commit_dt = commit.committed_datetime.isoformat()
        if commit_dt < c["first_commit"]:
            c["first_commit"] = commit_dt
        if commit_dt > c["last_commit"]:
            c["last_commit"] = commit_dt

        # Get diff stats (limit to avoid slowness)
        if c["commits"] <= 200:
            try:
                stats = commit.stats
                c["lines_added"] += stats.total.get("insertions", 0)
                c["lines_deleted"] += stats.total.get("deletions", 0)
                for f in stats.files:
                    c["files_touched"][f] += 1
            except Exception:
                pass

    result = []
    for email, data in contributors.items():
        # Determine owned files (files this contributor changed the most)
        owned = [f for f, _ in data["files_touched"].most_common(10)]
        result.append({
            "name": data["name"],
            "email": data["email"],
            "commits": data["commits"],
            "lines_added": data["lines_added"],
            "lines_deleted": data["lines_deleted"],
            "first_commit": data["first_commit"],
            "last_commit": data["last_commit"],
            "owned_files": owned,
        })

    return sorted(result, key=lambda x: x["commits"], reverse=True)


def _analyze_hotspots(commits: list) -> list[dict]:
    """Find files that change most frequently (complexity hotspots)."""
    file_changes: Counter[str] = Counter()
    file_authors: dict[str, set[str]] = defaultdict(set)

    for commit in commits[:300]:
        try:
            for f in commit.stats.files:
                file_changes[f] += 1
                file_authors[f].add(commit.author.email or "unknown")
        except Exception:
            pass

    hotspots = []
    for file_path, changes in file_changes.most_common(50):
        hotspots.append({
            "file": file_path,
            "changes": changes,
            "authors": len(file_authors.get(file_path, set())),
        })

    return hotspots


def _analyze_change_coupling(commits: list) -> list[dict]:
    """Find files that frequently change together."""
    co_changes: Counter[tuple[str, str]] = Counter()

    for commit in commits[:200]:
        try:
            changed_files = sorted(commit.stats.files.keys())
            # Pair up files that changed in the same commit
            for i in range(len(changed_files)):
                for j in range(i + 1, min(i + 5, len(changed_files))):
                    pair = (changed_files[i], changed_files[j])
                    co_changes[pair] += 1
        except Exception:
            pass

    coupling = []
    for (file_a, file_b), count in co_changes.most_common(30):
        if count >= 3:  # Only report meaningful coupling
            coupling.append({
                "file_a": file_a,
                "file_b": file_b,
                "coupling_strength": count,
            })

    return coupling


def _analyze_commit_frequency(commits: list) -> dict[str, int]:
    """Analyze commit frequency by date."""
    frequency: Counter[str] = Counter()

    for commit in commits:
        try:
            date = commit.committed_datetime.strftime("%Y-%m-%d")
            frequency[date] += 1
        except Exception:
            pass

    # Return sorted by date
    return dict(sorted(frequency.items()))
