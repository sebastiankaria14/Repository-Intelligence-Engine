"""
Repository Intelligence Engine — Security Analysis
Pattern-based security scanning: hardcoded secrets, SQL injection,
insecure deserialization, dangerous imports, weak crypto, debug mode,
and other common vulnerability patterns.
"""

from __future__ import annotations

import re
import uuid
from pathlib import Path

from app.core.logging import get_logger

log = get_logger(__name__)

# ── Secret Patterns ──────────────────────────────────────────

SECRET_PATTERNS: list[tuple[str, str, str]] = [
    # (regex, title, severity)
    (r"""(?i)(?:api[_-]?key|apikey)\s*[:=]\s*['"][A-Za-z0-9_\-]{16,}['"]""",
     "Hardcoded API key", "high"),
    (r"""(?i)(?:password|passwd|pwd)\s*[:=]\s*['"][^'"]{4,}['"]""",
     "Hardcoded password", "critical"),
    (r"""(?i)(?:secret|token|auth)\s*[:=]\s*['"][A-Za-z0-9_\-]{16,}['"]""",
     "Hardcoded secret/token", "high"),
    (r"""(?i)(?:aws_access_key_id)\s*[:=]\s*['"]AKIA[A-Z0-9]{16}['"]""",
     "AWS Access Key", "critical"),
    (r"""(?i)(?:private[_-]?key)\s*[:=]\s*['"][^'"]{20,}['"]""",
     "Hardcoded private key", "critical"),
    (r"""-----BEGIN (?:RSA |EC |DSA )?PRIVATE KEY-----""",
     "Private key in source", "critical"),
    (r"""(?i)(?:database_url|db_url|connection_string)\s*[:=]\s*['"][^'"]+['"]""",
     "Hardcoded database connection string", "high"),
]

# ── SQL Injection Patterns ───────────────────────────────────

SQLI_PATTERNS: list[tuple[str, str]] = [
    (r"""(?:execute|query|raw)\s*\(\s*f['"]""", "f-string in SQL query (SQL injection risk)"),
    (r"""(?:execute|query|raw)\s*\(\s*['"].*%s""", "String formatting in SQL query"),
    (r"""(?:execute|query|raw)\s*\(\s*['"].*\+\s*""", "String concatenation in SQL query"),
    (r"""\.format\s*\(.*\).*(?:SELECT|INSERT|UPDATE|DELETE|DROP)""", ".format() in SQL statement"),
]

# ── Dangerous Imports / Functions ────────────────────────────

DANGEROUS_IMPORTS: dict[str, tuple[str, str]] = {
    "pickle": ("Insecure deserialization via pickle", "high"),
    "marshal": ("Insecure deserialization via marshal", "high"),
    "shelve": ("Insecure deserialization via shelve", "medium"),
    "yaml.load": ("Unsafe YAML loading (use safe_load)", "high"),
    "eval(": ("Use of eval() — code injection risk", "critical"),
    "exec(": ("Use of exec() — code injection risk", "critical"),
    "subprocess.call": ("subprocess.call with potential shell injection", "medium"),
    "os.system": ("os.system with potential shell injection", "high"),
    "compile(": ("Dynamic code compilation", "medium"),
    "__import__": ("Dynamic import — potential injection", "medium"),
}

# ── Weak Crypto ──────────────────────────────────────────────

WEAK_CRYPTO: list[tuple[str, str]] = [
    (r"(?i)\bmd5\b", "MD5 hash — cryptographically weak"),
    (r"(?i)\bsha1\b", "SHA-1 hash — cryptographically weak"),
    (r"(?i)\bDES\b", "DES encryption — weak cipher"),
    (r"(?i)\bRC4\b", "RC4 encryption — weak cipher"),
    (r"(?i)verify\s*=\s*False", "SSL verification disabled"),
    (r"(?i)HTTPS.*verify.*False", "HTTPS verification disabled"),
]

# ── Debug / Misconfiguration ─────────────────────────────────

DEBUG_PATTERNS: list[tuple[str, str, str]] = [
    (r"""(?i)debug\s*[:=]\s*True""", "Debug mode enabled", "medium"),
    (r"""(?i)CORS.*\*""", "CORS allows all origins", "low"),
    (r"""(?i)allow_origins\s*=\s*\[['"]?\*""", "CORS wildcard origin", "low"),
]


