---

description: "Task list for the View and Edit Data Sheet Templates feature"
---

# Tasks: View and Edit Data Sheet Templates

**Input**: Design documents from `/specs/004-view-edit-templates/`

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md),
[data-model.md](data-model.md), [contracts/template-rules.md](contracts/template-rules.md),
[contracts/ui-windows.md](contracts/ui-windows.md), [quickstart.md](quickstart.md)

**Tests**: No automated tests. The spec doesn't ask for them. Research R12 makes
verification an offline scratch-script check of `template_rules.py` and the stores, plus
the manual [quickstart.md](quickstart.md). Scratch scripts are not committed.

**Organization**: Tasks are grouped by user story.

| Story | Priority | Delivers |
| --- | --- | --- |
| US1 | P1 | The Template Details window in view mode, the Students count column, and saving the description when a template is created |
| US2 | P2 | Edit mode: filled-in interpreter forms, automatic apply, form Cancel, reordering, the save confirmation, and validation shared with the Create window |
| US3 | P3 | The discard confirmation when leaving edit mode |
| US4 | P3 | Deleting a template in use, which clears those students' Current Template first |

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: US1–US4 from spec.md

## Path Conventions

- All code is under `therepy_sessions/`. Modules import each other by package path from
  that directory (e.g. `from interpretation.template_manager.template_rules import TemplateDraft`).
  `interpretation/` has no `__init__.py` files (namespace packages). Don't add any.
- Every public function, method, attribute, and `__init__` added or changed is fully
  annotated, as [type-declarations.md](../../docs/conventions/architecture/type-declarations.md)
  requires. Injected collaborators and callbacks are stored as `_`-prefixed attributes.
- `interpretation/template_manager/template_rules.py` MUST NOT import `tkinter` or
  anything from `students/`, `collection/`, `clients/`, or `storage/` (research R1, R8).
  No module under `interpretation/template_manager/` imports from `students/`. Only
  `program.py` connects the two.
- Windows report unexpected errors with `tk_utils.error_handling.throw(e, summary)`
  (dependency-injection rule 5).
- Use only placeholder keys (`AG`, `KT`, `JA`, `MK`) and scratch copies of
  `therepy_sessions/sample_data/templates.json` and `students.json` (Principle I).

---

## Phase 1: Setup (Shared Infrastructure)

- [ ] T001 Confirm the starting point, and change nothing:
  - `therepy_sessions/interpretation/template_manager/template_editor_window.py` is the "Implementation coming soon" stub. Only `template_management_window.py` imports it.
  - The two sample files hold templates `2`, `3`, `4`, and `5`, and students `AG` → `4` and `KT` → `2`.
  - No dependency changes are needed (plan Technical Context).

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Extend the template model and store, create the shared rules module and the config contract, and amend the docs and constitution first. No code then lands ahead of the rules it relies on. Every story depends on this phase.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [ ] T002 [P] Update `therepy_sessions/interpretation/template_manager/student_data_sheet_template.py` (research R6):
  - Replace the class attributes `_id`, `_name`, and `_configured_interpreters` with instance attributes (interpreters rule 3).
  - Change the constructor to `__init__(self, id: str, name: str, configured_interpreters: list[SessionDataSectionInterpreterBase] | None = None, description: str = "") -> None`.
  - Add a `description -> str` property.
  - Annotate `id -> str`, `name -> str`, `interpreters -> list[SessionDataSectionInterpreterBase]`, and `to_data_sheet_interpreter -> StudentDataSheetInterpreter`.
  - Keep the 2-space indentation the file already uses.
