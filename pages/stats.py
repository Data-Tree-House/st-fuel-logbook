from __future__ import annotations

import datetime
from typing import TYPE_CHECKING

import streamlit as st
from loguru import logger

from db import crud, get_engine
from utils.stats import CostPerKmOverTime, FuelEfficiencyHistogram, StatsFilter

if TYPE_CHECKING:
    import uuid

st.set_page_config(layout="wide")

st.markdown("## Statistics")

# =============== // LOAD USER // ===============

engine = get_engine()

try:
    user = crud.upsert_user(
        sub=str(st.user.sub),
        name=str(st.user.name),
        email=str(st.user.email),
        picture=str(st.user.picture),
        engine=engine,
    )
except Exception as e:
    logger.exception(f"An error occurred while loading the user: {e}")
    st.error("❌ An error occurred while loading your account")
    st.stop()

# =============== // LAYOUT // ===============

filter_col, chart_col = st.columns([1, 3])

# =============== // FILTERS // ===============

with filter_col:
    st.markdown("### Filters")

    # --- Vehicle multiselect ---
    car_options: dict[str, uuid.UUID] = {car.nickname: car.id for car in user.cars}
    selected_nicknames: list[str] = st.multiselect(
        label="Vehicle",
        options=list(car_options.keys()),
        default=[],
        placeholder="All vehicles",
    )
    selected_car_ids = [car_options[n] for n in selected_nicknames]

    # --- Date range ---
    filter_by_date = st.checkbox("Filter by date range", value=False)
    date_from: datetime.date | None = None
    date_to: datetime.date | None = None
    if filter_by_date:
        today = datetime.datetime.now(tz=datetime.UTC).date()
        date_range = st.date_input(
            label="Entry date range",
            value=(today, today),
            format="YYYY-MM-DD",
        )
        if isinstance(date_range, tuple) and len(date_range) == 2:
            from typing import cast

            dr = cast("tuple[datetime.date, datetime.date]", date_range)
            date_from = dr[0]
            date_to = dr[1]

    # --- Location multiselect ---
    # Derive available locations from all entries for this user
    all_entries = crud.get_all_fuel_entries(user_id=user.sub, engine=engine) or []
    location_options = sorted({e.location for e in all_entries if e.location})
    selected_locations: list[str] = st.multiselect(
        label="Location",
        options=location_options,
        default=[],
        placeholder="All locations",
    )

# Build the shared filter dataclass
active_filter = StatsFilter(
    user_id=user.sub,
    car_ids=list(selected_car_ids),
    date_from=date_from,
    date_to=date_to,
    locations=selected_locations,
)

# =============== // CHARTS // ===============

with chart_col:
    FuelEfficiencyHistogram(stats_filter=active_filter, engine=engine).run()
    st.divider()
    CostPerKmOverTime(stats_filter=active_filter, engine=engine).run()
