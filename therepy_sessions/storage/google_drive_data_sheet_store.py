"""
The Google Drive Data Sheet Store: saves each interpreted sheet as a Session Tab in its
Student Session Workbook, a Google Sheet in the Therapy Data Folder.

There is one workbook per Student Key and Template Structure. A workbook is found by its
hidden Drive label (`appProperties`), so renaming it in Drive does not lose it. Its
Workbook Layout Order is kept in the spreadsheet's developer metadata.

Every Drive and Sheets request body lives in this module. Google errors are translated
into DataSheetStoreError, with messages that name students only by Student Key.
"""

import contextlib
import random
from collections.abc import Callable, Iterator
from typing import Any

import httplib2
from google.auth.exceptions import GoogleAuthError, RefreshError, TransportError
from googleapiclient.errors import HttpError
from oauthlib.oauth2.rfc6749.errors import OAuth2Error

from interpretation.data_sheet_store import DataSheetStore, DataSheetStoreError, SavedDataSheet
from interpretation.student_data_sheet import StudentDataSheet
from storage.session_layout import (
    CellValue,
    SessionMoment,
    WorkbookLayout,
    insert_index,
    moment_from_rows,
    moment_of,
    session_rows,
    tab_base_name,
    unique_tab_name,
    workbook_name,
)
from storage.template_structure import TemplateShape, shape_of

# The Therapy Data Folder: a folder inside a folder in My Drive
DATA_FOLDER_PATH: tuple[str, str] = ("SLP Therepy Data", "Current Year")

FOLDER_MIME_TYPE: str = "application/vnd.google-apps.folder"
SPREADSHEET_MIME_TYPE: str = "application/vnd.google-apps.spreadsheet"

# The hidden Drive label on every workbook
LABEL_WORKBOOK: str = "slpWorkbook"
LABEL_STUDENT_KEY: str = "slpStudentKey"
LABEL_STRUCTURE: str = "slpStructure"
# The developer metadata key holding a workbook's Workbook Layout Order
LAYOUT_METADATA_KEY: str = "slpWorkbookLayout"

# The client library backs off and retries 429 and 5xx responses this many times
_NUM_RETRIES: int = 3
# New tabs get at least the default grid, so the SLP can add to them by hand
_MIN_ROWS: int = 1000
_MIN_COLUMNS: int = 26
_MAX_SHEET_ID: int = 2**31 - 1


def _quote(value: str) -> str:
    """Quote a value for a Drive search query."""
    return "'" + value.replace("\\", "\\\\").replace("'", "\\'") + "'"


def _cell_payload(cell: CellValue) -> dict[str, Any]:
    """The Sheets CellData for one cell. Text is never parsed as a date, number, or formula."""
    if cell.number is not None:
        return {"userEnteredValue": {"numberValue": cell.number}}
    if cell.text is not None:
        return {"userEnteredValue": {"stringValue": cell.text}}
    return {}


def _quote_tab(title: str) -> str:
    """Quote a tab name for an A1 range."""
    return "'" + title.replace("'", "''") + "'"


def _tab_url(spreadsheet_id: str, sheet_id: int) -> str:
    return f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit#gid={sheet_id}"


