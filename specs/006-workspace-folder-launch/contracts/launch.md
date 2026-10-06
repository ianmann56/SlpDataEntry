# Contract: Launch Command and Workspace Messages

**Feature**: [../spec.md](../spec.md)

This is what the SLP sees: the command line, the picker, and the text of each dialog.
`<folder>`, `<missing>`, and `<present>` stand for full paths. Wording may be polished in
implementation, but each message must keep the facts listed under it.

## Command line

```text
python program.py [<workspace_folder>]
```

| Invocation | Result | Exit code |
| --- | --- | --- |
| `program.py` | The folder picker opens. | 0 when closed normally |
| `program.py <folder>` | The folder is opened as a Workspace. | 0 when closed normally |
| `program.py <a> <b> ...` (including the old `templates.json students.json` form) | The usage message is printed, and no window opens. | 1 |

Usage message (console):

```text
Usage: python program.py [<workspace_folder>]
The Workspace folder holds students.json and templates.json.
Leave the folder out to choose it from a folder picker.
Example: python program.py ~/SLP-Workspace
```

## Folder picker

- Title: **Choose Workspace Folder**
- It starts in the current working directory and lists existing folders only.
- Cancel or close: the app exits, and nothing is created.

## Dialogs

Each dialog has the window title shown here. Closing it from the title bar, or pressing
Escape, does what **Close** does.

### New Workspace (state `NOT_SET_UP`)

Title: **Start a New Workspace?**

> This folder doesn't appear to be set up as a Workspace yet:
>
> `<folder>`
>
> Start a new Workspace here? This creates an empty students.json and an empty
> templates.json in this folder.

Buttons: **Start New Workspace** · **Close**

Must keep: the folder path, that it isn't set up yet, and which two files would be
created.

### Missing file (state `PARTIAL`)

Title: **Workspace File Missing**

When `students.json` is missing:

> The student records file is missing from this Workspace:
>
> `<missing>`
>
> Restore students.json next to templates.json in the same folder, then launch again.

When `templates.json` is missing:

> The Templates file is missing from this Workspace:
>
> `<missing>`
>
> Restore templates.json next to students.json in the same folder, then launch again.

Button: **Close** only.

Must keep: the missing file's name and path, what it holds, that it goes next to the
other file in the same folder, and launching again. It must not offer any way to
continue or start fresh (FR-008).

### Folder error

Title: **Can't Open Workspace**

| Cause | Body |
| --- | --- |
| The folder does not exist | "This folder doesn't exist: `<folder>`" |
| The path is a file | "This isn't a folder: `<folder>`. Choose the folder that holds students.json and templates.json." |
| A Workspace name is a folder | "`<path>` is a folder, but it should be a file. Fix this in the Workspace folder, then launch again." |
| A Workspace name is a broken link | "`<path>` is a link to a file that doesn't exist. Fix this in the Workspace folder, then launch again." |
| A new Workspace file could not be created | "Couldn't create `<path>`: `<reason>`. Nothing was set up in this folder." |

Button: **Close** only.

Must keep: the path, and what is wrong with it.
