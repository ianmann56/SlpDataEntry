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
| **Tally** | A running mark recorded each time the student attempts something, e.g. `Y` (yes), `N` (no), `P` (prompted). A **running tally** is a grid of these, read in order. |
| **Prompted / w/out Prompt** | Whether the student needed a cue from the SLP. It is a core metric in the summaries the tool produces. |

## Software concepts

| Term | Code | Meaning |
| --- | --- | --- |
| **Import** | `StudentDataSheetImport` | Raw OCR output for one sheet: `form_data` (label → text) and `tables` (list of 2D string arrays). It carries no meaning yet. |
| **Interpretation** | `StudentDataSheet` | The meaningful result: header fields plus typed tables and scalars. |
| **Scalar** | `DataSheetScalarDto` | One typed value (`key`, `value`, `type`, `choice_options`). |
| **Scalar Type** | `DataSheetScalarType` | `TEXT`, `INT`, `CHOICE`, `DATE`, `BOOLEAN`. |
| **Section Interpreter** | `SessionDataSectionInterpreterBase` | Gives meaning to one kind of data section. Current kinds: `TableInterpreter`, `RunningTallyInterpreter`, `SimpleFormInterpreter`. |
| **Data Sheet Template** | `StudentDataSheetTemplate` | A named, saved set of configured section interpreters describing one sheet layout. An SLP reuses it for every sheet with that layout. |
| **Interpreter Config** | `InterpreterConfig` | The UI form that lets the SLP configure a section interpreter while building a template. |
| **Template Store** | `TemplateStore` | Saves templates to and loads them from a local JSON file. |
| **Current Template** | `Student.current_template_id` | The Data Sheet Template used to interpret a student's data sheets. It is optional. Deleting a template from the app clears it from every student who used it. It may still refer to a template removed outside the app. |
| **Template Description** | `StudentDataSheetTemplate.description` | Optional free text describing the sheet layout a template reads. It never identifies a student. |
| **Template Usage** | `TemplateUsage` | The students, by Student Key, whose Current Template is a given template. |
| **Template Details** | `TemplateDetailsWindow` | The window showing one saved template, in *view mode* (read-only) or *edit mode*. |
| **Template Draft** | `TemplateDraft` | The working copy of a template that edit mode changes before Save. |
| **Template Form** | `TemplateForm` | The fields of one template (name, description, and interpreters) shared by the Create and Template Details windows. It shows a Template Draft and lets the SLP change it, and never saves anything itself. |
| **Student Store** | `StudentStore` | Saves and loads Students, identified by Student Key. The current implementation, `JsonStudentStore`, keeps them in a local JSON file given at launch. |
| **Selected File** | `SelectedFile` | An image in the Import window's list. It keeps its Import while the window is open, so a retry does not read it again unless the file changed. |
| **Import Batch** | `SheetImportBatch` | The list of Selected Files and the rules for importing them. |
| **Import Run** | | The Selected Files processed by one press of Import (those not yet succeeded). |
| **Sheet Outcome** | `SheetOutcome` | One file's result: *not imported*, *succeeded*, or *failed* with a reason that names the fix. |
| **Data Sheet Store** | `DataSheetStore` | The storage mechanism for interpreted data sheets. The import code and its window save sheets only through it. The current implementation, `GoogleDriveDataSheetStore`, saves to Student Session Workbooks. |
| **Template Structure** | `TemplateShape.structure_identity()` | The shape of a template that decides where its sessions are saved: its sections and, within each, the set of field, column, and tally keys, compared without regard to order. A template's name, description, ids, value types, and choice options are not part of it. |
| **Student Session Workbook** | `GoogleDriveDataSheetStore` | The Google Sheet holding every saved session for one Student Key and one Template Structure, in the Therapy Data Folder. It is named from the Student Key and the name of the template that started it, and found by a hidden label, so renaming it does not lose it. |
| **Session Tab** | | One tab in a Student Session Workbook, holding the values of one imported sheet. It is named with that sheet's Session Moment. |
| **Session Moment** | `SessionMoment` | A sheet's session Date plus its Time IN, as read from the sheet. It names a Session Tab and identifies the session within its workbook. A sheet with a blank Time IN has a date-only Session Moment, which never identifies a duplicate. |
| **Workbook Layout Order** | `WorkbookLayout` | The order of sections, form fields, and columns taken from the template that started a workbook. Every tab in that workbook uses it. |
| **Therapy Data Folder** | `DATA_FOLDER_PATH` | The Google Drive folder `SLP Therepy Data/Current Year` holding every Student Session Workbook. |

## Pipeline in one line

Photo of a data sheet → **Collection** (OCR into an Import) → **Interpretation**
(apply a Template to get a StudentDataSheet) → **Storage** (save to the student's Student Session
Workbook through the Data Sheet Store).

See [student-data-privacy.md](student-data-privacy.md) for how student information must be handled.
