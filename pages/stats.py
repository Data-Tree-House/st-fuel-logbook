import pandas as pd
import streamlit as st

st.markdown("## Statistics")
# 1. Initialize DataFrame in session state so edits persist properly
if "df" not in st.session_state:
    st.session_state.df = pd.DataFrame(
        [
            {"Product": "Laptop", "Stock": 10, "Price": 1200},
            {"Product": "Phone", "Stock": 25, "Price": 800},
            {"Product": "Monitor", "Stock": 15, "Price": 300},
        ]
    )


# 2. Define the callback function to handle row changes
def handle_row_change():
    # Access the state dictionary using the widget's key
    change_state = st.session_state["my_editor"]

    # Process Edited Rows
    # Structure: { row_index: { column_name: new_value } }
    if change_state["edited_rows"]:
        for row_idx, changes in change_state["edited_rows"].items():
            st.toast(f"Row {row_idx} changed fields: {changes}")

            # Apply changes directly to your master session state DataFrame
            for column, new_value in changes.items():
                st.session_state.df.at[row_idx, column] = new_value

    # Process Added Rows
    # Structure: [ { column_name: value } ]
    if change_state["added_rows"]:
        for new_row in change_state["added_rows"]:
            st.toast(f"Added new row data: {new_row}")
            # Append logic can be added here if using dynamic row configurations

    # Process Deleted Rows
    # Structure: [ row_index_1, row_index_2 ]
    if change_state["deleted_rows"]:
        for row_idx in change_state["deleted_rows"]:
            st.toast(f"Deleted row index: {row_idx}")


# 3. Render the data editor with the on_change callback assigned
st.subheader("Inventory Manager")
st.data_editor(
    st.session_state.df,
    key="my_editor",
    on_change=handle_row_change,
    num_rows="dynamic",  # Allows users to add/delete rows
)

# Display updated data for verification
st.write("Current Session State DataFrame:")
st.dataframe(st.session_state.df)
