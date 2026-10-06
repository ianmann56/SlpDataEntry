# Pluggable Section Interpreters and Templates

Data sheets vary by student and goal. The tool handles this by composing small
**section interpreters** into saved **templates**, so a new layout does not require
editing the core flow.

## How it fits together

```
StudentDataSheetTemplate(id, name, [interpreters...])
        │ to_data_sheet_interpreter()   (passes the interpreters and the template itself)
        ▼
StudentDataSheetInterpreter
  ├─ reads header fields from form_data: Student Key, Date, Time IN, Time OUT, Goal, Measure
  ├─ assigns each table on the sheet to one table section (rule 9)
  └─ for each SessionDataSectionInterpreterBase:
        interpret_student_data_sheet_content(import) → DataSheetInterpretationDto(tables, scalars)
     then merges all tables and scalars into one StudentDataSheet, which carries the
     template (sheet.template), and tags each table with its interpreter's id (section_id)
```

Storage reads the template only through `sheet.template`. It uses each interpreter's
public `id`, `title`, `section_kind`, and `section_keys()` to work out the Template
Structure, which decides the Student Session Workbook a sheet is saved to, and the
Workbook Layout Order of its tabs. Storage never checks interpreter types.

## Adding a new interpreter type

A new interpreter type is complete only when all four of these exist:

| Piece | Location | Responsibility |
| --- | --- | --- |
| Interpreter | `interpretation/interpreter_types/<name>_interpreter.py` | Subclass `SessionDataSectionInterpreterBase`. Take `id` and `title` plus its own config. Implement `interpret_student_data_sheet_content`, returning `DataSheetInterpretationDto`, and `section_keys()`, returning the field, column, or tally keys it produces, in template order. `section_kind` defaults to the class name; if the class is renamed, override it to keep the old name. A type that reads tables from the sheet overrides `consumes_tables` to return `True`. A type that emits form scalars rather than tables is also listed in `FORM_SECTION_KINDS` in `storage/session_layout.py`. |
| Config UI | `interpretation/template_manager/interpreter_configs.py` | Subclass `InterpreterConfig`. Implement `name`, `interpreter_type`, `create_config_form` (returning a `ConfigForm` with `frame`, `get_config`, `reset`, and `load`), `construct_interpreter`, and `describe` (readable lines for view mode). `load` fills the form from a saved interpreter so it can be edited. |
| Serializer | `interpretation/template_manager/storage/serialization.py` | Subclass `InterpreterSerializer` and register it. The output has the shape `{"type", "id", "title", "config"}`. |
| Registration | the config list passed to the management window, and the serializer registry | Makes the type visible in the UI and loadable from disk. |

## Rules

1. **Output is typed.** Every value an interpreter emits is a `DataSheetScalarDto` with
   a `DataSheetScalarType`. Tables use the shape `{"columns": [...], "data": [{col: DataSheetScalarDto}]}`.
2. **Interpreters are pure.** See [layers.md](layers.md), rule 3.
3. **Interpreter state is per instance.** Mutable containers (lists, dicts) MUST be
   created in `__init__`, never declared as class attributes, so instances do not share
   state. Existing classes that still use class attributes should be fixed when touched.
4. **Serialization is backward compatible.** Changing a serializer's `config` shape
   MUST keep loading templates saved in the old shape. Existing template files belong to
   the SLP and are not regenerated.
5. **Fail loudly on a mismatched sheet.** When a sheet does not match its template (a
   missing column, a missing header label), raise an exception naming what was expected
   and what was found, as `TableInterpreter` does. Never skip data silently.
6. **Ids are stable.** Template ids and interpreter ids are strings, unique within their
   scope, and never reused after deletion. `TemplateStore.generate_new_id` owns template ids.
   The templates file records `last_template_id`, the highest id ever given out, so a
   deleted template's id is never given out again.
7. **Untouched interpreters are saved as loaded.** When a template is edited, an
   interpreter the SLP did not change is saved exactly as it was loaded, never rebuilt
   from its config form. A form cannot always show every saved detail, so rebuilding it
   could lose data.
8. **Section keys decide the workbook.** `section_keys()` and `section_kind` feed the
   Template Structure. Changing what they return for an existing type changes which
   Student Session Workbook its templates' sessions go to, so treat that like a
   serialization change (rule 4).
9. **Each table is read by one section.** `StudentDataSheetInterpreter` decides which
   tables each section whose `consumes_tables` is `True` receives; the section reads
   only those. A template with one such section gets every table. A template with
   several gives each table to the section whose title matches the table's title on the
   sheet, ignoring letter case, spacing, and a trailing `:`. A table with no title or no
   matching section, a section with no table, or two such sections with the same title
   fails the sheet (rule 5).
