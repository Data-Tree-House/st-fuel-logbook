"""Tests for utils/stats visuals: fetch(), plot(), and _apply_filters().

The plots() can be tested because Altair charts are plain Python objects
whose encoding spec is inspectable without any browser or rendering engine.
"""

from __future__ import annotations

import datetime
import uuid
from typing import TYPE_CHECKING

import altair as alt
import pandas as pd
import pytest

from db import crud
from utils.stats.filters import StatsFilter
from utils.stats.visuals import (
    CostPerKmOverTime,
    FuelEfficiencyHistogram,
    _apply_filters,
)

if TYPE_CHECKING:
    from sqlalchemy.engine import Engine

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_DT = datetime.datetime
_counter: dict[str, int] = {}


def _unique(prefix: str) -> str:
    """Return a unique string each call with the given prefix."""
    _counter[prefix] = _counter.get(prefix, 0) + 1
    return f"{prefix}_{_counter[prefix]}"


def _make_filter(user_id: str, **kwargs) -> StatsFilter:
    return StatsFilter(user_id=user_id, **kwargs)


def _seed(engine: Engine, user_id: str, nickname: str) -> tuple[uuid.UUID, list]:
    """Create a user + car and return (car_id, [fuel_entry, ...])."""
    crud.upsert_user(
        sub=user_id,
        name="Test",
        email=f"{user_id}@datatreehouse.org",
        picture="https://example.com/p.jpg",
        engine=engine,
    )
    car_id = crud.new_car(
        user_id=user_id,
        nickname=nickname,
        fuel_type="Unleaded Petrol 95",
        engine=engine,
    )
    entries = []
    data = [
        (_DT(2026, 1, 10, 8, 0, tzinfo=datetime.UTC), 10000, 400, 40, 600, "Cape Town"),
        (_DT(2026, 2, 10, 8, 0, tzinfo=datetime.UTC), 10400, 300, 25, 450, "Joburg"),
        (_DT(2026, 3, 10, 8, 0, tzinfo=datetime.UTC), 10700, 500, 50, 800, "Durban"),
    ]
    for dt, odo, trip, fuel, price, loc in data:
        e = crud.new_fuel_entry(
            user_id,
            engine,
            car_id=car_id,
            entry_datetime=dt,
            odometer=float(odo),
            trip=float(trip),
            fuel_filled=float(fuel),
            price=float(price),
            currency="ZAR",
            location=loc,
        )
        entries.append(e)
    return car_id, entries


# ===========================================================================
# _apply_filters
# ===========================================================================


class TestApplyFilters:
    """Unit-tests for the module-level _apply_filters helper."""

    @pytest.fixture
    def base_df(self) -> pd.DataFrame:
        car_a = uuid.uuid4()
        car_b = uuid.uuid4()
        return pd.DataFrame(
            {
                "entry_date": pd.to_datetime(["2026-01-01", "2026-03-15", "2026-06-01"]),
                "car_id": [car_a, car_b, car_a],
                "location": ["Cape Town", "Joburg", "Durban"],
                "efficiency_km_l": [12.5, 14.0, 11.0],
                "_car_a": car_a,
                "_car_b": car_b,
            }
        )

    def test_no_filters_returns_all_rows(self, base_df: pd.DataFrame):
        f = _make_filter("u1")
        result = _apply_filters(base_df, f)
        assert len(result) == 3

    def test_car_id_filter(self, base_df: pd.DataFrame):
        car_a = base_df["_car_a"].iloc[0]
        f = _make_filter("u1", car_ids=[car_a])
        result = _apply_filters(base_df, f)
        assert len(result) == 2
        assert all(result["car_id"] == car_a)

    def test_date_from_filter(self, base_df: pd.DataFrame):
        f = _make_filter("u1", date_from=datetime.date(2026, 3, 1))
        result = _apply_filters(base_df, f)
        assert len(result) == 2

    def test_date_to_filter(self, base_df: pd.DataFrame):
        f = _make_filter("u1", date_to=datetime.date(2026, 1, 31))
        result = _apply_filters(base_df, f)
        assert len(result) == 1

    def test_date_range_filter(self, base_df: pd.DataFrame):
        f = _make_filter(
            "u1",
            date_from=datetime.date(2026, 2, 1),
            date_to=datetime.date(2026, 4, 1),
        )
        result = _apply_filters(base_df, f)
        assert len(result) == 1
        assert result["location"].iloc[0] == "Joburg"

    def test_location_filter(self, base_df: pd.DataFrame):
        f = _make_filter("u1", locations=["Cape Town", "Durban"])
        result = _apply_filters(base_df, f)
        assert len(result) == 2
        assert set(result["location"]) == {"Cape Town", "Durban"}

    def test_combined_filters(self, base_df: pd.DataFrame):
        car_a = base_df["_car_a"].iloc[0]
        f = _make_filter("u1", car_ids=[car_a], locations=["Cape Town"])
        result = _apply_filters(base_df, f)
        assert len(result) == 1
        assert result["location"].iloc[0] == "Cape Town"


