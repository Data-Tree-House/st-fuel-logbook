"""Fuel statistics data pipeline and Altair chart builders.

Pipeline
--------
1. ``FuelStats.__init__``  - declare filters (user, cars, date range)
2. ``FuelStats.fetch()``   - query the database -> raw :class:`pandas.DataFrame`
3. ``FuelStats.clean()``   - derive metrics (efficiency, rolling cost, labels)
4. ``FuelStats.chart_*``   - build Altair ``Chart`` objects ready for ``st.altair_chart``

Usage example::

    fs = FuelStats(user_id=sub, engine=engine, car_ids=[1, 2], date_from=start)
    df = fs.clean()           # fetches + cleans in one call
    st.altair_chart(fs.chart_efficiency_distribution(df), use_container_width=True)
"""

from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING

import altair as alt
import pandas as pd
from loguru import logger
from sqlalchemy import select
from sqlalchemy.orm import Session

if TYPE_CHECKING:
    from sqlalchemy.engine import Engine

from db.model import Car, FuelEntry
from utils.palette import PRIMARY_COLOR, SECONDARY_COLOR

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ROLLING_WINDOW: int = 10
STD_MULTIPLIER: float = 2.0

_GOOD_LABEL = "Good"
_BAD_LABEL = "Bad"

_LABEL_COLOR_SCALE = alt.Scale(
    domain=[_GOOD_LABEL, _BAD_LABEL],
    range=[PRIMARY_COLOR, "#e74c3c"],
)

_CHART_CONFIG = {
    "background": "transparent",
    "view": {"stroke": "transparent"},
    "axis": {
        "labelColor": "#aaaaaa",
        "titleColor": "#aaaaaa",
        "gridColor": "#333333",
        "domainColor": "#555555",
        "tickColor": "#555555",
    },
    "legend": {
        "labelColor": "#aaaaaa",
        "titleColor": "#aaaaaa",
    },
    "title": {
        "color": "#eeeeee",
        "subtitleColor": "#aaaaaa",
    },
}


def _apply_theme(chart: alt.Chart | alt.LayerChart) -> alt.Chart | alt.LayerChart:
    """Apply a consistent dark-neutral theme to any Altair chart."""
    return chart.configure(**_CHART_CONFIG)


# ---------------------------------------------------------------------------
# Data pipeline
# ---------------------------------------------------------------------------


