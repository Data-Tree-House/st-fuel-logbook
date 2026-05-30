import datetime
from typing import TYPE_CHECKING

import pytest
from sqlalchemy.engine import Engine

from db import crud

if TYPE_CHECKING:
    from collections.abc import Sequence

    from db.model import FuelEntry


class TestNewFuelEntry:
    @pytest.fixture(autouse=True)
    def setup(self, mock_engine: Engine):
        self.user_id = "test_sub"
        crud.upsert_user(
            sub=self.user_id,
            name="Test User",
            email="johan@datatreehouse.org",
            picture="https://example.com/profile.jpg",
            engine=mock_engine,
        )
        self.car_id = crud.new_car(
            user_id=self.user_id,
            nickname="Ford Focus",
            fuel_type="Unleaded Petrol 95",
            engine=mock_engine,
        )

    def test_new_fuel_entry(
        self,
        mock_engine: Engine,
    ):
        fuel_entry = crud.new_fuel_entry(
            self.user_id,
            mock_engine,
            car_id=self.car_id,
            entry_datetime=datetime.datetime(2026, 6, 1, 12, 0, tzinfo=datetime.UTC),
            odometer=10000.0,
            trip=500.0,
            fuel_filled=50.0,
            price=750.0,
            currency="ZAR",
            location="Cape Town",
        )

        assert fuel_entry.odometer == 10000.0


class TestReadFuelEntries:
    @pytest.fixture(autouse=True)
    def setup(self, mock_engine: Engine):
        self.user_id = "test_sub"
        self.user_id_2 = "test_sub_2"
        crud.upsert_user(
            sub=self.user_id,
            name="Test User",
            email="johan@datatreehouse.org",
            picture="https://example.com/profile.jpg",
            engine=mock_engine,
        )
        crud.upsert_user(
            sub=self.user_id_2,
            name="Test User 2",
            email="johan2@datatreehouse.org",
            picture="https://example.com/profile.jpg",
            engine=mock_engine,
        )

    def test_read_all_fuel_entries(
        self,
        mock_engine: Engine,
    ):
        car_id_1 = crud.new_car(
            user_id=self.user_id,
            nickname="Ford Focus",
            fuel_type="Unleaded Petrol 95",
            engine=mock_engine,
        )
        crud.new_car(
            user_id=self.user_id_2,
            nickname="VW Polo",
            fuel_type="Diesel 10ppm",
            engine=mock_engine,
        )
        crud.new_fuel_entry(
            self.user_id,
            mock_engine,
            car_id=car_id_1,
            entry_datetime=datetime.datetime(2026, 6, 1, 12, 0, tzinfo=datetime.UTC),
            odometer=10000.0,
            trip=500.0,
            fuel_filled=50.0,
            price=750.0,
            currency="ZAR",
            location="Cape Town",
        )

        fuel_entries: Sequence[FuelEntry] | None = crud.get_all_fuel_entries(
            user_id=self.user_id,
            engine=mock_engine,
            load_car=True,
        )

        assert fuel_entries is not None
        assert len(list(fuel_entries)) == 1
        assert fuel_entries[0].car.id == car_id_1