# ===========================================================================
# FuelEfficiencyHistogram
# ===========================================================================


class TestFuelEfficiencyHistogramFetch:
    @pytest.fixture(autouse=True)
    def setup(self, mock_engine: Engine):
        self.user_id = _unique("hist_fetch_sub")
        self.car_id, self.entries = _seed(mock_engine, self.user_id, _unique("Hist Car"))

    def test_fetch_returns_expected_columns(self, mock_engine: Engine):
        f = _make_filter(self.user_id)
        df = FuelEfficiencyHistogram(stats_filter=f, engine=mock_engine).fetch()
        assert set(df.columns) == {"entry_date", "car_id", "location", "efficiency_km_l"}

    def test_fetch_computes_efficiency(self, mock_engine: Engine):
        f = _make_filter(self.user_id)
        df = FuelEfficiencyHistogram(stats_filter=f, engine=mock_engine).fetch()
        # trip / fuel_filled for each seeded row: 400/40=10, 300/25=12, 500/50=10
        assert len(df) == 3
        assert set(df["efficiency_km_l"].round(2)) == {10.0, 12.0}

    def test_fetch_empty_for_unknown_user(self, mock_engine: Engine):
        f = _make_filter("nobody")
        df = FuelEfficiencyHistogram(stats_filter=f, engine=mock_engine).fetch()
        assert df.empty

    def test_fetch_respects_car_filter(self, mock_engine: Engine):
        other_car_id = uuid.uuid4()
        f = _make_filter(self.user_id, car_ids=[other_car_id])
        df = FuelEfficiencyHistogram(stats_filter=f, engine=mock_engine).fetch()
        assert df.empty

    def test_fetch_respects_date_filter(self, mock_engine: Engine):
        f = _make_filter(
            self.user_id,
            date_from=datetime.date(2026, 2, 1),
            date_to=datetime.date(2026, 2, 28),
        )
        df = FuelEfficiencyHistogram(stats_filter=f, engine=mock_engine).fetch()
        assert len(df) == 1
        assert df["location"].iloc[0] == "Joburg"

    def test_fetch_respects_location_filter(self, mock_engine: Engine):
        f = _make_filter(self.user_id, locations=["Cape Town"])
        df = FuelEfficiencyHistogram(stats_filter=f, engine=mock_engine).fetch()
        assert len(df) == 1


class TestFuelEfficiencyHistogramPlot:
    def _sample_df(self) -> pd.DataFrame:
        return pd.DataFrame(
            {
                "entry_date": pd.to_datetime(["2026-01-01", "2026-02-01"]),
                "car_id": [uuid.uuid4(), uuid.uuid4()],
                "location": ["A", "B"],
                "efficiency_km_l": [10.0, 12.0],
            }
        )

    def test_plot_returns_altair_chart(self):
        f = _make_filter("u")
        visual = FuelEfficiencyHistogram.__new__(FuelEfficiencyHistogram)
        visual.filter = f
        chart = visual.plot(self._sample_df())
        assert isinstance(chart, alt.Chart)

    def test_plot_empty_df_returns_chart(self):
        f = _make_filter("u")
        visual = FuelEfficiencyHistogram.__new__(FuelEfficiencyHistogram)
        visual.filter = f
        chart = visual.plot(pd.DataFrame({"efficiency_km_l": []}))
        assert isinstance(chart, alt.Chart)

    def test_plot_mark_is_bar(self):
        f = _make_filter("u")
        visual = FuelEfficiencyHistogram.__new__(FuelEfficiencyHistogram)
        visual.filter = f
        chart = visual.plot(self._sample_df())
        spec = chart.to_dict()
        assert spec["mark"]["type"] == "bar"

    def test_plot_x_field_is_efficiency(self):
        f = _make_filter("u")
        visual = FuelEfficiencyHistogram.__new__(FuelEfficiencyHistogram)
        visual.filter = f
        chart = visual.plot(self._sample_df())
        spec = chart.to_dict()
        assert spec["encoding"]["x"]["field"] == "efficiency_km_l"

    def test_plot_x_bin_step_is_one(self):
        f = _make_filter("u")
        visual = FuelEfficiencyHistogram.__new__(FuelEfficiencyHistogram)
        visual.filter = f
        chart = visual.plot(self._sample_df())
        spec = chart.to_dict()
        assert spec["encoding"]["x"]["bin"]["step"] == 1

    def test_plot_title(self):
        f = _make_filter("u")
        visual = FuelEfficiencyHistogram.__new__(FuelEfficiencyHistogram)
        visual.filter = f
        chart = visual.plot(self._sample_df())
        spec = chart.to_dict()
        assert spec["title"] == "Fuel Efficiency Distribution"


# ===========================================================================
# CostPerKmOverTime
# ===========================================================================


