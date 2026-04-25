"""Efficiency distribution histogram.

Shows how km/L efficiency values are spread across bins, colour-coded by
vehicle nickname so multi-car comparisons are easy at a glance.

Pipeline
--------
fetch  -> raw FuelEntry + Car rows (inherited from BaseFuelChart)
clean  -> adds ``efficiency`` (km/L) column
plot   -> binned bar chart, one colour per vehicle

Example
-------
::

    fig = EfficiencyDistribution(user_id, car_ids=[1, 2]).fetch().clean().plot()
    st.altair_chart(fig, use_container_width=True)
"""

from __future__ import annotations

from typing import Self

import altair as alt

from utils.stats.base import BaseFuelChart, apply_theme


class EfficiencyDistribution(BaseFuelChart):
    """Histogram of fuel efficiency (km/L), colour-coded by vehicle."""

    # ------------------------------------------------------------------
    # Step 2 - clean
    # ------------------------------------------------------------------

    def clean(self) -> Self:
        """Add ``efficiency`` (km/L) column and cache on ``self._cleaned``.

        Derived columns
        ---------------
        ``efficiency``
            Trip distance divided by fuel filled (km/L).

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
        df["efficiency"] = df["trip"] / df["fuel_filled"]
        self._cleaned = df
        return self

    # ------------------------------------------------------------------
    # Step 3 - plot
    # ------------------------------------------------------------------

    def plot(self) -> alt.Chart | alt.LayerChart:
        """Build the efficiency distribution histogram.

        Returns
        -------
        alt.Chart | alt.LayerChart
            Binned bar chart ready for ``st.altair_chart``.
        """
        if self._cleaned is None:
            self.clean()
        assert self._cleaned is not None
        df = self._cleaned

        chart = (
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
        return apply_theme(chart)
