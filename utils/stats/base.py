from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    import altair as alt
    import pandas as pd
    from sqlalchemy.engine import Engine

    from utils.stats.filters import StatsFilter


@runtime_checkable
class Visual(Protocol):
    """Protocol that every Stats-page visual must satisfy.

    Implementors receive a :class:`StatsFilter` and a SQLAlchemy
    :class:`~sqlalchemy.engine.Engine` at construction time.  The
    three required methods map to a clear data-flow:

    1. :meth:`fetch` - pull raw data from the database and return a
       :class:`~pandas.DataFrame`.
    2. :meth:`plot` - accept that DataFrame and return an
       :class:`~altair.Chart` (or any Altair compound chart).
    3. :meth:`run` - orchestrate the full render: call ``fetch``, pass
       the result to ``plot``, then call ``st.altair_chart`` (and any
       other ``st.*`` helpers needed by this visual).
    """

    filter: StatsFilter
    engine: Engine

    def fetch(self) -> pd.DataFrame:
        """Query the database using ``self.filter`` and return a DataFrame."""
        ...

    def plot(self, df: pd.DataFrame) -> alt.Chart:
        """Build and return an Altair chart from *df*."""
        ...

    def run(self) -> None:
        """Fetch data, plot it, and render the visual via ``st.*`` calls."""
        ...
