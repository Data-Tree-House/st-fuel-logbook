import uuid
from collections.abc import Sequence

from loguru import logger
from sqlalchemy import func, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, selectinload

from db.model import Car, FuelEntry


def get_all_cars(
    user_id: str,
    engine: Engine,
) -> Sequence[Car] | None:
    """Gets all the cars for a user.

    Args:
        user_id (str): The user's sub
        engine (Engine): The SQLAlchemy engine to use for the query

    Returns:
        Sequence[Car] | None: A list of Car objects if any are found, otherwise None
    """

    with Session(engine) as session:
        stmt = select(Car).where(
            Car.user_id == user_id,
            Car.is_deleted == False,  # noqa: E712
        )
        cars: Sequence[Car] = session.execute(stmt).scalars().all()
        if not cars:
            logger.info(f"No cars found for user {user_id}")
            return None
        return cars


def get_all_fuel_entries(
    user_id: str,
    engine: Engine,
    load_car: bool = False,
) -> Sequence[FuelEntry] | None:
    with Session(engine) as session:
        stmt = (
            select(FuelEntry)
            .join(
                Car,
                FuelEntry.car_id == Car.id,
                full=True,
            )
            .where(
                Car.user_id == user_id,
                Car.is_deleted == False,  # noqa: E712
                FuelEntry.is_deleted == False,  # noqa: E712
            )
            .order_by(FuelEntry.entry_datetime.desc())
        )

        if load_car:
            stmt = stmt.options(selectinload(FuelEntry.car))  # EAGER!!!

        entries: Sequence[FuelEntry] = session.execute(stmt).scalars().all()
        if not entries:
            logger.info(f"No fuel entries found for user {user_id}")
            return None
        return entries


def get_user_fuel_stats(user_id: str, engine: Engine) -> dict[str, float]:
    """Return aggregate fuel-log statistics for a user across all their cars.

    Args:
        user_id: The user's ``sub``.
        engine: SQLAlchemy engine.

    Returns:
        A dict with keys ``entry_count``, ``total_trip_km``,
        ``total_fuel_litres``, and ``total_expense_zar``.
        All values default to ``0.0`` when the user has no entries.
    """
    with Session(engine) as session:
        # Join through cars so we only count entries belonging to this user.
        result = session.execute(
            select(
                func.count(FuelEntry.id).label("entry_count"),
                func.coalesce(func.sum(FuelEntry.trip), 0).label("total_trip_km"),
                func.coalesce(func.sum(FuelEntry.fuel_filled), 0).label("total_fuel_litres"),
                func.coalesce(func.sum(FuelEntry.price), 0).label("total_expense_zar"),
            )
            .join(Car, FuelEntry.car_id == Car.id)
            .where(
                Car.user_id == user_id,
                Car.is_deleted == False,  # noqa: E712
            )
        ).one()

    return {
        "entry_count": float(result.entry_count),
        "total_trip_km": float(result.total_trip_km),
        "total_fuel_litres": float(result.total_fuel_litres),
        "total_expense_zar": float(result.total_expense_zar),
    }


def get_fuel_entries_for_car(
    car_id: uuid.UUID,
    engine: Engine,
) -> Sequence[FuelEntry] | None:
    """Get all non-deleted fuel entries for a specific car, newest first.

    Args:
        car_id: UUID of the car.
        engine: SQLAlchemy engine.

    Returns:
        Sequence of FuelEntry objects, or None if none found.
    """
    with Session(engine) as session:
        stmt = (
            select(FuelEntry)
            .where(
                FuelEntry.car_id == car_id,
                FuelEntry.is_deleted == False,  # noqa: E712
            )
            .order_by(FuelEntry.entry_datetime.desc())
        )
        entries: Sequence[FuelEntry] = session.execute(stmt).scalars().all()
        if not entries:
            logger.info(f"No fuel entries found for car {car_id}")
            return None
        return entries
