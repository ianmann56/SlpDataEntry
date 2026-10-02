# Contract: Template Rules, Stores, and Interpreter Configs

**Feature**: [../spec.md](../spec.md) | **Data model**: [../data-model.md](../data-model.md)

Every public member below is fully annotated (Principle VI). None of the modules imports
Tkinter except `interpreter_configs.py`, which already does.

## `interpretation/template_manager/template_rules.py` (new)

```python
class TitleConflictError(ValueError):
    """Another interpreter in the template already has this non-blank title. The message is shown to the SLP."""
    def __init__(self, title: str) -> None: ...

def find_title_conflict(
    title: str,
    interpreters: list[SessionDataSectionInterpreterBase],
    ignore_index: int | None = None,
) -> bool:
    """True when a non-blank, trimmed `title` matches another interpreter's trimmed title exactly (R2)."""

def validate_template(name: str, interpreters: list[SessionDataSectionInterpreterBase]) -> list[str]:
    """
    Problems, in order, or [] when valid (FR-009). Used by the Create window and edit mode.
      "Template name is required."                 - name is blank after trimming
      "At least one interpreter must be added."    - interpreters is empty
      'The title "<t>" is used by more than one interpreter.'  - once per duplicated title
    """

class TemplateUsage(NamedTuple): ...          # see data-model.md
def group_usage(pairs: list[tuple[str, str | None]]) -> TemplateUsage:
    """Build usage from (student_key, current_template_id) pairs. A None template id is skipped."""

class TemplateDraft: ...                      # see data-model.md
    @classmethod
    def from_template(cls, template: StudentDataSheetTemplate) -> "TemplateDraft": ...

def save_confirmation(template_name: str, template_id: str, usage: TemplateUsage | None) -> str | None:
    """
    None when no confirmation is needed (usage known, nobody uses the template).
    Otherwise the confirmation text:
      used:    'Saving changes "<name>" for students JA, MK. Their next data sheets will be read with the changed template.'
      unknown: 'It could not be checked which students use "<name>". Save the changes anyway?'
    """

def delete_confirmation(template_name: str, template_id: str, usage: TemplateUsage | None) -> str:
    """
      unused:  'Are you sure you want to delete the template "<name>"?'
      used:    'Students JA, MK use "<name>". Deleting it leaves them with no Current Template, and they will need a new one.'
      unknown: 'It could not be checked which students use "<name>". Delete it anyway? No student records will be changed.'
    """

class DeleteResult(Enum): ...                 # see data-model.md
class DeleteOutcome(NamedTuple): ...

def delete_template_and_clear_students(
    template_id: str,
    usage: TemplateUsage | None,
    clear_template_from_students: Callable[[str], list[str]],
    delete_template: Callable[[str], bool],
) -> DeleteOutcome:
    """
    1. If usage is known and lists any students, call clear_template_from_students(template_id).
       An exception from it propagates: no template change has happened (FR-010f).
    2. Call delete_template(template_id). False -> NOT_FOUND. An exception after a
       clear -> FAILED_AFTER_CLEARING with the exception text in `detail`.
       An exception with nothing cleared propagates.
    """
```

Student Keys in messages are joined with ", " in the order of the usage list. No
other student information is ever included (FR-010b, Principle I).

## `interpretation/template_store.py` (changed)

```python
@dataclass
class TemplateCreateDto:
    name: str
    configured_interpreters: list[SessionDataSectionInterpreterBase]
    description: str = ""

@dataclass
class TemplateEditDto:
    name: str
    configured_interpreters: list[SessionDataSectionInterpreterBase]
    description: str = ""

class TemplateStore:
    def __init__(self, storage_file_path: str) -> None: ...
    def check_readable(self) -> None: ...                       # accepts format 1 and format 2 (R10)
    def get_all_templates(self) -> list[StudentDataSheetTemplate]: ...
    def get_template_by_id(self, template_id: str) -> StudentDataSheetTemplate | None: ...
    def create_template(self, create_dto: TemplateCreateDto) -> StudentDataSheetTemplate: ...
    def edit_template(self, template_id: str, edit_dto: TemplateEditDto) -> StudentDataSheetTemplate | None: ...
    def delete_template(self, template_id: str) -> bool: ...
    def generate_new_id(self) -> str: ...                       # never returns an id used before (R10)
```

Behavior changes:
- Entries are read with `description` defaulting to `""`. They are written with it (R6).
- `create_template`, `edit_template`, `delete_template`, and `generate_new_id` raise
  `UnreadableTemplatesError` when the file is unreadable or has `format_version` > 2,
  and they write nothing. Only `get_all_templates` and `get_template_by_id` return an
  empty result for an unreadable file (R10).
- Every write is format 2 with `last_template_id`, written to a temp file and then
  replaced. A write failure raises `OSError`, and the old file stays as it was.
- `create_template` saves the new id as `last_template_id` in the same write.
- `edit_template` keeps the entry's position in the list.

## `students/student_store.py` and `json_student_store.py` (changed)

```python
class StudentStore(ABC):
    @abstractmethod
    def clear_current_template(self, template_id: str) -> list[str]:
        """
        Set current_template_id to None for every student using `template_id`, in one save.
        Returns the cleared Student Keys sorted ignoring case; [] (and no write) when none match.

        Raises:
            UnreadableStudentRecordsError: If the saved records cannot be read
            OSError: If the records cannot be saved; no student is changed
        """
```

`students/` still imports nothing from the pipeline (layers rule 8).

## `interpretation/template_manager/interpreter_configs.py` (changed)

```python
class ConfigForm(TypedDict):
    frame: ttk.Frame
    get_config: Callable[[], dict[str, Any]]                        # values for construct_interpreter
    reset: Callable[[], None]
    load: Callable[[SessionDataSectionInterpreterBase], None]       # NEW (R3)

class InterpreterConfig(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...
    @property
    @abstractmethod
    def interpreter_type(self) -> type[SessionDataSectionInterpreterBase]: ...   # NEW (R3)
    @abstractmethod
    def create_config_form(self, parent_frame: tk.Misc) -> ConfigForm: ...
    @abstractmethod
    def construct_interpreter(self, id: str, config_values: dict[str, Any]) -> SessionDataSectionInterpreterBase: ...
    @abstractmethod
    def describe(self, interpreter: SessionDataSectionInterpreterBase) -> list[str]: ...   # NEW (R5)

def find_config(
    configs: list[InterpreterConfig], interpreter: SessionDataSectionInterpreterBase
) -> InterpreterConfig | None: ...
```

| Config | `interpreter_type` | `load` fills | `describe` lines |
| --- | --- | --- | --- |
| `TableInterpreterConfig` | `TableInterpreter` | title, column names | `Columns: A, B, C` |
| `RunningTallyInterpreterConfig` | `RunningTallyInterpreter` | title, tally characters | `Tally characters: Y, N, P` |
| `SimpleFormInterpreterConfig` | `SimpleFormInterpreter` | title, field names | `Fields: Define tone, ...` |

An empty list is described as `(none)`. The extra form keys (`listbox`, `entry_var`) are
dropped, because nothing reads them.

## `interpretation/template_manager/student_data_sheet_template.py` (changed)

This module gains `description: str` (a property, defaulting to `""`) and type
annotations on every public member.
