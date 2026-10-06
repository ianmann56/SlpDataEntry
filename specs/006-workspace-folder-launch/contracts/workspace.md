# Contract: Workspace

**Feature**: [../spec.md](../spec.md) | **Data model**: [../data-model.md](../data-model.md)

These are the public members this feature adds or changes. All of them are fully
annotated (Principle VI).

## `workspace/workspace.py` (new; no Tkinter)

```python
STUDENTS_FILE_NAME: str = "students.json"
TEMPLATES_FILE_NAME: str = "templates.json"


class WorkspaceState(Enum):
    COMPLETE = "complete"
    PARTIAL = "partial"
    NOT_SET_UP = "not_set_up"


class WorkspaceFiles(NamedTuple):
    folder: str
    students_file: str
    templates_file: str


class WorkspaceInspection(NamedTuple):
    files: WorkspaceFiles
    state: WorkspaceState
    missing_file: str | None        # set only when state is PARTIAL


class WorkspaceFolderError(Exception):
    def __init__(self, path: str, reason: str) -> None: ...
    path: str
    reason: str


class WorkspaceCreateError(Exception):
    def __init__(self, path: str, reason: str) -> None: ...
    path: str
    reason: str


def workspace_files(folder: str) -> WorkspaceFiles:
    """Return the Workspace file paths in `folder`. Touches nothing on disk."""


def inspect_workspace(folder: str) -> WorkspaceInspection:
    """
    Decide the Workspace State of `folder`.

    Raises:
        WorkspaceFolderError: The folder does not exist or is not a folder, or a
            Workspace file name in it is a folder
    """


def open_workspace(
    folder: str,
    ask_to_start_new_workspace: Callable[[str], bool],
    show_missing_workspace_file: Callable[[WorkspaceInspection], None],
    create_students_file: Callable[[], None],
    create_templates_file: Callable[[], None],
) -> WorkspaceFiles | None:
    """
    Open the Workspace in `folder`, asking the SLP when it is not complete.

    Returns:
        The Workspace files when the Workspace is (now) complete, or None when the SLP
        declined a new Workspace or the Workspace is partial. Nothing is created,
        changed, or deleted when None is returned.

    Raises:
        WorkspaceFolderError: From inspect_workspace
        WorkspaceCreateError: A new Workspace file could not be created; any file
            created for it was removed again
    """
```

### `open_workspace` behavior

| State | Calls | Returns |
| --- | --- | --- |
| `COMPLETE` | nothing | `files` |
| `PARTIAL` | `show_missing_workspace_file(inspection)` | `None` |
| `NOT_SET_UP`, declined | `ask_to_start_new_workspace(folder)` returns `False` | `None` |
| `NOT_SET_UP`, accepted | `create_students_file()`, then `create_templates_file()` | `files` |

If `create_students_file` raises, it raises `WorkspaceCreateError` for the students file.
If `create_templates_file` raises, it removes the students file and raises
`WorkspaceCreateError` for the templates file. If that removal also fails, the reason
names the students file too. `OSError` (including `FileExistsError`) is the only error
it wraps. Anything else propagates.

## `workspace/workspace_dialogs.py` (new; Tkinter only)

```python
def ask_to_start_new_workspace(parent: tk.Misc, folder: str) -> bool:
    """
    Say the folder is not set up as a Workspace yet and ask whether to start one there.

    Returns:
        True only if the SLP pressed Start New Workspace. Close and the title bar
        return False.
    """


def show_missing_workspace_file(parent: tk.Misc, inspection: WorkspaceInspection) -> None:
    """
    Name the missing Workspace file and what it holds, and tell the SLP to restore it
    next to the other file in the same folder and launch again. Offers only Close.
    """


def show_workspace_error(parent: tk.Misc, error: WorkspaceFolderError | WorkspaceCreateError) -> None:
    """Show the problem and the path it is about. Offers only Close."""
```

Every dialog:

- is a modal ttk `Toplevel`, themed like the other windows (FR-014)
- is centered on the screen and returns when it is closed
- shows only paths and fixed text, never file contents (FR-016)

The message text is defined in [launch.md](launch.md).

`workspace_dialogs.py` imports from `workspace.workspace` and Tkinter only.

## Store additions

```python
class JsonStudentStore(StudentStore):
    def create_empty_file(self) -> None:
        """
        Create the student records file holding no Students.

        Raises:
            FileExistsError: The file already exists; it is left unchanged
            OSError: The file could not be written; any partial file is removed
        """


class TemplateStore:
    def create_empty_file(self) -> None:
        """
        Create the templates file holding no Templates, with last_template_id 0.

        Raises:
            FileExistsError: The file already exists; it is left unchanged
            OSError: The file could not be written; any partial file is removed
        """
```

`create_empty_file` is not added to the `StudentStore` ABC. Creating a file is specific
to the JSON store, and only `program.py` calls it, through `open_workspace`.

## `program.py` wiring

```python
def parse_command_line_args() -> str | None: ...   # see launch.md

def main() -> None:
    folder_arg = parse_command_line_args()
    root = tk.Tk()
    sv_ttk.set_theme(darkdetect.theme())
    root.withdraw()

    folder = folder_arg if folder_arg is not None else filedialog.askdirectory(
        parent=root, title="Choose Workspace Folder", mustexist=True)
    if not folder:
        root.destroy(); return

    files = workspace_files(folder)
    template_store = TemplateStore(files.templates_file)
    student_store: StudentStore = JsonStudentStore(files.students_file)

    try:
        opened = open_workspace(
            folder,
            ask_to_start_new_workspace=lambda f: ask_to_start_new_workspace(root, f),
            show_missing_workspace_file=lambda i: show_missing_workspace_file(root, i),
            create_students_file=student_store.create_empty_file,
            create_templates_file=template_store.create_empty_file,
        )
    except (WorkspaceFolderError, WorkspaceCreateError) as e:
        show_workspace_error(root, e)
        opened = None
    if opened is None:
        root.destroy(); return

    root.deiconify()
    ...  # everything below is unchanged: providers, open_* paths, HomeWindow, mainloop
```

This is illustrative only; the exact structure is left to implementation. The rules
that must hold are:

- Nothing builds a window other than the dialogs and the picker until `open_workspace`
  returns files.
- Removed: `validate_storage_file_path` and `validate_distinct_storage_files`.
