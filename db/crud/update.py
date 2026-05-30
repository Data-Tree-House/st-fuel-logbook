import uuid

from loguru import logger
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from db.model import FuelEntry


def update_fuel_entry(
    entry_id: uuid.UUID,
    changes: dict[str, object],
    engine: Engine,
) -> bool:
    """Update specific fields of a fuel entry.

    Args:
        entry_id: UUID of the entry to update.
        changes: Dict mapping field name to new value.
        engine: SQLAlchemy engine.

    Returns:
        True if the entry was found and updated, False otherwise.
    """
    with Session(engine) as session:
        entry = session.get(FuelEntry, entry_id)
        if entry is None:
            logger.warning(f"FuelEntry {entry_id} not found for update")
            return False
        for field, value in changes.items():
            setattr(entry, field, value)
        session.commit()
    return True


def soft_delete_fuel_entry(
    entry_id: uuid.UUID,
    engine: Engine,
) -> bool:
    """Soft-delete a fuel entry by setting is_deleted=True.

    Args:
        entry_id: UUID of the entry to delete.
        engine: SQLAlchemy engine.

    Returns:
        True if the entry was found and deleted, False otherwise.
    """
    with Session(engine) as session:
        entry = session.get(FuelEntry, entry_id)
        if entry is None:
            logger.warning(f"FuelEntry {entry_id} not found for deletion")
            return False
        entry.is_deleted = True
        session.commit()
    return True
