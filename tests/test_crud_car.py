import datetime

import pytest
from dirty_equals import IsAnyStr, IsDate, IsStr
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from db import crud, m


class TestNewCar:
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

    def test_new_user(
        self,
        mock_engine: Engine,
    ):
        """Test if I can create a new car, only using the required fields"""
        crud.new_car(
            user_id=self.user_id,
            nickname="Ford Focus",
            fuel_type="Unleaded Petrol 95",
            engine=mock_engine,
        )

        with Session(mock_engine) as session:
            stmt = session.query(m.Car).filter_by(user_id=self.user_id, nickname="Ford Focus")
            car = stmt.one_or_none()
            assert car is not None
            assert car.nickname == "Ford Focus"
            assert car.fuel_type == "Unleaded Petrol 95"

    def test_new_car_with_all_optionals(
        self,
        mock_engine: Engine,
    ):
        """Test if I can create a new car, using all of the available fields"""
        crud.new_car(
            user_id=self.user_id,
            nickname="Ford Fiesta",
            fuel_type="Unleaded Petrol 95",
            registration_number="XX XX XX GP",
            vin_number="1FALP42X9PF111111",
            model_description="ford focus 1.0 ecoboost ambiente 5dr",
            color="Blue",
            registration_date=datetime.date(2017, 9, 28),
            engine=mock_engine,
        )

        with Session(mock_engine) as session:
            stmt = session.query(m.Car).filter_by(user_id=self.user_id, nickname="Ford Fiesta")
            car = stmt.one_or_none()
            assert car is not None
            assert car.nickname == IsAnyStr(max_length=50)
            assert car.fuel_type == IsStr(
                regex=r"Unleaded Petrol 95|Unleaded Petrol 93|Diesel 10ppm|Diesel 50ppm|Diesel 500ppm"
            )
            assert car.registration_number == "XX XX XX GP"
            assert car.model_description == IsAnyStr(max_length=255)
            assert car.color == IsAnyStr(max_length=255)
            assert car.registration_date == IsDate(gt=datetime.date(2000, 1, 1))


class TestCarValidations:
    @pytest.fixture(autouse=True)
    def setup(
        self,
        pg_engine: Engine,
    ):
        self.user_id_1 = "test_sub_1"
        self.user_id_2 = "test_sub_2"

        crud.upsert_user(
            sub=self.user_id_1,
            name="Test User 1",
            email=f"{self.user_id_1}@datatreehouse.org",
            picture="https://example.com/profile.jpg",
            engine=pg_engine,
        )
        crud.upsert_user(
            sub=self.user_id_2,
            name="Test User 2",
            email=f"{self.user_id_2}@datatreehouse.org",
            picture="https://example.com/profile.jpg",
            engine=pg_engine,
        )

    @pytest.mark.integration
    def test_unique_nickname_constraint(
        self,
        pg_engine: Engine,
    ):
        # First one will be okay
        crud.new_car(
            user_id=self.user_id_1,
            nickname="Ford Focus",
            fuel_type="Unleaded Petrol 95",
            engine=pg_engine,
        )

        # Second one will raise an error
        with pytest.raises(IntegrityError):
            crud.new_car(
                user_id=self.user_id_1,
                nickname="Ford Focus",
                fuel_type="Unleaded Petrol 95",
                engine=pg_engine,
            )

        # But a different user won't
        crud.new_car(
            user_id=self.user_id_2,
            nickname="Ford Focus",
            fuel_type="Unleaded Petrol 95",
            engine=pg_engine,
        )

    @pytest.mark.integration
    def test_unique_registration_number_constraint(
        self,
        pg_engine: Engine,
    ):
        # First one will be okay
        crud.new_car(
            user_id=self.user_id_1,
            nickname="Volkswagen Polo",
            fuel_type="Unleaded Petrol 95",
            engine=pg_engine,
            registration_number="XX XX XX FS",
        )

        # Second one will raise an error
        with pytest.raises(IntegrityError):
            crud.new_car(
                user_id=self.user_id_1,
                nickname="Volkswagen Polo Rolo",
                fuel_type="Unleaded Petrol 95",
                engine=pg_engine,
                registration_number="XX XX XX FS",
            )

        # A different user as well
        with pytest.raises(IntegrityError):
            crud.new_car(
                user_id=self.user_id_2,
                nickname="Volkswagen Polo Lux",
                fuel_type="Unleaded Petrol 95",
                engine=pg_engine,
                registration_number="XX XX XX FS",
            )

    @pytest.mark.integration
    def test_unique_vin_number_constraint(
        self,
        pg_engine: Engine,
    ):
        # First one will be okay
        crud.new_car(
            user_id=self.user_id_1,
            nickname="Isuzu Mux",
            fuel_type="Diesel 50ppm",
            engine=pg_engine,
            vin_number="1FALP42X9PF111111",
        )

        # Second one will raise an error
        with pytest.raises(IntegrityError):
            crud.new_car(
                user_id=self.user_id_1,
                nickname="Isuzu Muxxie",
                fuel_type="Diesel 50ppm",
                engine=pg_engine,
                vin_number="1FALP42X9PF111111",
            )

        # A different user as well
        with pytest.raises(IntegrityError):
            crud.new_car(
                user_id=self.user_id_2,
                nickname="Isuzu Mux Max",
                fuel_type="Diesel 50ppm",
                engine=pg_engine,
                vin_number="1FALP42X9PF111111",
            )


class TestReadCar:
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

    def test_read_cars_returns_none(self, mock_engine: Engine):
        """Test if I get None when I try to read cars for a user that has no cars"""
        cars = crud.get_cars(user_id=self.user_id, engine=mock_engine)
        assert cars is None

    def test_read_all_cars(self, mock_engine: Engine):
        """Test if I can read all the cars for a user"""
        crud.new_car(
            user_id=self.user_id,
            nickname="Ford Focus",
            fuel_type="Unleaded Petrol 95",
            engine=mock_engine,
        )
        crud.new_car(
            user_id=self.user_id,
            nickname="VW Polo",
            fuel_type="Diesel 10ppm",
            engine=mock_engine,
        )

        cars = crud.get_cars(user_id=self.user_id, engine=mock_engine)
        assert cars is not None
        assert len(cars) == 2
        assert cars[0].nickname == "Ford Focus"
        assert cars[1].nickname == "VW Polo"


# TODO update car

# TODO get specific car

# TODO delete car (also deletes fuel entries)
