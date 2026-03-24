from typing import TypedDict


class StreamlitUser(TypedDict):
    sub: str
    name: str
    email: str
    picture: str


class Preferences(TypedDict):
    last_fuel_type: str
    last_location: str
    last_currency: str
    last_vehicle: str
    all_vehicles: dict[str, int]