- [ ] T003 Rewrite persistence in `therepy_sessions/interpretation/template_store.py` (research R6, R10; [contracts/template-rules.md](contracts/template-rules.md)). Depends on T002, because it builds templates with `description=`.
  - **DTOs**: turn `TemplateCreateDto` and `TemplateEditDto` into `@dataclass` records with `name: str`, `configured_interpreters: list[SessionDataSectionInterpreterBase]`, and `description: str = ""`.
  - **Reading**: add `FORMAT_VERSION: int = 2`. Replace `_load_templates_from_file` with `_load() -> tuple[list[dict[str, Any]], int]`, which returns the entries and `last_template_id`.
    - A missing file returns `([], 0)`.
    - A bare list is format 1. Its `last_template_id` is the highest numeric `id`.
    - A dict with an int `format_version` ≤ 2 and a list `templates` is read with its `last_template_id`, which defaults to the highest numeric `id`.
    - Bad JSON, `UnicodeDecodeError`, any other shape, or `format_version` > 2 raises `UnreadableTemplatesError`.
  - **`check_readable`**: call `_load()` and discard the result.
  - **Existing read methods**: `get_all_templates` and `get_template_by_id` keep returning an empty result when the file is unreadable, as they do today.
  - **Never overwrite an unreadable file**: `create_template`, `edit_template`, `delete_template`, and `generate_new_id` call `_load()` without catching `UnreadableTemplatesError`. A corrupt file, or one with `format_version` > 2, makes them raise before anything is written (Principle V).
  - **`_convert_data_to_template`**: pass `description=template_data.get("description", "")`.
  - **Writing**: replace `_save_templates_to_file` with `_save(entries, last_template_id) -> None`. It writes `{"format_version": 2, "last_template_id": N, "templates": entries}` with UTF-8 and `indent=2` to a `tempfile.NamedTemporaryFile` in the same directory, then calls `os.replace` (the same pattern as `JsonStudentStore._save`). `OSError` propagates.
  - **IDs**: `generate_new_id` returns `str(max(last_template_id, highest numeric id) + 1)`.
  - **`create_template`**: write the new entry, including `description`, and set `last_template_id` to the new ID in one save.
  - **`edit_template`**: write `description` and keep the entry at its index.
  - **`delete_template`**: keep `last_template_id` unchanged.
  - **`_ensure_storage_file_exists`**: remove it. A missing file is now read as empty, so nothing is created at construction.
  - **Annotations**: annotate every public method as the contract shows.
- [ ] T004 [P] Create `therepy_sessions/interpretation/template_manager/template_rules.py` with the shared rules every story uses (research R1, R2, R8; data-model.md Template Usage):
  - `class TitleConflictError(ValueError)`, with the message `An interpreter titled "<title>" has already been added.`
  - `find_title_conflict(title, interpreters, ignore_index=None) -> bool`. It compares `title.strip()` with each other interpreter's `title.strip()` exactly, and a blank title never conflicts.
  - `validate_template(name, interpreters) -> list[str]`, with the three messages listed in the contract, in that order. There is one duplicate message per duplicated non-blank title.
  - `class TemplateUsage(NamedTuple)` with `student_keys_by_template_id: dict[str, list[str]]`, plus the methods `keys_for(template_id) -> list[str]` (`[]` when absent) and `count_for(template_id) -> int`.
  - `group_usage(pairs: list[tuple[str, str | None]]) -> TemplateUsage`. It skips `None` IDs and sorts each list with `key=str.casefold`.

  The module imports nothing from `tkinter` or `students`.
- [ ] T005 [P] Extend the config contract in `therepy_sessions/interpretation/template_manager/interpreter_configs.py` (research R3; contract table):
  - Add `class ConfigForm(TypedDict)` with `frame: ttk.Frame`, `get_config: Callable[[], dict[str, Any]]`, `reset: Callable[[], None]`, and `load: Callable[[SessionDataSectionInterpreterBase], None]`.
  - Add the abstract property `interpreter_type -> type[SessionDataSectionInterpreterBase]` to `InterpreterConfig`, and fully annotate `name`, `create_config_form(self, parent_frame: tk.Misc) -> ConfigForm`, and `construct_interpreter(self, id: str, config_values: dict[str, Any]) -> SessionDataSectionInterpreterBase`.
  - Implement `interpreter_type` in `TableInterpreterConfig` (`TableInterpreter`), `RunningTallyInterpreterConfig` (`RunningTallyInterpreter`), and `SimpleFormInterpreterConfig` (`SimpleFormInterpreter`).
  - For now, each `create_config_form` returns a `ConfigForm` whose `load` raises `NotImplementedError`. US2 (T015) fills it in. Drop the unused `listbox` and `entry_var` keys.
  - Add the module function `find_config(configs: list[InterpreterConfig], interpreter: SessionDataSectionInterpreterBase) -> InterpreterConfig | None`, which uses `isinstance(interpreter, config.interpreter_type)`.
  - Annotate `STUB_INTERPRETER_CONFIGS: list[InterpreterConfig]`.
