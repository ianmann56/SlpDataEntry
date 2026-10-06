---

description: "Task list for the Table Column Types feature"
---

# Tasks: Table Column Types

**Input**: Design documents from `/specs/007-table-column-types/`

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md),
[data-model.md](data-model.md),
[contracts/values-and-interpreters.md](contracts/values-and-interpreters.md),
[contracts/config-import-and-storage.md](contracts/config-import-and-storage.md),
[quickstart.md](quickstart.md)

**Tests**: No automated tests. The spec doesn't ask for them. Research R11 makes
verification:

- offline scratch-script checks of the pure modules
- `SheetImportBatch` with a fake `DataSheetStore`
- `GoogleDriveDataSheetStore` with a fake Sheets service
- live checks from [quickstart.md](quickstart.md) on synthetic sheets and a test Google
  account

Scratch scripts are not committed.

**Organization**: Tasks are grouped by user story, in spec priority order.

- **US1 (P1)**: the simple column types (Text, Integer, Decimal, True/False, Date), read
  and saved as typed values.
- **US4 (P1)**: existing templates keep loading, and keep their workbooks.
- **US2 (P2)**: Choice columns with descriptions, plus the Workbook Key tab.
- **US3 (P3)**: Tally columns and the Tally Summary.
- **US5 (P3)**: Running Tally sections switch to described options and a Tally Summary.
- **US6 (P3)**: Simple Form fields get every type except Tally.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: US1–US6 from spec.md

## Path Conventions

- All code is under `therepy_sessions/`. Modules import each other by package path from
  that directory (e.g. `from interpretation.value_types import ColumnType`).
- **Types**: every public function, method, property, attribute, and `__init__` added or
  changed is fully annotated per
  [type-declarations.md](../../docs/conventions/architecture/type-declarations.md).
  Mutable attributes are created in `__init__`, never at class level (interpreters rule 3).
- **One-way imports**:
  - `interpretation/value_types.py` imports from `interpretation/student_data_sheet.py`,
    and never the reverse.
  - `interpretation/` never imports `storage/`, `clients/`, or `google*`.
  - `storage/` never checks interpreter types: it uses only `title`, `section_kind`,
    `section_keys()`, and `option_descriptions()`.
- **Rules out of widgets**: every rule message comes from `option_rules.py` or an
  interpreter's `config_problems()`. The widgets only display those messages (layers
  rule 5).
- **Privacy**: offline and live checks use only synthetic data and the made-up Student
  Key `ZZ`.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Record the "before" state, so compatibility can be proven later.

- [ ] T001 Copy the current templates JSON file to `/tmp/templates-before-007.json`, and copy the students JSON file to `/tmp/students-before-007.json`. Confirm the templates copy contains at least one TableInterpreter, one RunningTallyInterpreter, and one SimpleFormInterpreter. If it doesn't, launch the unchanged app on the copies only (`python3 therepy_sessions/program.py /tmp/templates-before-007.json /tmp/students-before-007.json`) and add synthetic ones there, so every old shape is represented without touching the real templates file (quickstart Prerequisites)
- [ ] T002 With the code unchanged, run a scratch script from `therepy_sessions/` that loads `/tmp/templates-before-007.json` through `interpretation/template_store.py` and prints each template's `storage.template_structure.shape_of(t).structure_fingerprint()`. Save the output to `/tmp/fingerprints-before-007.txt` for T023

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Typed values, value reading, failure reporting, typed cells, setup rules, and
the shared editors that every story builds on.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [ ] T003 In `therepy_sessions/interpretation/student_data_sheet.py`:
  - add `TypedValue = int | float | bool | date | str | None`
  - add `DECIMAL = 'decimal'` and `PERCENT = 'percent'` to `DataSheetScalarType`
  - replace the untyped `namedtuple` `DataSheetScalarDto` with a `NamedTuple` (`key: str`, `value: str`, `type: DataSheetScalarType`, `choice_options: list[str] | None = None`, `typed_value: TypedValue = None`), keeping the docstring
  - narrow `StudentDataSheet._scalars`, `scalars`, and `register_scalar` to `DataSheetScalarDto` only
  - update `debug()` so it still prints scalars

  (research R10, contracts/values-and-interpreters.md)
