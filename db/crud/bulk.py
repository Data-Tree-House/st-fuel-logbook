"""Transactional bulk-upload persistence layer."""

from loguru import logger
from openpyxl.workbook import Workbook
from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from db.model import Car, FuelEntry
from utils.bulk_upload import ParsedVehicle, parse_fuel_entries_sheet


def save_bulk_upload(
    user_id: str,
    wb: Workbook,
    parsed_vehicles: list[ParsedVehicle],
    engine: Engine,
) -> tuple[list[Car], list[FuelEntry]]:
    """Transactionally insert new cars and fuel entries from a bulk upload.

    Execution order within a single transaction:

    1. Resolve every vehicle to a database ``Car.id``:
       - If ``ParsedVehicle.id`` is set, use it directly.
       - If ``id`` is ``None``, check whether a car with the same nickname
         already exists for this user (idempotent re-upload safety).  If it
         does, reuse its ID.  Otherwise insert a new ``Car``.
    2. ``flush()`` so newly inserted cars receive their primary keys.
    3. Build a ``nickname -> car_id`` map from all resolved vehicles.
    4. Parse the ``Fuel Entries`` sheet using the resolved mapping.
    5. Insert all :class:`~db.model.FuelEntry` rows.
    6. ``commit()``.

    If *any* step raises an exception the transaction is rolled back in full
    and the exception is re-raised to the caller.

    Args:
        user_id: The ``sub`` of the currently logged-in user.
        wb: The uploaded workbook (used to parse the Fuel Entries sheet).
        parsed_vehicles: Vehicles parsed from the Vehicles sheet.  Items with
            ``id=None`` will be created or matched to an existing car by
            nickname; items with a non-``None`` ``id`` are used as-is.
        engine: SQLAlchemy engine.

    Returns:
        A tuple of ``(new_cars, fuel_entries)`` listing exactly the rows that
        were committed to the database.

    Raises:
        ValueError: If the fuel entry sheet contains parse errors after car IDs
            are resolved.
        Exception: Any other database error (re-raised after rollback).
    """
    with Session(engine, expire_on_commit=False) as session:
        try:
            # ── 1. Resolve / insert cars ───────────────────────────────────────
            # Pre-fetch existing cars for this user so we can match by nickname
            # without issuing a separate query per row.
            existing_by_nickname: dict[str, Car] = {
                car.nickname: car
                for car in session.execute(
                    select(Car).where(Car.user_id == user_id, Car.is_deleted == False)  # noqa: E712
                ).scalars()
            }

            new_cars: list[tuple[str, Car]] = []
            nickname_to_car_id: dict[str, int] = {}

            for pv in parsed_vehicles:
                if pv.id is not None:
                    # Explicit ID provided - use it directly.
                    nickname_to_car_id[pv.nickname] = pv.id

                elif pv.nickname in existing_by_nickname:
                    # Car already exists - reuse it (idempotent re-upload).
                    existing = existing_by_nickname[pv.nickname]
                    logger.info(
                        f"Bulk upload: car '{pv.nickname}' already exists "
                        f"(id={existing.id}) for user {user_id} -  reusing."
                    )
                    nickname_to_car_id[pv.nickname] = existing.id  # type: ignore[assignment]

                else:
                    # Genuinely new car - insert it.
                    logger.info(f"Bulk upload: creating new car '{pv.nickname}' for user {user_id}")
                    car = Car(
                        user_id=user_id,
                        nickname=pv.nickname,
                        fuel_type=pv.fuel_type,
                        registration_number=pv.registration_number,
                        vin_number=pv.vin_number,
                        model_description=pv.model_description,
                        color=pv.color,
                        registration_date=pv.registration_date,
                    )
                    session.add(car)
                    new_cars.append((pv.nickname, car))

            # ── 2. Flush so new cars receive their primary keys ────────────────
            session.flush()
            for nickname, car in new_cars:
                nickname_to_car_id[nickname] = car.id  # type: ignore[assignment]

            # ── 3. Parse fuel entries ──────────────────────────────────────────
            fuel_entries, parse_errors = parse_fuel_entries_sheet(wb, nickname_to_car_id)
            if parse_errors:
                details = "; ".join(f"Row {e.row}: {e.error}" for e in parse_errors)
                raise ValueError(f"Fuel entry errors after resolving car IDs: {details}")

            # ── 4. Insert fuel entries ─────────────────────────────────────────
            session.add_all(fuel_entries)

            # ── 5. Commit ─────────────────────────────────────────────────────
            session.commit()

            created_cars = [car for _, car in new_cars]
            logger.info(
                f"Bulk upload committed for user {user_id}: "
                f"{len(created_cars)} new car(s), {len(fuel_entries)} fuel entr(ies)."
            )
            return created_cars, fuel_entries

        except Exception:
            session.rollback()
            raise

    """Transactionally insert new cars and fuel entries from a bulk upload.

    Execution order within a single transaction:

    1. Insert any new :class:`~db.model.Car` rows (vehicles with ``id=None``).
    2. ``flush()`` so SQLAlchemy assigns primary keys to the new cars.
    3. Build a ``nickname -> car_id`` map from both pre-existing and new cars.
    4. Parse the ``Fuel Entries`` sheet using the resolved mapping.
    5. Insert all :class:`~db.model.FuelEntry` rows.
    6. ``commit()``.

    If *any* step raises an exception the transaction is rolled back in full
    and the exception is re-raised to the caller.

    Args:
        user_id: The ``sub`` of the currently logged-in user.
        wb: The uploaded workbook (used to parse the Fuel Entries sheet).
        parsed_vehicles: Vehicles parsed from the Vehicles sheet.  Items with
            ``id=None`` will be created; items with a non-``None`` ``id`` are
            assumed to already exist in the database.
        engine: SQLAlchemy engine.

    Returns:
        A tuple of ``(new_cars, fuel_entries)`` listing exactly the rows that
        were committed to the database.

    Raises:
        ValueError: If the fuel entry sheet contains parse errors after car IDs
            are resolved.
        Exception: Any other database error (re-raised after rollback).
    """
    with Session(engine, expire_on_commit=False) as session:
        try:
            # ── 1. Insert new cars ─────────────────────────────────────────────
            new_cars: list[tuple[str, Car]] = []
            for pv in parsed_vehicles:
                if pv.id is None:
                    logger.info(f"Bulk upload: creating new car '{pv.nickname}' for user {user_id}")
                    car = Car(
                        user_id=user_id,
                        nickname=pv.nickname,
                        fuel_type=pv.fuel_type,
                        registration_number=pv.registration_number,
                        vin_number=pv.vin_number,
                        model_description=pv.model_description,
                        color=pv.color,
                        registration_date=pv.registration_date,
                    )
                    session.add(car)
                    new_cars.append((pv.nickname, car))

            # ── 2. Flush so new cars receive their primary keys ────────────────
            session.flush()

            # ── 3. Build nickname → car_id mapping ────────────────────────────
            nickname_to_car_id: dict[str, int] = {pv.nickname: pv.id for pv in parsed_vehicles if pv.id is not None}
            for nickname, car in new_cars:
                nickname_to_car_id[nickname] = car.id  # type: ignore[assignment]

            # ── 4. Parse fuel entries ──────────────────────────────────────────
            fuel_entries, parse_errors = parse_fuel_entries_sheet(wb, nickname_to_car_id)
            if parse_errors:
                details = "; ".join(f"Row {e.row}: {e.error}" for e in parse_errors)
                raise ValueError(f"Fuel entry errors after resolving car IDs: {details}")

            # ── 5. Insert fuel entries ─────────────────────────────────────────
            session.add_all(fuel_entries)

            # ── 6. Commit ─────────────────────────────────────────────────────
            session.commit()

            created_cars = [car for _, car in new_cars]
            logger.info(
                f"Bulk upload committed for user {user_id}: "
                f"{len(created_cars)} new car(s), {len(fuel_entries)} fuel entr(ies)."
            )
            return created_cars, fuel_entries

        except Exception:
            session.rollback()
            raise
