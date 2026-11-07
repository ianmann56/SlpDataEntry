# Feature Specification: Hide Analysis Results

**Feature Branch**: `010-hide-analysis-results`

**Created**: 2026-11-06

**Status**: Draft

**Input**: User description: "As a SLP, I want to configure whether an analysis result will show up in imported data sheets so that I can hide calculations that are only there to lead to another calculation."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Hide a stepping-stone calculation (Priority: P1)

The SLP has a template whose Data Sheet Analysis builds a final number in steps. For example, "Correct trials" and "Total trials" in a lower layer feed "Accuracy" in a higher layer. Only "Accuracy" means anything when reading a session; the other two only exist to work it out. While editing the template, the SLP selects "Correct trials", clears **Show in imported sheets** in the editor panel, and presses Apply. They do the same for "Total trials" and save the template.

From then on, every sheet imported with that template shows "Accuracy" but not "Correct trials" or "Total trials". "Accuracy" is still worked out from them as before.

**Why this priority**: This is the whole request. Without it, every intermediate step clutters each imported session.

**Independent Test**: Create a template with two lower-layer calculations and one higher-layer calculation that uses both. Hide the two lower ones, save, and reopen. Confirm the two are marked hidden, the higher one is marked shown, and the higher one still uses the hidden two without any problem.

**Acceptance Scenarios**:

1. **Given** a template in edit mode or being created, **When** the SLP adds a calculation, **Then** the editor panel shows a **Show in imported sheets** setting, turned on.
2. **Given** a calculation selected in the editor panel, **When** the SLP turns Show in imported sheets off and presses Apply, **Then** the calculation is hidden in the Template Draft, and the list marks it as hidden.
3. **Given** the SLP changed the setting in the editor panel, **When** they press the editor's Cancel instead of Apply, **Then** the calculation keeps its previous setting.
4. **Given** a hidden calculation in a lower layer, **When** the SLP builds or edits a higher-layer calculation, **Then** the hidden calculation's result is offered in the menu and in the Formula Legend exactly as a shown one is, and using it raises no problem.
5. **Given** the SLP saved a template with hidden calculations, **When** they reopen it, **Then** each calculation's setting is as they saved it.
6. **Given** a template with hidden and shown calculations, **When** sheets imported with it get their calculation results, **Then** only the shown calculations' results appear with each imported sheet, and the hidden ones are still worked out wherever a shown calculation needs them.

---

### User Story 2 - See at a glance which results will show (Priority: P2)

The SLP opens a template in view mode to check what each imported session will include. In the Analysis section, every hidden calculation is plainly marked as hidden, so they can tell, without switching to edit mode, which results will appear with each imported sheet.

**Why this priority**: It makes the setting checkable later, but the hiding itself (Story 1) already delivers the value.

**Independent Test**: Open a template with one hidden and one shown calculation in view mode. Confirm the hidden one is marked as hidden, the shown one is not, and neither setting can be changed until switching to edit mode.

**Acceptance Scenarios**:

1. **Given** a template in view mode, **When** the SLP looks at the Analysis section, **Then** each hidden calculation is marked as hidden next to its name, and shown calculations carry no mark.
2. **Given** a template in view mode, **When** the SLP looks at a hidden calculation, **Then** they cannot change its setting until they switch to edit mode.
3. **Given** a template in edit mode, **When** the SLP looks at the calculation list, **Then** hidden calculations are marked the same way as in view mode.

---

### Edge Cases

- A template saved before this feature: every calculation in it is shown, so imported sheets show exactly what they would have shown without this feature.
- Every calculation is hidden: allowed. Sheets imported with the template show no calculation results.
- A hidden calculation that no other calculation uses: allowed. The SLP may hide a result they don't currently need without deleting it.
- A hidden calculation whose result is a Row List: hidden the same way as a single-number result.
- A hidden calculation is renamed, reordered within its layer, or edited: it stays hidden.
- A calculation is deleted and rebuilt in another layer: the rebuilt calculation starts shown, like any new calculation.
- The SLP changes the setting after sheets were already imported: only sheets imported afterward follow the new setting. Sessions already saved are not changed.
- Two calculations have the same name with different letter case: not possible, since names are already unique ignoring case.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Every calculation, menu or formula, in every layer, MUST have a **Show in imported sheets** setting that says whether its result appears with each sheet imported with the template.
- **FR-002**: A new calculation MUST start with Show in imported sheets turned on.
- **FR-003**: In edit mode and when creating a template, the editor panel MUST let the SLP turn the setting on or off. The change MUST take effect in the Template Draft only when the SLP presses Apply, and MUST be discarded on the editor's Cancel, like every other change in the editor panel.
- **FR-004**: The calculation list (edit mode and creating a template) and the Analysis section in view mode MUST mark each hidden calculation as hidden. Shown calculations MUST NOT carry the mark. In view mode the setting MUST be read-only.
- **FR-005**: The setting MUST be saved with the template and restored when the template is opened again.
- **FR-006**: A calculation saved before this feature existed MUST be treated as shown.
- **FR-007**: Hiding a calculation MUST NOT change what higher-layer calculations may use. A hidden calculation's result MUST still be offered in the menu and in the Formula Legend, and accepted in formulas, exactly as a shown one is.
- **FR-008**: Hiding a calculation MUST NOT change how any calculation's result is worked out, including its own.
- **FR-009**: When results are shown with an imported sheet, only shown calculations' results MUST appear. A hidden calculation's result MUST still be worked out whenever a shown calculation depends on it.
- **FR-010**: Changing the setting MUST NOT change the template's Template Structure, so the template's existing Student Session Workbooks stay its own.
- **FR-011**: Renaming, editing, or reordering a calculation MUST keep its setting.
- **FR-012**: The new term (Show in imported sheets, and a **Hidden Calculation**) MUST be added to the domain glossary as part of this feature.

### Key Entities

- **Calculation**: Gains one setting, **Show in imported sheets** (on or off). Every other part of the calculation is unchanged.
- **Hidden Calculation**: A calculation with Show in imported sheets turned off. Its result is worked out and may be used by higher layers, but does not appear with imported sheets.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The SLP can hide or show any one calculation in under 10 seconds from opening the template in edit mode, not counting saving.
- **SC-002**: 100% of templates saved before this feature open with every calculation shown, and with no change to their calculations or their Student Session Workbooks.
- **SC-003**: 100% of higher-layer calculations that were valid before a lower-layer calculation was hidden are still valid after, and give the same result.
- **SC-004**: In view mode, the SLP can name every hidden calculation of a template without opening an editor or switching modes.
- **SC-005**: For a template whose intermediate steps are hidden, the number of calculation results shown with each imported sheet equals the number of shown calculations.

## Assumptions

- Calculation results are not yet worked out or shown with imported sheets: feature 009 only configures calculations, and working out results is a later feature (see `FEATURE_IDEAS.md`). This feature adds and saves the setting and shows it in the template window. FR-009 and User Story 1 scenario 6 describe the behavior that the later results feature must follow, and are verified when that feature ships.
- "Imported data sheets" means wherever a sheet's calculation results are shown once imported (for example, its Session Tab in the Student Session Workbook). Where exactly that is, is left to the results feature.
- The setting is per calculation, not per layer. Hiding a whole layer is done by hiding each of its calculations.
- Shown is the default, both for new calculations and for templates saved earlier, so nothing disappears without the SLP choosing it.
- Hidden calculations are not removed from the Formula Legend or menus, and do not warn when nothing uses them.
- The setting has no effect on Historical Analysis, which is still out of scope.
- The setting is saved with the template's Data Sheet Analysis, which is not part of the Template Structure.
