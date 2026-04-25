"""Bulk upload page - allows users to upload multiple fuel entries via Excel."""

import pandas as pd
import streamlit as st
from loguru import logger
from numpy import mean

from constants import settings
from db import crud, get_engine, m
from db.crud.read import get_cars
from utils import coloured_text, primary_text
from utils.bulk_upload import (
    FUEL_ENTRIES_SHEET,
    ParsedVehicle,
    ParseError,
    load_workbook_from_bytes,
    parse_vehicles_sheet,
    validate_vehicle_references,
    validate_workbook,
)
from utils.template import populate_template

st.markdown(f"## Ready to perform a {primary_text('bulk upload')}?")

# ── Template download ──────────────────────────────────────────────────────────

_engine = get_engine()
_user_sub: str = str(st.user.sub)
_user_cars: list[m.Car] = list(get_cars(_user_sub, _engine) or [])

_template_bytes = populate_template(settings.static_dir / "template.xlsx", _user_cars)

st.download_button(
    label=f"Download your {coloured_text('personalised template.xlsx', '#1DCC1D')}",
    data=_template_bytes,
    file_name="template.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    type="tertiary",
)

# ── Session state initialisation ───────────────────────────────────────────────

_DEFAULTS: dict[str, object] = {
    "uploaded_file_processed": False,
    "validated_entries": None,
    "validated_vehicles": None,
    "file_uploader_key": 0,
    "total_filled_sum": 0.0,
    "total_km_sum": 0.0,
    "ave_km_per_l_performance": 0.0,
}

for _key, _default in _DEFAULTS.items():
    if _key not in st.session_state:
        st.session_state[_key] = _default


# ── Helpers ────────────────────────────────────────────────────────────────────


def _show_errors(errors: list[ParseError]) -> None:
    """Render a table of row-level errors."""
    rows = [{"Excel Row": e.row, "Error": e.error} for e in errors]
    st.dataframe(pd.DataFrame(rows), use_container_width=True)


def _compute_summary(entries: list[m.FuelEntry]) -> tuple[float, float, float]:
    """Return ``(total_fuel_L, total_km, avg_km_per_L)`` for a list of entries."""
    total_fuel = sum(e.fuel_filled for e in entries)
    total_km = sum(e.trip for e in entries)
    avg_perf = float(mean([e.trip / e.fuel_filled for e in entries if e.fuel_filled > 0])) if entries else 0.0
    return total_fuel, total_km, avg_perf


# ── Main UI ────────────────────────────────────────────────────────────────────