- [ ] T006 [P] Amend `docs/conventions/architecture/dependency-injection.md` rule 6 (plan, Principle IV). Add: `DataSheetTemplateManagementWindow` and `TemplateDetailsWindow` receive `load_template_usage: Callable[[], TemplateUsage | None]`, and the management window also receives `clear_template_from_students: Callable[[str], list[str]]`. Both are wired in `program.py` from the one `StudentStore`. Template management never receives the `StudentStore` itself.
- [ ] T007 [P] Amend `docs/conventions/architecture/interpreters.md` (plan, Principle V):
  - In the "Adding a new interpreter type" table, the Config UI piece now also requires `interpreter_type`, `describe(interpreter) -> list[str]`, and a `load` entry in the returned `ConfigForm` (`frame`, `get_config`, `reset`, `load`).
  - Rule 6 adds that `TemplateStore` records `last_template_id` in the templates file, so a deleted template's ID is never given out again.
  - Add a rule 7: an interpreter the SLP did not change is saved as loaded, never rebuilt from its form (research R4).
- [ ] T008 [P] Amend `docs/domain/glossary.md`, "Software concepts" table:
  - Add **Template Description** (`StudentDataSheetTemplate.description`): optional free text describing the sheet layout.
  - Add **Template Usage** (`TemplateUsage`): the students, by Student Key, whose Current Template is a template.
  - Add **Template Details** (`TemplateDetailsWindow`): the window showing one template, in *view mode* (read-only) or *edit mode*.
  - Add **Template Draft** (`TemplateDraft`): the working copy that edit mode changes before Save.
  - Update **Current Template** to say that deleting a template from the app clears it from every student who used it.
- [ ] T009 Update `.specify/memory/constitution.md` (depends on T006–T008):
  - Bump the version to 1.5.0 and set Last Amended to the change date.
  - Prepend a new Sync Impact Report: version change 1.4.0 → 1.5.0 (MINOR: new rules in referenced docs). No principles change. Under Supporting docs, list the changes to dependency-injection.md rule 6, interpreters.md Config UI and rules 6–7, and glossary.md. Templates requiring updates: none.
  - Keep the 1.4.0 report as "Previous report (1.4.0)", the same way earlier reports were kept.

**Checkpoint**: The store reads both file formats, the rules module and config contract exist, and the docs allow the new injections.

---

## Phase 3: User Story 1 - View a template's details (Priority: P1) 🎯 MVP

**Goal**: The SLP opens any template and sees its name, ID, description, every interpreter with its configuration, and the Student Keys of the students who use it. The list shows a Students count for each template.

**Independent Test**: [quickstart.md](quickstart.md) V3. Also check that a template created after this story shows its description in view mode.

- [ ] T010 [P] [US1] In `therepy_sessions/interpretation/template_manager/interpreter_configs.py`, add the abstract `describe(self, interpreter: SessionDataSectionInterpreterBase) -> list[str]` to `InterpreterConfig` and implement it (research R5):
  - Table: `["Columns: " + ", ".join(c.column_name for c in interpreter.columns)]`.
  - Running Tally: `["Tally characters: " + ", ".join(interpreter.tally_choice_options or [])]`.
  - Simple Form: `["Fields: " + ", ".join(interpreter.fields.keys())]`.
  - An empty list renders as `(none)`, e.g. `Columns: (none)`.
- [ ] T011 [US1] Create `therepy_sessions/interpretation/template_manager/template_details_window.py` with `class DetailsMode(Enum)` (`VIEW` and `EDIT`) and `class TemplateDetailsWindow`. Use the constructor signature from [contracts/ui-windows.md](contracts/ui-windows.md). Implement view mode only (depends on T002, T004, T005, T010).
  - **Window**: a modal `Toplevel` built like `TemplateCreatorWindow._setup_window` (transient, `wait_visibility`, `grab_set`, centred on the parent), with the title `Template: <name>`. Put a scrollable container inside it (`Canvas` + `ttk.Scrollbar` + inner `ttk.Frame`) so long content scrolls.
  - **Fields**: a read-only `ttk.Entry` for Name (`state="readonly"`) and a `ttk.Label` for ID. Use a `tk.Text` for Description with `state=tk.DISABLED`. Below it, add a hint label "Describe the sheet layout. Don't include student names.", shown only in edit mode (Principle I). T017 shows it.
  - **Interpreters**: a `ttk.Treeview` with columns `type` and `title`.
    - Insert one parent row per interpreter. Its type is `find_config(...).name`, or `type(interpreter).__name__` when no config handles it. Its title is the interpreter's title, or `(untitled)` when blank.
    - Under each parent, insert its child rows, opened by default. Use `config.describe(interpreter)`. When no config handles an interpreter that loaded (FR-015), build them from `serialize(interpreter)["config"]` as `f"{key}: {value}"` lines (FR-015).
  - **Used by**: a label filled from `load_template_usage()`:
    - `None` → "Could not determine which students use this template."
    - `[]` → "No students use this template."
    - otherwise `", ".join(keys)`
  - **Buttons**: Edit and Close. Edit is disabled until US2 (T017). Close and the window's close button call `destroy()` with no prompt.
  - Store `start_mode`. US2 handles `EDIT`. Until then, treat every mode as `VIEW`.
