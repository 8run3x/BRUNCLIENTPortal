from datetime import datetime
from typing import List, Optional

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session, select

from app import auth, models, schemas
from app.database import engine, get_session, init_db

app = FastAPI(title="Sõidupäeviku API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    init_db()
    with Session(engine) as session:
        ensure_admin_exists(session)


def ensure_admin_exists(session: Session) -> None:
    existing_admin = session.exec(select(models.User).where(models.User.role == models.Role.admin)).first()
    if existing_admin:
        return
    admin_user = models.User(
        username="admin",
        password_hash=auth.get_password_hash("admin123"),
        role=models.Role.admin,
    )
    session.add(admin_user)
    session.commit()


@app.post("/auth/login", response_model=schemas.Token)
def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(), session: Session = Depends(get_session)
):
    user = auth.authenticate_user(session, form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect username or password")
    access_token = auth.create_access_token(
        data={"sub": user.username, "role": user.role.value, "user_id": user.id}
    )
    return schemas.Token(access_token=access_token)


@app.post("/users", response_model=schemas.UserRead)
def create_user(
    user_in: schemas.UserCreate,
    session: Session = Depends(get_session),
    admin: models.User = Depends(auth.require_admin),
):
    if auth.get_user_by_username(session, user_in.username):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already exists")
    user = models.User(
        username=user_in.username,
        password_hash=auth.get_password_hash(user_in.password),
        role=user_in.role,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@app.post("/vehicles", response_model=schemas.VehicleRead)
def create_vehicle(
    vehicle_in: schemas.VehicleCreate,
    session: Session = Depends(get_session),
    admin: models.User = Depends(auth.require_admin),
):
    vehicle = models.Vehicle(
        name=vehicle_in.name,
        client=vehicle_in.client,
        odometer_start=vehicle_in.odometer_start,
    )
    session.add(vehicle)
    session.commit()
    session.refresh(vehicle)
    return vehicle


@app.get("/vehicles", response_model=List[schemas.VehicleRead])
def list_vehicles(
    session: Session = Depends(get_session), current_user: models.User = Depends(auth.get_current_user)
):
    if current_user.role == models.Role.admin:
        statement = select(models.Vehicle)
    else:
        statement = (
            select(models.Vehicle)
            .join(models.UserVehicleLink)
            .where(models.UserVehicleLink.user_id == current_user.id)
        )
    return list(session.exec(statement).all())


@app.post("/vehicles/{vehicle_id}/assign")
def assign_vehicle(
    vehicle_id: int,
    payload: schemas.VehicleAssign,
    session: Session = Depends(get_session),
    admin: models.User = Depends(auth.require_admin),
):
    vehicle = session.get(models.Vehicle, vehicle_id)
    user = session.get(models.User, payload.user_id)
    if not vehicle or not user:
        raise HTTPException(status_code=404, detail="Vehicle or user not found")
    link = session.exec(
        select(models.UserVehicleLink)
        .where(models.UserVehicleLink.user_id == user.id)
        .where(models.UserVehicleLink.vehicle_id == vehicle.id)
    ).first()
    if not link:
        session.add(models.UserVehicleLink(user_id=user.id, vehicle_id=vehicle.id))
        session.commit()
    return {"message": "Vehicle assigned"}


@app.post("/vehicles/{vehicle_id}/odometer", response_model=schemas.VehicleRead)
def update_vehicle_odometer(
    vehicle_id: int,
    payload: schemas.OdometerUpdate,
    session: Session = Depends(get_session),
    admin: models.User = Depends(auth.require_admin),
):
    vehicle = session.get(models.Vehicle, vehicle_id)
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    vehicle.odometer_start = payload.odometer_start
    session.add(vehicle)
    session.commit()
    session.refresh(vehicle)
    return vehicle


def verify_vehicle_access(session: Session, user: models.User, vehicle_id: int) -> models.Vehicle:
    vehicle = session.get(models.Vehicle, vehicle_id)
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    if user.role == models.Role.admin:
        return vehicle
    allowed = session.exec(
        select(models.UserVehicleLink)
        .where(models.UserVehicleLink.user_id == user.id)
        .where(models.UserVehicleLink.vehicle_id == vehicle_id)
    ).first()
    if not allowed:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Vehicle not assigned to user")
    return vehicle


def get_last_odometer(session: Session, vehicle_id: int) -> float:
    last_trip = session.exec(
        select(models.Trip)
        .where(models.Trip.vehicle_id == vehicle_id)
        .where(models.Trip.end_odometer.is_not(None))
        .order_by(models.Trip.end_time.desc())
    ).first()
    if last_trip and last_trip.end_odometer is not None:
        return last_trip.end_odometer
    vehicle = session.get(models.Vehicle, vehicle_id)
    return vehicle.odometer_start if vehicle else 0


@app.post("/trips/manual", response_model=schemas.TripRead)
def create_manual_trip(
    trip_in: schemas.TripManualCreate,
    session: Session = Depends(get_session),
    current_user: models.User = Depends(auth.get_current_user),
):
    vehicle = verify_vehicle_access(session, current_user, trip_in.vehicle_id)
    start_odometer = trip_in.start_odometer or get_last_odometer(session, vehicle.id)
    start_time = trip_in.start_time or datetime.utcnow()
    if trip_in.end_odometer < start_odometer:
        raise HTTPException(status_code=400, detail="End odometer cannot be lower than start")
    trip = models.Trip(
        vehicle_id=vehicle.id,
        user_id=current_user.id,
        start_time=start_time,
        end_time=trip_in.end_time or datetime.utcnow(),
        start_odometer=start_odometer,
        end_odometer=trip_in.end_odometer,
        start_lat=trip_in.start_lat,
        start_lon=trip_in.start_lon,
        end_lat=trip_in.end_lat,
        end_lon=trip_in.end_lon,
        trip_type=trip_in.trip_type,
        client=trip_in.client,
    )
    session.add(trip)
    session.commit()
    session.refresh(trip)
    return trip


@app.post("/trips/start", response_model=schemas.TripRead)
def start_trip(
    payload: schemas.TripStart,
    session: Session = Depends(get_session),
    current_user: models.User = Depends(auth.get_current_user),
):
    vehicle = verify_vehicle_access(session, current_user, payload.vehicle_id)
    start_odometer = payload.start_odometer or get_last_odometer(session, vehicle.id)
    trip = models.Trip(
        vehicle_id=vehicle.id,
        user_id=current_user.id,
        start_time=datetime.utcnow(),
        start_odometer=start_odometer,
        start_lat=payload.start_lat,
        start_lon=payload.start_lon,
        trip_type=payload.trip_type,
        client=payload.client,
    )
    session.add(trip)
    session.commit()
    session.refresh(trip)
    return trip


@app.post("/trips/{trip_id}/stop", response_model=schemas.TripRead)
def stop_trip(
    trip_id: int,
    payload: schemas.TripStop,
    session: Session = Depends(get_session),
    current_user: models.User = Depends(auth.get_current_user),
):
    trip = session.get(models.Trip, trip_id)
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    if current_user.role != models.Role.admin and trip.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to finish this trip")
    if trip.end_time is not None:
        raise HTTPException(status_code=400, detail="Trip already finished")
    if payload.end_odometer < trip.start_odometer:
        raise HTTPException(status_code=400, detail="End odometer cannot be lower than start")
    trip.end_time = datetime.utcnow()
    trip.end_odometer = payload.end_odometer
    trip.end_lat = payload.end_lat
    trip.end_lon = payload.end_lon
    session.add(trip)
    session.commit()
    session.refresh(trip)
    return trip


@app.get("/trips", response_model=schemas.TripCollection)
def list_trips(
    client: Optional[str] = None,
    session: Session = Depends(get_session),
    current_user: models.User = Depends(auth.get_current_user),
):
    statement = select(models.Trip)
    if current_user.role != models.Role.admin:
        statement = statement.where(models.Trip.user_id == current_user.id)
    if client:
        statement = statement.where(models.Trip.client == client)
    trips = session.exec(statement.order_by(models.Trip.start_time.desc())).all()
    return schemas.TripCollection(trips=trips)
