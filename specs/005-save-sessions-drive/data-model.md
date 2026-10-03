# Data Model: Save Imported Sessions to Google Drive

**Feature**: [spec.md](spec.md) | **Date**: 2026-10-02

The entities below cover what this feature adds or changes. The full typed signatures
are in [contracts/](contracts/).

## Interpretation side

### DataSheetStore (new abstraction, `interpretation/data_sheet_store.py`)

The storage mechanism for interpreted data sheets. `SheetImportBatch` and `ImportWindow`
depend only on it (research R1).

| Member | Meaning |
| --- | --- |
| `prepare() -> None` | Get ready to save: connect, sign in, and find or create the destination (FR-006a). It is idempotent. |
| `save(sheet: StudentDataSheet) -> SavedDataSheet` | Store one sheet, or report it is already stored. Writes nothing partial. |
| raises `DataSheetStoreError` | Its message is SLP-readable and names students only by Student Key. |

Implementations: `GoogleDriveDataSheetStore` (storage side, below). Offline checks use an
in-memory fake.

### SavedDataSheet (new record, same module)

| Field | Type | Meaning |
| --- | --- | --- |
| `location_url` | `str` | Opens the saved session. For Google this is the tab URL, `https://docs.google.com/spreadsheets/d/<id>/edit#gid=<sheetId>`. |
| `location_name` | `str` | SLP-readable, e.g. `AG - Emotion Causes › 9/14/2026 11:00 AM`. |
| `already_saved` | `bool` | `True` when the session was already stored and nothing was written (FR-016a). |

### StudentDataSheet (changed)

| Change | Meaning |
| --- | --- |
| `template: StudentDataSheetTemplate` | The template the sheet was interpreted with, set by `StudentDataSheetInterpreter`. Storage drives every template-dependent rule from it (R2). |
| `register_table(table, section_id)` | Tags each table with the id of the interpreter that produced it. `DataSheetTable` gains `section_id: NotRequired[str]`. |
| `use_student_key(key)` | After matching, the batch replaces the key read from the sheet with the stored key. They differ only in case and surrounding spaces. |

### SessionDataSectionInterpreterBase (changed)

- `section_kind: str` property. The default is `type(self).__name__`.
- `section_keys() -> list[str]`, abstract, returning keys in template order:
  - `TableInterpreter`: its column names.
  - `RunningTallyInterpreter`: `["Tally"]`, the column it emits.
  - `SimpleFormInterpreter`: its field names, in `fields` dict order.

## Import side

### SheetOutcome (changed)

New field:

| Field | Type | Meaning |
| --- | --- | --- |
| `saved` | `SavedDataSheet \| None` | Set only on `SUCCEEDED`. It enables Open (FR-003b), and its `already_saved` value picks the message. |

### FailureReason (changed)

| New reason | When | Message (names the fix; Student Key only) |
| --- | --- | --- |
| `MISSING_DATE` | The interpreted `date` is blank (FR-017). Checked before saving. | "No session Date was found on the sheet. Fill in the Date and retake the photo." |
| `SAVE_FAILED` | `DataSheetStore.save` raised. | "Could not save to Google Drive: {detail}. Press Import again to retry." |

### Sheet state transitions (changed)

```text
NOT_IMPORTED ──Import──► read ─► match student ─► load template ─► interpret ─► check date ─► save
                                                                                              │
     ┌──────────────── FAILED (any step; the Import is kept and reused on retry) ◄────────────┤
     │                                                                                         ▼
     └──next Import──► (retried from the first step whose result isn't kept)       SUCCEEDED
                                                                          (saved, or already saved)
```

A `SUCCEEDED` sheet is never processed again in that window (existing rule). Saving is
the last step, so a sheet that fails to save comes back as `FAILED` / `SAVE_FAILED` and
is retried as a whole on the next press. Retrying is safe: if the earlier attempt did
write a tab, the retry finds it as a duplicate (FR-016a).

## Storage side (`storage/`)

### TemplateShape (`storage/template_structure.py`, derived from `sheet.template`)

| Field | Type | Meaning |
| --- | --- | --- |
| `template_name` | `str` | The template name. A new workbook is named from it (FR-011). |
| `sections` | `tuple[SectionShape, ...]` | In template order. Each holds `section_id`, `kind` (`section_kind`), `title`, and `keys` (`section_keys()`, in template order). |

Derived:

- `structure_identity()`: the sorted `(kind, title, sorted(keys))` for each section.
  This is the **Template Structure** (FR-009).
- `structure_fingerprint()`: `"s1-" + sha256(canonical JSON)[:32]` (R3).

