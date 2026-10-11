# Implementation Plan: Table Column Types

**Branch**: `007-table-column-types` | **Date**: 2026-10-05 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/007-table-column-types/spec.md`

## Summary

Each table column, and each Simple Form field, gets a type: **Text**, **Integer**,
**Decimal**, **True/False**, **Date**, **Choice**, or **Tally** (Tally is for columns
only). Choice and Tally options carry descriptions.

**Reading is pure and in one place.** A new `interpretation/value_types.py` owns:

- the `ColumnType` enum
- the option records `ChoiceOption` and `TallyOption`
- every reading rule, via `read_value` and `read_tally`

Interpreters call it, collect every value that doesn't fit, and raise one
`InvalidValuesError`. The sheet interpreter combines these across sections, and the
import batch reports them as a new `INVALID_VALUES` outcome naming every bad cell (R2,
R5).

**A tally is several keys.** A Tally column, or a Running Tally section, emits a
**Tally Summary** as ordinary keys: marks, a count per option, a total, and a
percentage per option. Because the Template Structure already comes from
`section_keys()`, tally option changes move sessions to a new workbook, and nothing else
does. Storage needs no tally logic. Existing Running Tally templates start a new
workbook, as the spec accepts (R3).

**Typed cells.** `CellValue` gains booleans, dates (serial number with a date format),
and percentages, and `DataSheetScalarDto` becomes a typed `NamedTuple` carrying
`typed_value` (R4, R10).

**The Workbook Key.** Interpreters expose `option_descriptions()`. Storage builds a
`Workbook Key` tab from them, found by developer metadata. Every save rebuilds it last
in the same atomic batch as the new session tab, and it's never treated as a session
(R6).

**Rules out of the UI.** Interpreters expose `config_problems()`, built from pure
helpers in `option_rules.py`. `validate_template` and the form's apply step enforce
them. Two shared Tkinter widgets do the editing (R8):

- `TypedItemEditor`: a Name and Type list, with the selected item's details below
- `OptionListEditor`: a Code and Meaning list

**Compatibility.** Serializers write new shapes and read the old ones (R7). A ticked
checkbox in a table cell is read as `✓` (R9).

## Technical Context

**Language/Version**: Python 3.12

**Primary Dependencies**: Tkinter + `sv-ttk`, `boto3` (Textract), and
`google-api-python-client`. No new dependency.

**Storage**: The local templates JSON file, with new config shapes and old ones still
read. Google Sheets workbooks, with typed cells and a Workbook Key tab.

**Testing**:

- Offline scratch-script checks of the pure modules: `value_types`, the interpreters,
  `option_rules`, the serializers, `session_layout`, and `template_structure`.
- `SheetImportBatch` with a fake store.
- `GoogleDriveDataSheetStore` with a fake Sheets service.
- Live validation per [quickstart.md](quickstart.md).
- No test framework (R11).

**Target Platform**: Desktop (Linux primary; any OS that runs Tkinter).

**Project Type**: Desktop app (single project under `therepy_sessions/`).

**Performance Goals**:

- Reading values adds microseconds per cell.
- The key tab adds 3 requests to the existing single `batchUpdate` per save, with no
  extra round trip.
- The batch's existing read gains `sheets.developerMetadata`.

**Constraints**:

- Interpretation stays pure.
- Storage never checks interpreter types.
- Old templates keep loading (interpreters rule 4).
- Templates without tallies keep the same Template Structure (SC-003).
- Every workbook write is one atomic batch.
- The key tab holds template text only, never student data.

**Scale/Scope**:

- 1 SLP; templates with a handful of sections and up to about 10 columns each.
- Code: 4 new modules and about 13 changed modules.
- Docs: 3 doc amendments plus the constitution version.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | How this plan complies | Result |
| --- | --- | --- |
| I. Student Data Privacy | No new service. Values go only to the SLP's Google Sheets, as before. Option descriptions are template text that never identifies a student (spec Assumptions); the key tab holds only them. Failure messages quote cell values from the sheet's data section and name students only by Student Key. Validation uses synthetic sheets, `ZZ`, and a test account. | ✅ Pass |
| II. Domain Language Fidelity | Code names match glossary terms: `ColumnType`, `ChoiceOption`, `TallyOption`, `TallySummary`, Workbook Key (`WORKBOOK_KEY_TAB_NAME`), and Field Type (`FIELD_TYPES`, `field_type`). The glossary gains these terms in this change, and updates Scalar Type, Template Structure, and Tally (R12). | ✅ Pass (glossary update in scope) |
| III. Layered Pipeline | Reading lives in `interpretation/` and is pure. Storage gets typed values only through `StudentDataSheet` and reads the template through `sheet.template`, using public members (`section_keys`, `option_descriptions`, `title`, `section_kind`). Collection only renders a checkbox as `✓`, assigning no meaning (R9). Rules live in `option_rules.py` and the interpreters, never in widget callbacks. `program.py` is unchanged. | ✅ Pass |
| IV. Injected External Services | No new client. The store uses its injected Sheets service, and new Sheets request bodies stay in `google_drive_data_sheet_store.py`. | ✅ Pass |
| V. Pluggable Interpreters & Templates | No new interpreter type. The three existing types each keep their four pieces, updated together. Old shapes still load (R7, SC-003). Bad values fail loudly with every cell named (R5). Section key changes are deliberate and documented (interpreters rule 8; FR-022). New base members are non-abstract with defaults, so a future type isn't forced to implement them. | ✅ Pass |
| VI. Typed Public Interfaces | Every new and changed public member is annotated. `DataSheetScalarDto` moves from an untyped `namedtuple` to a `NamedTuple`. Changed classes (`ColumnDefinition`, `FieldConfiguration`, `RunningTallyInterpreter`) get annotated per-instance attributes. | ✅ Pass |
| Tech constraints | No new dependency, so `pip_requirements.txt` and `ALL_DEPENDENCIES.md` are unchanged. JSON is still written as UTF-8 with `indent=2`. | ✅ Pass |
| Development Workflow | Offline checks use synthetic inputs, and the live checks use a test account. | ✅ Pass |

**Post-design re-check (after Phase 1)**: Still passing.

- `value_types.py` imports from `student_data_sheet.py` only, and that module never
  imports it back, so there is no cycle.
- `storage/` imports `interpretation/` records (downstream, allowed).
- The UI widgets call `option_rules` only for messages.
- The doc amendments add rules, so they are MINOR: the constitution goes 1.6.0 → 1.7.0.

## Project Structure

### Documentation (this feature)

```text
specs/007-table-column-types/
├── plan.md                       # This file
├── research.md                   # Phase 0: decisions R1–R12
├── data-model.md                 # Types, options, saved shapes, scalars, cells, key tab, structure effects
├── quickstart.md                 # Validation V1–V11
├── contracts/
│   ├── values-and-interpreters.md      # value_types, scalar DTO, interpreter members, serializers, option_rules, collection
│   └── config-import-and-storage.md    # editors, configs, form apply, INVALID_VALUES, cells, key tab
├── checklists/
│   └── requirements.md           # Spec quality checklist
└── tasks.md                      # Phase 2 (/speckit-tasks; not created here)
```

### Source Code (repository root)

```text
therepy_sessions/
├── collection/images/aws_image_collection.py        # CHANGE: ticked checkbox in a cell → "✓" (R9)
├── interpretation/
│   ├── value_types.py                               # NEW: ColumnType, FIELD_TYPES, ChoiceOption, TallyOption, TallySummary, read_value, read_tally, tally_keys/scalars, ValueProblem, InvalidValuesError, OptionDescription
│   ├── student_data_sheet.py                        # CHANGE: TypedValue; DataSheetScalarType DECIMAL, PERCENT; DataSheetScalarDto NamedTuple + typed_value; scalars typed
│   ├── templates/student_data_sheet_interpreter.py  # CHANGE: base config_problems / option_descriptions; combine InvalidValuesError across sections
│   ├── interpreter_types/
│   │   ├── table_interpreter.py                     # CHANGE: typed ColumnDefinition; typed reading; tally keys; problems; descriptions
│   │   ├── simple_form_interpreter.py               # CHANGE: typed FieldConfiguration; emits DataSheetScalarDto; problems; descriptions
│   │   └── running_tally_interpreter.py             # CHANGE: tally_options; one Tally Summary row per table; problems; descriptions
│   ├── template_manager/
│   │   ├── option_rules.py                          # NEW: pure option/name/collision rules and messages
│   │   ├── option_list_editor.py                    # NEW: OptionListEditor widget (Code | Meaning)
│   │   ├── typed_item_editor.py                     # NEW: TypedItemEditor widget (Name | Type + detail)
│   │   ├── interpreter_configs.py                   # CHANGE: three configs use the editors; describe() shows types and descriptions
│   │   ├── template_form.py                         # CHANGE: _apply_form refuses interpreters with config_problems()
│   │   ├── template_rules.py                        # CHANGE: validate_template appends config_problems()
│   │   └── storage/serialization.py                 # CHANGE: new shapes; old shapes still read
│   └── importing/sheet_import_batch.py              # CHANGE: FailureReason.INVALID_VALUES
└── storage/
    ├── session_layout.py                            # CHANGE: CellValue boolean/number_format; cell_for by type; workbook_key_rows
    ├── template_structure.py                        # CHANGE: docstring only (tally options count through keys)
    └── google_drive_data_sheet_store.py             # CHANGE: typed cell payloads; Workbook Key tab create/replace/exclude

docs/
├── conventions/architecture/interpreters.md         # AMEND: config_problems/option_descriptions in the new-type table; rule 10 (value_types, InvalidValuesError)
└── domain/glossary.md                               # AMEND: new terms; Scalar Type, Template Structure, Tally updated

.specify/memory/constitution.md                      # AMEND: Sync Impact Report, version 1.7.0
```

**Structure Decision**: This is a single desktop project under `therepy_sessions/`.

- The type and value rules sit in `interpretation/value_types.py`, beside
  `student_data_sheet.py`, because every interpreter and the serializers use them.
- Configuration rules sit in `template_manager/option_rules.py`, beside
  `template_rules.py`, so both template windows share them through `TemplateForm`.
- The two editors are UI-only modules in the same package.
- Storage changes stay in the two existing storage modules, keeping pure layout
  (`session_layout.py`) apart from the Google adapter.

## Complexity Tracking

No violations.
