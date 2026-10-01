# Pluggable Section Interpreters and Templates

Data sheets vary by student and goal. The tool handles this by composing small
**section interpreters** into saved **templates**, so a new layout does not require
editing the core flow.

## How it fits together

```
StudentDataSheetTemplate(id, name, [interpreters...])
        │ to_data_sheet_interpreter()
        ▼
StudentDataSheetInterpreter
  ├─ reads header fields from form_data: Student Key, Date, Time IN, Time OUT, Goal, Measure
  └─ for each SessionDataSectionInterpreterBase:
        interpret_student_data_sheet_content(import) → DataSheetInterpretationDto(tables, scalars)
     then merges all tables and scalars into one StudentDataSheet
```

## Adding a new interpreter type

A new interpreter type is complete only when all four of these exist:

| Piece | Location | Responsibility |
| --- | --- | --- |
| Interpreter | `interpretation/interpreter_types/<name>_interpreter.py` | Subclass `SessionDataSectionInterpreterBase`. Take `id` and `title` plus its own config. Implement `interpret_student_data_sheet_content`. Return `DataSheetInterpretationDto`. |
| Config UI | `interpretation/template_manager/interpreter_configs.py` | Subclass `InterpreterConfig`. Implement `name`, `create_config_form` (returning `frame`, `get_config`, `reset`), and `construct_interpreter`. |
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
