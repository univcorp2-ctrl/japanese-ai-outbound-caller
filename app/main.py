import secrets
from datetime import UTC, datetime, timedelta
from typing import Annotated
from uuid import uuid4

from fastapi import Depends, FastAPI, Header, HTTPException, status

from app.config import Settings
from app.dispatcher import Dispatcher, DryRunDispatcher, LiveKitDispatcher
from app.models import CallRequest, CallResponse, CallStatus, HealthResponse, SuppressionRequest
from app.policy import CallingPolicy
from app.privacy import mask_phone, phone_hash
from app.storage import SQLiteStore


def create_app(settings: Settings | None = None, store: SQLiteStore | None = None,
               dispatcher: Dispatcher | None = None) -> FastAPI:
    config = settings or Settings()
    config.validate_production()
    database = store or SQLiteStore(config.database_path)
    call_dispatcher = dispatcher or (DryRunDispatcher() if config.dry_run else LiveKitDispatcher(config))
    policy = CallingPolicy(config)
    app = FastAPI(title="Japanese AI Outbound Caller", version="0.1.0")

    def require_app_key(x_api_key: Annotated[str | None, Header()] = None) -> None:
        if config.app_api_key and (
            x_api_key is None or not secrets.compare_digest(x_api_key, config.app_api_key)
        ):
            raise HTTPException(status_code=401, detail="invalid API key")

    def require_internal_key(x_internal_api_key: Annotated[str | None, Header()] = None) -> None:
        if x_internal_api_key is None or not secrets.compare_digest(
            x_internal_api_key, config.internal_api_key
        ):
            raise HTTPException(status_code=401, detail="invalid internal API key")

    @app.get("/healthz", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse(status="ok", dry_run=config.dry_run)

    @app.post("/v1/calls", response_model=CallResponse, status_code=status.HTTP_202_ACCEPTED,
              dependencies=[Depends(require_app_key)])
    async def create_call(request: CallRequest) -> CallResponse:
        phone_decision = policy.evaluate_phone(request.phone_number)
        if not phone_decision.allowed:
            raise HTTPException(status_code=422, detail=phone_decision.reason)
        time_decision = policy.evaluate_time()
        if not time_decision.allowed:
            raise HTTPException(status_code=403, detail=time_decision.reason)
        hashed_phone = phone_hash(request.phone_number, config.phone_hash_pepper)
        masked_phone = mask_phone(request.phone_number)
        if database.is_suppressed(hashed_phone):
            raise HTTPException(status_code=409, detail="recipient is on the suppression list")
        now = datetime.now(UTC)
        start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
        if database.count_calls_since(start_of_day.isoformat()) >= config.max_calls_per_day:
            raise HTTPException(status_code=429, detail="daily call limit reached")
        latest = database.latest_call_for_phone(hashed_phone)
        if latest and now - datetime.fromisoformat(latest) < timedelta(days=config.recipient_cooldown_days):
            raise HTTPException(status_code=429, detail="recipient cooldown is active")
        call_id = str(uuid4())
        created_at = now.isoformat()
        database.create_call({
            "id": call_id, "phone_hash": hashed_phone, "phone_masked": masked_phone,
            "recipient_name": request.recipient_name, "purpose": request.purpose,
            "consent_basis": request.consent_basis.value, "status": CallStatus.QUEUED.value,
            "room_name": None, "dispatch_id": None, "error": None, "created_at": created_at,
        })
        metadata = {
            "call_id": call_id, "phone_number": request.phone_number,
            "recipient_name": request.recipient_name, "purpose": request.purpose,
            "consent_basis": request.consent_basis.value, "context": request.context,
            "transfer_to": request.transfer_to,
        }
        try:
            result = await call_dispatcher.dispatch(metadata)
        except Exception as exc:
            database.update_dispatch(call_id, status=CallStatus.FAILED.value, error=str(exc))
            raise HTTPException(status_code=502, detail="voice dispatch failed") from exc
        database.update_dispatch(call_id, status=CallStatus.DISPATCHED.value,
                                 room_name=result.room_name, dispatch_id=result.dispatch_id)
        return CallResponse(
            id=call_id, status=CallStatus.DISPATCHED, phone_masked=masked_phone,
            room_name=result.room_name, dispatch_id=result.dispatch_id, created_at=created_at,
            policy_summary=f"{phone_decision.reason}; {time_decision.reason}; consent={request.consent_basis.value}",
        )

    @app.get("/v1/calls/{call_id}", response_model=CallResponse,
             dependencies=[Depends(require_app_key)])
    def get_call(call_id: str) -> CallResponse:
        record = database.get_call(call_id)
        if record is None:
            raise HTTPException(status_code=404, detail="call not found")
        return CallResponse(
            id=record["id"], status=CallStatus(record["status"]),
            phone_masked=record["phone_masked"], room_name=record["room_name"],
            dispatch_id=record["dispatch_id"], created_at=record["created_at"],
            policy_summary=f"consent={record['consent_basis']}",
        )

    @app.post("/v1/internal/opt-outs", status_code=status.HTTP_204_NO_CONTENT,
              dependencies=[Depends(require_internal_key)])
    def add_opt_out(request: SuppressionRequest) -> None:
        decision = policy.evaluate_phone(request.phone_number)
        if not decision.allowed:
            raise HTTPException(status_code=422, detail=decision.reason)
        database.add_suppression(phone_hash(request.phone_number, config.phone_hash_pepper),
                                 mask_phone(request.phone_number), request.reason)

    return app


app = create_app()
