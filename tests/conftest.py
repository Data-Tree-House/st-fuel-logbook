import tempfile
from collections.abc import Generator
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from testcontainers.postgres import PostgresContainer

from db import crud


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory that's cleaned up after the test."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture(scope="class")
def mock_engine() -> Generator[Engine, None, None]:
    """Create a fresh in-memory SQLite database for each test."""
    engine = create_engine("sqlite:///:memory:", echo=True)
    crud.create_all_tables(engine)

    yield engine

    # However, there are many cases where it is desirable that all connection resources referred to by the Engine be
    # completely closed out. It's generally not a good idea to rely on Python garbage collection for this to occur for
    # these cases; instead, the Engine can be explicitly disposed using the Engine.dispose() method.
    # ref: https://docs.sqlalchemy.org/en/21/core/connections.html
    engine.dispose()


@pytest.fixture(scope="module")
def pg_engine() -> Generator[Engine, None, None]:
    with PostgresContainer("postgres:18-alpine") as postgres:
        engine = create_engine(postgres.get_connection_url(), echo=True)
        crud.create_all_tables(engine)
        yield engine
        engine.dispose()