- [ ] T012 [US1] Update `therepy_sessions/interpretation/template_manager/template_management_window.py` for view mode (depends on T011):
  - Add the constructor parameters `load_template_usage` and `clear_template_from_students`, in the order and with the types shown in the contract. Store them as `_load_template_usage` and `_clear_template_from_students`. Annotate the constructor.
  - Change the tree columns to `("id", "students")`, keeping `#0` as the template name. Drop the duplicate `name` column, and update `_get_selected_template` to read the ID from `values[0]`.
  - `_populate_templates_list` first calls `self._template_store.check_readable()`. On `UnreadableTemplatesError`, it shows `showerror("Error", f"Could not read the templates file: {e}")`, leaves the list empty, and returns (contract "Unreadable templates file").
  - It then calls `self._load_template_usage()` once and fills `students` with `str(usage.count_for(t.id))`, or `Unknown` when usage is `None`.
  - Add a **View** button before Edit. View and a double-click both call `_open_details(DetailsMode.VIEW)`.
  - `_open_details(mode)` reloads the template with `get_template_by_id`. With no selection, it shows "Please select a template first." When the template is gone, it shows "This template no longer exists." and refreshes the list (FR-013). Otherwise, it opens `TemplateDetailsWindow` with `on_saved=self._populate_templates_list`.
  - Leave the Edit and Delete buttons as they are for now.
- [ ] T013 [US1] Wire usage in `therepy_sessions/program.py` (depends on T004, T012):
  - Add `load_template_usage() -> TemplateUsage | None` inside `main()`, as [contracts/ui-windows.md](contracts/ui-windows.md) shows. It catches `UnreadableStudentRecordsError` and returns `None`.
  - Pass `load_template_usage=load_template_usage` to `DataSheetTemplateManagementWindow`.
  - Pass `clear_template_from_students=student_store.clear_current_template`. If T022 has not landed yet, pass a placeholder `lambda template_id: []`, and T025 replaces it.
- [ ] T014 [US1] In `therepy_sessions/interpretation/template_manager/template_creator_window.py`, pass `description=self.description_text.get("1.0", tk.END).strip()` to `TemplateCreateDto` in `_on_create` (FR-006c, research R6). Add a hint label "Describe the sheet layout. Don't include student names." under the Description field (Principle I). Annotate `__init__` (`parent: tk.Misc`, `template_store: TemplateStore`, `save_callback: Callable[[], None]`, `interpreter_configs: list[InterpreterConfig]`, `-> None`).

**Checkpoint**: V3 passes. A newly created template shows its description in view mode.

---

## Phase 4: User Story 2 - Edit a template's name and interpreters (Priority: P2)

**Goal**: From view mode or the list, the SLP edits the name, description, and interpreters, including changing an existing interpreter in its filled-in form and reordering. They save after confirming when students use the template. The Create window applies the same rules.

**Independent Test**: [quickstart.md](quickstart.md) V4, plus the V1 rows for validation, the draft, and `save_confirmation`, and the V2 rows for `edit_template`.

- [ ] T015 [P] [US2] In `therepy_sessions/interpretation/template_manager/interpreter_configs.py`, implement `load(interpreter)` in each config's `create_config_form`, replacing T005's placeholder (research R3, FR-006b). Each `load` calls `reset()` first, then sets `title_var` to `interpreter.title`, then fills the listbox:
  - Table: `[c.column_name for c in interpreter.columns]`
  - Running Tally: `interpreter.tally_choice_options or []`
  - Simple Form: `list(interpreter.fields.keys())`
