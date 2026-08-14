"""
Repository Intelligence Engine — Celery Application
Configures the Celery task queue with Redis broker/backend.
"""

from __future__ import annotations

from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "rie",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    result_expires=3600,
    task_soft_time_limit=3600,  # 1 hour soft limit
    task_time_limit=7200,  # 2 hour hard limit
)

# Auto-discover tasks in all task modules
celery_app.autodiscover_tasks([
    "app.tasks.pipeline",
    "app.tasks.clone",
    "app.tasks.parse",
    "app.tasks.graph_build",
    "app.tasks.analyze",
    "app.tasks.embed",
    "app.tasks.index",
])
