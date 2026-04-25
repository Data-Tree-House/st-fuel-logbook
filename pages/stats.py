"""Statistics page - three Altair-powered fuel analytics charts.

Filters (vehicle + date range) live at the top of the page and are passed
directly into each chart class.  Every chart follows the builder pipeline:

    chart.fetch().clean().plot()

``fetch()`` results are cached for 5 minutes via ``@st.cache_data`` so
repeated filter tweaks within a session are fast.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

import streamlit as st

from db import crud, get_engine
from utils import primary_text
from utils.stats import EfficiencyDistribution, EfficiencyOverTime, RollingCostPerKm

st.set_page_config(layout="wide")

st.markdown("## Statistics")

# ---------------------------------------------------------------------------
# Global filters
# ---------------------------------------------------------------------------

user_id = str(st.user.sub)
cars = crud.get_cars(user_id, get_engine()) or []

with st.expander("Filters", expanded=True):
    filter_col1, filter_col2, filter_col3 = st.columns([2, 1, 1])

    with filter_col1:
        car_options: dict[str, int] = {car.nickname: car.id for car in cars}
        selected_nicknames: list[str] = st.multiselect(
            "Vehicles",
            options=list(car_options.keys()),
            default=list(car_options.keys()),
            placeholder="All vehicles",
        )
        selected_car_ids: list[int] | None = (
            [car_options[n] for n in selected_nicknames] if selected_nicknames else None
        )

    today = datetime.now(tz=UTC).date()

    with filter_col2:
        _date_from_raw = st.date_input("From", value=today - timedelta(days=365))
        date_from = _date_from_raw if isinstance(_date_from_raw, date) else today - timedelta(days=365)

    with filter_col3:
        _date_to_raw = st.date_input("To", value=today)
        date_to = _date_to_raw if isinstance(_date_to_raw, date) else today

# ---------------------------------------------------------------------------
# Build all charts once (fetch results are cached, so cross-tab navigation
# does not re-query the database)
# ---------------------------------------------------------------------------

dist = EfficiencyDistribution(user_id, car_ids=selected_car_ids, date_from=date_from, date_to=date_to).fetch().clean()

overtime = EfficiencyOverTime(user_id, car_ids=selected_car_ids, date_from=date_from, date_to=date_to).fetch().clean()

rolling = RollingCostPerKm(user_id, car_ids=selected_car_ids, date_from=date_from, date_to=date_to).fetch().clean()

# ---------------------------------------------------------------------------
# Tabs
# ---------------------------------------------------------------------------

tab_eff, tab_cost = st.tabs(["Efficiency", "Cost"])

# ── Tab 1 : Efficiency ────────────────────────────────────────────────────

with tab_eff:
    if dist.is_empty:
        st.info("No data available for the selected filters.")
    else:
        df = dist.data

        # Row 1: distribution histogram (left) + summary stats (right)
        col_chart, col_stats = st.columns([3, 2], vertical_alignment="center")

        with col_chart:
            st.caption("Efficiency distribution (km/L)")
            st.altair_chart(dist.plot(), use_container_width=True)

        with col_stats:
            st.caption("Summary")
            m1, m2 = st.columns(2)
            m1.metric(primary_text("Mean (km/L)"), f"{df['efficiency'].mean():.1f}")
            m2.metric(primary_text("Std dev (km/L)"), f"{df['efficiency'].std():.1f}")
            m3, m4 = st.columns(2)
            m3.metric(primary_text("Best (km/L)"), f"{df['efficiency'].max():.1f}")
            m4.metric(primary_text("Worst (km/L)"), f"{df['efficiency'].min():.1f}")

            bad_count = int((df["label"] == "Bad").sum()) if "label" in df.columns else 0
            st.metric(primary_text("Bad entries"), str(bad_count))

        st.divider()

        # Row 2: efficiency over time (full width)
        st.caption("Entries below -2 std from the per-vehicle mean are labelled Bad.")
        st.altair_chart(overtime.plot(), use_container_width=True)

# ── Tab 2 : Cost ─────────────────────────────────────────────────────────

with tab_cost:
    if rolling.is_empty:
        st.info("No data available for the selected filters.")
    else:
        df_cost = rolling.data
        avg_cost = df_cost["cost_per_km"].mean()
        total_spend = df_cost["price"].sum()

        m1, m2 = st.columns(2)
        m1.metric(primary_text("Avg cost / km (R)"), f"{avg_cost:.2f}")
        m2.metric(primary_text("Total spend (R)"), f"{total_spend:,.0f}")

        st.caption(f"Rolling {rolling.rolling_window}-entry average cost per km (R/km) per vehicle.")
        st.altair_chart(rolling.plot(), use_container_width=True)