- [ ] T016 [P] [US2] Add `TemplateDraft` and `save_confirmation` to `therepy_sessions/interpretation/template_manager/template_rules.py` ([data-model.md](data-model.md) Template Draft; contract):
  - `TemplateDraft.from_template(template)` copies the name, the description, and `list(template.interpreters)`.
  - `add(interpreter)` and `replace(index, interpreter)` raise `TitleConflictError` through `find_title_conflict` (with `ignore_index=index` for `replace`) and leave the draft unchanged.
  - The caller builds the replacement with the old interpreter's `id`. `replace` raises `ValueError` if the ids differ, so an interpreter's id never changes (FR-008).
  - `remove(index)` removes the interpreter at that index.
  - `move(index, offset)` swaps the interpreter with its neighbour, and does nothing past either end.
  - `problems()` returns `validate_template(name, interpreters)`.
  - `to_edit_dto()` returns a `TemplateEditDto` with `name.strip()` and the description and interpreters as they are.
  - `save_confirmation(template_name, template_id, usage) -> str | None` returns the two texts from the contract. It returns `None` when usage is known and empty.
- [ ] T017 [US2] Add edit mode to `therepy_sessions/interpretation/template_manager/template_details_window.py`, following [contracts/ui-windows.md](contracts/ui-windows.md) "Mode behavior" (depends on T011, T015, T016).
  - **Entering edit mode**: enable the Edit button. Edit, or `start_mode=EDIT`, builds `self._draft = TemplateDraft.from_template(self._saved)`, makes Name and Description editable, shows the Description hint label, and shows the buttons Save and Cancel instead of Edit and Close. Returning to view mode hides the hint.
  - **Edit controls**: show the edit controls under the tree:
    - Up, Down, and Remove, which call `draft.move` or `draft.remove` and redraw the tree
    - an "Add interpreter" `ttk.Combobox` listing the config names, plus an Add button that empties the form panel for that type
  - **Form panel**: a `ttk.LabelFrame` holding one `ConfigForm` per config, created once, with Apply and Cancel buttons.
    - Selecting a parent row loads its config's form.
    - For an interpreter no config handles, show the text "This interpreter's type can't be edited here." and disable Apply.
  - **Unapplied changes**: record `serialize(config.construct_interpreter(id, form["get_config"]()))` right after each `load` or `reset`. The form has unapplied changes when that value differs from the current one (research R4).
  - **Apply**: build the interpreter with the same `id`, then call `draft.replace(index, ...)`, or `draft.add(...)` with `str(uuid.uuid4())` when adding. On `TitleConflictError`, show the message and keep the form. Then redraw the tree.
  - **Automatic apply (FR-006e)**: before a selection change, and at the start of Save, apply any unapplied changes. If that raises `TitleConflictError`, put the old selection back and stop.
  - **Form Cancel (FR-006f)**: `load` the selected interpreter again, or `reset` the form when adding.
  - **Save**: auto-apply, then:
    1. If `draft.problems()` is not empty, show them in one `showerror`.
    2. Read `usage = self._load_template_usage()` now.
    3. If `save_confirmation(...)` returns text, ask with `askyesno`. On No, return.
    4. Call `edit_template(id, draft.to_edit_dto())`.
       - `None`: show "This template no longer exists.", call `on_saved()`, and `destroy()`.
       - `OSError` or `UnreadableTemplatesError`: call `throw(e, "The change was not saved")` and stay in edit mode.
       - Success: set `self._saved` to the result, call `on_saved()`, and return to view mode. Redraw the window title, fields, and tree, and read `load_template_usage()` again to refresh the Used by line (FR-010b).
  - **Cancel (until US3)**: return to view mode without asking.
- [ ] T018 [US2] In `therepy_sessions/interpretation/template_manager/template_management_window.py` (depends on T017):
  - The Edit button calls `_open_details(DetailsMode.EDIT)`.
  - Remove the `TemplateEditorWindow` import and `_open_template_editor_window`.
  - Delete `therepy_sessions/interpretation/template_manager/template_editor_window.py`.
