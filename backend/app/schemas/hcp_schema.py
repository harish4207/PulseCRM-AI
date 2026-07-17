from pydantic import BaseModel, EmailStr


class HCPCreate(BaseModel):
    doctor_name: str
    specialization: str
    hospital: str
    city: str
    phone: str
    email: EmailStr


class HCPResponse(HCPCreate):
    id: int

    class Config:
        from_attributes = True
class HCPUpdate(BaseModel):
    doctor_name: str
    specialization: str
    hospital: str
    city: str
    phone: str
    email: EmailStr