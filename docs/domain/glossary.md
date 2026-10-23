# Domain Glossary

SlpDataEntry helps a speech-language pathologist (SLP) turn photographed paper data
sheets from therapy sessions into structured, analyzable data. These are the terms the
code, specs, and UI use. When a term here has a matching class or field, the code MUST
use the same name.

## People and sessions

| Term | Meaning |
| --- | --- |
| **SLP** | Speech-language pathologist. The person using the tool. |
| **Student** | A child receiving speech therapy. The tool never needs a student's full name. |
| **Student Key** | A short identifier for a student, usually initials (e.g. `JA`). It sits unlabeled in the top-left corner of a data sheet. Goals refer to it as `{JA}`. |
| **Therapy Session** | One sitting with a student, bounded by **Time IN** and **Time OUT** on a given **Date**. |
| **Goal** | The IEP-style objective the session works toward, e.g. "identify a possible cause of a given emotion ... 70% accuracy". Free text. |
| **Measure** | How progress toward the goal is observed in this session. Free text. |

## Paper artifacts

| Term | Meaning |
| --- | --- |
| **Student Data Sheet** | The physical sheet the SLP fills out during a session: a header (Student Key, Date, Time IN/OUT, Goal, Measure), then a **Data** section. |
| **Data section** | The part of the sheet holding session observations: tables, tallies, or form fields. |
| **Tally** | A running mark recorded each time the student attempts something, e.g. `Y` (yes), `N` (no), `P` (prompted). A **running tally** is a grid of these, read in order. A table cell can hold a tally too (a **Tally column**). Either way, a tally is saved as its **Tally Summary**. |
| **Prompted / w/out Prompt** | Whether the student needed a cue from the SLP. It is a core metric in the summaries the tool produces. |

## Software concepts

