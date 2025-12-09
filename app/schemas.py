from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, validator

from app.models import Role, TripType


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    username: str
    role: Role
    user_id: int


class UserCreate(BaseModel):
    username: str
    password: str
    role: Role = Role.user


class UserRead(BaseModel):
    id: int
    username: str
    role: Role

    class Config:
        orm_mode = True


class VehicleCreate(BaseModel):
    name: str
    client: Optional[str] = None
    odometer_start: float = 0


class VehicleRead(BaseModel):
    id: int
    name: str
    client: Optional[str]
    odometer_start: float

    class Config:
        orm_mode = True


class VehicleAssign(BaseModel):
    user_id: int


class OdometerUpdate(BaseModel):
    odometer_start: float


class TripBase(BaseModel):
    vehicle_id: int
    start_time: Optional[datetime] = None
    start_odometer: Optional[float] = None
    start_lat: Optional[float] = None
    start_lon: Optional[float] = None
    client: Optional[str] = None
    trip_type: TripType = TripType.business


class TripManualCreate(TripBase):
    end_time: Optional[datetime] = None
    end_odometer: float
    end_lat: Optional[float] = None
    end_lon: Optional[float] = None

    @validator("end_odometer")
    def positive(cls, value: float) -> float:
        if value < 0:
            raise ValueError("Odometer must be non-negative")
        return value


class TripStart(BaseModel):
    vehicle_id: int
    start_odometer: Optional[float] = None
    start_lat: Optional[float] = None
    start_lon: Optional[float] = None
    client: Optional[str] = None
    trip_type: TripType = TripType.business


class TripStop(BaseModel):
    end_odometer: float
    end_lat: Optional[float] = None
    end_lon: Optional[float] = None


class TripRead(BaseModel):
    id: int
    vehicle_id: int
    user_id: int
    start_time: datetime
    end_time: Optional[datetime]
    start_odometer: float
    end_odometer: Optional[float]
    start_lat: Optional[float]
    start_lon: Optional[float]
    end_lat: Optional[float]
    end_lon: Optional[float]
    trip_type: TripType
    client: Optional[str]

    class Config:
        orm_mode = True


class TripCollection(BaseModel):
    trips: List[TripRead]
