"""utils.stats - modular fuel statistics charts.

Each class follows a three-step pipeline::

    chart = SomeChart(user_id=..., engine=..., car_ids=..., date_from=..., date_to=...)
    df    = chart.fetch()   # Step 1 - raw DB rows
    df    = chart.clean()   # Step 2 - derived analytical columns
    fig   = chart.plot(df)  # Step 3 - Altair Chart object

All classes inherit from :class:`~utils.stats.base.BaseFuelChart` which
provides the shared ``fetch()`` implementation and enforces the interface.
"""

from utils.stats.base import BaseFuelChart  # noqa: F401
from utils.stats.efficiency_distribution import EfficiencyDistribution  # noqa: F401
from utils.stats.efficiency_over_time import EfficiencyOverTime  # noqa: F401
from utils.stats.rolling_cost_per_km import RollingCostPerKm  # noqa: F401
