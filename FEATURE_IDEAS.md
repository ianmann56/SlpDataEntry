# Feature Ideas

Ideas that were deliberately left out of a feature's scope, kept here for a later spec.

## Analysis

From [009 Data Sheet Analysis](specs/009-data-sheet-analysis/spec.md), which only configures calculations on a template.

### Work out calculation results for each imported sheet

When a sheet is imported, work out each Data Sheet Analysis calculation from that sheet's interpreted values, layer by layer, and save the results with the session (for example, as extra values in its Session Tab), so the SLP reads "Accuracy: 72%" instead of computing it.

The 009 spec already fixes what each calculation means, for this feature to follow:

- An Average covers only the rows whose measured value is not empty.
- A Sum over no values is 0; empty values add nothing.
- An Average over no values, and a division or percentage by 0, give an empty result, and a calculation using an empty result is also empty.
- Results are worked out from interpreted values (Typed Values, Tally Summaries), never from raw OCR text.

Still to decide: where results are saved and how they are shown (for example, whether a formula's result is shown as a percentage).

### Historical Analysis

Calculations across many sessions of one student with the same template, such as progress over time toward a Goal's target. It would sit beside Data Sheet Analysis in the template's Analysis section, which currently says historical analysis is not yet available.