def analyze_security(
    repo_path: str,
    files: list[dict],
    symbols: list[dict],
    imports: list[dict],
) -> dict:
    """Run pattern-based security analysis on the repository."""
    findings: list[dict] = []

    # Scan source files for patterns
    for f in files:
        lang = f.get("language")
        if not lang or lang in ("Markdown", "JSON", "YAML", "XML"):
            continue

        # Skip large files and non-code
        size = f.get("size_bytes", 0)
        if size > 500_000 or size == 0:
            continue

        abs_path = Path(repo_path) / f["path"]
        if not abs_path.exists():
            continue

        try:
            content = abs_path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue

        lines = content.splitlines()

        # Check secret patterns
        for pattern, title, severity in SECRET_PATTERNS:
            for i, line in enumerate(lines):
                if re.search(pattern, line):
                    # Skip if it looks like an example/template
                    if any(skip in line.lower() for skip in ("example", "changeme", "xxx", "placeholder", "todo")):
                        continue
                    findings.append(_make_finding(
                        severity=severity,
                        title=title,
                        description=f"Potential hardcoded secret found in source code.",
                        file_path=f["path"],
                        line_start=i + 1,
                        rule_id="secret-detection",
                        tool="rie-scanner",
                    ))
                    break  # One finding per file per pattern

        # Check SQL injection patterns
        for pattern, title in SQLI_PATTERNS:
            for i, line in enumerate(lines):
                if re.search(pattern, line, re.IGNORECASE):
                    findings.append(_make_finding(
                        severity="high",
                        title=title,
                        description="User input may reach SQL queries without parameterization.",
                        file_path=f["path"],
                        line_start=i + 1,
                        rule_id="sql-injection",
                        tool="rie-scanner",
                        recommendation="Use parameterized queries or ORM methods instead of string formatting.",
                    ))
                    break

        # Check dangerous functions
        for keyword, (title, severity) in DANGEROUS_IMPORTS.items():
            for i, line in enumerate(lines):
                if keyword in line and not line.strip().startswith("#"):
                    findings.append(_make_finding(
                        severity=severity,
                        title=title,
                        description=f"Potentially dangerous usage of `{keyword}` detected.",
                        file_path=f["path"],
                        line_start=i + 1,
                        rule_id="dangerous-function",
                        tool="rie-scanner",
                    ))
                    break

        # Check weak crypto
        for pattern, title in WEAK_CRYPTO:
            for i, line in enumerate(lines):
                if re.search(pattern, line) and not line.strip().startswith("#"):
                    findings.append(_make_finding(
                        severity="medium",
                        title=title,
                        description="Weak cryptographic algorithm or disabled security check.",
                        file_path=f["path"],
                        line_start=i + 1,
                        rule_id="weak-crypto",
                        tool="rie-scanner",
                        recommendation="Use SHA-256+ for hashing and AES-256 for encryption.",
                    ))
                    break

        # Check debug/misconfig
        for pattern, title, severity in DEBUG_PATTERNS:
            for i, line in enumerate(lines):
                if re.search(pattern, line):
                    findings.append(_make_finding(
                        severity=severity,
                        title=title,
                        description="Potential security misconfiguration detected.",
                        file_path=f["path"],
                        line_start=i + 1,
                        rule_id="misconfiguration",
                        tool="rie-scanner",
                    ))
                    break

    # Build summary
    summary: dict[str, int] = {}
    for finding in findings:
        sev = finding["severity"]
        summary[sev] = summary.get(sev, 0) + 1

    # Compute risk score (0-100)
    risk_score = _compute_risk_score(findings)

    log.info("security_analysis_complete", findings=len(findings), risk_score=risk_score)

    return {
        "findings": findings,
        "summary": summary,
        "risk_score": risk_score,
    }


def _make_finding(
    severity: str,
    title: str,
    description: str,
    file_path: str,
    line_start: int,
    rule_id: str,
    tool: str,
    recommendation: str | None = None,
    line_end: int | None = None,
) -> dict:
    return {
        "id": str(uuid.uuid4()),
        "severity": severity,
        "title": title,
        "description": description,
        "file_path": file_path,
        "line_start": line_start,
        "line_end": line_end or line_start,
        "rule_id": rule_id,
        "tool": tool,
        "recommendation": recommendation or f"Review and remediate this {severity}-severity finding.",
        "affected_services": [],
    }


def _compute_risk_score(findings: list[dict]) -> float:
    """Compute a 0-100 risk score. Higher = more risk."""
    if not findings:
        return 0.0

    weights = {"critical": 25, "high": 15, "medium": 5, "low": 2, "info": 0}
    total = sum(weights.get(f["severity"], 0) for f in findings)
    return min(round(total, 1), 100.0)