class GoogleDriveDataSheetStore(DataSheetStore):
    """
    Saves sessions to Student Session Workbooks in the SLP's Google Drive.

    One store is built per Import window visit, and used only from that window's worker
    thread. It remembers the workbooks it found or created during the visit, because
    Drive search can take a while to list a new file. That memory only speeds things up:
    each remembered workbook is checked in Drive before use, and Drive is always the
    source of truth.
    """

    def __init__(
        self,
        inject_drive_service: Callable[[], Any],    # googleapiclient Resource, drive v3
        inject_sheets_service: Callable[[], Any],   # googleapiclient Resource, sheets v4
    ) -> None:
        """
        Args:
            inject_drive_service: Returns the Drive service, signing in if needed
            inject_sheets_service: Returns the Sheets service, signing in if needed
        """
        self._inject_drive_service = inject_drive_service
        self._inject_sheets_service = inject_sheets_service
        self._drive: Any = None    # googleapiclient Resource, drive v3
        self._sheets: Any = None   # googleapiclient Resource, sheets v4
        self._folder_id: str | None = None
        self._workbook_ids: dict[tuple[str, str], str] = {}

    def prepare(self) -> None:
        """Connect, signing in if needed, and find or create the Therapy Data Folder."""
        if self._folder_id is not None:
            return
        with self._translate_errors():
            self._drive = self._inject_drive_service()
            self._sheets = self._inject_sheets_service()
            parent_id = "root"
            for folder_name in DATA_FOLDER_PATH:
                parent_id = self._find_or_create_folder(folder_name, parent_id)
            self._folder_id = parent_id

    def save(self, sheet: StudentDataSheet) -> SavedDataSheet:
        """Save one session to its Student Session Workbook, or find it already saved."""
        self.prepare()
        with self._translate_errors():
            shape = shape_of(sheet.template)
            fingerprint = shape.structure_fingerprint()
            student_key = sheet.student_key
            moment = moment_of(sheet)

            spreadsheet_id = self._find_workbook(student_key, fingerprint)
            if spreadsheet_id is None:
                layout = WorkbookLayout.from_shape(shape)
                name = workbook_name(student_key, shape.template_name)
                return self._create_workbook(sheet, student_key, fingerprint, name, layout, moment)
            return self._add_to_workbook(spreadsheet_id, sheet, shape, moment)

    # Folder

    def _find_or_create_folder(self, name: str, parent_id: str) -> str:
        """Return the oldest folder with this name in the parent, creating it if there is none."""
        query = (
            f"name = {_quote(name)} and {_quote(parent_id)} in parents"
            f" and mimeType = {_quote(FOLDER_MIME_TYPE)} and trashed = false"
        )
        found = self._drive.files().list(
            q=query, spaces="drive", orderBy="createdTime", fields="files(id)", pageSize=1,
        ).execute(num_retries=_NUM_RETRIES)
        files = found.get("files", [])
        if files:
            return files[0]["id"]
        created = self._drive.files().create(
            body={"name": name, "mimeType": FOLDER_MIME_TYPE, "parents": [parent_id]}, fields="id",
        ).execute(num_retries=_NUM_RETRIES)
        return created["id"]

    # Finding a workbook

    def _find_workbook(self, student_key: str, fingerprint: str) -> str | None:
        """
        Return the id of the workbook for this Student Key and structure, or None.

        A remembered workbook is used while it is still in the folder and not trashed.
        Otherwise the folder is searched by the hidden label, and the most recently
        changed match wins (FR-013b).
        """
        cache_key = (student_key, fingerprint)
        cached = self._workbook_ids.get(cache_key)
        if cached is not None:
            if self._still_in_folder(cached):
                return cached
            del self._workbook_ids[cache_key]

        query = (
            f"{_quote(self._folder_id)} in parents and trashed = false"
            f" and mimeType = {_quote(SPREADSHEET_MIME_TYPE)}"
            f" and appProperties has {{ key={_quote(LABEL_WORKBOOK)} and value='1' }}"
            f" and appProperties has {{ key={_quote(LABEL_STUDENT_KEY)} and value={_quote(student_key)} }}"
            f" and appProperties has {{ key={_quote(LABEL_STRUCTURE)} and value={_quote(fingerprint)} }}"
        )
        found = self._drive.files().list(
            q=query, spaces="drive", orderBy="modifiedTime desc", fields="files(id,name)", pageSize=10,
        ).execute(num_retries=_NUM_RETRIES)
        files = found.get("files", [])
        if not files:
            return None
        self._workbook_ids[cache_key] = files[0]["id"]
        return files[0]["id"]

    def _still_in_folder(self, spreadsheet_id: str) -> bool:
        """Whether the workbook still exists in the folder and is not trashed."""
        try:
            file = self._drive.files().get(
                fileId=spreadsheet_id, fields="trashed,parents",
            ).execute(num_retries=_NUM_RETRIES)
        except HttpError as e:
            if e.resp.status == 404:
                return False
            raise
        return not file.get("trashed", False) and self._folder_id in file.get("parents", [])

    # Writing

    def _create_workbook(
        self,
        sheet: StudentDataSheet,
        student_key: str,
        fingerprint: str,
        name: str,
        layout: WorkbookLayout,
        moment: SessionMoment,
    ) -> SavedDataSheet:
        """
        Create a labeled workbook in the folder holding just this session's tab.

        If filling it fails, the new file is deleted so nothing partial remains (FR-002).
        If that delete fails too, the next save to it repairs it.
        """
        created = self._drive.files().create(
            body={
                "name": name,
                "mimeType": SPREADSHEET_MIME_TYPE,
                "parents": [self._folder_id],
                "appProperties": {LABEL_WORKBOOK: "1", LABEL_STUDENT_KEY: student_key, LABEL_STRUCTURE: fingerprint},
            },
            fields="id",
        ).execute(num_retries=_NUM_RETRIES)
        spreadsheet_id = created["id"]

        try:
            spreadsheet = self._sheets.spreadsheets().get(
                spreadsheetId=spreadsheet_id, fields="sheets.properties.sheetId",
            ).execute(num_retries=_NUM_RETRIES)
            default_sheet_ids = [tab["properties"]["sheetId"] for tab in spreadsheet.get("sheets", [])]

            sheet_id = self._new_sheet_id(default_sheet_ids)
            title = tab_base_name(moment)
            requests = self._add_tab_requests(sheet_id, title, 0, session_rows(sheet, layout))
            requests += [{"deleteSheet": {"sheetId": default_id}} for default_id in default_sheet_ids]
            requests.append(self._layout_metadata_request(layout))
            self._batch_update(spreadsheet_id, requests)
        except Exception:
            try:
                self._drive.files().delete(fileId=spreadsheet_id).execute(num_retries=_NUM_RETRIES)
            except Exception as delete_error:
                print(f"Could not remove the incomplete workbook for {student_key}: {delete_error!r}")
            raise

        self._workbook_ids[(student_key, fingerprint)] = spreadsheet_id
        return SavedDataSheet(_tab_url(spreadsheet_id, sheet_id), f"{name} › {title}", already_saved=False)

    def _add_to_workbook(
        self,
        spreadsheet_id: str,
        sheet: StudentDataSheet,
        shape: TemplateShape,
        moment: SessionMoment,
    ) -> SavedDataSheet:
        """
        Add this session as a new tab in an existing workbook, never changing its other tabs.

        If a tab already holds this session (the same Date and Time IN, read from the
        tab's values), nothing is written and that tab is returned (FR-016a). Otherwise
        the new tab goes in newest-first order (FR-018a). The tab is laid out in the workbook's own Workbook Layout Order (FR-025a), and the
        workbook is never renamed (FR-011). A workbook with no stored layout was left by a
        failed create, so this save also completes it: it stores the layout and removes
        its empty tabs (FR-019).
        """
        spreadsheet = self._sheets.spreadsheets().get(
            spreadsheetId=spreadsheet_id,
            fields="properties.title,sheets.properties(sheetId,title,index),developerMetadata",
        ).execute(num_retries=_NUM_RETRIES)
        workbook_title = spreadsheet["properties"]["title"]
        tabs = sorted((tab["properties"] for tab in spreadsheet.get("sheets", [])), key=lambda tab: tab["index"])

        layout, layout_missing = self._stored_layout(spreadsheet, shape)
        tab_tops = self._tab_tops(spreadsheet_id, tabs)

        moments = [moment_from_rows(top) for top in tab_tops]
        for tab, tab_moment in zip(tabs, moments):
            if tab_moment is not None and moment.matches(tab_moment):
                return SavedDataSheet(
                    _tab_url(spreadsheet_id, tab["sheetId"]), f"{workbook_title} › {tab['title']}", already_saved=True,
                )

        empty_tab_ids: set[int] = set()
        if layout_missing:
            empty_tab_ids = self._empty_tab_ids(spreadsheet_id, tabs, tab_tops)
        kept = [(tab, tab_moment) for tab, tab_moment in zip(tabs, moments) if tab["sheetId"] not in empty_tab_ids]

        sheet_id = self._new_sheet_id([tab["sheetId"] for tab in tabs])
        title = unique_tab_name(tab_base_name(moment), [tab["title"] for tab, _ in kept])
        # Placed among the tabs that stay; empty tabs being removed don't count
        position = insert_index(moment, [tab_moment for _, tab_moment in kept])
        index = kept[position][0]["index"] if position < len(kept) else len(tabs)

        requests = self._add_tab_requests(sheet_id, title, index, session_rows(sheet, layout))
        if layout_missing:
            requests.append(self._layout_metadata_request(layout))
            requests += [{"deleteSheet": {"sheetId": tab_id}} for tab_id in sorted(empty_tab_ids)]
        self._batch_update(spreadsheet_id, requests)
        return SavedDataSheet(_tab_url(spreadsheet_id, sheet_id), f"{workbook_title} › {title}", already_saved=False)

    @staticmethod
    def _stored_layout(spreadsheet: dict[str, Any], shape: TemplateShape) -> tuple[WorkbookLayout, bool]:
        """
        The workbook's stored Workbook Layout Order, and whether it was missing.

        Falls back to the sheet's own template order when the layout is missing or
        unreadable. The fallback has the same structure, so every value still has a place.
        """
        entries = [
            entry for entry in spreadsheet.get("developerMetadata", [])
            if entry.get("metadataKey") == LAYOUT_METADATA_KEY
        ]
        if not entries:
            print("A workbook has no stored layout; using the template's order and storing it.")
            return WorkbookLayout.from_shape(shape), True
        try:
            return WorkbookLayout.from_json(entries[0].get("metadataValue", "")), False
        except ValueError as e:
            print(f"A workbook's stored layout could not be read ({e}); using the template's order.")
            return WorkbookLayout.from_shape(shape), False

    def _tab_tops(self, spreadsheet_id: str, tabs: list[dict[str, Any]]) -> list[list[list[str]]]:
        """The A1:B6 values of each tab, in the order given, read in one call."""
        if not tabs:
            return []
        ranges = [f"{_quote_tab(tab['title'])}!A1:B6" for tab in tabs]
        result = self._sheets.spreadsheets().values().batchGet(
            spreadsheetId=spreadsheet_id, ranges=ranges, valueRenderOption="FORMATTED_VALUE",
        ).execute(num_retries=_NUM_RETRIES)
        return [value_range.get("values", []) for value_range in result.get("valueRanges", [])]

    def _empty_tab_ids(
        self,
        spreadsheet_id: str,
        tabs: list[dict[str, Any]],
        tab_tops: list[list[list[str]]],
    ) -> set[int]:
        """
        The tabs holding no values at all. Each tab whose A1:B6 is empty is read in full
        before it counts, so a tab with values further down is never removed.
        """
        candidates = [tab for tab, top in zip(tabs, tab_tops) if not any(any(cell for cell in row) for row in top)]
        if not candidates:
            return set()
        result = self._sheets.spreadsheets().values().batchGet(
            spreadsheetId=spreadsheet_id, ranges=[_quote_tab(tab["title"]) for tab in candidates],
        ).execute(num_retries=_NUM_RETRIES)
        return {
            tab["sheetId"]
            for tab, value_range in zip(candidates, result.get("valueRanges", []))
            if not any(any(cell for cell in row) for row in value_range.get("values", []))
        }

    @staticmethod
    def _new_sheet_id(used: list[int]) -> int:
        """A random tab id no tab in the workbook uses."""
        while True:
            sheet_id = random.randint(1, _MAX_SHEET_ID)
            if sheet_id not in used:
                return sheet_id

    @staticmethod
    def _add_tab_requests(sheet_id: int, title: str, index: int, rows: list[list[CellValue]]) -> list[dict[str, Any]]:
        """The requests that add a tab and write its rows, sent in one atomic batch."""
        widest = max((len(row) for row in rows), default=0)
        return [
            {
                "addSheet": {
                    "properties": {
                        "sheetId": sheet_id,
                        "title": title,
                        "index": index,
                        "gridProperties": {"rowCount": max(_MIN_ROWS, len(rows)), "columnCount": max(_MIN_COLUMNS, widest)},
                    },
                },
            },
            {
                "updateCells": {
                    "start": {"sheetId": sheet_id, "rowIndex": 0, "columnIndex": 0},
                    "rows": [{"values": [_cell_payload(cell) for cell in row]} for row in rows],
                    "fields": "userEnteredValue",
                },
            },
        ]

    @staticmethod
    def _layout_metadata_request(layout: WorkbookLayout) -> dict[str, Any]:
        """The request that stores a workbook's Workbook Layout Order in its hidden metadata."""
        return {
            "createDeveloperMetadata": {
                "developerMetadata": {
                    "metadataKey": LAYOUT_METADATA_KEY,
                    "metadataValue": layout.to_json(),
                    "location": {"spreadsheet": True},
                    "visibility": "DOCUMENT",
                },
            },
        }

    def _batch_update(self, spreadsheet_id: str, requests: list[dict[str, Any]]) -> None:
        """Send requests as one all-or-nothing batch."""
        self._sheets.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id, body={"requests": requests},
        ).execute(num_retries=_NUM_RETRIES)

    # Errors

    @staticmethod
    @contextlib.contextmanager
    def _translate_errors() -> Iterator[None]:
        """Turn Google, sign-in, and connection errors into DataSheetStoreError (DI rule 5)."""
        try:
            yield
        except DataSheetStoreError:
            raise
        except HttpError as e:
            raise DataSheetStoreError(f"Google Drive refused the request ({e.resp.status})") from e
        except RefreshError as e:
            raise DataSheetStoreError("not signed in to Google; press Import to sign in") from e
        except OAuth2Error as e:
            raise DataSheetStoreError("Google sign-in was cancelled or refused; press Import to try again") from e
        except FileNotFoundError as e:
            raise DataSheetStoreError(f"the Google sign-in settings file was not found ({e.filename})") from e
        except (TransportError, httplib2.HttpLib2Error, OSError) as e:
            raise DataSheetStoreError("no connection to Google Drive") from e
        except GoogleAuthError as e:
            raise DataSheetStoreError("could not sign in to Google; press Import to try again") from e
