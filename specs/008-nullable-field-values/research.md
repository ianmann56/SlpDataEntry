# Research: Nullable Field Values

There were no open technical unknowns. The stack, storage, and testing approach are
those of feature 007. Each entry below records a design decision this feature needs,
with what was rejected.

## R1. Lenient reading sits beside the strict reading rule

**Decision**: Keep `read_value` as the strict reading rule. Add
`read_value_leniently(column_type, text, choices) -> ValueReading` to
`interpretation/value_types.py`. It calls `read_value` and turns its outcome into a
record holding the Typed Value plus, when the value didn't fit, what was expected and
what was saved. Every interpreter reads typed values through it.

**Rationale**: FR-004 keeps every reading rule unchanged except Integer, so the strict
rule stays the single place those rules live. The lenient wrapper is the only new
policy: an Unreadable Value becomes `typed_value=None`, and a Rounded Value becomes an
`int`. Interpreters stay simple, with one call per cell and no `try`/`except`.

**Alternatives considered**:

- Make `read_value` itself return `None` for an Unreadable Value. Rejected because the
  interpreter could then no longer tell an Unreadable Value from a blank one, which it
  needs for the warning (FR-012).
- Signal a rounded value with an exception subclass. Rejected because rounding is not
  an error, and an exception can't carry the rounded value back cleanly.

## R2. Integer rounding is half away from zero, using `decimal`

**Decision**: For an Integer column or field, text that fails the integer rule but
passes 007's Decimal rule (`_DECIMAL_PATTERN`) is a Rounded Value. It is rounded with
`Decimal(trimmed).quantize(Decimal(1), rounding=ROUND_HALF_UP)` and saved as an `int`.
`7.0` still matches the integer rule, so it is read as 7 with no warning.

**Rationale**: The spec rounds halves away from zero (`2.5` → 3, `-2.5` → -3). Python's
`round()` rounds half to even, so it gives `2.5` → 2. `decimal.ROUND_HALF_UP` rounds
ties away from zero, and working from the decimal text avoids binary float error.

**Alternatives considered**: `math.floor(x + 0.5)` was rejected because it rounds
`-2.5` to -2 and inherits float error.

## R3. A tally never fails; it records unknown marks

**Decision**: `read_tally` no longer raises. `TallySummary` gains two fields:

- `text_as_read`: the text exactly as given
- `unknown_marks`: each character that isn't an option, in reading order, as read

The counts, total, and percentages use only the recognised marks. `tally_scalars` keeps
the marks scalar as today when `unknown_marks` is empty. Otherwise the marks scalar's
`value` and `typed_value` are both `text_as_read` (a TEXT scalar), so the workbook
shows what was written (FR-009, FR-010).

**Rationale**: The full set of unknown marks is needed for the warning (FR-012). A
Running Tally grid has several of them, and today only the first is reported. Keeping
the scalar's type as TEXT means storage writes it as text with no new rule.

**Alternatives considered**: Saving only the recognised marks in the marks cell. The
clarification rejected this, because what was written must stay visible.

## R4. Value problems travel with the interpretation, not as an exception

**Decision**:

- `DataSheetInterpretationDto` gains a third field, `value_problems: list[ValueProblem]`,
  defaulting to empty.
- Each interpreter returns its problems instead of raising.
- `StudentDataSheetInterpreter` collects them from every section, in template order,
  into the new `StudentDataSheet.value_warnings`.
- `InvalidValuesError` and `FailureReason.INVALID_VALUES` are removed. Nothing raises
  them any more.

**Rationale**: A sheet with Unreadable Values now succeeds, so the problems must reach
the import batch alongside the data, not instead of it. `StudentDataSheet` is already
the one record that crosses from Interpretation (Principle III), so the warnings ride on
it. `StudentDataSheet` imports `ValueProblem` only under `TYPE_CHECKING`, as it already
does for the template, so no import cycle is created.

**Alternatives considered**:

- Raising a warning exception that carries the finished sheet. Rejected because it
  makes success flow through `except`.
