from pydantic import BaseModel, validator
from typing import Optional
from datetime import datetime, timedelta


def _next_weekday_for_relative_date(value: str) -> Optional[datetime]:
    weekday_map = {
        "monday": 0,
        "tuesday": 1,
        "wednesday": 2,
        "thursday": 3,
        "friday": 4,
        "saturday": 5,
        "sunday": 6,
    }

    key = value.strip().lower().replace("next ", "", 1)
    target = weekday_map.get(key)
    if target is None:
        return None

    today = datetime.now()
    days_ahead = (target - today.weekday()) % 7
    if days_ahead == 0:
        days_ahead = 7

    return datetime.combine((today.date() + timedelta(days=days_ahead)), datetime.min.time())


class AIExtraction(BaseModel):
    doctor_name: str
    hospital: Optional[str] = None
    specialization: Optional[str] = None
    city: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    products_discussed: Optional[str] = None
    follow_up_date: Optional[datetime] = None
    meeting_summary: str

    @validator("products_discussed", pre=True)
    def parse_products(cls, v):
        if isinstance(v, list):
            return ", ".join(str(x).strip() for x in v if str(x).strip())
        return v

    @validator("phone", "email", pre=True)
    def normalize_optional_contact(cls, v):
        if v is None or v == "":
            return None
        if isinstance(v, str):
            value = v.strip()
            return value or None
        return str(v).strip() or None

    @validator("doctor_name", "meeting_summary")
    def not_empty(cls, v):
        if v is None or (isinstance(v, str) and not v.strip()):
            raise ValueError("must not be empty")
        return v

    @validator("follow_up_date", pre=True)
    def parse_follow_up(cls, v):
        if v is None or v == "":
            return None
        if isinstance(v, datetime):
            return v
        if isinstance(v, str):
            value = v.strip()
            if not value:
                return None
            lower_value = value.lower()
            if lower_value.startswith("next "):
                relative_date = _next_weekday_for_relative_date(value)
                if relative_date is not None:
                    return relative_date
            try:
                return datetime.fromisoformat(value)
            except Exception:
                try:
                    return datetime.fromisoformat(f"{value}T00:00:00")
                except Exception:
                    raise ValueError("follow_up_date must be an ISO8601 datetime string or a relative 'next <weekday>' value or null")
        raise ValueError("follow_up_date must be an ISO8601 datetime string or a relative 'next <weekday>' value or null")
