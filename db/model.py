import hashlib
from datetime import datetime
from functools import cached_property
from typing import Literal

import pytz
from email_validator import validate_email
from sqlalchemy import DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship,
    validates,
)

TIMEZONE = pytz.timezone("Africa/Johannesburg")


class Base(DeclarativeBase):
    """Base class for all models."""

    pass


class BaseModel(Base):
    """Abstract base model with timestamp fields."""

    __abstract__ = True

    created_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(TIMEZONE),
        nullable=False,
        comment="Timestamp when record was created (Africa/Johannesburg)",
    )
    last_modified_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(TIMEZONE),
        onupdate=lambda: datetime.now(TIMEZONE),
        nullable=False,
        comment="Timestamp when record was last modified (Africa/Johannesburg)",
    )


class User(BaseModel):
    __tablename__ = "users"

    sub: Mapped[str] = mapped_column(
        String(30),
        primary_key=True,
        index=True,
        comment="The Google Id of the user logged in",
    )
    name: Mapped[str] = mapped_column(
        String(255),
        comment="The name and surname of the user",
    )
    email: Mapped[str] = mapped_column(
        String(250),  # according to email standards, the true max is 254...
        unique=True,
        index=True,
        comment="The email of the logged in user",
    )
    picture: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        # Thanks, https://vinicius73.github.io/gravatar-url-generator/#/
        default="https://gravatar.com/avatar/580b828f66630050b21aeaf8c20b89b3?s=400&d=mp&r=x",
        comment="The URL picture of the user",
    )

    # ====> Relationships
    # https://docs.sqlalchemy.org/en/21/orm/basic_relationships.html
    fuel_entries: Mapped[list["FuelEntry"]] = relationship(
        "FuelEntry",
        back_populates="user",
        # Indicates that the child object should follow along with its parent in all cases,
        # and be deleted once it is no longer associated with that parent
        # https://docs.sqlalchemy.org/en/21/orm/cascades.html
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"User(id={self.sub}, name='{self.name}', email='{self.email}')"

    @cached_property
    def gravatar_hash(self) -> str:
        return hashlib.md5(self.email.strip().lower().encode("utf-8")).hexdigest()

    @property
    def gravatar_avatar(self) -> str:
        return f"https://secure.gravatar.com/avatar/{self.gravatar_hash}"

    @property
    def gravatar_profile(self) -> str:
        return f"https://gravatar.com/{self.gravatar_hash}"

    # https://docs.sqlalchemy.org/en/21/orm/mapped_attributes.html#simple-validators
    @validates("email")
    def validate_email(self, key, value):  # noqa
        email_info = validate_email(
            value,
            # If true, DNS queries are made to check that the domain name in the email address
            # (the part after the @-sign) can receive mail, as described above.
            check_deliverability=True,
        )
        return email_info.normalized


class FuelEntry(BaseModel):
    """Fuel entry model for tracking vehicle refueling."""

    __tablename__ = "fuel_entries"

    id: Mapped[str] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
        autoincrement=True,
    )
    user_id: Mapped[str] = mapped_column(
        String(30),
        ForeignKey(
            "users.sub",
            ondelete="CASCADE",
        ),
        index=True,
        comment="Reference to the user who created this entry",
    )
    entry_datetime: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        index=True,
        comment="Date and time of the fuel entry",
    )
    odometer_km: Mapped[float] = mapped_column(
        Float,
        comment="Odometer reading in kilometres",
    )
    trip_km: Mapped[float] = mapped_column(
        Float,
        comment="Trip distance in kilometres",
    )
    fuel_litres: Mapped[float] = mapped_column(
        Float,
        comment="Amount of fuel filled in litres",
    )
    fuel_type: Mapped[
        Literal[
            "Unleaded Petrol 95",
            "Unleaded Petrol 93",
            "Diesel 10ppm",
            "Diesel 50ppm",
            "Diesel 500ppm",
        ]
    ] = mapped_column(
        String(20),
        nullable=False,
        comment="Type of fuel used (e.g., Petrol, Diesel)",
    )
    price: Mapped[float] = mapped_column(
        Float,
        comment="Total price paid in Rand",
    )
    currency: Mapped[str] = mapped_column(
        String(255),
        default="ZAR",
        comment="Goes with the price",
    )
    vehicle: Mapped[str] = mapped_column(
        String(255),
        comment="e.g. Ford Focus",
    )
    location: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="Location where fuel was purchased",
    )

    # ====> Relationships
    # https://docs.sqlalchemy.org/en/21/orm/basic_relationships.html
    user: Mapped["User"] = relationship(
        "User",
        back_populates="fuel_entries",
    )

    def __repr__(self) -> str:
        return (
            f"<FuelEntry(id={self.id}, user_id={self.user_id}, "
            f"date={self.entry_datetime}, odometer={self.odometer_km}km)>"
        )

    @validates("odometer_km", "trip_km", "fuel_litres", "price")
    def validate_non_negative(self, key, value):
        if value < 0:
            raise ValueError(f"{key} cannot be negative")
        return value

    @property
    def price_per_litre(self) -> float:
        return self.price / self.fuel_litres

    @property
    def fuel_consumption(self) -> float:
        return self.trip_km / self.fuel_litres

    @property
    def fuel_consumption_per_100(self) -> float:
        return (self.fuel_litres / self.trip_km) * 100
