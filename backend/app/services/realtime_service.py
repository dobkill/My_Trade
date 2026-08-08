from __future__ import annotations

import asyncio
import contextlib
import logging
from collections import defaultdict
from typing import Any

from app.market_data.manager import MarketDataManager
from app.services.bar_aggregator import BarAggregator
from app.utils.symbols import canonical_symbol
from app.utils.time import market_status

logger = logging.getLogger(__name__)


class RealtimeService:
    def __init__(self, manager: MarketDataManager, poll_seconds: float = 2.5):
        self.manager = manager
        self.poll_seconds = max(2.0, poll_seconds)
        self.aggregator = BarAggregator()
        self._subscribers: dict[str, set[asyncio.Queue[dict[str, Any]]]] = defaultdict(set)
        self._tasks: dict[str, asyncio.Task[None]] = {}
        self._cache: dict[str, dict[str, Any]] = {}
        self._lock = asyncio.Lock()

    async def subscribe(self, symbol: str) -> asyncio.Queue[dict[str, Any]]:
        canonical = canonical_symbol(symbol)
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=100)
        async with self._lock:
            self._subscribers[canonical].add(queue)
            if canonical not in self._tasks or self._tasks[canonical].done():
                self._tasks[canonical] = asyncio.create_task(self._run_symbol(canonical))
            logger.info("websocket subscribe symbol=%s clients=%s", canonical, len(self._subscribers[canonical]))
        cached = self._cache.get(canonical)
        if cached:
            await queue.put(cached)
        return queue

    async def unsubscribe(self, symbol: str, queue: asyncio.Queue[dict[str, Any]]) -> None:
        canonical = canonical_symbol(symbol)
        async with self._lock:
            subscribers = self._subscribers.get(canonical)
            if subscribers:
                subscribers.discard(queue)
                logger.info("websocket unsubscribe symbol=%s clients=%s", canonical, len(subscribers))
                if not subscribers:
                    task = self._tasks.pop(canonical, None)
                    if task:
                        task.cancel()
                        with contextlib.suppress(asyncio.CancelledError):
                            await task
                    self._subscribers.pop(canonical, None)

    async def shutdown(self) -> None:
        async with self._lock:
            tasks = list(self._tasks.values())
            self._tasks.clear()
            self._subscribers.clear()
        for task in tasks:
            task.cancel()
        for task in tasks:
            with contextlib.suppress(asyncio.CancelledError):
                await task

    async def _run_symbol(self, symbol: str) -> None:
        backoff = self.poll_seconds
        while True:
            try:
                status = market_status()
                if status == "closed":
                    await self._broadcast(symbol, {"type": "status", "symbol": symbol, "market_status": "closed"})
                    await asyncio.sleep(max(self.poll_seconds * 10, 15.0))
                    continue

                quote = await self.manager.get_realtime_quote(symbol)
                message = {"type": "quote", "data": quote}
                self._cache[symbol] = message
                await self._broadcast(symbol, message)
                for bar in self.aggregator.update(quote):
                    await self._broadcast(symbol, bar)
                backoff = self.poll_seconds
                await asyncio.sleep(self.poll_seconds)
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # noqa: BLE001
                logger.warning("websocket symbol=%s action=poll error=%s", symbol, exc)
                await self._broadcast(
                    symbol,
                    {"type": "status", "symbol": symbol, "market_status": "reconnecting", "message": str(exc)},
                )
                await asyncio.sleep(backoff)
                backoff = min(backoff * 1.8, 30.0)

    async def _broadcast(self, symbol: str, message: dict[str, Any]) -> None:
        subscribers = list(self._subscribers.get(symbol, set()))
        for queue in subscribers:
            if queue.full():
                with contextlib.suppress(asyncio.QueueEmpty):
                    queue.get_nowait()
            await queue.put(message)
