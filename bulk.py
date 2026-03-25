import pandas as pd
import streamlit as st
from loguru import logger
from sqlalchemy.orm import Session

from constants import settings
from utils import coloured_text, model, primary_text
from utils.db import get_engine

st.set_page_config(
    page_title="Bulk Upload",
)

st.markdown(f"## Ready to perform a {primary_text('bulk upload')}?")

template_path = settings.static_dir / "template.xlsx"
with template_path.open("rb") as f:
    st.download_button(
        label=f"Download our {coloured_text('template.xlsx', '#1DCC1D')}",
        data=f,
        file_name="template.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        type="tertiary",
    )

COLUMN_NAME_MAPPING = {
    "Date (DD/MM/YYYY)": "date",
    "Vehicle": "vehicle",
    "Odometer (km)": "odometer_km",
    "Trip Distance (km)": "trip_km",
    "Fuel Filled (Liters)": "fuel_litres",
    "Fuel Type": "fuel_type",
    "Price": "price",
    "Location": "location",
}

REQUIRED_COLUMNS = list(COLUMN_NAME_MAPPING.keys())


def validate_dataframe(
    df: pd.DataFrame,
) -> tuple[bool, str]:
    missing_columns = set(REQUIRED_COLUMNS) - set(df.columns)
    if missing_columns:
        return False, f"Missing required columns: {', '.join(missing_columns)}"

    if df.empty or len(df) == 0:
        return False, "The uploaded file contains no data rows."

    if df.dropna(how="all").empty:
        return False, "The uploaded file contains only empty rows."

    return True, ""


with st.container(border=True):
    st.markdown("### New Bulk Upload")

    if "uploaded_file_processed" not in st.session_state:
        st.session_state.uploaded_file_processed = False

    if "validated_entries" not in st.session_state:
        st.session_state.validated_entries = None

    if "file_uploader_key" not in st.session_state:
        st.session_state.file_uploader_key = 0

    if not st.session_state.uploaded_file_processed:
        uploaded_file = st.file_uploader(
            f"Choose your {primary_text('bulk upload file')}",
            type="xlsx",
            max_upload_size=10,
            key=f"uploader_{st.session_state.file_uploader_key}",
        )

        if uploaded_file is not None and st.session_state.validated_entries is None:
            try:
                df = pd.read_excel(uploaded_file)
            except Exception as e:
                st.error(f"Failed to read Excel file: {e!s}")
                st.stop()

            is_valid, error_message = validate_dataframe(df)
            if not is_valid:
                st.error(error_message)
                st.stop()

            df.rename(
                columns=COLUMN_NAME_MAPPING,
                inplace=True,
            )

            entries: list[model.FuelEntry] = []
            errors: list[dict] = []

            for index, row in df.iterrows():
                try:
                    entry = model.FuelEntry(
                        entry_datetime=row["date"],
                        user_id=st.user.sub,
                        vehicle=row["vehicle"],
                        odometer_km=row["odometer_km"],
                        trip_km=row["trip_km"],
                        fuel_litres=row["fuel_litres"],
                        fuel_type=row["fuel_type"],
                        price=row["price"],
                        location=row["location"],
                    )
                    entries.append(entry)
                except ValueError as e:
                    # +2 for Excel row (header + 0-indexing)
                    errors.append(
                        {
                            "row": index + 2,  # type: ignore
                            "error": str(e),
                        }
                    )
                except Exception as e:
                    logger.exception(f"Unexpected error processing row {index + 2}: {e!s}")  # type: ignore
                    errors.append(
                        {
                            "row": index + 2,  # type: ignore
                            "error": f"Unexpected error: {e!s}",
                        }
                    )

            if errors:
                st.error(f"Found {len(errors)} validation error(s). No entries were uploaded.")
                st.markdown("### Validation Errors")

                error_df = pd.DataFrame(errors)
                error_df.columns = ["Excel Row", "Error"]
                st.dataframe(error_df, use_container_width=True)

                st.info("Please fix the errors in your file and upload again.")
                st.stop()

            st.session_state.validated_entries = entries
            st.rerun()

        if st.session_state.validated_entries is not None:
            entry_count = len(st.session_state.validated_entries)
            st.info(
                f"File validated successfully. Ready to upload **{entry_count}** {'entry' if entry_count == 1 else 'entries'}."
            )

            col1, col2 = st.columns([1, 1])

            with col1:
                if st.button(
                    f"Confirm Upload ({entry_count} {'entry' if entry_count == 1 else 'entries'})",
                    type="primary",
                    use_container_width=True,
                ):
                    try:
                        with st.spinner("Saving entries to the database..."), Session(get_engine()) as session:
                            session.add_all(st.session_state.validated_entries)
                            session.commit()

                        st.success(f"Successfully uploaded {entry_count} entries!")
                        st.session_state.uploaded_file_processed = True
                        st.session_state.validated_entries = None
                        st.rerun()

                    except Exception as e:
                        st.error("Database error: Failed to save entries. No data was uploaded.")
                        st.exception(e)
                        st.stop()

            with col2:
                if st.button(
                    "Cancel",
                    use_container_width=True,
                ):
                    st.session_state.validated_entries = None
                    st.session_state.file_uploader_key += 1
                    st.rerun()

    else:
        st.success("Upload completed successfully!")
        if st.button("Upload Another File"):
            st.session_state.uploaded_file_processed = False
            st.session_state.validated_entries = None
            st.session_state.file_uploader_key += 1
            st.rerun()