class FuelStats:
    """Fetch, clean, and visualise fuel-log data for a single user.

    Parameters
    ----------
    user_id:
        The authenticated user's ``sub``.
    engine:
        A live SQLAlchemy engine (see ``db.get_engine``).
    car_ids:
        Optional list of ``Car.id`` values to restrict results to.
        ``None`` (default) includes all non-deleted cars.
    date_from:
        Inclusive lower bound on ``FuelEntry.entry_datetime``.
    date_to:
        Inclusive upper bound on ``FuelEntry.entry_datetime``.
    rolling_window:
        Number of preceding entries (per vehicle) used for the rolling
        cost-per-km average.  Defaults to :data:`ROLLING_WINDOW` (10).
    std_multiplier:
        Number of standard deviations that define the *bad* efficiency
        band on the time-series chart.  Defaults to :data:`STD_MULTIPLIER` (2).
    """

    def __init__(
        self,
        user_id: str,
        engine: Engine,
        *,
        car_ids: list[int] | None = None,
        date_from: date | datetime | None = None,
        date_to: date | datetime | None = None,
        rolling_window: int = ROLLING_WINDOW,
        std_multiplier: float = STD_MULTIPLIER,
    ) -> None:
        self._user_id = user_id
        self._engine = engine
        self._car_ids = car_ids
        self._date_from = date_from
        self._date_to = date_to
        self.rolling_window = rolling_window
        self.std_multiplier = std_multiplier

        self._raw: pd.DataFrame | None = None
        self._cleaned: pd.DataFrame | None = None

    # ------------------------------------------------------------------
    # Step 1 - Fetch
    # ------------------------------------------------------------------

    def fetch(self) -> pd.DataFrame:
        """Query the database and return a raw :class:`~pandas.DataFrame`.

        Columns
        -------
        ``id``, ``entry_datetime``, ``trip``, ``fuel_filled``, ``price``,
        ``car_id``, ``nickname``

        Soft-deleted cars are automatically excluded.  The result is cached;
        calling ``fetch()`` again reuses the cached data unless you create a
        new :class:`FuelStats` instance.

        Returns
        -------
        pd.DataFrame
            Empty DataFrame (with correct columns) if no data is found.
        """
        if self._raw is not None:
            return self._raw

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
                Car.user_id == self._user_id,
                Car.is_deleted == False,  # noqa: E712
            )
        )

        if self._car_ids:
            stmt = stmt.where(FuelEntry.car_id.in_(self._car_ids))

        if self._date_from is not None:
            stmt = stmt.where(FuelEntry.entry_datetime >= self._date_from)

        if self._date_to is not None:
            # include the full final day
            end = (
                datetime.combine(self._date_to, datetime.max.time())
                if isinstance(self._date_to, date) and not isinstance(self._date_to, datetime)
                else self._date_to
            )
            stmt = stmt.where(FuelEntry.entry_datetime <= end)

        stmt = stmt.order_by(Car.id, FuelEntry.entry_datetime)

        with Session(self._engine) as session:
            rows = session.execute(stmt).mappings().all()

        if not rows:
            logger.info(f"FuelStats: no entries found for user {self._user_id}")
            self._raw = pd.DataFrame(
                columns=pd.Index(["id", "entry_datetime", "trip", "fuel_filled", "price", "car_id", "nickname"])
            )
        else:
            self._raw = pd.DataFrame(rows)

        return self._raw

    # ------------------------------------------------------------------
    # Step 2 - Clean
    # ------------------------------------------------------------------

    def clean(self) -> pd.DataFrame:
        """Derive all analytical columns and return an enriched DataFrame.

        Derived columns
        ---------------
        ``efficiency``
            Trip distance divided by fuel filled (km/L).
        ``cost_per_km``
            Total price divided by trip distance (R/km).
        ``rolling_cost_per_km``
            Per-vehicle rolling mean of ``cost_per_km`` over the last
            :attr:`rolling_window` entries.
        ``efficiency_mean``, ``efficiency_std``
            Per-vehicle mean and standard deviation of ``efficiency``.
        ``lower_bound``, ``upper_bound``
            +/-N*sigma thresholds used for labelling.
        ``label``
            ``"Good"`` for entries within the band, ``"Bad"`` outside.

        Returns
        -------
        pd.DataFrame
            Empty DataFrame (with correct columns) when there is no raw data.
        """
        if self._cleaned is not None:
            return self._cleaned

        raw = self.fetch()

        if raw.empty:
            self._cleaned = raw.copy()
            return self._cleaned

        df = raw.copy()

        # --- core metrics ------------------------------------------------
        df["efficiency"] = df["trip"] / df["fuel_filled"]
        df["cost_per_km"] = df["price"] / df["trip"]

        # --- rolling cost per km (per vehicle, sorted by date) -----------
        df = df.sort_values(["car_id", "entry_datetime"]).reset_index(drop=True)
        df["rolling_cost_per_km"] = df.groupby("car_id")["cost_per_km"].transform(
            lambda s: s.rolling(window=self.rolling_window, min_periods=1).mean()
        )

        # --- per-vehicle efficiency statistics for labelling -------------
        per_car = df.groupby("car_id")["efficiency"].agg(efficiency_mean="mean", efficiency_std="std").reset_index()
        # std is NaN for single-entry cars - default to 0
        per_car["efficiency_std"] = per_car["efficiency_std"].fillna(0)

        df = df.merge(per_car, on="car_id")
        df["lower_bound"] = df["efficiency_mean"] - self.std_multiplier * df["efficiency_std"]
        df["upper_bound"] = df["efficiency_mean"] + self.std_multiplier * df["efficiency_std"]

        is_bad = (df["efficiency"] < df["lower_bound"]) | (df["efficiency"] > df["upper_bound"])
        df["label"] = _GOOD_LABEL
        df.loc[is_bad, "label"] = _BAD_LABEL

        # friendly date column for Altair tooltips
        df["date"] = pd.to_datetime(df["entry_datetime"]).dt.date.astype(str)

        self._cleaned = df
        return self._cleaned

    # ------------------------------------------------------------------
    # Step 3 - Charts
    # ------------------------------------------------------------------

    def chart_efficiency_distribution(self, df: pd.DataFrame) -> alt.Chart | alt.LayerChart:
        """Histogram of efficiency (km/L), colour-coded by vehicle.

        Parameters
        ----------
        df:
            Output of :meth:`clean`.

        Returns
        -------
        alt.Chart
        """
        base = (
            alt.Chart(df)
            .mark_bar(opacity=0.75, binSpacing=1)
            .encode(
                alt.X(
                    "efficiency:Q",
                    bin=alt.Bin(maxbins=30),
                    title="Efficiency (km/L)",
                ),
                alt.Y("count():Q", title="Entries"),
                alt.Color(
                    "nickname:N",
                    title="Vehicle",
                    scale=alt.Scale(scheme="tableau10"),
                ),
                tooltip=[
                    alt.Tooltip("nickname:N", title="Vehicle"),
                    alt.Tooltip("efficiency:Q", title="Efficiency (km/L)", format=".2f"),
                    alt.Tooltip("count():Q", title="Count"),
                ],
            )
            .properties(title="Efficiency Distribution (km/L)")
        )
        return _apply_theme(base)

    def chart_rolling_cost_per_km(self, df: pd.DataFrame) -> alt.Chart | alt.LayerChart:
        """Rolling cost-per-km line chart, one line per vehicle.

        The rolling window is :attr:`rolling_window` entries.

        Parameters
        ----------
        df:
            Output of :meth:`clean`.

        Returns
        -------
        alt.Chart
        """
        base = (
            alt.Chart(df)
            .mark_line(point=alt.OverlayMarkDef(filled=True, size=40))
            .encode(
                alt.X("entry_datetime:T", title="Date"),
                alt.Y(
                    "rolling_cost_per_km:Q",
                    title="Cost per km (R/km)",
                    scale=alt.Scale(zero=False),
                ),
                alt.Color(
                    "nickname:N",
                    title="Vehicle",
                    scale=alt.Scale(scheme="tableau10"),
                ),
                tooltip=[
                    alt.Tooltip("nickname:N", title="Vehicle"),
                    alt.Tooltip("date:N", title="Date"),
                    alt.Tooltip("rolling_cost_per_km:Q", title="Rolling Cost/km (R)", format=".2f"),
                    alt.Tooltip("cost_per_km:Q", title="Actual Cost/km (R)", format=".2f"),
                ],
            )
            .properties(title=f"Rolling Cost per km - {self.rolling_window}-entry window (R/km)")
        )
        return _apply_theme(base)

    def chart_efficiency_over_time(self, df: pd.DataFrame) -> alt.Chart | alt.LayerChart:
        """Efficiency (km/L) scatter plot with Good/Bad labels.

        Points outside ±:attr:`std_multiplier` standard deviations from the
        per-vehicle mean are coloured as *Bad*; the rest as *Good*.

        A semi-transparent band showing the +/-N*sigma range is drawn per vehicle
        when only one vehicle is selected (multi-vehicle bands would overlap
        and become confusing).

        Parameters
        ----------
        df:
            Output of :meth:`clean`.

        Returns
        -------
        alt.Chart
        """
        points = (
            alt.Chart(df)
            .mark_circle(size=70, opacity=0.85)
            .encode(
                alt.X("entry_datetime:T", title="Date"),
                alt.Y(
                    "efficiency:Q",
                    title="Efficiency (km/L)",
                    scale=alt.Scale(zero=False),
                ),
                alt.Color("label:N", scale=_LABEL_COLOR_SCALE, title="Label"),
                alt.Shape("nickname:N", title="Vehicle"),
                tooltip=[
                    alt.Tooltip("nickname:N", title="Vehicle"),
                    alt.Tooltip("date:N", title="Date"),
                    alt.Tooltip("efficiency:Q", title="Efficiency (km/L)", format=".2f"),
                    alt.Tooltip("lower_bound:Q", title=f"Lower bound (-{self.std_multiplier}sigma)", format=".2f"),
                    alt.Tooltip("upper_bound:Q", title=f"Upper bound (+{self.std_multiplier}sigma)", format=".2f"),
                    alt.Tooltip("label:N", title="Label"),
                ],
            )
        )

        # --- +/-N*sigma band (only rendered when a single vehicle is shown) ----
        unique_cars = df["car_id"].nunique()
        if unique_cars == 1:
            band = (
                alt.Chart(df)
                .mark_area(opacity=0.12, color=SECONDARY_COLOR)
                .encode(
                    alt.X("entry_datetime:T"),
                    alt.Y("lower_bound:Q"),
                    alt.Y2("upper_bound:Q"),
                )
            )
            mean_line = (
                alt.Chart(df)
                .mark_rule(strokeDash=[4, 4], color=SECONDARY_COLOR, opacity=0.6)
                .encode(
                    alt.Y("mean(efficiency):Q"),
                )
            )
            chart = band + mean_line + points
        else:
            chart = points

        return _apply_theme(chart.properties(title=f"Efficiency over Time (+/-{self.std_multiplier}sigma bands)"))
