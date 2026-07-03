import json
from dataclasses import dataclass
from typing import Any, Protocol
from uuid import uuid4

from app.config import Settings


@dataclass(frozen=True)
class DispatchResult:
    room_name: str
    dispatch_id: str


class Dispatcher(Protocol):
    async def dispatch(self, metadata: dict[str, Any]) -> DispatchResult: ...


class DryRunDispatcher:
    async def dispatch(self, metadata: dict[str, Any]) -> DispatchResult:
        call_id = str(metadata["call_id"])
        return DispatchResult(
            room_name=f"dry-run-{call_id}",
            dispatch_id=f"dry-{uuid4().hex[:12]}",
        )


class LiveKitDispatcher:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def dispatch(self, metadata: dict[str, Any]) -> DispatchResult:
        from livekit import api

        room_name = f"outbound-{metadata['call_id']}"
        client = api.LiveKitAPI(
            self.settings.livekit_url,
            self.settings.livekit_api_key,
            self.settings.livekit_api_secret,
        )
        try:
            dispatch = await client.agent_dispatch.create_dispatch(
                api.CreateAgentDispatchRequest(
                    agent_name=self.settings.livekit_agent_name,
                    room=room_name,
                    metadata=json.dumps(metadata, ensure_ascii=False),
                )
            )
        finally:
            await client.aclose()
        return DispatchResult(room_name=room_name, dispatch_id=dispatch.id)
