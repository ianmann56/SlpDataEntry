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
| **Session Sheet** | `create_therapy_session_sheet` | The Google Sheet the tool writes as output, with summary text and charts. |

## Pipeline in one line

Photo of a data sheet → **Collection** (OCR into an Import) → **Interpretation**
(apply a Template to get a StudentDataSheet) → **Storage** (write a Session Sheet to Google Sheets).

See [student-data-privacy.md](student-data-privacy.md) for how student information must be handled.
