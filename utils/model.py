from datetime import datetime
from typing import Literal

import pytz
from sqlalchemy import DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship,
    synonym,
    validates,
)

# Define the timezone
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

    id: Mapped[str] = mapped_column(
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
        String(255),
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
        return f"<User(id={self.id}, name='{self.name}', email='{self.email}')>"

    # https://docs.sqlalchemy.org/en/21/orm/mapped_attributes.html#simple-validators
    @validates("email")
    def validate_email(self, key, value):  # noqa
        if "@" not in value:
            raise ValueError("failed simple email validation")
        return value


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
            "users.id",
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
    fuel_type: Mapped[Literal["Petrol", "Diesel"]] = mapped_column(
        String(20),
        nullable=False,
        comment="Type of fuel used (e.g., Petrol, Diesel, LPG, Electric)",
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

    # ====> Synonyms
    # https://docs.sqlalchemy.org/en/21/orm/mapped_attributes.html#synonyms
    odometer: Mapped[float] = synonym("odometer_km")
    trip: Mapped[float] = synonym("trip_km")
    fuel_litres: Mapped[float] = synonym("fuel")

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

    @validates("fuel_type")
    def validate_fuel_type(self, key, value):  # noqa
        allowed_fuel_types = {"Petrol", "Diesel"}
        if value not in allowed_fuel_types:
            raise ValueError(f"Invalid fuel type '{value}'. Allowed types are: {', '.join(allowed_fuel_types)}")
        return value

    @validates("odometer_km")
    def validate_odometer_km(self, key, value):  # noqa
        if value < 0:
            raise ValueError("Odometer reading cannot be negative")
        return value

    @validates("trip_km")
    def validate_trip_km(self, key, value):  # noqa
        if value < 0:
            raise ValueError("Trip distance cannot be negative")
        return value

    @validates("fuel_litres")
    def validate_fuel_litres(self, key, value):  # noqa
        if value < 0:
            raise ValueError("Fuel litres cannot be negative")
        return value

    @validates("price")
    def validate_price(self, key, value):  # noqa
        if value < 0:
            raise ValueError("Price cannot be negative")
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


def validate_fuel_consistency(
    session,
    user_id: str,
    vehicle: str,
    fuel_type: str,
    entry_id: str | None = None,
):
    query = session.query(FuelEntry).filter(FuelEntry.user_id == user_id, FuelEntry.vehicle == vehicle)

    if entry_id:  # Exclude current entry when updating
        query = query.filter(FuelEntry.id != entry_id)

    previous_entry = query.first()

    if previous_entry and previous_entry.fuel_type != fuel_type:
        raise ValueError(
            f"Fuel type inconsistency: {vehicle} previously used "
            f"{previous_entry.fuel_type}, cannot switch to {fuel_type}"
        )
