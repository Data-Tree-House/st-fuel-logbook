"""Abstract base class and shared infrastructure for all fuel-stats chart classes.

Builder pipeline
----------------
Every concrete chart class supports a fluent three-step chain::

    fig = MyChart(user_id, car_ids=[1], date_from=start, date_to=end)
              .fetch()   # Step 1 - pull raw rows from the DB (cached)
              .clean()   # Step 2 - derive analytical columns
              .plot()    # Step 3 - return an Altair Chart

Each step stores its result on ``self`` so you can also drive the steps
individually (useful when you need to inspect the data before plotting)::

    chart = MyChart(user_id)
    chart.fetch()
    chart.clean()
    if not chart.is_empty:
        st.altair_chart(chart.plot(), use_container_width=True)

``clean()`` will auto-call ``fetch()`` if it has not been called yet, and
``plot()`` will auto-call ``clean()`` for the same reason.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date, datetime
from typing import TYPE_CHECKING, Self

import pandas as pd
import streamlit as st
from loguru import logger
from sqlalchemy import select
from sqlalchemy.orm import Session

from db.model import Car, FuelEntry
from utils.palette import PRIMARY_COLOR, SECONDARY_COLOR  # noqa: F401

if TYPE_CHECKING:
    import altair as alt

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CACHE_TTL_SECONDS: int = 300
"""How long (seconds) the raw-fetch result is cached per unique query."""

_RAW_COLUMNS = ["id", "entry_datetime", "trip", "fuel_filled", "price", "car_id", "nickname"]

# ---------------------------------------------------------------------------
# Shared Altair theme
# ---------------------------------------------------------------------------

_CHART_CONFIG: dict = {
    "background": "transparent",
    "view": {"stroke": "transparent"},
    "axis": {
        "labelColor": "#aaaaaa",
        "titleColor": "#aaaaaa",
        # Subtle grid lines tinted with the secondary (navy) palette colour
        "gridColor": "rgba(32, 59, 86, 0.5)",
        "domainColor": SECONDARY_COLOR,
        "tickColor": SECONDARY_COLOR,
    },
    "legend": {
        "labelColor": "#cccccc",
        "titleColor": "#cccccc",
        "symbolStrokeColor": SECONDARY_COLOR,
    },
    "title": {
        "color": "#eeeeee",
        "subtitleColor": "#aaaaaa",
        "anchor": "start",
    },
    "point": {
        "strokeWidth": 0,
    },
}


def apply_theme(chart: alt.Chart | alt.LayerChart) -> alt.Chart | alt.LayerChart:
    """Apply the shared dark-neutral Altair theme to any chart."""
    return chart.configure(**_CHART_CONFIG)


# ---------------------------------------------------------------------------
# Cached DB fetch (module-level so @st.cache_data can key on plain args)
# ---------------------------------------------------------------------------


@st.cache_data(ttl=CACHE_TTL_SECONDS, show_spinner=False)
def _fetch_raw(
    user_id: str,
    car_ids: tuple[int, ...] | None,
    date_from: date | datetime | None,
    date_to: date | datetime | None,
) -> pd.DataFrame:
    """Query FuelEntry rows for *user_id*, honouring optional filters.

    This is a module-level function (not a method) so that
    ``@st.cache_data`` can hash its arguments without needing to hash an
    ``Engine`` instance.  The engine is obtained via ``get_engine()`` which
    is itself a ``@st.cache_resource`` - it is created once and reused.

    Returns
    -------
    pd.DataFrame
        Columns: ``id``, ``entry_datetime``, ``trip``, ``fuel_filled``,
        ``price``, ``car_id``, ``nickname``.
        Empty DataFrame (with correct columns) when no rows match.
    """
    # Deferred import avoids a circular dependency at module load time.
    from db.client import get_engine

    stmt = (
        select(
            FuelEntry.id,
            FuelEntry.entry_datetime,
            FuelEntry.trip,
            FuelEntry.fuel_filled,
            FuelEntry.price,
            FuelEntry.car_id,
            Car.nickname,
        )
        .join(Car, FuelEntry.car_id == Car.id)
        .where(
            Car.user_id == user_id,
            Car.is_deleted == False,  # noqa: E712
        )
    )

    if car_ids:
        stmt = stmt.where(FuelEntry.car_id.in_(car_ids))

    if date_from is not None:
        stmt = stmt.where(FuelEntry.entry_datetime >= date_from)

    if date_to is not None:
        # Stretch to the very end of the requested day
        end: date | datetime = (
            datetime.combine(date_to, datetime.max.time())
            if isinstance(date_to, date) and not isinstance(date_to, datetime)
            else date_to
        )
        stmt = stmt.where(FuelEntry.entry_datetime <= end)

    stmt = stmt.order_by(Car.id, FuelEntry.entry_datetime)

    with Session(get_engine()) as session:
        rows = session.execute(stmt).mappings().all()

    if not rows:
        logger.info(f"_fetch_raw: no rows for user={user_id!r} car_ids={car_ids}")
        return pd.DataFrame(columns=pd.Index(_RAW_COLUMNS))

    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Abstract base class
# ---------------------------------------------------------------------------


class BaseFuelChart(ABC):
    """Abstract base for all fuel-stats chart classes.

    Parameters
    ----------
    user_id:
        The authenticated user's ``sub``.
    car_ids:
        Optional list of ``Car.id`` values to restrict results to.
        ``None`` (default) includes all non-deleted cars.
    date_from:
        Inclusive lower bound on ``FuelEntry.entry_datetime``.
    date_to:
        Inclusive upper bound on ``FuelEntry.entry_datetime``.
    """

    def __init__(
        self,
        user_id: str,
        *,
        car_ids: list[int] | None = None,
        date_from: date | datetime | None = None,
        date_to: date | datetime | None = None,
    ) -> None:
        self._user_id = user_id
        self._car_ids = car_ids
        self._date_from = date_from
        self._date_to = date_to

        self._raw: pd.DataFrame | None = None
        self._cleaned: pd.DataFrame | None = None

    # ------------------------------------------------------------------
    # Convenience properties
    # ------------------------------------------------------------------

    @property
    def is_empty(self) -> bool:
        """``True`` when the cleaned dataset is empty or not yet computed."""
        return self._cleaned is None or self._cleaned.empty

    @property
    def data(self) -> pd.DataFrame:
        """The cleaned DataFrame, or an empty one if ``clean()`` hasn't run yet."""
        return self._cleaned if self._cleaned is not None else pd.DataFrame(columns=pd.Index(_RAW_COLUMNS))

    # ------------------------------------------------------------------
    # Step 1 - fetch
    # ------------------------------------------------------------------

    def fetch(self) -> Self:
        """Pull raw rows from the database and cache them on ``self._raw``.

        Uses a module-level ``@st.cache_data`` function keyed on the
        constructor arguments so repeated calls within the same Streamlit
        session reuse the cached result.

        Returns
        -------
        Self
            The same instance - enables builder chaining.
        """
        car_ids_key = tuple(self._car_ids) if self._car_ids else None
        self._raw = _fetch_raw(self._user_id, car_ids_key, self._date_from, self._date_to)
        return self

    # ------------------------------------------------------------------
    # Step 2 - clean (sub-class responsibility)
    # ------------------------------------------------------------------

    @abstractmethod
    def clean(self) -> Self:
        """Derive analytical columns from ``self._raw``.

        Implementations must:

        1. Call ``self.fetch()`` if ``self._raw`` is ``None``.
        2. Populate ``self._cleaned`` with the enriched DataFrame.
        3. Return ``self`` for chaining.
        """

    # ------------------------------------------------------------------
    # Step 3 - plot (sub-class responsibility)
    # ------------------------------------------------------------------

    @abstractmethod
    def plot(self) -> alt.Chart | alt.LayerChart:
        """Build and return an Altair chart from ``self._cleaned``.

        Implementations must call ``self.clean()`` automatically if
        ``self._cleaned`` is ``None``.
        """
