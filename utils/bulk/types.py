from enum import StrEnum


class RowAction(StrEnum):
    READ = "Read"
    UPDATE = "Update"
    DELETE = "Delete"
    INSERT = "Insert"


all_row_actions: list[RowAction] = [
    RowAction.READ,
    RowAction.UPDATE,
    RowAction.DELETE,
    RowAction.INSERT,
]


class SheetNames(StrEnum):
    FUEL_ENTRIES_SHEET = "Fuel Entries"
    CARS_SHEET = "Cars"
    METADATA_SHEET = "metadata"


class DefinedNames(StrEnum):
    FUEL_TYPE_OPTIONS = "FuelTypeOptions"
    ROW_ACTION_OPTIONS = "RowActionOptions"


ROW_ACTION_COLUMN_NAME = "Action"


all_sheet_names: list[SheetNames] = [
    SheetNames.FUEL_ENTRIES_SHEET,
    SheetNames.CARS_SHEET,
    SheetNames.METADATA_SHEET,
]
