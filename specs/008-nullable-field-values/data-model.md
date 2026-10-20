# Data Model: Nullable Field Values

All records are in-memory and pure, except `SheetOutcome`, which the Import window shows.
Nothing new is persisted. The templates file and the workbook layout don't change.

## ValueReading *(new, `interpretation/value_types.py`)*

The result of reading one non-tally value leniently.

| Field | Type | Meaning |
| --- | --- | --- |
| `typed_value` | `TypedValue` | The value in its type, or `None` for a blank or Unreadable Value |
| `expected` | `str` | `""` when the value fit its type. Otherwise what it should have been, e.g. `"a whole number"` |
| `saved_as` | `str` | For a Rounded Value, the number saved, e.g. `"8"`. Otherwise `""` |

The fields combine into four states:

| State | `typed_value` | `expected` | `saved_as` |
| --- | --- | --- | --- |
| Fits | set | `""` | `""` |
| Blank | `None` | `""` | `""` |
| Unreadable Value | `None` | set | `""` |
| Rounded Value (Integer only) | `int` | `"a whole number"` | set |

## TallySummary *(changed)*

| Field | Type | Change |
| --- | --- | --- |
| `marks` | `str` | Unchanged: the recognised marks, in order, as configured |
| `counts` | `dict[str, int]` | Unchanged: from recognised marks only |
| `total` | `int` | Unchanged: the number of recognised marks |
| `percentages` | `dict[str, float \| None]` | Unchanged: `None` when `total` is 0 |
| `text_as_read` | `str` | **New**: the tally's text exactly as given |
| `unknown_marks` | `str` | **New**: each non-space character that isn't an option, in order, as read. `""` when every mark is known |

When `unknown_marks` is set, the marks scalar's `value` and `typed_value` are both
`text_as_read` (FR-009, FR-010).

## ValueProblem *(changed)*

| Field | Type | Change |
| --- | --- | --- |
| `section`, `item`, `row`, `value`, `expected`, `item_kind` | as before | Unchanged |
| `saved_as` | `str = ""` | **New**: appended to `message()` as `; saved as {saved_as}` when set |

It now describes a warning rather than a failure.

## DataSheetInterpretationDto *(changed)*

`namedtuple('DataSheetInterpretationDto', ['tables', 'scalars', 'value_problems'], defaults=[()])`

- `value_problems`: every Unreadable Value, Rounded Value, and unknown tally mark in the
  section, in reading order. It defaults to empty, so existing two-argument
  constructions keep working.

## StudentDataSheet *(changed)*

| Member | Type | Meaning |
| --- | --- | --- |
| `value_warnings` | `list[ValueProblem]` (property) | **New**: the sheet's problems, in template order, then in reading order within each section. `[]` when every value fit |
| `add_value_warnings(problems)` | `(Sequence[ValueProblem]) -> None` | **New**: called by `StudentDataSheetInterpreter` only |

## SheetOutcome *(changed, `interpretation/importing/sheet_import_batch.py`)*

| Field | Type | Change |
| --- | --- | --- |
| `warnings` | `tuple[str, ...] = ()` | **New**: one message per entry of `value_warnings`. Set only when `status` is `SUCCEEDED` |

**Derived state**: *succeeded with warnings* means `status is SUCCEEDED and warnings`.
`SheetStatus` keeps three members, so the transitions are unchanged:

```text
NOT_IMPORTED ──Import──▶ SUCCEEDED (warnings may be empty or not) ── never re-processed
             └─────────▶ FAILED ──Import again──▶ …
```

## ListTotals *(changed)*

| Field | Change |
| --- | --- |
| `with_warnings: int` | **New**: how many SUCCEEDED files have warnings. They are also counted in `succeeded` |

## Removed

- `InvalidValuesError`: nothing raises it now.
- `FailureReason.INVALID_VALUES`, and its entry in `_FAILURE_MESSAGES`.

`ValueReadError` stays. It is still raised by the strict `read_value` and is caught
inside `read_value_leniently`.

## Glossary changes (FR-016)

| Term | Change |
| --- | --- |
| Scalar | The Typed Value is `None` when blank **or an Unreadable Value** |
| Unreadable Value | New, as in the spec's Key Entities |
| Rounded Value | New, as in the spec's Key Entities |
| Sheet Outcome | Adds *succeeded with warnings*: a success listing every Unreadable Value, Rounded Value, and unknown tally mark |
| Tally Summary | Unknown marks are left out of the counts. The marks value is then the text as read |
