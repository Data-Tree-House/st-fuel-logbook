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


class TestGetUserFuelStats:
    @pytest.fixture(autouse=True)
    def setup(self, mock_engine: Engine):
        self.user_id = "stats_sub"
        crud.upsert_user(
            sub=self.user_id,
            name="Stats User",
            email="stats@datatreehouse.org",
            picture="https://example.com/profile.jpg",
            engine=mock_engine,
        )

    def test_stats_no_entries_returns_zeros(self, mock_engine: Engine):
        stats = crud.get_user_fuel_stats(user_id=self.user_id, engine=mock_engine)
        assert stats["entry_count"] == 0.0
        assert stats["total_trip_km"] == 0.0
        assert stats["total_fuel_litres"] == 0.0
        assert stats["total_expense_zar"] == 0.0

    def test_stats_aggregates_entries(self, mock_engine: Engine):
        car_id = crud.new_car(
            user_id=self.user_id,
            nickname="Stats Car",
            fuel_type="Unleaded Petrol 95",
            engine=mock_engine,
        )
        crud.new_fuel_entry(
            self.user_id,
            mock_engine,
            car_id=car_id,
            entry_datetime=datetime.datetime(2026, 1, 1, 8, 0, tzinfo=datetime.UTC),
            odometer=5000.0,
            trip=200.0,
            fuel_filled=20.0,
            price=300.0,
            currency="ZAR",
            location="Joburg",
        )
        crud.new_fuel_entry(
            self.user_id,
            mock_engine,
            car_id=car_id,
            entry_datetime=datetime.datetime(2026, 2, 1, 8, 0, tzinfo=datetime.UTC),
            odometer=5200.0,
            trip=300.0,
            fuel_filled=30.0,
            price=450.0,
            currency="ZAR",
            location="Cape Town",
        )

        stats = crud.get_user_fuel_stats(user_id=self.user_id, engine=mock_engine)
        assert stats["entry_count"] == 2.0
        assert stats["total_trip_km"] == 500.0
        assert stats["total_fuel_litres"] == 50.0
        assert stats["total_expense_zar"] == 750.0


class TestGetFuelEntriesForCar:
    @pytest.fixture(autouse=True)
    def setup(self, mock_engine: Engine):
        self.user_id = "car_entries_sub"
        crud.upsert_user(
            sub=self.user_id,
            name="Car Entries User",
            email="car_entries@datatreehouse.org",
            picture="https://example.com/profile.jpg",
            engine=mock_engine,
        )

    def test_returns_none_when_no_entries(self, mock_engine: Engine):
        car_id = crud.new_car(
            user_id=self.user_id,
            nickname="Empty Car",
            fuel_type="Diesel 10ppm",
            engine=mock_engine,
        )
        result = crud.get_fuel_entries_for_car(car_id=car_id, engine=mock_engine)
        assert result is None

    def test_returns_entries_for_car(self, mock_engine: Engine):
        car_id = crud.new_car(
            user_id=self.user_id,
            nickname="Entry Car",
            fuel_type="Diesel 10ppm",
            engine=mock_engine,
        )
        crud.new_fuel_entry(
            self.user_id,
            mock_engine,
            car_id=car_id,
            entry_datetime=datetime.datetime(2026, 3, 1, 10, 0, tzinfo=datetime.UTC),
            odometer=8000.0,
            trip=150.0,
            fuel_filled=15.0,
            price=200.0,
            currency="ZAR",
            location="Pretoria",
        )

        entries = crud.get_fuel_entries_for_car(car_id=car_id, engine=mock_engine)
        assert entries is not None
        assert len(list(entries)) == 1
        assert entries[0].car_id == car_id

    def test_excludes_soft_deleted_entries(self, mock_engine: Engine):
        car_id = crud.new_car(
            user_id=self.user_id,
            nickname="Deleted Entry Car",
            fuel_type="Diesel 10ppm",
            engine=mock_engine,
        )
        entry = crud.new_fuel_entry(
            self.user_id,
            mock_engine,
            car_id=car_id,
            entry_datetime=datetime.datetime(2026, 4, 1, 10, 0, tzinfo=datetime.UTC),
            odometer=9000.0,
            trip=100.0,
            fuel_filled=10.0,
            price=150.0,
            currency="ZAR",
            location="Durban",
        )
        crud.soft_delete_fuel_entry(entry_id=entry.id, engine=mock_engine)

        result = crud.get_fuel_entries_for_car(car_id=car_id, engine=mock_engine)
        assert result is None


