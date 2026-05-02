from db.model import Car, FuelEntry

from collections.abc import Sequence


def generate_bulk_template(
    fuel_entries: Sequence[FuelEntry],
    cars: Sequence[Car],
) -> bytes:
    return b""
