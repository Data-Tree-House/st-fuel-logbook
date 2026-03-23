import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from utils import PRIMARY_COLOR


def generate_fuel_data(start_year: int = 2016, end_year: int = 2026) -> pd.DataFrame:
    """Generate fake fuel efficiency data over years."""
    years = list(range(start_year, end_year + 1))

    # Generate realistic fuel efficiency data (km per liter)
    # Starting around 12 km/L and gradually improving to ~15 km/L
    np.random.seed(42)  # For reproducibility

    base_efficiency = 12.0
    improvement_rate = 0.25  # km/L improvement per year

    fuel_efficiency = []
    for i, year in enumerate(years):
        # Add trend improvement + some random variation
        efficiency = base_efficiency + (i * improvement_rate) + np.random.uniform(-0.5, 0.5)
        fuel_efficiency.append(round(efficiency, 2))

    return pd.DataFrame({"Year": years, "Fuel Efficiency (km/L)": fuel_efficiency})


def plot_fuel_efficiency():
    df = generate_fuel_data()

    fig = go.Figure()

    line_style = {"color": f"#{PRIMARY_COLOR}", "width": 3}

    marker_style = {"size": 8, "color": f"#{PRIMARY_COLOR}"}

    # Add line trace
    fig.add_trace(
        go.Scatter(
            x=df["Year"],
            y=df["Fuel Efficiency (km/L)"],
            mode="lines+markers",
            name="Fuel Efficiency",
            line=line_style,
            marker=marker_style,
        )
    )

    # Update layout
    fig.update_layout(
        title="",
        xaxis_title="Year",
        yaxis_title="Fuel Efficiency (km/L)",
        hovermode="x unified",
        template="plotly_white",
        height=500,
    )

    return fig


def st_plot_fuel_efficiency():
    st.plotly_chart(plot_fuel_efficiency(), use_container_width=True)
