# Implementation Plan: Nullable Field Values

**Branch**: `008-nullable-field-values` | **Date**: 2026-10-11 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/008-nullable-field-values/spec.md`

## Summary

A value that doesn't fit its type no longer fails the sheet. Blank values already import
as empty (007). This feature extends the same idea to what the SLP writes. Each such
value is saved, the sheet succeeds, and the Import window warns about every one.

**Reading.** `value_types.read_value` stays the strict rule (FR-004). A new
`read_value_leniently` wraps it and returns a `ValueReading` (R1):

- **Unreadable Value**: `typed_value=None`, with what was expected
- **Rounded Value**: a non-whole number in an Integer column or field, rounded half away
  from zero with `decimal`, with the number saved (R2)

`read_tally` stops raising. Unknown marks go to `TallySummary.unknown_marks`, the
counts use the recognised marks only, and the marks scalar then holds the text as read
(R3).

**Flow.** Interpreters return their problems in a new
`DataSheetInterpretationDto.value_problems` field instead of raising. The sheet
interpreter gathers them into `StudentDataSheet.value_warnings` (R4).
`InvalidValuesError` and `FailureReason.INVALID_VALUES` are removed.

**Outcome.** `SheetOutcome` gains `warnings`, and its status stays SUCCEEDED, so
re-processing and totals can't drift from FR-011 (R5). The Import window shows
`⚠ Succeeded with warnings` in amber. The wording reuses `ValueProblem.message()`, plus
`; saved as N` for a rounded value (R6).

**Storage.** Unchanged. `cell_for` already writes a value with text but no typed value
as plain text, through `stringValue`, so Sheets never re-parses it. The Template
Structure doesn't change (R7).

**Docs.** interpreters.md rule 10 is rewritten and the glossary gains the new terms.
The constitution goes to 1.9.0 (R8).

## Technical Context

**Language/Version**: Python 3.12

**Primary Dependencies**: Tkinter + `sv-ttk`, `boto3` (Textract), and
`google-api-python-client`. No new dependency. `decimal` is in the standard library.

**Storage**: No change. The templates JSON file and the workbook layout are unchanged.
Unreadable Values are written as text cells by the existing `cell_for`.

**Testing**:

- Offline scratch-script checks of `value_types`, the three interpreters, the sheet
  interpreter, `SheetImportBatch` with a fake store, and the store with a fake Sheets
  service.
- One live import per [quickstart.md](quickstart.md).
- No test framework (007 R11).

**Target Platform**: Desktop (Linux primary; any OS that runs Tkinter).

**Project Type**: Desktop app (single project under `therepy_sessions/`).

**Performance Goals**: No measurable change. Reading stays microseconds per cell, and
the number of save requests is unchanged.

**Constraints**:

- Interpretation stays pure.
- Layout mismatches still fail (FR-014).
- Old templates load unchanged, and sheets with no problems produce identical workbooks
  (SC-005).
- Warning messages name students only by Student Key, and quote only cell text.

**Scale/Scope**:

- Code: about 8 changed modules, all in `interpretation/`, and no new module.
- Data: 1 new synthetic sample, and 1 sample README update.
- Docs: 2 doc amendments plus the constitution version.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | How this plan complies | Result |
| --- | --- | --- |
| I. Student Data Privacy | No new service or destination. The kept text goes to the same workbook cell the value would have gone to. Warnings, like 007's failure reasons, quote only cell text, and name students only by Student Key. Checks use `ZZ` samples and a test account. | ✅ Pass |
| II. Domain Language Fidelity | New code names match new glossary terms: `ValueReading`, `value_warnings`, and *succeeded with warnings*. Unreadable Value and Rounded Value are added to the glossary in this change. Scalar, Sheet Outcome, and Tally Summary are updated (FR-016, R8). | ✅ Pass (glossary update in scope) |
| III. Layered Pipeline | Lenient reading lives in pure `interpretation/value_types.py`. Warnings cross to the import batch only on `StudentDataSheet`. The batch turns them into strings, and the window only shows them (no rules in the UI). `storage/`, `collection/`, and `program.py` are unchanged. | ✅ Pass |
| IV. Injected External Services | No client changes. | ✅ Pass |
| V. Pluggable Interpreters & Templates | No new interpreter type, and no template or serializer change, so saved templates load as before. The three types change together under the amended rule 10. A sheet that doesn't match its template's layout still fails loudly (FR-014). Values that don't fit are still reported, now as visible warnings. They are never silently dropped. | ✅ Pass (rule 10 amended, R8) |
| VI. Typed Public Interfaces | Every new or changed member is annotated: `ValueReading`, `read_value_leniently`, `TallySummary` fields, `ValueProblem.saved_as`, `value_warnings`, `add_value_warnings`, `SheetOutcome.warnings`, and `ListTotals.with_warnings`. | ✅ Pass |
| Tech constraints | No new dependency, so `pip_requirements.txt` and `ALL_DEPENDENCIES.md` are unchanged. | ✅ Pass |
| Development Workflow | Offline checks use synthetic inputs, and the live check uses a test account. The constitution amendment follows Governance (version bump and Sync Impact Report). | ✅ Pass |

**Post-design re-check (after Phase 1)**: Still passing. The design removes an error
path, `INVALID_VALUES`, and adds no new layer crossing.

## Project Structure

### Documentation (this feature)

```text
specs/008-nullable-field-values/
├── plan.md              # This file
├── research.md          # Phase 0: R1–R9
├── data-model.md        # Phase 1
├── quickstart.md        # Phase 1: V1–V7
├── contracts/
│   └── lenient-values-and-outcomes.md
├── checklists/
│   └── requirements.md
└── tasks.md             # Phase 2 (/speckit-tasks)
```

### Source Code (repository root)

```text
therepy_sessions/
├── interpretation/
│   ├── value_types.py                         # ValueReading, read_value_leniently, Integer rounding,
│   │                                          #   TallySummary fields, non-raising read_tally,
│   │                                          #   tally_scalars marks text, ValueProblem.saved_as;
│   │                                          #   InvalidValuesError removed
│   ├── student_data_sheet.py                  # value_warnings / add_value_warnings
│   ├── templates/
│   │   └── student_data_sheet_interpreter.py  # DataSheetInterpretationDto.value_problems; gather warnings
│   ├── interpreter_types/
│   │   ├── table_interpreter.py               # lenient cells, keep unreadable text, report problems
│   │   ├── simple_form_interpreter.py         # lenient fields, report problems
│   │   └── running_tally_interpreter.py       # skip unknown marks, report each
│   └── importing/
│       ├── sheet_import_batch.py              # SheetOutcome.warnings, ListTotals.with_warnings;
│       │                                      #   INVALID_VALUES removed
│       └── import_window.py                   # ⚠ status label, amber tag, summary count
├── sample_data/
│   ├── 007/README.md                          # bad_values.json now succeeds with warnings
│   └── 008/                                   # README.md + lenient_values.json (rounding, N/A, QZ)
docs/
├── conventions/architecture/interpreters.md   # rule 10 rewritten
└── domain/glossary.md                         # Unreadable Value, Rounded Value, Sheet Outcome, Scalar, Tally Summary
.specify/memory/constitution.md                # 1.8.0 → 1.9.0, Sync Impact Report
```

**Structure Decision**: This is the existing single desktop project. All code changes
are inside `interpretation/`, and `storage/`, `collection/`, `students/`,
`workspace/`, and `program.py` are untouched.

## Complexity Tracking

No constitution violations to justify.
