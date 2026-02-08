"""SSEイベントストリームルート"""

import asyncio
import json
import logging

from fastapi import APIRouter, Depends, Query
from sse_starlette.sse import EventSourceResponse

from api.dependencies import get_current_user
from api.services.event_stream import get_event_stream

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/events", tags=["events"])


@router.get("/stream")
async def event_stream(
    guild_id: int = Query(..., description="ギルドID"),
    current_user: dict = Depends(get_current_user),
):
    """SSEイベントストリーム（JWT認証必須）"""
    manager = get_event_stream()
    queue = manager.subscribe(guild_id)

    async def event_generator():
        try:
            while True:
                try:
                    data = await asyncio.wait_for(queue.get(), timeout=15.0)
                    yield {
                        "event": data.get("type", "message"),
                        "data": json.dumps(data, default=str),
                    }
                except asyncio.TimeoutError:
                    yield {"event": "heartbeat", "data": "ping"}
        except asyncio.CancelledError:
            pass
        finally:
            manager.unsubscribe(guild_id, queue)

    return EventSourceResponse(event_generator())
