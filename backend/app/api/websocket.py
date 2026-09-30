"""
Repository Intelligence Engine — WebSocket Router
Real-time scan progress updates over in-memory WebSocket connections.
100% offline and zero Redis requirement.
"""

from __future__ import annotations

import asyncio
from typing import Dict, List

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.logging import get_logger

router = APIRouter(tags=["websocket"])
log = get_logger(__name__)


class ConnectionManager:
    """Manages active WebSocket connections per repository in-memory."""

    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}
        self._latest_progress: Dict[str, dict] = {}

    async def connect(self, repo_id: str, websocket: WebSocket):
        await websocket.accept()
        if repo_id not in self.active_connections:
            self.active_connections[repo_id] = []
        self.active_connections[repo_id].append(websocket)
        log.info("ws_connected", repo_id=repo_id)

        # Immediately send cached latest progress if available
        if repo_id in self._latest_progress:
            try:
                await websocket.send_json(self._latest_progress[repo_id])
            except Exception:
                pass

    def disconnect(self, repo_id: str, websocket: WebSocket):
        if repo_id in self.active_connections:
            if websocket in self.active_connections[repo_id]:
                self.active_connections[repo_id].remove(websocket)
            if not self.active_connections[repo_id]:
                del self.active_connections[repo_id]
        log.info("ws_disconnected", repo_id=repo_id)

    async def broadcast(self, repo_id: str, message: dict):
        self._latest_progress[repo_id] = message
        if repo_id in self.active_connections:
            dead = []
            for ws in self.active_connections[repo_id]:
                try:
                    await ws.send_json(message)
                except Exception:
                    dead.append(ws)
            for ws in dead:
                if ws in self.active_connections[repo_id]:
                    self.active_connections[repo_id].remove(ws)


manager = ConnectionManager()


@router.websocket("/ws/scan/{repo_id}")
async def scan_progress_ws(websocket: WebSocket, repo_id: str):
    """
    WebSocket endpoint for real-time scan progress.
    Local in-process runner publishes progress directly to this manager.
    """
    await manager.connect(repo_id, websocket)

    try:
        while True:
            # Keep connection open; receive ping or client queries
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        pass
    except Exception as e:
        log.warning("ws_error", repo_id=repo_id, error=str(e))
    finally:
        manager.disconnect(repo_id, websocket)