**Rules**:

- The same sections and keys in any order give the same fingerprint.
- Type and choice changes leave the fingerprint unchanged.
- Adding, removing, or renaming a section, field, or column changes it (SC-004).
- Section ids, the template name, and the description are never part of it (FR-008).

### Student Session Workbook (a Google Sheet in Drive)

| Attribute | Where | Value |
| --- | --- | --- |
| Name | Drive `name` | `"{student_key} - {template_name}"` when created. Never changed by the app afterwards (FR-011). |
| Folder | Drive `parents` | The Therapy Data Folder (`SLP Therepy Data/Current Year`). |
| `slpWorkbook` | Drive `appProperties` | `"1"` |
| `slpStudentKey` | Drive `appProperties` | The stored Student Key. |
| `slpStructure` | Drive `appProperties` | `shape_of(sheet.template).structure_fingerprint()` |
| `slpWorkbookLayout` | Spreadsheet `developerMetadata` (`DOCUMENT`) | Workbook Layout Order JSON (below). |

**Identity**: `(slpStudentKey, slpStructure)` within the folder. If several match, the
one with the newest `modifiedTime` wins (FR-013b).

### Workbook Layout Order (JSON in developer metadata)

```json
{
  "version": 1,
  "sections": [
    {"kind": "SimpleFormInterpreter", "title": "Counts", "keys": ["Total", "Prompted"]},
    {"kind": "TableInterpreter", "title": "Words", "keys": ["Word", "Times Prompted", "Times w/out Prompt"]}
  ]
}
```

This JSON holds template keys only: no values, no Student Key, no types or choices
(FR-028).

**Mapping a later sheet onto it**: a section in `shape_of(sheet.template)` matches the
next unused layout section with the same `(kind, title)` and the same key set. The
fingerprints are equal, so a match always exists. Within a matched section, values are
placed by key, so the sheet's own key order is ignored.

### Session Tab (one per saved session)

| Attribute | Value |
| --- | --- |
| Name | `"{date} {time_in}"`, or `"{date}"` when Time IN is blank. Cleaned and trimmed to 100 characters. ` N` is appended only on a clash with a tab that isn't a duplicate. |
| Position | Sorted by Session Moment, newest first. Blank or unreadable times sort after timed tabs of the same date. Unreadable dates go last (FR-018a). |
| Contents | The rows from research R9. Values only. |

**Session Moment of an existing tab**: the B-column values next to the `Date` and
`Time IN` labels in its first 6 rows.

### Session Moment (value object, `storage/session_layout.py`)

| Field | Type | Meaning |
| --- | --- | --- |
| `date_text` | `str` | Date as read. |
| `time_text` | `str` | Time IN as read. May be blank. |
| `sort_key` | `tuple` | `(has_date, date, has_time, time)`, used for ordering. |

`matches(other)` is `True` only when both `time_text` values are non-blank and the dates
and times are equal after `casefold().strip()` (FR-016).

### GoogleDriveDataSheetStore (`storage/google_drive_data_sheet_store.py`)

The `DataSheetStore` implementation for this feature. Its `save` returns a
`SavedDataSheet` with:

- `location_url`: the tab URL
- `location_name`: `"{workbook} › {tab}"`
- `already_saved`

Internally it caches `(student_key, fingerprint) → spreadsheet id` for the window's life
(R5).

### Cell values

| Interpreted value | Cell written |
| --- | --- |
| `DataSheetScalarDto` with type `INT` and an integer text | `numberValue` |
| `DataSheetScalarDto` with type `INT` and a non-integer text | `stringValue` with the original text |
| `DataSheetScalarDto` with any other type | `stringValue` |
| Raw `str` (from a simple form) | `stringValue` |
| Blank or `None` | an empty cell (no `userEnteredValue`) |

## Validation rules (from the spec)

| Rule | Where it is enforced |
| --- | --- |
| A blank Date fails the sheet (FR-017) | `SheetImportBatch`, before `DataSheetStore.save` |
| A blank Time IN still saves, gets a date-only name, and is never a duplicate (FR-017a) | `session_layout.tab_base_name`, `SessionMoment.matches` |
| A duplicate writes nothing (FR-016a) | `GoogleDriveDataSheetStore.save`, before any write |
| No partial tab or empty new workbook remains (FR-002, FR-019) | One atomic `batchUpdate`; a new file is deleted if its first batch fails. If that delete also fails, the next save repairs the workbook (contracts/session-storage.md § `save(sheet)` step 5.1) |
| Labels and layout hold no session values (FR-028) | They are built only from `shape_of(sheet.template)` and the stored Student Key |
