import uuid
from datetime import datetime

import pandas as pd
import streamlit as st

from db import crud, get_engine
from utils import primary_text

st.set_page_config(layout="wide")

st.markdown(f"## {primary_text('Edit')} Fuel Entries")

engine = get_engine()
cars = crud.get_all_cars(user_id=str(st.user.sub), engine=engine)
available_cars: dict[str, uuid.UUID] = {car.nickname: car.id for car in cars} if cars else {}
car_nicknames = list(available_cars.keys())


def new_car_layout():
    st.markdown(f"Please {primary_text('add a car')} to start logging fuel entries.")
    st.page_link(
        "pages/new_car.py",
        label="Add my first car",
        icon=":material/directions_car:",
        width="stretch",
        query_params={"first_car": "true"},
    )


if not cars:
    new_car_layout()
    st.stop()

selected_car_nickname = st.selectbox("Car", options=car_nicknames)
selected_car_id: uuid.UUID = available_cars[selected_car_nickname]  # type: ignore[index]

# Reset the editor state when the selected car changes
if st.session_state.get("_edit_car_id") != selected_car_id:
    st.session_state["_edit_car_id"] = selected_car_id
    st.session_state.pop("edit_df", None)

# Load entries for the selected car into session state
if "edit_df" not in st.session_state:
    entries = crud.get_fuel_entries_for_car(car_id=selected_car_id, engine=engine)
    if entries:
        records = [
            {
                "id": str(e.id),
                "entry_datetime": e.entry_datetime,
                "odometer": e.odometer,
                "trip": e.trip,
                "fuel_filled": e.fuel_filled,
                "price": e.price,
                "location": e.location or "",
            }
            for e in entries
        ]
        df = pd.DataFrame(records).set_index("id")
    else:
        df = pd.DataFrame(columns=["entry_datetime", "odometer", "trip", "fuel_filled", "price", "location"])  # ty:ignore[invalid-argument-type]
    st.session_state["edit_df"] = df


def handle_row_change():
    change_state = st.session_state["fuel_entry_editor"]
    entry_ids = list(st.session_state["edit_df"].index)

    # Process edited rows — { row_index: { column_name: new_value } }
    if change_state["edited_rows"]:
        for row_idx, changes in change_state["edited_rows"].items():
            raw_id = entry_ids[row_idx]
            entry_id = uuid.UUID(raw_id)
            success = crud.update_fuel_entry(
                entry_id=entry_id,
                changes=changes,
                engine=get_engine(),
            )
            if success:
                for column, new_value in changes.items():
                    st.session_state["edit_df"].at[raw_id, column] = new_value
                st.toast(f"Row {row_idx + 1} updated.")
            else:
                st.toast(f"Failed to update row {row_idx + 1}.", icon="⚠️")

    # Process added rows — [ { column_name: value } ]
    if change_state["added_rows"]:
        for new_row in change_state["added_rows"]:
            try:
                entry = crud.new_fuel_entry(
                    str(st.user.sub),
                    get_engine(),
                    car_id=st.session_state["_edit_car_id"],
                    entry_datetime=datetime.fromisoformat(new_row["entry_datetime"]),
                    odometer=float(new_row.get("odometer", 0)),
                    trip=float(new_row.get("trip", 0)),
                    fuel_filled=float(new_row.get("fuel_filled", 0)),
                    price=float(new_row.get("price", 0)),
                    currency="ZAR",
                    location=new_row.get("location", "") or "",
                )
                new_record = pd.DataFrame(
                    [
                        {
                            "id": str(entry.id),
                            "entry_datetime": entry.entry_datetime,
                            "odometer": entry.odometer,
                            "trip": entry.trip,
                            "fuel_filled": entry.fuel_filled,
                            "price": entry.price,
                            "location": entry.location or "",
                        }
                    ]
                ).set_index("id")
                st.session_state["edit_df"] = pd.concat([st.session_state["edit_df"], new_record])
                st.toast("New entry added.")
            except Exception as e:
                st.toast(f"Failed to add entry: {e}", icon="⚠️")

    # Process deleted rows — [ row_index, ... ]
    if change_state["deleted_rows"]:
        deleted_raw_ids = [entry_ids[i] for i in sorted(change_state["deleted_rows"], reverse=True)]
        for raw_id in deleted_raw_ids:
            entry_id = uuid.UUID(raw_id)
            success = crud.soft_delete_fuel_entry(entry_id=entry_id, engine=get_engine())
            if success:
                st.session_state["edit_df"].drop(index=raw_id, inplace=True)
                st.toast("Entry deleted.")
            else:
                st.toast("Failed to delete entry.", icon="⚠️")


st.markdown(f"### {primary_text('Fuel Entries')}")

if st.session_state["edit_df"].empty:
    st.info("No fuel entries found for this car.")
else:
    st.data_editor(
        st.session_state["edit_df"],
        key="fuel_entry_editor",
        on_change=handle_row_change,
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True,
        disabled=["id"],
        column_config={
            "entry_datetime": st.column_config.DatetimeColumn(
                "Date & Time",
                required=True,
            ),
            "odometer": st.column_config.NumberColumn(
                "Odometer (km)",
                min_value=0.0,
                required=True,
            ),
            "trip": st.column_config.NumberColumn(
                "Trip (km)",
                min_value=0.0,
                required=True,
            ),
            "fuel_filled": st.column_config.NumberColumn(
                "Fuel Filled (L)",
                min_value=0.0,
                required=True,
            ),
            "price": st.column_config.NumberColumn(
                "Price (ZAR)",
                min_value=0.0,
                required=True,
            ),
            "location": st.column_config.TextColumn(
                "Location",
                required=True,
            ),
        },
    )
