from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date


@dataclass
class StatsFilter:
    """Holds the user-selected filter state for the Stats page.

    Attributes:
        user_id: The authenticated user's ``sub``.
        car_ids: UUIDs of selected cars. Empty list means *all cars*.
        date_from: Inclusive lower bound on ``entry_datetime``. ``None`` means no lower bound.
        date_to: Inclusive upper bound on ``entry_datetime``. ``None`` means no upper bound.
        locations: Selected location strings. Empty list means *all locations*.
    """

    user_id: str
    car_ids: list[uuid.UUID] = field(default_factory=list)
    date_from: date | None = None
    date_to: date | None = None
    locations: list[str] = field(default_factory=list)
