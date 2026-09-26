<!--
Sync Impact Report
- Version change: (unratified template) → 1.0.0
- Modified principles: all placeholders replaced (initial ratification)
  - [PRINCIPLE_1_NAME] → I. Student Data Privacy (NON-NEGOTIABLE)
  - [PRINCIPLE_2_NAME] → II. Domain Language Fidelity
  - [PRINCIPLE_3_NAME] → III. Layered Pipeline
  - [PRINCIPLE_4_NAME] → IV. Injected External Services
  - [PRINCIPLE_5_NAME] → V. Pluggable Interpreters & Templates
- Added sections: Technology Constraints; Development Workflow; Referenced Documents
- Removed sections: none
- Supporting docs created (detailed rules live here; the constitution references them):
  - docs/domain/README.md, glossary.md, student-data-privacy.md
  - docs/conventions/architecture/README.md, layers.md, dependency-injection.md,
    interpreters.md
- Templates requiring updates: none. plan-template.md reads the constitution at runtime
  for its "Constitution Check" gate.
- Deferred TODOs: none
-->

# SlpDataEntry Constitution

This constitution states the project's non-negotiable principles. Detailed rules,
vocabulary, and examples live in `docs/`. Each principle links to the document that
defines it. The linked documents are binding as part of this constitution.

## Core Principles

### I. Student Data Privacy (NON-NEGOTIABLE)

Data sheets describe minors in special education. Code and specs MUST identify students
only by Student Key. Real student data and credentials MUST NOT be committed. Student
data MUST go only to approved external services (currently AWS Textract and Google
Sheets/Drive).

Full rules: [docs/domain/student-data-privacy.md](../../docs/domain/student-data-privacy.md)

Rationale: a leak harms a child and the SLP's professional standing. No feature is worth that.

### II. Domain Language Fidelity

Specs, code identifiers, UI labels, and docs MUST use the terms defined in the glossary
(Student Key, Data Sheet, Template, Section Interpreter, Scalar, Tally, etc.). A new
domain concept MUST be added to the glossary in the same change that introduces it.

Full rules: [docs/domain/glossary.md](../../docs/domain/glossary.md)

Rationale: the project is small and personal. One shared vocabulary lets the SLP, the
developer, and AI agents reason about it without translating between terms.

### III. Layered Pipeline

Code MUST follow the one-way Collection → Interpretation → Storage pipeline. Only
`StudentDataSheetImport` and `StudentDataSheet` cross layer boundaries. Interpretation
MUST be pure (no I/O). UI code MUST NOT contain business rules. `program.py` is the only
composition root.

Full rules: [docs/conventions/architecture/layers.md](../../docs/conventions/architecture/layers.md)

Rationale: OCR vendors, output formats, and sheet layouts each change on their own
schedule. Separate layers let one change without affecting the others.

### IV. Injected External Services

Only `clients/` may construct AWS and Google clients. Consumers receive them through
`inject_*` provider callables. Modules MUST NOT create clients or read credentials at
import time. Adapters MUST translate vendor exceptions at the boundary.

Full rules: [docs/conventions/architecture/dependency-injection.md](../../docs/conventions/architecture/dependency-injection.md)

Rationale: injection lets the logic run and be verified without network access, paid
API calls, or real credentials.

### V. Pluggable Interpreters & Templates

A new data-sheet layout MUST be supported by adding or configuring section interpreters,
not by editing the core flow. A new interpreter type MUST ship with its interpreter,
config UI, serializer, and registration. Serialized templates MUST stay loadable across
changes. A sheet that does not match its template MUST fail loudly.

Full rules: [docs/conventions/architecture/interpreters.md](../../docs/conventions/architecture/interpreters.md)

Rationale: every student's sheet can differ. The SLP builds templates without writing
code, and the templates they have saved must keep working.

## Technology Constraints

- Language: Python 3, managed with `venv` at `.venv/`. Dependencies are pinned in
  `pip_requirements.txt`, and system-level or explanatory dependencies are listed in
  `ALL_DEPENDENCIES.md`. Both MUST be updated in the same change that adds a dependency.
- Desktop UI: Tkinter with the `sv-ttk` theme and `darkdetect` for light/dark mode.
- OCR: AWS Textract (`boto3`) using the `FORMS` and `TABLES` features.
- Output: Google Sheets and Drive through `google-api-python-client` with OAuth.
- Local persistence: JSON files (e.g. the template store), written with UTF-8 and
  `indent=2`.
- A new runtime dependency or external service MUST be justified in the feature's plan.
  An external service that receives student data also triggers Principle I.

## Development Workflow

- Features follow the Spec Kit flow: `/speckit-specify` → `/speckit-plan` →
  `/speckit-tasks` → `/speckit-implement`. Every plan MUST pass a Constitution Check
  against Principles I–V.
- Interpretation and collection-normalization logic SHOULD be verifiable offline with
  synthetic sample inputs under `therepy_sessions/sample_data/` (see Principle I for
  what those samples may contain).
- Before merging, confirm that no secrets, token files, or real student artifacts are
  staged.
- Commented-out experiments and debug scaffolding in `program.py` are acceptable while
  exploring, but MUST NOT become the only path to a shipped feature.

## Referenced Documents

| Area | Location |
| --- | --- |
| Domain vocabulary and rules | [docs/domain/](../../docs/domain/README.md) |
| Architecture conventions | [docs/conventions/architecture/](../../docs/conventions/architecture/README.md) |

A referenced document may be edited on its own. Any edit that adds, removes, or changes
the meaning of a rule counts as an amendment and follows the Governance procedure below.

## Governance

- This constitution and its referenced documents take precedence over other practices in
  this repository. Where they conflict, the constitution wins.
- Amendment procedure: edit the constitution and/or referenced docs, update the Sync
  Impact Report at the top of this file, bump the version, and set Last Amended to the
  change date.
- Versioning policy (semantic):
  - MAJOR: a principle is removed or redefined in a backward-incompatible way.
  - MINOR: a principle or section is added, or guidance is materially expanded
    (including new rules in a referenced doc).
  - PATCH: clarifications, wording, and typo fixes that do not change meaning.
- Compliance: `/speckit-plan` Constitution Checks and code reviews MUST verify adherence.
  Any justified deviation MUST be recorded in the plan's Complexity Tracking section.
- Runtime guidance for agents lives in `AGENTS.md` (via `CLAUDE.md`) and the project
  `README.md`.

**Version**: 1.0.0 | **Ratified**: 2026-09-26 | **Last Amended**: 2026-09-26
