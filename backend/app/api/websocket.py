"""
Repository Intelligence Engine — WebSocket Router
Real-time scan progress updates over WebSocket.
"""

from __future__ import annotations

import asyncio
import json
from uuid import UUID

import redis.asyncio as aioredis
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.config import settings
from app.core.logging import get_logger

router = APIRouter(tags=["websocket"])
log = get_logger(__name__)


class ConnectionManager:
    """Manages active WebSocket connections per repository."""

    def __init__(self):
        self.active_connections: dict[str, list[WebSocket]] = {}

    async def connect(self, repo_id: str, websocket: WebSocket):
        await websocket.accept()
        if repo_id not in self.active_connections:
            self.active_connections[repo_id] = []
        self.active_connections[repo_id].append(websocket)
        log.info("ws_connected", repo_id=repo_id)

    def disconnect(self, repo_id: str, websocket: WebSocket):
        if repo_id in self.active_connections:
            self.active_connections[repo_id].remove(websocket)
            if not self.active_connections[repo_id]:
                del self.active_connections[repo_id]
        log.info("ws_disconnected", repo_id=repo_id)

    async def broadcast(self, repo_id: str, message: dict):
        if repo_id in self.active_connections:
            dead = []
            for ws in self.active_connections[repo_id]:
                try:
                    await ws.send_json(message)
                except Exception:
                    dead.append(ws)
            for ws in dead:
                self.active_connections[repo_id].remove(ws)


manager = ConnectionManager()


@router.websocket("/ws/scan/{repo_id}")
async def scan_progress_ws(websocket: WebSocket, repo_id: str):
    """
    WebSocket endpoint for real-time scan progress.
    Celery tasks publish progress to Redis pub/sub channel `scan:{repo_id}`.
    This endpoint subscribes and forwards messages to connected clients.
    """
    await manager.connect(repo_id, websocket)

    try:
        # Subscribe to Redis pub/sub for this repo's scan updates
        r = aioredis.from_url(settings.redis_url)
        pubsub = r.pubsub()
        await pubsub.subscribe(f"scan:{repo_id}")

        async def listen_redis():
            """Listen for Redis pub/sub messages and forward to WebSocket."""
            async for message in pubsub.listen():
                if message["type"] == "message":
                    try:
                        data = json.loads(message["data"])
                        await manager.broadcast(repo_id, data)
                    except (json.JSONDecodeError, Exception) as e:
                        log.warning("ws_broadcast_error", error=str(e))

        # Run Redis listener and WebSocket receiver concurrently
        redis_task = asyncio.create_task(listen_redis())

        try:
            while True:
                # Keep connection alive, handle client messages if needed
                data = await websocket.receive_text()
                # Could handle client commands here (e.g., cancel scan)
        except WebSocketDisconnect:
            pass
        finally:
            redis_task.cancel()
            await pubsub.unsubscribe(f"scan:{repo_id}")
            await pubsub.aclose()
            await r.aclose()
    except Exception as e:
        log.error("ws_error", repo_id=repo_id, error=str(e))
    finally:
        manager.disconnect(repo_id, websocket)
