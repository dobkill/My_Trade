from __future__ import annotations

import asyncio
import contextlib

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.utils.symbols import canonical_symbol

router = APIRouter(tags=["websocket"])


@router.websocket("/ws/stocks/{symbol}")
async def stock_ws(websocket: WebSocket, symbol: str):
    await websocket.accept()
    canonical = canonical_symbol(symbol)
    service = websocket.app.state.realtime_service
    queue = await service.subscribe(canonical)
    heartbeat = asyncio.create_task(_heartbeat(websocket))
    try:
        while True:
            message = await queue.get()
            await websocket.send_json(message)
    except WebSocketDisconnect:
        pass
    finally:
        heartbeat.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await heartbeat
        await service.unsubscribe(canonical, queue)


async def _heartbeat(websocket: WebSocket) -> None:
    while True:
        await asyncio.sleep(15)
        await websocket.send_json({"type": "heartbeat"})
