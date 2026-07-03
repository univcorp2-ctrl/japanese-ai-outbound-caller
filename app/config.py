from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_api_key: str = ""
    internal_api_key: str = "dev-internal-key"
    database_path: str = "data/calls.db"
    dry_run: bool = True
    phone_hash_pepper: str = "development-only-pepper"

    enforce_business_hours: bool = True
    business_timezone: str = "Asia/Tokyo"
    business_hour_start: int = 9
    business_hour_end: int = 19
    max_calls_per_day: int = 20
    recipient_cooldown_days: int = 30

    livekit_url: str = ""
    livekit_api_key: str = ""
    livekit_api_secret: str = ""
    livekit_agent_name: str = "japanese-outbound-agent"
    livekit_sip_outbound_trunk_id: str = ""

    def validate_production(self) -> None:
        if self.dry_run:
            return
        required = {
            "LIVEKIT_URL": self.livekit_url,
            "LIVEKIT_API_KEY": self.livekit_api_key,
            "LIVEKIT_API_SECRET": self.livekit_api_secret,
            "LIVEKIT_SIP_OUTBOUND_TRUNK_ID": self.livekit_sip_outbound_trunk_id,
        }
        missing = [name for name, value in required.items() if not value]
        if missing:
            raise ValueError(f"Missing production settings: {', '.join(missing)}")
