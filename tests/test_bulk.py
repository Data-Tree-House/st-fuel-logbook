import pytest
from sqlalchemy.engine import Engine
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
        crud.new_car(
            user_id=self.user_id,
            nickname="Ford Focus",
            fuel_type="Unleaded Petrol 95",
            engine=mock_engine,
        )

    def test_new_user(
        self,
        mock_engine: Engine,
    ):
        """Test if I can create a new car, only using the required fields"""

        with Session(mock_engine) as session:
            stmt = session.query(m.Car).filter_by(user_id=self.user_id, nickname="Ford Focus")
            car = stmt.one_or_none()
