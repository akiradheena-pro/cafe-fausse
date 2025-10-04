from pydantic import BaseModel, EmailStr, Field, field_validator
from datetime import datetime


BUSINESS_HOURS = {
    0: (17, 22), 
    1: (17, 22),
    2: (17, 22),
    3: (17, 22),
    4: (17, 22),
    5: (17, 22),
    6: (17, 20), 
}

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
    def validate_reservation_time(cls, v: datetime):

        if v.astimezone() <= datetime.now().astimezone():
            raise ValueError('Reservation time must be in the future.')
        
        weekday = v.weekday()
        request_hour = v.hour
        
        if weekday not in BUSINESS_HOURS:
            raise ValueError('Reservations are not available on this day.')
            
        open_hour, last_booking_hour = BUSINESS_HOURS[weekday]
        if not (open_hour <= request_hour <= last_booking_hour):
            raise ValueError(f'Reservations are only accepted between {open_hour}:00 and {last_booking_hour}:59 on this day.')
            
        return v