with st.container(border=True):
    st.markdown("### New Bulk Upload")

    if not st.session_state.uploaded_file_processed:
        # ── Step 1: file upload & validation ──────────────────────────────────
        uploaded_file = st.file_uploader(
            f"Choose your {primary_text('bulk upload file')}",
            type="xlsx",
            key=f"uploader_{st.session_state.file_uploader_key}",
        )

        if uploaded_file is not None and st.session_state.validated_entries is None:
            raw_bytes: bytes = uploaded_file.read()

            try:
                wb = load_workbook_from_bytes(raw_bytes)
            except Exception as exc:
                st.error(f"Failed to read Excel file: {exc!s}")
                st.stop()

            # Validate sheet structure & required columns
            is_valid, error_message = validate_workbook(wb)
            if not is_valid:
                st.error(error_message)
                st.stop()

            # Parse and validate the Vehicles sheet
            parsed_vehicles, vehicle_errors = parse_vehicles_sheet(wb)
            if vehicle_errors:
                st.error(f"Found {len(vehicle_errors)} error(s) in the Vehicles sheet.")
                st.markdown("### Vehicles Sheet Errors")
                _show_errors(vehicle_errors)
                st.info("Please fix the errors in your file and upload again.")
                st.stop()

            # Validate that every nickname in Fuel Entries is declared in Vehicles
            known_nicknames: set[str] = {pv.nickname for pv in parsed_vehicles}
            ref_errors = validate_vehicle_references(wb, known_nicknames)
            if ref_errors:
                st.error(f"Found {len(ref_errors)} vehicle reference error(s) in the Fuel Entries sheet.")
                st.markdown("### Vehicle Reference Errors")
                _show_errors(ref_errors)
                st.info("Please fix the errors in your file and upload again.")
                st.stop()

            # Store validated state (raw bytes + vehicles) for the confirmation step
            st.session_state.validated_entries = raw_bytes
            st.session_state.validated_vehicles = parsed_vehicles
            st.rerun()

        # ── Step 2: confirmation ───────────────────────────────────────────────
        if st.session_state.validated_entries is not None:
            raw_bytes = st.session_state.validated_entries
            parsed_vehicles: list[ParsedVehicle] = st.session_state.validated_vehicles

            wb = load_workbook_from_bytes(raw_bytes)

            fuel_ws = wb[FUEL_ENTRIES_SHEET]
            entry_count = sum(
                1 for row in fuel_ws.iter_rows(min_row=2, values_only=True) if any(cell is not None for cell in row)
            )
            new_vehicle_count = sum(1 for pv in parsed_vehicles if pv.id is None)

            summary_parts = [f"**{entry_count}** fuel {'entry' if entry_count == 1 else 'entries'}"]
            if new_vehicle_count:
                summary_parts.append(
                    f"**{new_vehicle_count}** new {'vehicle' if new_vehicle_count == 1 else 'vehicles'}"
                )
            st.info(f"File validated successfully. Ready to upload {' and '.join(summary_parts)}.")

            col1, col2 = st.columns([1, 1])

            with col1:
                label = f"Confirm Upload ({entry_count} {'entry' if entry_count == 1 else 'entries'})"
                if st.button(label, type="primary", use_container_width=True):
                    try:
                        with st.spinner("Saving entries to the database..."):
                            new_cars, fuel_entries = crud.save_bulk_upload(
                                user_id=_user_sub,
                                wb=wb,
                                parsed_vehicles=parsed_vehicles,
                                engine=_engine,
                            )

                        st.success(f"Successfully uploaded {len(fuel_entries)} entries!")

                        total_fuel, total_km, avg_perf = _compute_summary(fuel_entries)
                        st.session_state.total_filled_sum = total_fuel
                        st.session_state.total_km_sum = total_km
                        st.session_state.ave_km_per_l_performance = avg_perf

                        st.session_state.uploaded_file_processed = True
                        st.session_state.validated_entries = None
                        st.session_state.validated_vehicles = None
                        st.rerun()

                    except ValueError as exc:
                        st.error(f"Validation error: {exc!s}")
                        st.stop()
                    except Exception as exc:
                        logger.exception(f"Bulk upload failed for user {st.user.sub}")
                        st.error("Database error: Failed to save entries. No data was uploaded.")
                        st.exception(exc)
                        st.stop()

            with col2:
                if st.button("Cancel", use_container_width=True):
                    st.session_state.validated_entries = None
                    st.session_state.validated_vehicles = None
                    st.session_state.file_uploader_key += 1
                    st.rerun()

    else:
        # ── Step 3: success summary ────────────────────────────────────────────
        st.success("Upload completed successfully!")

        total_fuel = st.session_state.total_filled_sum
        total_km = st.session_state.total_km_sum
        avg_perf = st.session_state.ave_km_per_l_performance

        if all(v > 0 for v in [total_fuel, total_km, avg_perf]):
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric(
                    label="Total Fuel Filled",
                    value=f"{total_fuel:.0f} {primary_text('L')}",
                )
            with col2:
                st.metric(
                    label="Total Trip Distance",
                    value=f"{total_km:.0f} {primary_text('km')}",
                )
            with col3:
                st.metric(
                    label="Ave Performance (km/L)",
                    value=f"{avg_perf:.2f} {primary_text('km/L')}",
                )

        if st.button("Upload Another File"):
            st.session_state.uploaded_file_processed = False
            st.session_state.validated_entries = None
            st.session_state.validated_vehicles = None
            st.session_state.file_uploader_key += 1
            st.rerun()