- [ ] T019 [US2] In `therepy_sessions/interpretation/template_manager/template_creator_window.py`, use the shared rules (research R1, FR-009):
  - `_validate_form` calls `validate_template(self.name_var.get(), self.interpreters)` and shows every returned problem in one `showerror`.
  - `_add_interpreter` uses `find_title_conflict(title, self.interpreters)` in place of its inline check. Keep the message wording from `TitleConflictError`.

**Checkpoint**: V4 passes. The Create window still creates templates and rejects the same problems as edit mode.

---

## Phase 5: User Story 3 - Leave an edit without saving (Priority: P3)

**Goal**: Cancelling or closing edit mode with changes asks before discarding. Unapplied form changes count as changes.

**Independent Test**: [quickstart.md](quickstart.md) V5, plus the V1 rows for `has_changes_from`.

- [ ] T020 [P] [US3] Add `TemplateDraft.has_changes_from(self, template: StudentDataSheetTemplate) -> bool` to `therepy_sessions/interpretation/template_manager/template_rules.py`. It compares `name.strip()`, `description`, and `[serialize(i) for i in interpreters]` with the saved template's name, description, and serialized interpreters ([data-model.md](data-model.md)).
- [ ] T021 [US3] In `therepy_sessions/interpretation/template_manager/template_details_window.py`, change how edit mode is left (depends on T017, T020):
  - Cancel and `WM_DELETE_WINDOW` in edit mode check `self._draft.has_changes_from(self._saved)` or whether the form has unapplied changes.
  - With changes, ask `askyesno("Discard Changes", "Discard your changes to this template?")`. Yes discards the draft, and then Cancel returns to view mode and the close button calls `destroy()`. No does nothing.
  - Without changes, change mode or close without asking.
  - In view mode, `WM_DELETE_WINDOW` closes without asking (FR-011).

**Checkpoint**: V5 passes.

---

## Phase 6: User Story 4 - Delete a template that students use (Priority: P3)

**Goal**: Deleting a template in use names the students, clears their Current Template in one save, and then deletes the template. A failure to clear leaves everything unchanged.

**Independent Test**: [quickstart.md](quickstart.md) V6, plus the V1 delete rows and the V2 `clear_current_template` rows.

- [ ] T022 [P] [US4] Add `clear_current_template(self, template_id: str) -> list[str]` as an abstract method on `StudentStore` in `therepy_sessions/students/student_store.py`, with the docstring from the contract. Implement it in `therepy_sessions/students/json_student_store.py` (research R9):
  - `_load()`, then replace every student whose `current_template_id == template_id` with `replace(student, current_template_id=None)`.
  - Call `_save` once, but only if something matched.
  - Return the matched keys sorted with `key=str.casefold`.

  The method imports nothing new.
- [ ] T023 [P] [US4] Add `delete_confirmation`, `class DeleteResult(Enum)`, `class DeleteOutcome(NamedTuple)`, and `delete_template_and_clear_students(...)` to `therepy_sessions/interpretation/template_manager/template_rules.py`, exactly as [contracts/template-rules.md](contracts/template-rules.md) and [data-model.md](data-model.md) specify. Clearing happens only when usage is known and lists students. An exception from clearing propagates before the delete is called. An exception from the delete propagates when nothing was cleared.
- [ ] T024 [US4] Replace `_on_delete_template` in `therepy_sessions/interpretation/template_manager/template_management_window.py` with the delete flow in [contracts/ui-windows.md](contracts/ui-windows.md) (depends on T023):
  1. Read the usage fresh.
  2. `askyesno` with `delete_confirmation(...)`.
  3. Run `delete_template_and_clear_students(...)`.
  4. Map each outcome or exception to its message. Catch any exception from step 3, whether from clearing or from deleting when nothing was cleared (e.g. `UnreadableTemplatesError`, `OSError`), and show "The template was not deleted: <reason>". No exception may escape the button callback.
  5. Always refresh the list afterwards.
- [ ] T025 [US4] In `therepy_sessions/program.py`, pass `clear_template_from_students=student_store.clear_current_template` to `DataSheetTemplateManagementWindow`, replacing any placeholder from T013 (depends on T022).

**Checkpoint**: V6 passes. Setup → Students shows the cleared students with no Current Template.

---

## Phase 7: Polish & Cross-Cutting Concerns

