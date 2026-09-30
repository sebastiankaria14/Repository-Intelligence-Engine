"""
Security hardening tests (Strix methodology verification).
Validates clone argument injection prevention, SSRF guards, directory traversal / symlink traps,
and OS root protection.
"""

import os
import tempfile
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.models.schemas import RepositoryCreate
from app.tasks.clone import enumerate_files, validate_safe_repo_url
from app.tasks.local_runner import FORBIDDEN_ROOTS, validate_safe_local_directory


def test_validate_safe_repo_url():
    # Valid URLs
    assert validate_safe_repo_url("https://github.com/torvalds/linux.git") == "https://github.com/torvalds/linux.git"
    assert validate_safe_repo_url("https://gitlab.com/user/project") == "https://gitlab.com/user/project"

    # Argument injection attempts
    with pytest.raises(ValueError, match="leading hyphens"):
        validate_safe_repo_url("--upload-pack=calc.exe")

    with pytest.raises(ValueError, match="leading hyphens"):
        validate_safe_repo_url("-u/tmp/evil")

    # Null byte injection
    with pytest.raises(ValueError, match="null bytes"):
        validate_safe_repo_url("https://github.com/org/repo\x00.git")

    # Empty
    with pytest.raises(ValueError, match="non-empty string"):
        validate_safe_repo_url("")


def test_repository_create_schema_validation():
    # Valid
    schema = RepositoryCreate(github_url="https://github.com/org/repo")
    assert schema.github_url == "https://github.com/org/repo"

    # Argument injection
    with pytest.raises(ValidationError):
        RepositoryCreate(github_url="--config=core.gitProxy=evil")

    # Null byte
    with pytest.raises(ValidationError):
        RepositoryCreate(github_url="https://github.com/org/repo\x00malicious")

    # Empty string
    with pytest.raises(ValidationError):
        RepositoryCreate(github_url="   ")


def test_validate_safe_local_directory_protected_roots():
    # Protected roots must raise ValueError
    for root in FORBIDDEN_ROOTS:
        if root.exists():
            with pytest.raises(ValueError, match="protected system directory"):
                validate_safe_local_directory(root)

    # Safe directory must pass
    with tempfile.TemporaryDirectory() as tmpdir:
        safe_path = Path(tmpdir)
        validated = validate_safe_local_directory(safe_path)
        assert validated == safe_path.resolve()


def test_enumerate_files_symlink_boundary_protection():
    """Ensure symlinks pointing outside the repository boundary are ignored and do not leak."""
    with tempfile.TemporaryDirectory() as outer_dir:
        outer = Path(outer_dir)
        secret_file = outer / "secret_outside.txt"
        secret_file.write_text("SUPER_SECRET_TOKEN=xyz123", encoding="utf-8")

        repo_dir = outer / "repo"
        repo_dir.mkdir()
        (repo_dir / "index.py").write_text("print('hello')", encoding="utf-8")

        # Create symlink pointing outside repo
        symlink_path = repo_dir / "leak_link.py"
        try:
            symlink_path.symlink_to(secret_file)
            has_symlink = True
        except (OSError, NotImplementedError):
            # On Windows without developer mode/admin privileges, symlinks might not be permitted
            has_symlink = False

        files = enumerate_files(repo_dir)
        paths = [f["path"] for f in files]

        assert "index.py" in paths
        if has_symlink:
            # The escaped symlink must not be included
            assert "leak_link.py" not in paths
