"""Efficiency over time with Good/Bad outlier labelling.

Plots km/L efficiency as a scatter chart ordered by date.  Each point is
labelled *Good* or *Bad* based on whether it falls within +/-N standard
deviations of the per-vehicle mean.

When exactly one vehicle is in view a semi-transparent band and a dashed
mean rule are added for context.  For multiple vehicles only the
colour-coded points are rendered (overlapping bands would be misleading).

Pipeline
--------
fetch  -> raw FuelEntry + Car rows (inherited from BaseFuelChart)
clean  -> adds efficiency, per-vehicle stats, and Good/Bad labels
plot   -> scatter with optional band + mean overlay

Example
-------
::

    fig = EfficiencyOverTime(user_id, std_multiplier=2.0).fetch().clean().plot()
    st.altair_chart(fig, use_container_width=True)
"""

from __future__ import annotations

from typing import Self

import altair as alt

from utils.palette import SECONDARY_COLOR
from utils.stats.base import BaseFuelChart, apply_theme

STD_MULTIPLIER = 2.0

_GOOD = "Good"
_BAD = "Bad"

# Distinct green/red so Good and Bad are never confused
_LABEL_COLOR_SCALE = alt.Scale(
    domain=[_GOOD, _BAD],
    range=["#2ecc71", "#e74c3c"],
)


class EfficiencyOverTime(BaseFuelChart):
    """Efficiency (km/L) scatter chart with Good / Bad outlier labels.

    Points outside +/- :attr:`std_multiplier` standard deviations from
    the per-vehicle mean are coloured *Bad*; all others are *Good*.

    Parameters
    ----------
    std_multiplier:
        Number of standard deviations that define the outlier threshold.
        Defaults to ``2.0``.
    *args / **kwargs:
        Forwarded to :class:`~utils.stats.base.BaseFuelChart`.
    """

    def __init__(self, *args, std_multiplier: float = STD_MULTIPLIER, **kwargs) -> None:  # type: ignore[no-untyped-def]
        super().__init__(*args, **kwargs)
        self.std_multiplier = std_multiplier

    # ------------------------------------------------------------------
    # Step 2 - clean
    # ------------------------------------------------------------------

    def clean(self) -> Self:
        """Derive efficiency and outlier-label columns and cache on ``self._cleaned``.

        Derived columns
        ---------------
        ``efficiency``
            Trip distance divided by fuel filled (km/L).
        ``efficiency_mean``, ``efficiency_std``
            Per-vehicle mean and standard deviation.
            Standard deviation is set to ``0`` for single-entry vehicles.
        ``lower_bound``, ``upper_bound``
            +/-N*std thresholds per vehicle.
        ``label``
            ``"Good"`` for in-band entries, ``"Bad"`` for outliers.
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
        df["efficiency"] = df["trip"] / df["fuel_filled"]

        # Per-vehicle statistics for thresholds
        per_car = df.groupby("car_id")["efficiency"].agg(efficiency_mean="mean", efficiency_std="std").reset_index()
        # Single-entry vehicles have NaN std - treat as 0 (no outlier band)
        per_car["efficiency_std"] = per_car["efficiency_std"].fillna(0)

        df = df.merge(per_car, on="car_id")
        df["lower_bound"] = df["efficiency_mean"] - self.std_multiplier * df["efficiency_std"]
        df["upper_bound"] = df["efficiency_mean"] + self.std_multiplier * df["efficiency_std"]

        is_outlier = df["efficiency"] < df["lower_bound"]
        df["label"] = _GOOD
        df.loc[is_outlier, "label"] = _BAD

        # Floor used by the bad-zone area so the shared Y scale never reaches 0
        eff_min = df["efficiency"].min()
        eff_range = df["efficiency"].max() - eff_min
        df["y_floor"] = eff_min - max(eff_range * 0.1, 0.5)

        df["date"] = df["entry_datetime"].dt.date.astype(str)

        self._cleaned = df
        return self

    # ------------------------------------------------------------------
    # Step 3 - plot
    # ------------------------------------------------------------------

    def plot(self) -> alt.Chart | alt.LayerChart:
        """Build the efficiency-over-time scatter chart.

        Returns
        -------
        alt.Chart | alt.LayerChart
            Chart ready for ``st.altair_chart``.
        """
        if self._cleaned is None:
            self.clean()
        assert self._cleaned is not None
        df = self._cleaned

        title = f"Efficiency over Time (Bad = below -{self.std_multiplier} std from mean)"

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
                    alt.Tooltip(
                        "lower_bound:Q",
                        title=f"Threshold (-{self.std_multiplier} std)",
                        format=".2f",
                    ),
                    alt.Tooltip("label:N", title="Label"),
                ],
            )
        )

        if df["car_id"].nunique() == 1:
            # Shade the "bad" zone below the lower threshold
            bad_zone = (
                alt.Chart(df)
                .mark_area(opacity=0.10, color="#e74c3c")
                .encode(
                    alt.X("entry_datetime:T"),
                    alt.Y("lower_bound:Q"),
                    alt.Y2("y_floor:Q"),
                )
            )
            threshold_rule = (
                alt.Chart(df)
                .mark_rule(strokeDash=[4, 4], color="#e74c3c", opacity=0.5)
                .encode(alt.Y("mean(lower_bound):Q"))
            )
            mean_rule = (
                alt.Chart(df)
                .mark_rule(strokeDash=[4, 4], color=SECONDARY_COLOR, opacity=0.6)
                .encode(alt.Y("mean(efficiency):Q"))
            )
            chart: alt.Chart | alt.LayerChart = (bad_zone + threshold_rule + mean_rule + points).properties(title=title)
        else:
            chart = points.properties(title=title)

        return apply_theme(chart)
