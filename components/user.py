import streamlit as st

from constants import settings
from db import get_engine
from db.crud.read import get_user_fuel_stats
from utils import primary_text


def format_currency(value: float) -> str:
    abs_value = abs(value)
    sign = "-" if value < 0 else ""

    if abs_value >= 1_000_000_000:
        return f"{primary_text('R')} {sign}{abs_value / 1_000_000_000:.1f} B"
    if abs_value >= 1_000_000:
        return f"{primary_text('R')} {sign}{abs_value / 1_000_000:.1f} M"
    if abs_value >= 1_000:
        return f"{primary_text('R')} {sign}{abs_value / 1_000:.1f} K"
    return f"{primary_text('R')} {sign}{abs_value:,.2f}"


def metrics() -> None:
    """Render aggregate fuel-log metrics for the currently logged-in user."""
    stats = get_user_fuel_stats(str(st.user.sub), get_engine())

    with st.container(border=True):
        col1, col2 = st.columns(2)
        with col1:
            st.metric(
                f"{primary_text('Entries')}",
                value=f"{stats['entry_count']:.0f}",
            )
            st.metric(
                f"{primary_text('Total Trip')}",
                value=f"{stats['total_trip_km']:,.0f} {primary_text('km')}",
            )
        with col2:
            st.metric(
                f"{primary_text('Total Fuel Usage')}",
                value=f"{stats['total_fuel_litres']:,.0f} {primary_text('L')}",
            )
            st.metric(
                f"{primary_text('Total Expense')}",
                value=format_currency(stats["total_expense_zar"]),
            )


def profile():
    with st.sidebar:
        try:
            profile_picture = st.user.picture or settings.default_picture
        except Exception:
            profile_picture = settings.default_picture

        col1, col2 = st.columns([0.4, 0.6])
        with col1:
            st.image(
                f"{profile_picture}",
                width="content",
            )
        with col2:
            st.markdown(f"{st.user.name}")
            st.markdown(f"{st.user.email}")

        metrics()