- A separate return value from `interpret_student_data_sheet`. Rejected because it
  breaks the existing signature the batch and storage rely on.

## R5. "Succeeded with warnings" is SUCCEEDED plus a warning list

**Decision**: `SheetStatus` is unchanged. `SheetOutcome` gains
`warnings: tuple[str, ...] = ()`, filled from `data_sheet.value_warnings` when the
sheet is saved. A succeeded outcome with warnings is the glossary's *succeeded with
warnings*.

The outcome's `message` becomes the save message followed by one sentence:
`N values didn't fit their type: <warning>; <warning>`.

The window shows such a row as `⚠ Succeeded with warnings` with its own colour, and
the run summary counts it under *succeeded*, adding `(N with warnings)`.

**Rationale**: FR-011 says it "counts as succeeded for every purpose". Keeping the
status as SUCCEEDED means `files_to_process`, `totals`, the progress bar, and
double-click-to-open need no change and can't drift from the spec.

**Alternatives considered**: A new `SheetStatus.SUCCEEDED_WITH_WARNINGS`. Rejected
because every `== SUCCEEDED` check would need updating, and missing one would
re-import a saved sheet.

## R6. Warning wording reuses `ValueProblem.message`

**Decision**: `ValueProblem` gains `saved_as: str = ""`. `message()` appends
`; saved as {saved_as}` when it is set. This gives three kinds of message:

| Kind | Example |
| --- | --- |
| Unreadable Value | `"Words", column "Trials", row 3: "N/A" is not a whole number` (unchanged wording) |
| Rounded Value | `"Words", column "Trials", row 3: "7.5" is not a whole number; saved as 8` |
| Unknown tally mark | `"Words", column "Attempts", row 2: "YQN" is not made of only the marks Y, N, P ("Q" is not one; left out of the counts)` |

For a Running Tally section, `value` is the unknown mark itself, as today.

**Rationale**: The spec requires the same wording as today's failure reasons
(FR-012). It also needs the rounded number named, and the SLP must be able to find
each cell (SC-003).

## R7. Storage needs no change

**Decision**: `storage/` is unchanged.

`session_layout.cell_for` already handles each case:

- a scalar with `typed_value is None` and non-blank text is written as plain text
- an `int` typed value is written as a number
- a TEXT scalar is written as text

`google_drive_data_sheet_store` writes text as `userEnteredValue.stringValue`, which
Sheets never re-parses. So `7.5` kept as text could not turn back into a number, and
`13/45/2026` could not become a date (FR-005).

The Template Structure comes from `section_keys()`, which this feature doesn't touch
(FR-007).

**Rationale**: Verified by reading `cell_for` and `_cell_payload`. Quickstart V5
confirms it against a fake Sheets service.

## R8. The constitution amendment is MINOR

**Decision**: Rewrite interpreters.md rule 10: values that don't fit are kept and
reported as warnings, never failing the sheet, and are never silently dropped. Update
the glossary as follows:

- Scalar / Typed Value: `None` for a blank or Unreadable Value
- Sheet Outcome: adds *succeeded with warnings*
- new terms: Unreadable Value, Rounded Value
- Tally Summary: unknown marks are left out of the counts

Bump the constitution from 1.8.0 to **1.9.0**, with a Sync Impact Report.

**Rationale**: Rule 10 changes meaning, which counts as an amendment under Governance.
No principle is removed or redefined: Principle V's "fail loudly" still applies to
layout mismatches (FR-014), and values that don't fit are still reported, now as
warnings. Under the versioning policy that is MINOR.

## R9. Validation stays offline scratch scripts plus one live run

**Decision**: As in 007, there is no test framework. The quickstart lists throwaway
checks of `value_types`, the interpreters, the batch with a fake store, and the store
with a fake Sheets service, then one live import against a test account.
`sample_data/007/bad_values.json` gets a new expected result, and
`sample_data/008/lenient_values.json` adds the rounding and tally cases.

**Rationale**: This matches the project's established practice (007 R11).