- [ ] T026 Run [quickstart.md](quickstart.md) V1 and V2 as uncommitted scratch scripts in `$SCRATCH_OFFLINE`, copying the samples in fresh before each row that changes or breaks the files, as the quickstart says. Never use `$SCRATCH` for these. Record any failing row and fix it in the module it names before continuing.
- [ ] T027 Run [quickstart.md](quickstart.md) V3–V7 in the app on `$SCRATCH`, freshly copied from `sample_data/` and untouched by T026. V2's offline interpretation row already covers FR-012 and SC-004. Run V8 too when Textract credentials are available, and note it if skipped.
- [ ] T028 [P] Check the layer rules:
  - `grep -rn "students" therepy_sessions/interpretation/template_manager/` finds no imports.
  - `grep -rn "interpretation\|collection\|clients\|storage" therepy_sessions/students/*.py` finds no new imports.
  - `grep -n "tkinter" therepy_sessions/interpretation/template_manager/template_rules.py` finds nothing.
- [ ] T029 [P] Check annotations on every public member added or changed by T002–T025 in the files listed in the plan's Source Code tree. Fill in any that are missing (Principle VI).
- [ ] T030 Run `git status` and confirm that `therepy_sessions/sample_data/templates.json` and `students.json` are unchanged. The quickstart works only on scratch copies, and the format 1 sample must stay in format 1 for V2. Also confirm that no scratch scripts, token files, or real student artifacts are staged (Development Workflow).

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)** comes first.
- **Foundational (Phase 2)** blocks every story. T009 waits for T006–T008. T002–T008 can otherwise run in parallel.
- **US1 (Phase 3)** needs Phase 2.
- **US2 (Phase 4)** needs US1's `TemplateDetailsWindow` (T011) and the management changes (T012).
- **US3 (Phase 5)** needs US2's edit mode (T017).
- **US4 (Phase 6)** needs only Phase 2 and T012/T013 (the management window's injected callables). T022, T023, and T025 can run in parallel with US2 and US3. T024 edits `template_management_window.py`, so it waits for T018 (see below).
- **Polish (Phase 7)** comes after the stories being shipped.

### Within Each Story

- Rules and store tasks marked [P] come before the window tasks that call them.
- `template_details_window.py` is changed by T011 → T017 → T021, in that order.
- `template_management_window.py` is changed by T012, T018, and T024, one at a time. The default order is T012 → T018 → T024. If US4 goes first, T024 may come before T018.
- `template_rules.py` is changed by T004 → T016 → T020 → T023, in that order. These are not [P] with each other.

### Parallel Opportunities

- Phase 2: T002, T004, T005, T006, T007, and T008 all touch different files. T003 starts once T002 is done.
- US1: T010 can run alongside T011's layout work. T014 is independent of T011–T013.
- US2: T015 (`interpreter_configs.py`) and T016 (`template_rules.py`) can run together.
- US4: T022 (`students/`) and T023 (`template_rules.py`) can run together, and alongside US2 once T016 is merged. T024 runs after T018.

---

## Parallel Example: Phase 2

```text
Task: "T002 description + annotations in student_data_sheet_template.py"
Task: "T004 TemplateUsage, validation, title conflicts in template_rules.py"
Task: "T005 ConfigForm, interpreter_type, find_config in interpreter_configs.py"
Task: "T006–T008 doc amendments"
# then, after T002:
Task: "T003 format 2, last_template_id, atomic save in template_store.py"
```

## Parallel Example: User Story 4

```text
Task: "T022 StudentStore.clear_current_template in students/student_store.py + json_student_store.py"
Task: "T023 delete_confirmation + delete_template_and_clear_students in template_rules.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Phase 1 and Phase 2.
2. Phase 3 (US1): the SLP can finally see what each template holds, and how many students use it.
3. **Stop and validate**: quickstart V2 (store rows) and V3.

### Incremental Delivery

1. US1 → view mode and usage counts.
2. US2 → editing with the save confirmation. The stub window is gone.
3. US3 → the discard confirmation.
4. US4 → a safe delete. This can come before US2 or US3 if a safe delete is wanted sooner. In that case, do T024 before T018, and have T018 keep T024's delete handler (the two tasks only need to run in some order, not this exact one).

---

## Notes

- Commit after each task or logical group. Don't commit scratch scripts.
- The templates file is rewritten in format 2 on the first save. Test only on scratch
  copies, so the format 1 sample stays available for V2.
