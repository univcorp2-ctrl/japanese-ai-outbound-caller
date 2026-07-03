from datetime import datetime
from zoneinfo import ZoneInfo

from app.config import Settings
from app.policy import CallingPolicy


def test_japanese_business_hours():
    policy = CallingPolicy(Settings(enforce_business_hours=True))
    zone = ZoneInfo("Asia/Tokyo")
    assert policy.evaluate_time(datetime(2026, 7, 3, 10, tzinfo=zone)).allowed
    assert not policy.evaluate_time(datetime(2026, 7, 3, 20, tzinfo=zone)).allowed
    assert not policy.evaluate_time(datetime(2026, 7, 4, 10, tzinfo=zone)).allowed


def test_e164_validation():
    policy = CallingPolicy(Settings())
    assert policy.evaluate_phone("+819012345678").allowed
    assert not policy.evaluate_phone("09012345678").allowed