- [ ] T004 Create `therepy_sessions/interpretation/value_types.py` (pure, no I/O). Define:
  - `ColumnType` (`TEXT`, `INT`, `DECIMAL`, `BOOLEAN`, `DATE`, `CHOICE`, `TALLY`)
  - `FIELD_TYPES` (all but `TALLY`)
  - `COLUMN_TYPE_LABELS` (Text, Integer, Decimal, True/False, Date, Choice, Tally)
  - `has_options(column_type) -> bool`
  - the `NamedTuple`s `ChoiceOption(value, description="")` and `TallyOption(mark, description="")`
  - `ValueReadError(ValueError)` with `expected: str` and `found: str = ""` (the offending part of the text; empty means the whole text)
  - `ValueProblem(section, item, row, value, expected)`, with a `message()` that renders e.g. `"Words", column "Trials", row 3: "l" is not a whole number`; empty `item`/`row` parts are omitted, and `section` is always shown quoted (it holds a title or the interpreter's fallback name, e.g. `"Table"`)
  - `InvalidValuesError(ValueError)` holding `problems: list[ValueProblem]`, whose `str()` joins the messages with `"; "`
  - `OptionDescription(section, item, item_type, option, description)`
  - `scalar_type_for(column_type) -> DataSheetScalarType` (TEXT→TEXT, INT→INT, DECIMAL→DECIMAL, BOOLEAN→BOOLEAN, DATE→DATE, CHOICE→CHOICE; raise `ValueError` for TALLY)
  - `read_value(column_type, text, choices=()) -> TypedValue`, implementing every non-Tally row of research R2:
    - blank → `None`
    - Text returned unchanged
    - every other type trimmed first
    - Integer accepts `[+-]?\d+` optionally followed by `.0+`
    - Decimal accepts `3`, `2.5`, `.5`, with a sign
    - True/False, case-insensitive: true from `y yes t true 1 ✓ ✔ ☑`, false from `n no f false 0`, so `X` is rejected
    - Date accepts `M/D/YYYY`, `M/D/YY`, `M-D-YYYY`, `M-D-YY`, with two-digit years expanded by hand to `2000+YY`, and impossible dates rejected
    - Choice matches ignoring case and surrounding spaces, and returns the configured value
    - TALLY raises `ValueError`
    - on a mismatch, raise `ValueReadError` with an `expected` phrase such as `"a whole number"`, `"a number"`, `"yes or no (Y, N, ✓, …)"`, `"a date (month/day/year)"`, `"one of +, -, P"`
- [ ] T005 In `therepy_sessions/interpretation/templates/student_data_sheet_interpreter.py`:
  - add the non-abstract `config_problems(self) -> list[str]` (returns `[]`) and `option_descriptions(self) -> list[OptionDescription]` (returns `[]`) to `SessionDataSectionInterpreterBase`, with docstrings saying they feed `validate_template` and the Workbook Key
  - in `StudentDataSheetInterpreter.interpret_student_data_sheet`, wrap each section's `interpret_student_data_sheet_content` call: catch `InvalidValuesError`, keep its problems, and continue with the next section
  - after the loop, if any problems were kept, raise one `InvalidValuesError` holding all of them in section order
  - let every other exception propagate at once, as today (research R5)
- [ ] T006 [P] In `therepy_sessions/interpretation/importing/sheet_import_batch.py`:
  - add `FailureReason.INVALID_VALUES = "invalid_values"`, with the `_FAILURE_MESSAGES` entry `'Some values on the sheet don\'t fit template "{template_name}": {detail}. Fix the template, or retake the photo.'`
  - in `_interpret`, add `except InvalidValuesError as e:` before the generic `except Exception`, raising `_SheetFailed(FailureReason.INVALID_VALUES, student_key=..., template_name=template.name, detail=str(e))` (contracts/config-import-and-storage.md)
- [ ] T007 [P] In `therepy_sessions/storage/session_layout.py`:
  - add `CellNumberFormat(Enum)` (`DATE`, `PERCENT`)
  - extend `CellValue` to `text`, `number: int | float | None`, `boolean: bool | None = None`, `number_format: CellNumberFormat | None = None`
  - replace `CellKind` / `CELL_KIND_BY_TYPE` so INT and DECIMAL → number, BOOLEAN → boolean, DATE → number of days since 1899-12-30 with `DATE`, PERCENT → the fraction with `PERCENT`, and TEXT and CHOICE → text
  - rewrite `cell_for` per research R4:
    - `None`/blank → `EMPTY_CELL`
    - `str` → text
    - a scalar whose `typed_value is None` with non-blank `value` → text
    - otherwise, by type from `typed_value`
  - update the docstring (the old "only INT becomes a number" note goes)
- [ ] T008 In `therepy_sessions/storage/google_drive_data_sheet_store.py` (depends on T007):
  - `_cell_payload` writes `{"userEnteredValue": {"boolValue": ...}}` for `boolean`, `numberValue` for `number`, and adds `"userEnteredFormat": {"numberFormat": {"type": "DATE", "pattern": "m/d/yyyy"}}` or `{"type": "PERCENT", "pattern": "0%"}` when `number_format` is set
  - `_add_tab_requests` uses `"fields": "userEnteredValue,userEnteredFormat.numberFormat"`
- [ ] T009 [P] Create `therepy_sessions/interpretation/template_manager/option_rules.py` (pure). Define:
  - `name_problems(kind: str, names: Sequence[str]) -> list[str]`: blank names, and names duplicated ignoring case and surrounding spaces; e.g. `Column names must not be blank.` and `The column name "Trials" is used more than once.`
  - `option_problems(item: str, column_type: ColumnType, values: Sequence[str]) -> list[str]`, for CHOICE and TALLY:
    - at least one option, e.g. `Column "Accuracy" needs at least one choice.` / `… at least one tally option.`
    - no blank value
    - no duplicates ignoring case and surrounding spaces, naming the duplicate
    - for TALLY, every value exactly one character
  - `check_new_option(column_type: ColumnType, value: str, existing: Sequence[str]) -> str | None`: the single message for adding one option (blank, too long for a tally mark, or duplicate), or `None`

  The `kind` and `item` wording must work for both columns and fields (contracts/values-and-interpreters.md).
- [ ] T010 In `therepy_sessions/interpretation/template_manager/template_rules.py`, make `validate_template` append every interpreter's `config_problems()` after the existing checks, in template order (FR-005). In `therepy_sessions/interpretation/template_manager/template_form.py`, make `_apply_form` call `config_problems()` on the interpreter it builds; if there are any, show them with `messagebox.showerror("Fix the Section", "\n".join(problems), parent=...)` and return `False` without changing the draft, like a duplicate title
- [ ] T011 [P] Create `therepy_sessions/interpretation/template_manager/option_list_editor.py` with `OptionListEditor(parent, mode: ColumnType)`:
  - a `ttk.Treeview` with the columns **Code** and **Meaning**
  - code and meaning `ttk.Entry`s
  - the buttons **Add**, **Update** (replaces the selected row), **Remove**, **Up**, and **Down**
  - selecting a row fills the entries
  - Add and Update call `option_rules.check_new_option` (ignoring the row being updated) and show its message with `messagebox.showwarning` instead of changing the list
  - public: `frame`, `get() -> list[tuple[str, str]]`, `set(options)`, `set_mode(mode)` (the code column header reads "Choice" or "Mark"), `set_read_only(read_only)`
  - no rules of its own (contracts/config-import-and-storage.md)
- [ ] T012 Create `therepy_sessions/interpretation/template_manager/typed_item_editor.py` with `TypedItem(NamedTuple)` (`name: str`, `item_type: ColumnType`, `options: list[tuple[str, str]]`) and `TypedItemEditor(parent, item_label: str, allowed_types: Sequence[ColumnType])` (depends on T011):
  - the top is a `ttk.Treeview` with the columns **Name** and **Type** (labels from `COLUMN_TYPE_LABELS`), and **Add {item_label}**, **Remove**, **Up**, and **Down**
  - the bottom is the selected item's detail: a name entry, a read-only `ttk.Combobox` type picker over `allowed_types` (Text first and the default for new items), and an `OptionListEditor` shown only when `has_options(type)`, with its mode set to the type
  - edits to the detail update the selected row immediately
  - changing the type away from Choice or Tally while options exist asks `messagebox.askyesno` to confirm discarding N options; on yes it clears them, and on no it restores the previous type
  - public: `frame`, `get() -> list[TypedItem]`, `set(items)`, `reset()`, `set_allowed_types(types)`
- [ ] T013 Offline check (scratch script, not committed): run the non-Tally rows of quickstart V1 against `value_types.read_value`, and confirm that: (scenarios in `specs/007-table-column-types/quickstart.md`)
  - `InvalidValuesError` message joining works
  - `cell_for` gives the expected `CellValue` for INT, DECIMAL, BOOLEAN, DATE (2026-10-03 → 46298 with `DATE`), PERCENT, TEXT, and CHOICE scalars, and for a raw `str`
  - `option_rules` returns the expected messages for blank, duplicate, and long-mark cases

**Checkpoint**: The foundation is ready. The app still runs: existing interpreters emit
TEXT scalars as before.

---

## Phase 3: User Story 1 - Give each table column a type (Priority: P1) 🎯 MVP

**Goal**: A table column can be Text, Integer, Decimal, True/False, or Date. Its cells are
read as that type, a bad value fails the sheet naming every bad cell, and the workbook
holds native numbers, booleans, and dates.

**Independent Test**: Create a template with a table section of Text, Integer, Decimal,
True/False, and Date columns. Import a valid synthetic sheet and check that the workbook
holds typed values. Import a sheet with `l` in the Integer column and check that it
fails, naming the cell (quickstart V7, V8, V9 for these types).

### Implementation for User Story 1

- [ ] T014 [US1] Rewrite `ColumnDefinition` in `therepy_sessions/interpretation/interpreter_types/table_interpreter.py`:
  - `__init__(self, column_name: str, column_type: ColumnType = ColumnType.TEXT, choices: list[ChoiceOption] | None = None, tally_options: list[TallyOption] | None = None)`, storing per-instance lists
  - annotated properties `column_name`, `column_type`, `choices`, `tally_options`, and the read-only `column_choices -> list[str]` (the choice values)
  - `to_json()` returns the new saved shape `{"column_name", "column_type": <member name>, "options": [{"value", "description"}]}` (options are the choices for CHOICE, the tally options as `value` for TALLY, `[]` otherwise)

  (data-model.md)
- [ ] T015 [US1] In `TableInterpreter` in `therepy_sessions/interpretation/interpreter_types/table_interpreter.py` (depends on T014):
  - remove the unused `import ipdb`
  - in `_interpret_single_student_data_sheet_table`, keep the missing-column check by column name (FR-013), then read each non-Tally cell with `read_value(column.column_type, cell_text, column.choices)`
  - build `DataSheetScalarDto(column_name, cell_text, scalar_type_for(column.column_type), column.column_choices or None, typed_value)`
  - catch `ValueReadError` per cell and record `ValueProblem(section=self.title or "Table", item=column_name, row=..., value=cell_text, expected=e.expected)`, where `row` is `f"row {n}"` (1-based data row), or `f"table {t}, row {n}"` when this section received more than one table
  - after every table is read, raise one `InvalidValuesError` if any problems were found
  - override `config_problems()` to return `option_rules.name_problems("column", [c.column_name for c in self.columns])`
- [ ] T016 [US1] In `TableInterpreterSerializer` in `therepy_sessions/interpretation/template_manager/storage/serialization.py` (depends on T014):
  - `serialize` writes `column.to_json()` for each column
  - `deserialize` reads each column:
    - `column_type` by member name, defaulting to `CHOICE` when it's absent and `column_choices` is non-empty, otherwise `TEXT`; an unknown name loads as `TEXT`
    - options from `"options"` (`value`/`description`), or else from the old `column_choices` strings with blank descriptions
    - options go to `choices` for CHOICE and to `tally_options` (as `TallyOption(value, description)`) for TALLY

  (research R7, FR-006, FR-018)
- [ ] T017 [US1] Rewrite `TableInterpreterConfig` in `therepy_sessions/interpretation/template_manager/interpreter_configs.py` (depends on T012, T014):
  - the form is the title entry plus `TypedItemEditor(frame, "Column", [TEXT, INT, DECIMAL, BOOLEAN, DATE])`
  - `get_config()` returns `{"title", "columns": editor.get()}`
  - `reset()` clears both
  - `load(interpreter)` sets the title and `editor.set([TypedItem(c.column_name, c.column_type, <options as (value, description)>) …])`
  - `construct_interpreter` builds `ColumnDefinition`s from the items (CHOICE options → `ChoiceOption`, TALLY → `TallyOption`)
  - `describe()` returns one line per column, `"{name} — {label}"`
  - delete this class's now-unused `_add_config_item` / `_remove_config_item`
- [ ] T018 [P] [US1] In `therepy_sessions/collection/images/aws_image_collection.py`, `_get_cell_text`: also handle `SELECTION_ELEMENT` children of the cell's `CHILD` relationship, appending `✓ ` when `SelectionStatus == "SELECTED"` and nothing when `NOT_SELECTED`. Word handling is unchanged (research R9)
- [ ] T019 [US1] Offline check (scratch, not committed): quickstart V2 for the Text, Integer, Decimal, True/False, and Date columns. A synthetic `StudentDataSheetImport` with bad values in two rows gives one `InvalidValuesError` naming both cells. A valid one gives typed scalars, and `session_layout.session_rows` gives numeric, boolean, and date `CellValue`s. Also check that a `TableInterpreter` serializes and deserializes back to equal columns and types, and that `SheetImportBatch` with a fake store turns the bad sheet into `FAILED` / `INVALID_VALUES` with the full message (scenarios in `specs/007-table-column-types/quickstart.md`)
- [ ] T020 [US1] Live check, quickstart V7 (simple types only), V8 (Trials, Score, Done, When), and V9, with a test Google account and synthetic `ZZ` sheets. Include a synthetic sheet whose True/False column uses printed checkboxes, to confirm T018 (scenarios in `specs/007-table-column-types/quickstart.md`)

**Checkpoint**: US1 is fully functional. Typed simple columns can be set up, read, and
saved, and bad values fail with every cell named. US1 acceptance scenario 1 ("one of the
seven column types") is fully met once US2 adds Choice (T026) and US3 adds Tally (T034).

---

## Phase 4: User Story 4 - Existing templates keep working (Priority: P1)

**Goal**: Templates saved before this feature load without edits, columns without a type
are Text (or Choice when they had choices), and table-only templates keep the same
Template Structure, so they keep using the same workbook.

**Independent Test**: Load `/tmp/templates-before-007.json`, confirm the column types and
fingerprints, and import into an existing workbook (quickstart V5, V10).

### Implementation for User Story 4

- [ ] T021 [P] [US4] Update the module docstring of `therepy_sessions/storage/template_structure.py`: value types, choices, and descriptions are not part of the Template Structure, but Tally options are, through the Tally-derived keys in `section_keys()` (research R3). Do not change `_FINGERPRINT_VERSION`
- [ ] T022 [US4] Offline check (scratch, not committed): load `/tmp/templates-before-007.json` with the new code. Every old table column comes out `TEXT`, or `CHOICE` with blank descriptions when it had `column_choices`. Serializing and reloading gives the same result (US4 scenarios 1–3)
- [ ] T023 [US4] Offline check (scratch, not committed): print the structure fingerprints of the templates in `/tmp/templates-before-007.json` with the new code, and diff them against `/tmp/fingerprints-before-007.txt` (T002). Every template without a Running Tally section must match (SC-003). Running Tally templates are expected to differ only after US5
- [ ] T024 [US4] Live check, quickstart V10 first bullet: an old table-only template imports into its existing workbook, with values as before (scenarios in `specs/007-table-column-types/quickstart.md`)

**Checkpoint**: US1 and US4 together are a safe, shippable MVP.

---

## Phase 5: User Story 2 - Choice columns with described choices (Priority: P2)

**Goal**: Choice columns have choices with descriptions, validated on setup and on import.
Every workbook gets a Workbook Key tab listing every code and its meaning.

**Independent Test**: Create a Choice column `+` correct, `-` incorrect, `P` with prompt.
View it, import a sheet using `p` and `X`, and check the workbook and its Workbook Key
(quickstart V4, V6, V7, V8, V11).

### Implementation for User Story 2

- [ ] T025 [US2] In `TableInterpreter` in `therepy_sessions/interpretation/interpreter_types/table_interpreter.py`:
  - extend `config_problems()` with `option_rules.option_problems(column.column_name, CHOICE, [o.value for o in column.choices])` for each CHOICE column
  - override `option_descriptions()` to return an `OptionDescription(self.title or "Table", column.column_name, "Choice", o.value, o.description)` for each choice of each CHOICE column, in column order then option order
- [ ] T026 [US2] In `TableInterpreterConfig` in `therepy_sessions/interpretation/template_manager/interpreter_configs.py`:
  - add `ColumnType.CHOICE` to the editor's allowed types
  - make `describe()` render Choice columns as `"{name} — Choice: + (correct), - (incorrect), P"`; a choice without a description shows just its value
- [ ] T027 [P] [US2] In `therepy_sessions/storage/session_layout.py`, add `WORKBOOK_KEY_TAB_NAME: str = "Workbook Key"` and `workbook_key_rows(template: StudentDataSheetTemplate) -> list[list[CellValue]]`:
  - a header row `Section | Column or Field | Type | Code | Meaning`
  - then one text row per `OptionDescription` from each interpreter's `option_descriptions()`, in template order
  - if there are none, a single row `This template has no choice or tally codes to explain.`

  It uses no interpreter type checks (FR-024).
- [ ] T028 [US2] In `therepy_sessions/storage/google_drive_data_sheet_store.py`, add the Workbook Key (depends on T027; research R6, contracts/config-import-and-storage.md):
  - `KEY_TAB_METADATA_KEY: str = "slpWorkbookKey"`
  - `_key_tab_requests(sheet_id, title, index, rows)`: the `_add_tab_requests` requests plus `createDeveloperMetadata` with `location: {"sheetId": sheet_id}` and `visibility: "DOCUMENT"`
  - in `_create_workbook`, add the key tab at index 1 in the same batch
  - in `_add_to_workbook`:
    - request `sheets(properties(sheetId,title,index),developerMetadata)` too
    - find the key tab's sheet id by metadata
    - remove it from `tabs` before computing tab tops, duplicates, empty tabs, and `insert_index`
    - in the same batch as the new session tab, `deleteSheet` the old key tab (if any) and add a new key tab at the last index, named `unique_tab_name(WORKBOOK_KEY_TAB_NAME, <other tab titles>)`
    - when the session is already saved, write nothing

  Keep one `batchUpdate` per save (FR-024, FR-025).
- [ ] T029 [US2] Offline check (scratch, not committed): quickstart V4 (Choice cases) and V6 (`workbook_key_rows` with and without options, and fingerprints unchanged after a description edit). With an in-memory fake Sheets/Drive service, check that: (scenarios in `specs/007-table-column-types/quickstart.md`)
  - creating a workbook adds the session tab, then `Workbook Key` with `slpWorkbookKey` metadata
  - a second save inserts the new session tab before the key tab, and deletes and re-adds the key tab in the same batch
  - an already-saved session writes nothing
  - the key tab is never returned as a duplicate or removed as empty
- [ ] T030 [US2] Live check: quickstart V7 (Accuracy and its descriptions in view mode, plus the empty-choices refusal), V8 (Accuracy and the Workbook Key), V9 (`X` in Accuracy), V10 third bullet (an old workbook gets a key), and V11 first bullet (a description edit keeps the workbook and updates the key) (scenarios in `specs/007-table-column-types/quickstart.md`)

**Checkpoint**: US2 works on its own on top of US1.

---

## Phase 6: User Story 3 - Tally columns with described tally options (Priority: P3)

**Goal**: A Tally column reads the marks in each cell and saves a Tally Summary (marks,
a count per option, a total, a percentage per option), with option changes starting a
new workbook.

**Independent Test**: Create a Tally column `Y` yes, `N` no, `P` prompted. Import rows
`YYN`, `PNY`, and blank, and check the summary columns and the Workbook Key (quickstart
V1, V2, V4, V8, V11).

### Implementation for User Story 3

- [ ] T031 [P] [US3] In `therepy_sessions/interpretation/value_types.py`, add:
  - `TallySummary(NamedTuple)` (`marks`, `counts`, `total`, `percentages`)
  - `read_tally(text, options) -> TallySummary`:
    - blank text gives marks `""`, zero counts, total 0, and `None` percentages
    - spaces are removed, each character is matched to an option mark ignoring case, and the configured mark is recorded
    - a non-option character raises `ValueReadError(f"only the marks {', '.join(marks)}", found=<that character, as read>)`
  - `tally_keys(base, options) -> list[str]`: `base`, `f"{base} {mark}"`…, `f"{base} Total"`, `f"{base} {mark} %"`…
  - `tally_scalars(base, summary, options) -> dict[str, DataSheetScalarDto]`: marks as TEXT, counts and total as INT, and percentages as PERCENT whose `typed_value` is the fraction or `None`, with `value` the formatted text

  (research R3, data-model.md)
- [ ] T032 [P] [US3] In `therepy_sessions/interpretation/template_manager/option_rules.py`, add `tally_key_collisions(columns: Sequence[ColumnDefinition]) -> list[str]`: for each TALLY column, every key from `tally_keys` other than the column's own name that equals another column's name (ignoring case and surrounding spaces) gives e.g. `The column "Attempts Y" has the same name as a count column of tally "Attempts". Rename one of them.`
- [ ] T033 [US3] In `TableInterpreter` in `therepy_sessions/interpretation/interpreter_types/table_interpreter.py` (depends on T031, T032):
  - `section_keys()` returns `tally_keys(name, options)` in place of the name for TALLY columns, in column order
  - when reading, a TALLY cell goes through `read_tally`, and its `tally_scalars` are merged into the row in key order; a `ValueReadError` is recorded as a `ValueProblem` like any other cell
  - the returned `"columns"` for the table stays the `ColumnDefinition` list
  - `config_problems()` adds `option_problems(name, TALLY, marks)` for TALLY columns and `tally_key_collisions(self.columns)`
  - `option_descriptions()` also returns one `"Tally"` entry per tally option of each TALLY column
- [ ] T034 [US3] In `TableInterpreterConfig` in `therepy_sessions/interpretation/template_manager/interpreter_configs.py`, add `ColumnType.TALLY` to the allowed types, and have `describe()` render Tally columns as `"{name} — Tally: Y (yes), N (no), P (prompted)"`
- [ ] T035 [US3] Offline check (scratch, not committed): the Tally rows of quickstart V1, V2 with an Attempts Tally column (8 keys in order, `YyN P` → `YYNP` / 2,1,1 / 4 / 0.5,0.25,0.25, and a blank row → 0s with `None` percentages), the V4 tally-mark and collision cases, and V6 (the fingerprint changes after adding a tally option, or after switching a column to or from Tally) (scenarios in `specs/007-table-column-types/quickstart.md`)
- [ ] T036 [US3] Live check: quickstart V7 (Attempts and the `YY` refusal), V8 (the Attempts summary columns, percentages formatted, and Tally rows in the Workbook Key), and V11 second bullet (adding option `X` starts a new workbook) (scenarios in `specs/007-table-column-types/quickstart.md`)

**Checkpoint**: US3 works on top of US1 (and shows in the Workbook Key once US2 is in).

---

## Phase 7: User Story 5 - Running Tally sections get described options and counts (Priority: P3)

**Goal**: A Running Tally section has tally options with descriptions, and saves one
Tally Summary row per table instead of one row per mark. Old Running Tally templates
load, and start a new workbook.

**Independent Test**: A Running Tally section `Y N P` reading the grid `Y Y N / P Y`
saves `YYNPY`, 3/1/1, 5, 60/20/20% (quickstart V3, V5, V10).

### Implementation for User Story 5

- [ ] T037 [US5] Rewrite `RunningTallyInterpreter` in `therepy_sessions/interpretation/interpreter_types/running_tally_interpreter.py` (depends on T031):
  - `__init__(self, id: str, title: str, tally_options: list[TallyOption])`, with no class-level attributes
  - the annotated `tally_options` property, and the read-only `tally_choice_options -> list[str]` (the marks)
  - `section_keys()` returns `tally_keys(TALLY_COLUMN_NAME, options)`
  - each table is read by concatenating every cell's text in row-major order (as today, without the `print`) and passing it to `read_tally`
  - each table emits one row, `tally_scalars(TALLY_COLUMN_NAME, summary, options)`, with `"columns"` equal to the key list
  - a `ValueReadError` becomes `ValueProblem(section=self.title or "Running Tally", item="", row=<"" or "table N">, value=e.found, expected=...)`, so the message names the bad mark read (FR-021, US5 scenario 3), raised as `InvalidValuesError` after every table
  - `config_problems()` returns `option_problems("Running Tally", TALLY, marks)`
  - `option_descriptions()` returns one `OptionDescription(title, "", "Tally", mark, description)` per option
- [ ] T038 [US5] In `RunningTallyInterpreterSerializer` in `therepy_sessions/interpretation/template_manager/storage/serialization.py`, `serialize` writes `{"tally_options": [{"mark", "description"}]}`. `deserialize` reads `tally_options`, or else the old `tally_choice_options` strings with blank descriptions, ignoring `tally_type` (research R7, FR-023)
- [ ] T039 [US5] Rewrite `RunningTallyInterpreterConfig` in `therepy_sessions/interpretation/template_manager/interpreter_configs.py`:
  - the form is the title entry plus `OptionListEditor(frame, ColumnType.TALLY)` under the label "Tally Options:"
  - `get_config()` returns `{"title", "tally_options": editor.get()}`
  - `load()` fills from `interpreter.tally_options`
  - `construct_interpreter` builds `[TallyOption(mark, description) …]`
  - `describe()` returns `"Tally options: Y (yes), N (no), P (prompted)"`
  - delete the unused listbox helpers
- [ ] T040 [US5] Offline check (scratch, not committed): quickstart V3, the V5 Running Tally part (old `tally_choice_options` loads as options with blank descriptions and round-trips in the new shape), and a fingerprint diff against `/tmp/fingerprints-before-007.txt` showing that only Running Tally templates changed (FR-022)
- [ ] T041 [US5] Live check: quickstart V10 second bullet (an old Running Tally template starts a new workbook, and the old workbook is untouched), and V8's Running Tally block and its Workbook Key rows (scenarios in `specs/007-table-column-types/quickstart.md`)

**Checkpoint**: US5 works on top of US3's tally reading.

---

## Phase 8: User Story 6 - Simple Form fields get types (Priority: P3)

**Goal**: Simple Form fields can be Text, Integer, Decimal, True/False, Date, or Choice,
read and saved like table columns, with old fields loading as Text.

**Independent Test**: A form section with Integer, Date, True/False, and Choice fields
saves typed values, and `abc` in the Integer field fails the sheet naming the field
(spec US6).

### Implementation for User Story 6

- [ ] T042 [US6] Rewrite `FieldConfiguration` and `SimpleFormInterpreter` in `therepy_sessions/interpretation/interpreter_types/simple_form_interpreter.py`:
  - `FieldConfiguration.__init__(self, name: str, field_type: ColumnType = ColumnType.TEXT, choices: list[ChoiceOption] | None = None)`, with annotated `name`, `field_type`, and `choices`, plus the read-only `fieldType` alias; no class-level attributes
  - `interpret_student_data_sheet_content` reads each configured field present in `form_data` with `read_value(field_type, text, choices)` and emits `DataSheetScalarDto(name, text, scalar_type_for(field_type), choice values or None, typed_value)`
  - a `ValueReadError` becomes `ValueProblem(section=self.title or "Form", item=name, row="", value=text, expected=...)`, collected and raised once as `InvalidValuesError`
  - `config_problems()` returns `name_problems("field", names)`, a problem for any `field_type` not in `FIELD_TYPES`, and `option_problems` for Choice fields
  - `option_descriptions()` returns a `"Choice"` entry per choice of each Choice field

  The `item` wording in messages says "field" (FR-026 to FR-029).
- [ ] T043 [US6] In `SimpleFormInterpreterSerializer` in `therepy_sessions/interpretation/template_manager/storage/serialization.py`:
  - `serialize` writes `{"name", "fieldType": <member name>, "options": [{"value", "description"}]}`
  - `deserialize` maps `fieldType` by `ColumnType` member name; `null`, unknown, or `TALLY` → `TEXT`; options come from `"options"`, defaulting to `[]` (research R7, FR-019)
- [ ] T044 [US6] Rewrite `SimpleFormInterpreterConfig` in `therepy_sessions/interpretation/template_manager/interpreter_configs.py`:
  - the form is the title plus `TypedItemEditor(frame, "Field", FIELD_TYPES)`
  - `get_config()` returns `{"title", "fields": editor.get()}`
  - `load()` maps fields to `TypedItem`s in order
  - `construct_interpreter` builds an ordered `dict[str, FieldConfiguration]`
  - `describe()` returns one `"{name} — {label}"` line per field (Choice fields list their choices with descriptions)
  - delete the unused listbox helpers, and the `DataSheetScalarType` import if it's no longer used
- [ ] T045 [US6] Offline check (scratch, not committed): spec US6's Independent Test with a synthetic Import, the V5 Simple Form part (old `fieldType: "TEXT"`/`null` loads as Text and round-trips), and that `session_rows` writes the typed form values in the field list (scenarios in `specs/007-table-column-types/quickstart.md`)
- [ ] T046 [US6] Live check: spec US6 acceptance scenarios 1–5 with a test account and synthetic `ZZ` sheets (scenarios in `specs/007-table-column-types/quickstart.md`)

**Checkpoint**: Every user story is complete.

---

## Phase 9: Polish & Cross-Cutting Concerns

- [ ] T047 [P] Update `docs/domain/glossary.md` (research R12):
  - add **Column Definition** (`ColumnDefinition`), **Column Type** (`ColumnType`), **Field Configuration** (`FieldConfiguration`), **Field Type** (`FIELD_TYPES`), **Choice Option** (`ChoiceOption`), **Tally Option** (`TallyOption`), **Tally Summary** (`TallySummary`), and **Workbook Key** (`WORKBOOK_KEY_TAB_NAME`)
  - update **Scalar** / **Scalar Type** to add `DECIMAL`, `PERCENT`, and the Scalar's Typed Value (`typed_value`)
  - update **Template Structure** to say that Tally options count through their keys
  - update **Tally** to mention Tally columns and the Tally Summary
- [ ] T048 [P] Update `docs/conventions/architecture/interpreters.md`:
  - in the "Adding a new interpreter type" Interpreter row, mention the optional `config_problems()` and `option_descriptions()`
  - add rule 10: values are read through `interpretation/value_types.py`, and every bad value in a section is collected into one `InvalidValuesError`, never skipped (FR-012)
  - note under rule 8 that Tally options feed the section keys
- [ ] T049 Amend `.specify/memory/constitution.md`: add a Sync Impact Report for 1.6.0 → 1.7.0 (MINOR: new rule in interpreters.md and glossary additions), move the 1.6.0 report under "Prior history", and set **Version** 1.7.0 and **Last Amended** to the change date
- [ ] T050 Run a grep sweep under `therepy_sessions/`:
  - no `import ipdb` left in the files touched
  - `interpretation/` has no `storage`/`clients`/`google` imports
  - `storage/` has no `isinstance(` checks on interpreter classes
  - no class-level mutable attributes remain in the three interpreter modules
  - every new public member is annotated (Principle VI)
- [ ] T051 Run the full quickstart (V1–V11) end to end on the finished branch, and record any failure as a new task before merging. Time V7 with every column type and the descriptions, and confirm it takes under 5 minutes (SC-001). Confirm that no real student artifact or token file is staged (`git status`) (scenarios in `specs/007-table-column-types/quickstart.md`)
- [ ] T052 [P] Commit synthetic sample Imports under `therepy_sessions/sample_data/007/`, as JSON files each holding a `StudentDataSheetImport`'s `form_data`, `tables`, and `table_titles`: a valid sheet covering every column type, a Running Tally grid, a Simple Form section, and a sheet with bad values (quickstart V2, V3, V9). Use only made-up values and the Student Key `ZZ`, never a real student's sheet (Principle I, constitution Development Workflow). Add a short `README.md` there saying what each file checks

---

## Dependencies & Execution Order

### Phase dependencies

- **Setup (Phase 1)**: none. It must run on the unchanged code (T002 records the
  "before" fingerprints).
- **Foundational (Phase 2)**: depends on Setup and blocks every story.
  - T003 → T004 → T005.
  - T006, T007, T009, and T011 can run in parallel once T004 exists.
  - T008 depends on T007, T012 on T011, and T010 on T009.
- **US1 (Phase 3)**: depends on Foundational.
- **US4 (Phase 4)**: depends on US1's T014 and T016 (the table serializer).
- **US2 (Phase 5)**: depends on US1 (TableInterpreter and its config).
- **US3 (Phase 6)**: depends on US1. It shows in the Workbook Key once US2 is done.
- **US5 (Phase 7)**: depends on US3's T031 (`read_tally`, `tally_keys`, `tally_scalars`).
- **US6 (Phase 8)**: depends on Foundational only, and can run beside US1–US5 (different
  interpreter, serializer class, and config class, though the same files as other
  stories, so coordinate edits).
- **Polish (Phase 9)**: after the stories you're shipping.

### User story dependencies

- US1 is the base. US4 verifies it with old files.
- US2 and US3 each build on US1's `TableInterpreter` and can follow in either order.
- US5 needs US3's tally functions.
- US6 is independent of US1–US5 apart from shared files.

### Parallel opportunities

- Foundational: T006, T007, T009, and T011 (all different files).
- US1: T018 (collection) beside T014–T017.
- US2: T027 (session_layout) beside T025–T026.
- US3: T031 (value_types) and T032 (option_rules) together.
- Polish: T047, T048, and T052.
- `serialization.py` and `interpreter_configs.py` hold one class per interpreter, so
  tasks on different classes can be done by different people, but they must be merged
  with care.

## Parallel Example: Foundational

```text
Task: "T006 FailureReason.INVALID_VALUES in interpretation/importing/sheet_import_batch.py"
Task: "T007 CellValue/cell_for typed cells in storage/session_layout.py"
Task: "T009 option_rules.py name/option rules"
Task: "T011 OptionListEditor in template_manager/option_list_editor.py"
```

## Parallel Example: User Story 3

```text
Task: "T031 read_tally / tally_keys / tally_scalars in interpretation/value_types.py"
Task: "T032 tally_key_collisions in template_manager/option_rules.py"
```

## Implementation Strategy

### MVP first (User Stories 1 + 4)

1. Phase 1 Setup, recorded on the unchanged code.
2. Phase 2 Foundational.
3. Phase 3 US1. Validate with T019 and T020.
4. Phase 4 US4. Validate that old templates and workbooks are unaffected.
5. **Stop and validate**: typed simple columns are saved as native values, and nothing
   existing broke. This is shippable.

### Incremental delivery

1. Add US2: Choice columns and the Workbook Key.
2. Add US3: Tally columns.
3. Add US5: Running Tally. Its existing templates start new workbooks, so ship it
   deliberately.
4. Add US6: Simple Form field types.
5. Polish: docs, constitution, sweep, and a full quickstart run.

Each step leaves the app working, with older templates loading.
