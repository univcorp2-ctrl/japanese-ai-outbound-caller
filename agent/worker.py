import asyncio
import json
import os
from dataclasses import dataclass

import httpx
from livekit import api
from livekit.agents import Agent, AgentSession, JobContext, WorkerOptions, cli, function_tool
from livekit.plugins import openai


@dataclass(frozen=True)
class CallMetadata:
    call_id: str
    phone_number: str
    recipient_name: str
    purpose: str
    consent_basis: str
    context: dict
    transfer_to: str | None

    @classmethod
    def from_json(cls, raw: str) -> "CallMetadata":
        return cls(**json.loads(raw))


class JapaneseOutboundAgent(Agent):
    def __init__(self, ctx: JobContext, metadata: CallMetadata) -> None:
        self.ctx = ctx
        self.metadata = metadata
        instructions = f"""
あなたは企業の電話担当AIです。自然で簡潔な日本語を使い、相手の発言を遮らず、
文脈を踏まえて一問ずつ返答してください。最初に必ず会社名・担当名・用件・
AI音声であることを明示し、会話継続の了承を取ってください。
相手が不要、停止、二度と電話しないで等と述べたら、直ちに opt_out を実行し、
謝意を述べて終了してください。知らないことを推測せず、個人情報を必要以上に
聞かないでください。契約、医療、法務、金融の最終判断は行わず、人間へ転送します。
受信者名: {metadata.recipient_name}
用件: {metadata.purpose}
同意根拠: {metadata.consent_basis}
補足文脈: {json.dumps(metadata.context, ensure_ascii=False)}
"""
        super().__init__(instructions=instructions)

    @function_tool
    async def opt_out(self, reason: str = "recipient_opt_out") -> str:
        """Add the recipient to the permanent suppression list and end politely."""
        control_plane = os.environ.get("CONTROL_PLANE_URL", "http://api:8000")
        internal_key = os.environ["INTERNAL_API_KEY"]
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(
                f"{control_plane}/v1/internal/opt-outs",
                headers={"X-Internal-API-Key": internal_key},
                json={"phone_number": self.metadata.phone_number, "reason": reason},
            )
            response.raise_for_status()
        return "The recipient was suppressed. Apologize briefly and end the call."

    @function_tool
    async def transfer_to_human(self, reason: str) -> str:
        """Transfer the call to a configured human operator when escalation is needed."""
        destination = self.metadata.transfer_to or os.environ.get("HUMAN_TRANSFER_NUMBER")
        if not destination:
            return "No operator is configured. Offer a callback and end politely."
        participant = next(iter(self.ctx.room.remote_participants.values()), None)
        if participant is None:
            return "The caller participant is unavailable."
        await self.ctx.api.sip.transfer_sip_participant(
            api.TransferSIPParticipantRequest(
                room_name=self.ctx.room.name,
                participant_identity=participant.identity,
                transfer_to=f"tel:{destination}",
                play_dialtone=True,
            )
        )
        return f"Transfer started because: {reason}"


async def entrypoint(ctx: JobContext) -> None:
    metadata = CallMetadata.from_json(ctx.job.metadata)
    session = AgentSession(
        llm=openai.realtime.RealtimeModel(
            model=os.environ.get("OPENAI_REALTIME_MODEL", "gpt-realtime-2"),
            voice=os.environ.get("OPENAI_VOICE", "marin"),
        )
    )
    await session.start(room=ctx.room, agent=JapaneseOutboundAgent(ctx, metadata))

    trunk_id = os.environ["LIVEKIT_SIP_OUTBOUND_TRUNK_ID"]
    participant = await ctx.api.sip.create_sip_participant(
        api.CreateSIPParticipantRequest(
            room_name=ctx.room.name,
            sip_trunk_id=trunk_id,
            sip_call_to=metadata.phone_number,
            participant_identity=f"phone-{metadata.call_id}",
            participant_name=metadata.recipient_name,
            wait_until_answered=True,
        )
    )
    await asyncio.sleep(0.2)
    await session.generate_reply(
        instructions=(
            "電話がつながりました。会社名、あなたの担当名、用件、AI音声であることを"
            "最初に明示し、今話せるか確認してください。"
        )
    )
    await participant.wait_for_disconnection()


if __name__ == "__main__":
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            agent_name=os.environ.get("LIVEKIT_AGENT_NAME", "japanese-outbound-agent"),
        )
    )
