import re
from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

from app.config import Settings

E164_PATTERN = re.compile(r"^\+[1-9]\d{7,14}$")


@dataclass(frozen=True)
class PolicyDecision:
    allowed: bool
    reason: str


class CallingPolicy:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def evaluate_phone(self, phone_number: str) -> PolicyDecision:
        if not E164_PATTERN.fullmatch(phone_number):
            return PolicyDecision(False, "phone_number must use E.164 format")
        return PolicyDecision(True, "valid E.164 number")

    def evaluate_time(self, now: datetime | None = None) -> PolicyDecision:
        if not self.settings.enforce_business_hours:
            return PolicyDecision(True, "business-hours policy disabled")
        local_now = now or datetime.now(ZoneInfo(self.settings.business_timezone))
        if local_now.tzinfo is None:
            local_now = local_now.replace(tzinfo=ZoneInfo(self.settings.business_timezone))
        else:
            local_now = local_now.astimezone(ZoneInfo(self.settings.business_timezone))
        if local_now.weekday() >= 5:
            return PolicyDecision(False, "outbound calls are disabled on weekends")
        if not (
            self.settings.business_hour_start
            <= local_now.hour
            < self.settings.business_hour_end
        ):
            return PolicyDecision(False, "outside configured business hours")
        return PolicyDecision(True, "within configured business hours")
