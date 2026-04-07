import datetime
import re

import pytest
from email_validator import EmailNotValidError
from sqlalchemy.engine import Engine

from db import crud

sample_data: dict[str, str] = {
    "sub": "116030117551259471713",
    "name": "Johan",
    "email": "johan@datatreehouse.org",
    "picture": "https://lh3.googleusercontent.com/a/ACg8ocJy2NqIQPaqxV2LHXxRqt-PagaU_4FPOowtbsRc2QnBFkjgD28=s96-c",
}


class TestCreateUser:
    def test_new_user(
        self,
        mock_engine: Engine,
    ):
        """Will test if a new user is created.
        The function will also fully detach the User object so that it can be used!
        """
        new_user = crud.upsert_user(
            sub=sample_data["sub"],
            name=sample_data["name"],
            email=sample_data["email"],
            picture=sample_data["picture"],
            engine=mock_engine,
        )

        assert new_user.sub == sample_data["sub"]
        assert len(new_user.gravatar_hash) == 32
        assert new_user.gravatar_avatar.startswith("https://secure.gravatar.com")
        assert new_user.gravatar_profile.startswith("https://gravatar.com")
        assert new_user.name == sample_data["name"]
        assert isinstance(new_user.last_modified_date, datetime.datetime)

    def test_get_old_user(
        self,
        mock_engine: Engine,
    ):
        """Will test if we can get get an old, existing user"""
        old_user = crud.upsert_user(
            sub=sample_data["sub"],
            name="i-will-not-be-used",
            email="i-will-not-be-used",
            picture="i-will-not-be-used",
            engine=mock_engine,
        )

        assert old_user.sub == sample_data["sub"]
        assert old_user.name == sample_data["name"]
        assert isinstance(old_user.last_modified_date, datetime.datetime)

        # throw in the test for the repr
        assert re.fullmatch(r"User\(id=.*?, name='.*?', email='.*?'\)", repr(old_user))


def test_invalid_email(mock_engine: Engine):
    with pytest.raises(EmailNotValidError):
        crud.upsert_user(
            sub=sample_data["sub"],
            name=sample_data["name"],
            email="invalid-email@mytest.com",
            picture=sample_data["picture"],
            engine=mock_engine,
        )
