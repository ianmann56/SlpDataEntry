# therepy_sessions
A tool for easily importing and analyzing speech therapy session data

## Dependencies

Dependencies are described in `./ALL_DEPENDENCIES.md`.

## How to Run

From this folder, launch the program with your Workspace folder:

```sh
../.venv/bin/python program.py [<workspace_folder>]
```

The Workspace folder holds `students.json` (the student records) and `templates.json`
(the Data Sheet Templates). Leave the folder out to choose it from a folder picker.

- A folder holding neither file can be set up as a new Workspace when you launch with it.
- A folder holding only one of them won't open until the missing file is put back next
  to the other one.
- To move from the old two-file launch, put your current student records file and
  templates file in one folder, named `students.json` and `templates.json`.

Load AWS credentials: source `/media/lydian/Programming/Personal/slp_data_entry_aws_credentials.sh`. This will set up the `$AWS_ACCESS_KEY_ID` and `$AWS_SECRET_ACCESS_KEY` environment variables for when you call AWS services as long as you're process using the services is started from that shell.