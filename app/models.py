import enum
from datetime import datetime
from typing import List, Optional

from sqlmodel import Field, Relationship, SQLModel


class Role(str, enum.Enum):
    admin = "admin"
    user = "user"


class TripType(str, enum.Enum):
    business = "business"
    personal = "personal"


class UserVehicleLink(SQLModel, table=True):
    user_id: Optional[int] = Field(default=None, foreign_key="user.id", primary_key=True)
    vehicle_id: Optional[int] = Field(default=None, foreign_key="vehicle.id", primary_key=True)


class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True)
    password_hash: str
    role: Role = Field(default=Role.user)

    vehicles: List["Vehicle"] = Relationship(back_populates="users", link_model=UserVehicleLink)
    trips: List["Trip"] = Relationship(back_populates="user")


class Vehicle(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    client: Optional[str] = Field(default=None, index=True)
    odometer_start: float = Field(default=0)

    users: List[User] = Relationship(back_populates="vehicles", link_model=UserVehicleLink)
    trips: List["Trip"] = Relationship(back_populates="vehicle")


class Trip(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    vehicle_id: int = Field(foreign_key="vehicle.id")
    user_id: int = Field(foreign_key="user.id")
    start_time: datetime = Field(default_factory=datetime.utcnow)
    end_time: Optional[datetime] = None
    start_odometer: float
    end_odometer: Optional[float] = None
    start_lat: Optional[float] = None
    start_lon: Optional[float] = None
    end_lat: Optional[float] = None
    end_lon: Optional[float] = None
    trip_type: TripType = Field(default=TripType.business)
    client: Optional[str] = Field(default=None, index=True)

    vehicle: Vehicle = Relationship(back_populates="trips")
    user: User = Relationship(back_populates="trips")
