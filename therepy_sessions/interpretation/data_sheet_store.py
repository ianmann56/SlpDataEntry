"""
The Data Sheet Store: the storage mechanism for interpreted data sheets.

The import code and its window reach storage only through `DataSheetStore`, received by
injection. Implementations live in `storage/`, and only `program.py` names one. This
module holds the abstraction and its records only, with no I/O.
"""

from abc import ABC, abstractmethod
from typing import NamedTuple

from interpretation.student_data_sheet import StudentDataSheet


class SavedDataSheet(NamedTuple):
    """
    Where a sheet's session now lives.

    Properties:
      location_url: Opens the saved session (for Google, the tab's URL).
      location_name: SLP-readable, e.g. "AG - Emotion Causes › 9/14/2026 11:00 AM". Names
        students only by Student Key.
      already_saved: True when the session was already stored and nothing was written.
    """
    location_url: str
    location_name: str
    already_saved: bool


class DataSheetStoreError(Exception):
    """A store operation failed. str(e) is an SLP-readable reason naming students only by Student Key."""


class DataSheetStore(ABC):
    """
    Saves interpreted data sheets. Business and UI logic use only this.

    Every message a store produces names students only by Student Key.
    """

    @abstractmethod
    def prepare(self) -> None:
        """
        Get ready to save: connect, sign in if needed, and find or create the destination.

        Idempotent: calling it again after it succeeded does nothing.

        Raises:
            DataSheetStoreError: If the destination can't be reached or prepared
        """

    @abstractmethod
    def save(self, sheet: StudentDataSheet) -> SavedDataSheet:
        """
        Store one interpreted sheet, or report that it is already stored.

        Calls `prepare` first if it hasn't run. Writes nothing partial: on failure,
        nothing from this attempt remains.

        Raises:
            DataSheetStoreError: If the sheet could not be stored
        """