| Term | Code | Meaning |
| --- | --- | --- |
| **Import** | `StudentDataSheetImport` | Raw OCR output for one sheet: `form_data` (label → text), `tables` (list of 2D string arrays), and `table_titles` (the title printed above each table, or `""`). It carries no meaning yet. |
| **Interpretation** | `StudentDataSheet` | The meaningful result: header fields plus typed tables and scalars. |
| **Scalar** | `DataSheetScalarDto` | One typed value (`key`, `value`, `type`, `choice_options`, `typed_value`). `value` is the text as read; the **Typed Value** (`typed_value`) is that value in its type (`int`, `float`, `bool`, `date`, or `str`), or `None` when blank or an Unreadable Value. |
| **Unreadable Value** | `ValueReading` with no `typed_value` | Non-blank text on a sheet that cannot be read as its column's or field's type, such as `N/A` in an Integer column. It has no Typed Value, and its workbook cell holds the text as read, as plain text. It never fails the sheet: the Sheet Outcome warns about it. For a tally, an unknown mark is a character that is not one of the Tally Options. |
| **Rounded Value** | `ValueReading.saved_as` | A non-whole number written in an Integer column or field, such as `7.5`. It is saved as the nearest whole number, with halves rounded away from zero (`7.5` → 8, `-2.5` → -3), and the Sheet Outcome warns about it. |
| **Scalar Type** | `DataSheetScalarType` | How one emitted value is saved: `TEXT`, `INT`, `DECIMAL`, `CHOICE`, `DATE`, `BOOLEAN`, `PERCENT`. Not the same as a Column Type: a Tally column emits several scalars. |
| **Column Type** | `ColumnType` | The type the SLP gives a table column: Text, Integer, Decimal, True/False, Date, Choice, or Tally. It decides how each cell is read, and which Scalars it emits. |
| **Column Definition** | `ColumnDefinition` | One column of a table section: its name, its Column Type, and its Choice Options or Tally Options. |
| **Field Type** | `FIELD_TYPES` | The Column Types a Simple Form field may have: every Column Type except Tally. |
| **Field Configuration** | `FieldConfiguration` | One field of a Simple Form section: its name, its Field Type (`field_type`), and its Choice Options. |
| **Choice Option** | `ChoiceOption` | One allowed code of a Choice column or field (`value`, e.g. `+`, `NR`), with an optional description of what it means (e.g. "correct"). A description never identifies a student. |
| **Tally Option** | `TallyOption` | One allowed mark of a Tally column or Running Tally section (`mark`, exactly one character), with an optional description. |
| **Tally Summary** | `TallySummary` | What a tally is saved as: the marks in order, a count per Tally Option, the total, and a percentage per option. Each is its own key (e.g. `Attempts`, `Attempts Y`, `Attempts Total`, `Attempts Y %`). Unknown marks are left out of the counts, total, and percentages; the marks value then holds the text as read, unknown marks included. |
| **Section Interpreter** | `SessionDataSectionInterpreterBase` | Gives meaning to one kind of data section. Current kinds: `TableInterpreter`, `RunningTallyInterpreter`, `SimpleFormInterpreter`. |
| **Data Sheet Template** | `StudentDataSheetTemplate` | A named, saved set of configured section interpreters describing one sheet layout. An SLP reuses it for every sheet with that layout. |
| **Interpreter Config** | `InterpreterConfig` | The UI form that lets the SLP configure a section interpreter while building a template. |
| **Template Store** | `TemplateStore` | Saves templates to and loads them from `templates.json` in the Workspace. |
| **Current Template** | `Student.current_template_id` | The Data Sheet Template used to interpret a student's data sheets. It is optional. Deleting a template from the app clears it from every student who used it. It may still refer to a template removed outside the app. |
| **Template Description** | `StudentDataSheetTemplate.description` | Optional free text describing the sheet layout a template reads. It never identifies a student. |
| **Template Usage** | `TemplateUsage` | The students, by Student Key, whose Current Template is a given template. |
| **Template Details** | `TemplateDetailsWindow` | The window showing one saved template, in *view mode* (read-only) or *edit mode*. |
| **Template Draft** | `TemplateDraft` | The working copy of a template that edit mode changes before Save. |
| **Template Form** | `TemplateForm` | The fields of one template (name, description, and interpreters) shared by the Create and Template Details windows. It shows a Template Draft and lets the SLP change it, and never saves anything itself. |
| **Student Store** | `StudentStore` | Saves and loads Students, identified by Student Key. The current implementation, `JsonStudentStore`, keeps them in `students.json` in the Workspace. |
| **Workspace** | `WorkspaceFiles` | The folder chosen at launch that holds `students.json` (the Student Store's file) and `templates.json` (the Template Store's file). Only a complete Workspace can be opened. |
| **Workspace State** | `WorkspaceState` | Whether a Workspace is complete (both files), partial (one), or not set up (neither). A folder that is not set up can become a Workspace by starting a new one; a partial one is fixed only by restoring the missing file. |
| **Selected File** | `SelectedFile` | An image in the Import window's list. It keeps its Import while the window is open, so a retry does not read it again unless the file changed. |
| **Import Batch** | `SheetImportBatch` | The list of Selected Files and the rules for importing them. |
| **Import Run** | | The Selected Files processed by one press of Import (those not yet succeeded). |
| **Sheet Outcome** | `SheetOutcome` | One file's result: *not imported*, *succeeded*, *succeeded with warnings*, or *failed* with a reason that names the fix. *Succeeded with warnings* (`SUCCEEDED` with `warnings`) counts as succeeded for every purpose, and lists every Unreadable Value, Rounded Value, and unknown tally mark on the sheet. |
| **Data Sheet Store** | `DataSheetStore` | The storage mechanism for interpreted data sheets. The import code and its window save sheets only through it. The current implementation, `GoogleDriveDataSheetStore`, saves to Student Session Workbooks. |
| **Template Structure** | `TemplateShape.structure_identity()` | The shape of a template that decides where its sessions are saved: its sections and, within each, the set of field, column, and tally keys, compared without regard to order. A template's name, description, ids, Column Types, choices, and option descriptions are not part of it. Tally Options are, through the Tally Summary keys they add. |
| **Student Session Workbook** | `GoogleDriveDataSheetStore` | The Google Sheet holding every saved session for one Student Key and one Template Structure, in the Therapy Data Folder. It is named from the Student Key and the name of the template that started it, and found by a hidden label, so renaming it does not lose it. |
| **Session Tab** | | One tab in a Student Session Workbook, holding the values of one imported sheet. It is named with that sheet's Session Moment. |
| **Session Moment** | `SessionMoment` | A sheet's session Date plus its Time IN, as read from the sheet. It names a Session Tab and identifies the session within its workbook. A sheet with a blank Time IN has a date-only Session Moment, which never identifies a duplicate. |
| **Workbook Layout Order** | `WorkbookLayout` | The order of sections, form fields, and columns taken from the template that started a workbook. Every tab in that workbook uses it. |
| **Workbook Key** | `WORKBOOK_KEY_TAB_NAME` | The last tab of every Student Session Workbook, listing each Choice and Tally code of the template with what it means. It is rebuilt with every new Session Tab, holds only template text, and is never a Session Tab. |
| **Therapy Data Folder** | `DATA_FOLDER_PATH` | The Google Drive folder `SLP Therepy Data/Current Year` holding every Student Session Workbook. |

## Pipeline in one line

Photo of a data sheet → **Collection** (OCR into an Import) → **Interpretation**
(apply a Template to get a StudentDataSheet) → **Storage** (save to the student's Student Session
Workbook through the Data Sheet Store).

See [student-data-privacy.md](student-data-privacy.md) for how student information must be handled.
