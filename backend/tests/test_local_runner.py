"""
Unit tests for LocalPipelineRunner.
Verifies file enumeration, in-memory graph construction, and full scan pipeline on local directories.
"""

import tempfile
from pathlib import Path

import pytest

from app.core.database import async_session_factory, init_db
from app.models.database import Repository, ScanJob, ScanStatus
from app.tasks.clone import enumerate_files
from app.tasks.local_runner import build_in_memory_graph, run_pipeline_async


@pytest.mark.asyncio
async def test_enumerate_local_directory():
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        (root / "src").mkdir()
        (root / "src" / "index.ts").write_text("export const answer = 42;", encoding="utf-8")
        (root / "src" / "app.py").write_text("def hello():\n    return 'world'\n", encoding="utf-8")

        files = enumerate_files(root)
        paths = [f["path"] for f in files]

        assert "src/index.ts" in paths
        assert "src/app.py" in paths
        assert any(f["language"] == "TypeScript" for f in files)
        assert any(f["language"] == "Python" for f in files)


@pytest.mark.asyncio
async def test_build_in_memory_graph():
    files = [{"path": "main.py", "language": "Python", "lines": 20, "size_bytes": 400}]
    symbols = [{
        "name": "MainEngine",
        "type": "class",
        "file_path": "main.py",
        "line_start": 5,
        "line_end": 18,
        "signature": "class MainEngine",
    }]
    imports = [{"module": "sys", "name": "exit", "file_path": "main.py"}]
    calls = []

    stats = await build_in_memory_graph("test-repo-g", files, symbols, imports, calls)
    assert stats["total_nodes"] >= 3
    assert stats["total_edges"] >= 2


@pytest.mark.asyncio
async def test_end_to_end_local_pipeline():
    await init_db()

    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        (root / "module.py").write_text("class Calculator:\n    def add(self, a, b):\n        return a + b\n", encoding="utf-8")

        async with async_session_factory() as session:
            repo = Repository(github_url=str(root), name="test-calc")
            session.add(repo)
            await session.flush()

            job = ScanJob(repository_id=repo.id, status=ScanStatus.PENDING)
            session.add(job)
            await session.commit()
            repo_id = str(repo.id)
            job_id = str(job.id)

        # Execute local pipeline directly
        await run_pipeline_async(repo_id, job_id, str(root))

        # Check job completed in SQLite
        async with async_session_factory() as session:
            updated_job = await session.get(ScanJob, job.id)
            assert updated_job.status == ScanStatus.COMPLETED
            assert updated_job.progress == 100.0
            assert "architecture" in updated_job.results_summary

            updated_repo = await session.get(Repository, repo.id)
            assert updated_repo.total_files >= 1
            assert updated_repo.health_score is not None
