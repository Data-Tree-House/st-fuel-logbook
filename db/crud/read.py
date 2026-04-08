from collections.abc import Sequence

from loguru import logger
from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from db.model import Car


def get_cars(user_id: str, engine: Engine) -> Sequence[Car] | None:
    """Gets all the cars for a user.

    Args:
        user_id (str): The user's sub
        engine (Engine): The SQLAlchemy engine to use for the query

    Returns:
        Sequence[Car] | None: A list of Car objects if any are found, otherwise None
    """

    with Session(engine) as session:
        stmt = select(Car).where(
            Car.user_id == user_id,
            Car.is_deleted == False,  # noqa: E712
        )
        cars: Sequence[Car] = session.execute(stmt).scalars().all()
        if not cars:
            logger.info(f"No cars found for user {user_id}")
            return None
        return cars