class TestCostPerKmOverTimeFetch:
    @pytest.fixture(autouse=True)
    def setup(self, mock_engine: Engine):
        self.user_id = _unique("cost_fetch_sub")
        self.car_id, self.entries = _seed(mock_engine, self.user_id, _unique("Cost Car"))

    def test_fetch_returns_expected_columns(self, mock_engine: Engine):
        f = _make_filter(self.user_id)
        df = CostPerKmOverTime(stats_filter=f, engine=mock_engine).fetch()
        assert set(df.columns) == {"entry_date", "car_id", "car_nickname", "location", "cost_per_km"}

    def test_fetch_computes_cost_per_km(self, mock_engine: Engine):
        f = _make_filter(self.user_id)
        df = CostPerKmOverTime(stats_filter=f, engine=mock_engine).fetch()
        # price/trip: 600/400=1.5, 450/300=1.5, 800/500=1.6
        assert len(df) == 3
        assert all(df["cost_per_km"] > 0)

    def test_fetch_sorted_by_date(self, mock_engine: Engine):
        f = _make_filter(self.user_id)
        df = CostPerKmOverTime(stats_filter=f, engine=mock_engine).fetch()
        assert list(df["entry_date"]) == sorted(df["entry_date"])

    def test_fetch_empty_for_unknown_user(self, mock_engine: Engine):
        f = _make_filter("nobody_cost")
        df = CostPerKmOverTime(stats_filter=f, engine=mock_engine).fetch()
        assert df.empty

    def test_fetch_respects_date_filter(self, mock_engine: Engine):
        f = _make_filter(
            self.user_id,
            date_from=datetime.date(2026, 3, 1),
        )
        df = CostPerKmOverTime(stats_filter=f, engine=mock_engine).fetch()
        assert len(df) == 1
        assert df["location"].iloc[0] == "Durban"


class TestCostPerKmOverTimePlot:
    def _sample_df(self, n_cars: int = 1) -> pd.DataFrame:
        car_name = "Car A"
        rows = [
            {
                "entry_date": pd.Timestamp(f"2026-0{i + 1}-01"),
                "car_id": uuid.uuid4(),
                "car_nickname": car_name if n_cars == 1 else f"Car {chr(65 + i)}",
                "location": "Somewhere",
                "cost_per_km": 1.5 + i * 0.1,
            }
            for i in range(3)
        ]
        return pd.DataFrame(rows)

    def test_plot_returns_layer_chart_for_single_car(self):
        f = _make_filter("u")
        visual = CostPerKmOverTime.__new__(CostPerKmOverTime)
        visual.filter = f
        chart = visual.plot(self._sample_df(n_cars=1))
        assert isinstance(chart, alt.LayerChart)

    def test_plot_returns_layer_chart_for_multiple_cars(self):
        f = _make_filter("u")
        visual = CostPerKmOverTime.__new__(CostPerKmOverTime)
        visual.filter = f
        chart = visual.plot(self._sample_df(n_cars=3))
        assert isinstance(chart, alt.LayerChart)

    def test_plot_empty_df_returns_chart(self):
        f = _make_filter("u")
        visual = CostPerKmOverTime.__new__(CostPerKmOverTime)
        visual.filter = f
        chart = visual.plot(pd.DataFrame({"entry_date": [], "cost_per_km": []}))
        assert isinstance(chart, alt.Chart)

    def test_plot_title(self):
        f = _make_filter("u")
        visual = CostPerKmOverTime.__new__(CostPerKmOverTime)
        visual.filter = f
        chart = visual.plot(self._sample_df())
        spec = chart.to_dict()
        assert spec["title"] == "Cost per km over Time"

    def test_plot_layer_contains_line_and_point(self):
        f = _make_filter("u")
        visual = CostPerKmOverTime.__new__(CostPerKmOverTime)
        visual.filter = f
        chart = visual.plot(self._sample_df())
        spec = chart.to_dict()
        marks = {layer["mark"]["type"] for layer in spec["layer"]}
        assert "line" in marks
        assert "point" in marks

    def test_plot_x_field_is_entry_date(self):
        f = _make_filter("u")
        visual = CostPerKmOverTime.__new__(CostPerKmOverTime)
        visual.filter = f
        chart = visual.plot(self._sample_df())
        spec = chart.to_dict()
        # x encoding lives on each layer (no shared top-level encoding)
        assert spec["layer"][0]["encoding"]["x"]["field"] == "entry_date"

    def test_plot_multi_car_has_color_encoding(self):
        f = _make_filter("u")
        visual = CostPerKmOverTime.__new__(CostPerKmOverTime)
        visual.filter = f
        chart = visual.plot(self._sample_df(n_cars=3))
        spec = chart.to_dict()
        # Each layer should carry a color encoding when multiple cars
        layer_with_color = [layer for layer in spec["layer"] if "color" in layer.get("encoding", {})]
        assert len(layer_with_color) > 0
