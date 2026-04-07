from db.model import FuelEntry


def validate_fuel_consistency(
    session,
    user_id: str,
    vehicle: str,
    fuel_type: str,
    entry_id: str | None = None,
):
    query = session.query(FuelEntry).filter(FuelEntry.user_id == user_id, FuelEntry.vehicle == vehicle)

    if entry_id:  # Exclude current entry when updating
        query = query.filter(FuelEntry.id != entry_id)

    previous_entry = query.first()

    if previous_entry and previous_entry.fuel_type != fuel_type:
        raise ValueError(
            f"Fuel type inconsistency: {vehicle} previously used "
            f"{previous_entry.fuel_type}, cannot switch to {fuel_type}"
        )
