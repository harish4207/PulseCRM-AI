from pydantic import BaseModel, validator
from typing import Optional
from datetime import datetime


class AIExtraction(BaseModel):
    doctor_name: str
    hospital: Optional[str] = None
    specialization: Optional[str] = None
    city: Optional[str] = None
    products_discussed: Optional[str] = None
    follow_up_date: Optional[datetime] = None
    meeting_summary: str

    @validator("products_discussed", pre=True)
    def parse_products(cls, v):
        if isinstance(v, list):
            return ", ".join(str(x).strip() for x in v if str(x).strip())
        return v

    @validator("doctor_name", "meeting_summary")
    def not_empty(cls, v):
        if v is None or (isinstance(v, str) and not v.strip()):
            raise ValueError("must not be empty")
        return v

    @validator("follow_up_date", pre=True)
    def parse_follow_up(cls, v):
        if v is None:
            return None
        if isinstance(v, datetime):
            return v
        if isinstance(v, str):
            try:
                # Allow ISO 8601 strings
                return datetime.fromisoformat(v)
            except Exception:
                raise ValueError("follow_up_date must be an ISO8601 datetime string or null")
        raise ValueError("follow_up_date must be an ISO8601 datetime string or null")