class TestUpdateFuelEntry:
    @pytest.fixture(autouse=True)
    def setup(self, mock_engine: Engine):
        self.user_id = "update_sub"
        crud.upsert_user(
            sub=self.user_id,
            name="Update User",
            email="update@datatreehouse.org",
            picture="https://example.com/profile.jpg",
            engine=mock_engine,
        )

    def test_update_returns_true_and_persists_change(self, mock_engine: Engine):
        car_id = crud.new_car(
            user_id=self.user_id,
            nickname="Update Car",
            fuel_type="Unleaded Petrol 93",
            engine=mock_engine,
        )
        entry = crud.new_fuel_entry(
            self.user_id,
            mock_engine,
            car_id=car_id,
            entry_datetime=datetime.datetime(2026, 5, 1, 9, 0, tzinfo=datetime.UTC),
            odometer=12000.0,
            trip=400.0,
            fuel_filled=40.0,
            price=600.0,
            currency="ZAR",
            location="East London",
        )

        result = crud.update_fuel_entry(
            entry_id=entry.id,
            changes={"odometer": 12050.0, "location": "Port Elizabeth"},
            engine=mock_engine,
        )
        assert result is True

        entries = crud.get_fuel_entries_for_car(car_id=car_id, engine=mock_engine)
        assert entries is not None
        updated = entries[0]
        assert updated.odometer == 12050.0
        assert updated.location == "Port Elizabeth"

    def test_update_nonexistent_entry_returns_false(self, mock_engine: Engine):
        import uuid

        result = crud.update_fuel_entry(
            entry_id=uuid.uuid4(),
            changes={"odometer": 99999.0},
            engine=mock_engine,
        )
        assert result is False


class TestSoftDeleteFuelEntry:
    @pytest.fixture(autouse=True)
    def setup(self, mock_engine: Engine):
        self.user_id = "delete_sub"
        crud.upsert_user(
            sub=self.user_id,
            name="Delete User",
            email="delete@datatreehouse.org",
            picture="https://example.com/profile.jpg",
            engine=mock_engine,
        )

    def test_soft_delete_returns_true(self, mock_engine: Engine):
        car_id = crud.new_car(
            user_id=self.user_id,
            nickname="Delete Car 1",
            fuel_type="Diesel 50ppm",
            engine=mock_engine,
        )
        entry = crud.new_fuel_entry(
            self.user_id,
            mock_engine,
            car_id=car_id,
            entry_datetime=datetime.datetime(2026, 6, 15, 7, 0, tzinfo=datetime.UTC),
            odometer=20000.0,
            trip=250.0,
            fuel_filled=25.0,
            price=375.0,
            currency="ZAR",
            location="Bloemfontein",
        )

        result = crud.soft_delete_fuel_entry(entry_id=entry.id, engine=mock_engine)
        assert result is True

    def test_soft_deleted_entry_hidden_from_queries(self, mock_engine: Engine):
        car_id = crud.new_car(
            user_id=self.user_id,
            nickname="Delete Car 2",
            fuel_type="Diesel 50ppm",
            engine=mock_engine,
        )
        entry = crud.new_fuel_entry(
            self.user_id,
            mock_engine,
            car_id=car_id,
            entry_datetime=datetime.datetime(2026, 6, 16, 7, 0, tzinfo=datetime.UTC),
            odometer=21000.0,
            trip=250.0,
            fuel_filled=25.0,
            price=375.0,
            currency="ZAR",
            location="Kimberley",
        )
        crud.soft_delete_fuel_entry(entry_id=entry.id, engine=mock_engine)

        entries = crud.get_fuel_entries_for_car(car_id=car_id, engine=mock_engine)
        assert entries is None

    def test_soft_delete_nonexistent_entry_returns_false(self, mock_engine: Engine):
        import uuid

        result = crud.soft_delete_fuel_entry(entry_id=uuid.uuid4(), engine=mock_engine)
        assert result is False
