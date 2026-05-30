from __future__ import annotations

from typing import TYPE_CHECKING

import altair as alt
import pandas as pd
import streamlit as st

from db import crud
from utils.palette import PRIMARY_COLOR, SECONDARY_COLOR
from utils.stats.base import Visual  # noqa: F401 - re-export for isinstance checks

if TYPE_CHECKING:
    from sqlalchemy.engine import Engine

    from utils.stats.filters import StatsFilter


def _apply_filters(df: pd.DataFrame, f: StatsFilter) -> pd.DataFrame:
    """Apply car, date, and location filters to a raw entries DataFrame."""
    if f.car_ids:
        df = df[df["car_id"].isin(f.car_ids)]
    if f.date_from is not None:
        df = df[df["entry_date"] >= pd.Timestamp(f.date_from)]
    if f.date_to is not None:
        df = df[df["entry_date"] <= pd.Timestamp(f.date_to)]
    if f.locations:
        df = df[df["location"].isin(f.locations)]
    return df


class FuelEfficiencyHistogram:
    """Histogram of fuel-efficiency (km/L) distribution.

    Each bin is exactly 1 km/L wide (e.g. 12-13, 13-14).
    Efficiency is computed as ``trip / fuel_filled``.
    """

    def __init__(self, stats_filter: StatsFilter, engine: Engine) -> None:
        self.filter = stats_filter
        self.engine = engine

    # ------------------------------------------------------------------
    # Visual protocol
    # ------------------------------------------------------------------

    def fetch(self) -> pd.DataFrame:
        entries = crud.get_all_fuel_entries(
            user_id=self.filter.user_id,
            engine=self.engine,
            load_car=False,
        )
        if not entries:
            return pd.DataFrame({"entry_date": [], "car_id": [], "location": [], "efficiency_km_l": []})

        rows = [
            {
                "entry_date": pd.Timestamp(e.entry_datetime),
                "car_id": e.car_id,
                "location": e.location or "",
                "trip": e.trip,
                "fuel_filled": e.fuel_filled,
            }
            for e in entries
            if e.fuel_filled > 0
        ]
        df = pd.DataFrame(rows)
        df = _apply_filters(df, self.filter)
        df["efficiency_km_l"] = df["trip"] / df["fuel_filled"]
        return df[["entry_date", "car_id", "location", "efficiency_km_l"]]

    def plot(self, df: pd.DataFrame) -> alt.Chart:
        if df.empty:
            return alt.Chart(pd.DataFrame({"efficiency_km_l": []}))

        return (
            alt.Chart(df)
            .mark_bar(color=PRIMARY_COLOR, stroke=SECONDARY_COLOR, strokeWidth=0.5)
            .encode(
                alt.X(
                    "efficiency_km_l:Q",
                    bin=alt.Bin(step=1),
                    title="Fuel Efficiency (km/L)",
                ),
                alt.Y(
                    "count():Q",
                    title="Number of Fill-ups",
                ),
                tooltip=[
                    alt.Tooltip("efficiency_km_l:Q", bin=alt.Bin(step=1), title="Efficiency range (km/L)"),
                    alt.Tooltip("count():Q", title="Count"),
                ],
            )
            .properties(title="Fuel Efficiency Distribution")
        )

    def run(self) -> None:
        df = self.fetch()
        if df.empty:
            st.info("No fuel entries match the selected filters.")
            return
        chart = self.plot(df)
        st.altair_chart(chart, use_container_width=True)


class CostPerKmOverTime:
    """Line chart of cost-per-km (ZAR/km) over time.

    Each point represents a single fill-up.  Cost per km is
    computed as ``price / trip``.
    """

    def __init__(self, stats_filter: StatsFilter, engine: Engine) -> None:
        self.filter = stats_filter
        self.engine = engine

    # ------------------------------------------------------------------
    # Visual protocol
    # ------------------------------------------------------------------

    def fetch(self) -> pd.DataFrame:
        entries = crud.get_all_fuel_entries(
            user_id=self.filter.user_id,
            engine=self.engine,
            load_car=True,
        )
        if not entries:
            return pd.DataFrame({"entry_date": [], "car_id": [], "car_nickname": [], "location": [], "cost_per_km": []})

        rows = [
            {
                "entry_date": pd.Timestamp(e.entry_datetime),
                "car_id": e.car_id,
                "car_nickname": e.car.nickname if e.car else str(e.car_id),
                "location": e.location or "",
                "trip": e.trip,
                "price": e.price,
            }
            for e in entries
            if e.trip > 0
        ]
        df = pd.DataFrame(rows)
        df = _apply_filters(df, self.filter)
        df["cost_per_km"] = df["price"] / df["trip"]
        df.sort_values("entry_date", inplace=True)
        return df[["entry_date", "car_id", "car_nickname", "location", "cost_per_km"]]

    def plot(self, df: pd.DataFrame) -> alt.Chart | alt.LayerChart:
        if df.empty:
            return alt.Chart(pd.DataFrame({"entry_date": [], "cost_per_km": []}))

        has_multiple_cars = df["car_nickname"].nunique() > 1

        base = alt.Chart(df).encode(
            alt.X("entry_date:T", title="Date"),
            alt.Y("cost_per_km:Q", title="Cost per km (ZAR/km)"),
            tooltip=[
                alt.Tooltip("entry_date:T", title="Date", format="%d %b %Y"),
                alt.Tooltip("car_nickname:N", title="Car"),
                alt.Tooltip("cost_per_km:Q", title="ZAR/km", format=".2f"),
                alt.Tooltip("location:N", title="Location"),
            ],
        )

        if has_multiple_cars:
            color_enc = alt.Color("car_nickname:N", title="Car")
            line = base.mark_line().encode(color=color_enc)
            points = base.mark_point(filled=True, size=60).encode(color=color_enc)
        else:
            line = base.mark_line(color=PRIMARY_COLOR)
            points = base.mark_point(filled=True, size=60, color=PRIMARY_COLOR)

        return (line + points).properties(title="Cost per km over Time")

    def run(self) -> None:
        df = self.fetch()
        if df.empty:
            st.info("No fuel entries match the selected filters.")
            return
        chart = self.plot(df)
        st.altair_chart(chart, use_container_width=True)
