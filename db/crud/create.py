from loguru import logger
from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from db import m


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
