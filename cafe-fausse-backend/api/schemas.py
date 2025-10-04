from pydantic import BaseModel, EmailStr, Field, field_validator
from datetime import datetime

class SubscribeRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=120, strip_whitespace=True)
    email: EmailStr  
    phone: str | None = Field(None, max_length=32, strip_whitespace=True)

class CreateReservationRequest(BaseModel):
    time: datetime
    guests: int = Field(..., gt=0, le=10) 
    name: str = Field(..., min_length=1, max_length=120, strip_whitespace=True)
    email: EmailStr
    phone: str | None = Field(None, max_length=32, strip_whitespace=True)

    @field_validator('time')
    @classmethod
    def time_must_be_in_future(cls, v: datetime):
        if v.astimezone() <= datetime.now().astimezone():
            raise ValueError('Reservation time must be in the future.')
        return v