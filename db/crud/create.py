import datetime

from loguru import logger
from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from db import m
from db.model import FuelTypeLiteral


def create_all_tables(
    engine: Engine,
) -> None:
    """Creates all the tables if they don't exist.

    Args:
        engine (Engine): The SQLAlchemy engine to use for creating tables
    """
    m.Base.metadata.create_all(
        engine,
        checkfirst=True,
    )


def upsert_user(
    sub: str,
    name: str,
    email: str,
    picture: str,
    engine: Engine,
) -> m.User:
    """Will get a user keyed on their sub. If the user does not exist, it will create a new one for you.

    Args:
        sub (str): User's sub. This is provided by Streamlit. See their docs for more.
        name (str): Logged in user's name
        email (str): Logged in user's email
        picture (str): A URL of the person's profile picture
        engine (Engine): Engine to use

    Returns:
        User: The user in the database.
    """
    with Session(engine) as session:
        stmt = select(m.User).where(m.User.sub == sub)
        user: m.User | None = session.execute(stmt).scalar_one_or_none()
        if user is None:
            logger.info(f"Creating new user {email}")
            new_user = m.User(
                sub=sub,
                name=name,
                email=email,
                picture=picture,
            )
            session.add(new_user)
            session.commit()
            user = new_user

        # Refresh to load all attributes while still in session,
        # then expunge so the object can be used outside the session.
        # ref: https://docs.sqlalchemy.org/en/21/orm/session_state_management.html#expunging
        session.refresh(user)
        session.expunge(user)
    return user


def new_car(
    user_id: str,
    nickname: str,
    fuel_type: FuelTypeLiteral,
    engine: Engine,
    registration_number: str | None = None,
    vin_number: str | None = None,
    model_description: str | None = None,
    color: str | None = None,
    registration_date: datetime.date | None = None,
) -> None:
    """Create a new car entry for a user

    Args:
        user_id (str): User Id (sub) of the logged in user
        nickname (str): A short nickname for the car
        fuel_type (FuelTypeLiteral): What fuel does the car use?
        engine (Engine): Engine to use for the database operation. NOT a car engine, lol!
        vin_number (str | None, optional): Vehicle Identification Number (VIN) (optional). Defaults to None.
        registration_number (str | None, optional): Vehicle registration number (optional). Defaults to None.
        model_description (str | None, optional): Model description of the car (optional),
            e.g. ford focus 1.0 ecoboost ambiente 5dr. Defaults to None.
        color (str | None, optional): Color of the car (optional). Defaults to None.
        registration_date (date | None, optional): Registration date of the car (optional).
            Defaults to None.
    """
    with Session(engine) as session:
        new_car = m.Car(
            user_id=user_id,
            nickname=nickname,
            fuel_type=fuel_type,
            registration_number=registration_number,
            vin_number=vin_number,
            model_description=model_description,
            color=color,
            registration_date=registration_date,
        )
        session.add(new_car)
        session.commit()
    return
