"""Rolling cost-per-km line chart.

Smooths out price volatility by averaging cost/km over the last N entries
(per vehicle), making long-term trends easy to spot.

Pipeline
--------
fetch  -> raw FuelEntry + Car rows (inherited from BaseFuelChart)
clean  -> adds ``cost_per_km``, ``rolling_cost_per_km``, and ``date`` columns
plot   -> multi-vehicle line chart with point overlay

Example
-------
::

    fig = RollingCostPerKm(user_id, rolling_window=10).fetch().clean().plot()
    st.altair_chart(fig, use_container_width=True)
"""

from __future__ import annotations

from typing import Self

import altair as alt

from utils.stats.base import BaseFuelChart, apply_theme

ROLLING_WINDOW = 10


class RollingCostPerKm(BaseFuelChart):
    """Rolling average cost-per-km (R/km) over time, per vehicle.

    Parameters
    ----------
    rolling_window:
        Number of preceding entries (per vehicle) to include in the rolling
        mean.  Defaults to ``10``.  ``min_periods=1`` ensures the first
        entries are never dropped.
    *args / **kwargs:
        Forwarded to :class:`~utils.stats.base.BaseFuelChart`.
    """

    def __init__(self, *args, rolling_window: int = ROLLING_WINDOW, **kwargs) -> None:  # type: ignore[no-untyped-def]
        super().__init__(*args, **kwargs)
        self.rolling_window = rolling_window

    # ------------------------------------------------------------------
    # Step 2 - clean
    # ------------------------------------------------------------------

    def clean(self) -> Self:
        """Add cost and rolling-cost columns and cache on ``self._cleaned``.

        Derived columns
        ---------------
        ``cost_per_km``
            Price divided by trip distance (R/km) for each individual entry.
        ``rolling_cost_per_km``
            Per-vehicle rolling mean of ``cost_per_km`` over the last
            :attr:`rolling_window` entries.
        ``date``
            ISO-format date string used by Altair tooltips.

        Returns
        -------
        Self
            The same instance - enables builder chaining.
        """
        if self._raw is None:
            self.fetch()
        assert self._raw is not None
        raw = self._raw

        if raw.empty:
            self._cleaned = raw.copy()
            return self

        df = raw.copy()
        df = df.sort_values(["car_id", "entry_datetime"]).reset_index(drop=True)

        df["cost_per_km"] = df["price"] / df["trip"]
        df["rolling_cost_per_km"] = df.groupby("car_id")["cost_per_km"].transform(
            lambda s: s.rolling(window=self.rolling_window, min_periods=1).mean()
        )
        df["date"] = df["entry_datetime"].dt.date.astype(str)

        self._cleaned = df
        return self

    # ------------------------------------------------------------------
    # Step 3 - plot
    # ------------------------------------------------------------------

    def plot(self) -> alt.Chart | alt.LayerChart:
        """Build the rolling cost-per-km line chart.

        Returns
        -------
        alt.Chart | alt.LayerChart
            Line chart with point overlay ready for ``st.altair_chart``.
        """
        if self._cleaned is None:
            self.clean()
        assert self._cleaned is not None
        df = self._cleaned

        chart = (
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
                    alt.Tooltip(
                        "rolling_cost_per_km:Q",
                        title=f"Rolling Cost/km ({self.rolling_window} entries) (R)",
                        format=".2f",
                    ),
                    alt.Tooltip("cost_per_km:Q", title="Actual Cost/km (R)", format=".2f"),
                ],
            )
            .properties(title=f"Rolling Cost per km - {self.rolling_window}-entry window (R/km)")
        )
        return apply_theme(chart)
