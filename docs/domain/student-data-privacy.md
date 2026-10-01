# Student Data Privacy

Data sheets describe minors receiving special-education services. Treat everything
derived from a real sheet as confidential student information, protected by FERPA and
by district policy.

## Rules

1. **Identify students only by Student Key.** Code, templates, logs, specs, and output
   MUST NOT require or store a student's full name or any other direct identifier beyond
   the key written on the sheet.
2. **Keep real student data out of the repository.** Real sheet images, OCR output,
   interpreted data, and generated spreadsheets MUST NOT be committed. Files under
   `sample_data/` MUST be synthetic or fully de-identified.
3. **Keep credentials out of the repository.** AWS keys, Google OAuth client secrets, and
   cached tokens (`.token_*.pickle`) stay outside the repo or in git-ignored paths.
   Code reads them from the environment or from a configured path.
4. **Send data only to approved services.** Student data may go to AWS Textract (OCR) and
   Google Sheets/Drive (output), and nowhere else. Adding a new external service that
   receives student data requires a constitution amendment.
5. **Keep debug output local.** Debug printing (e.g. `StudentDataSheet.debug()`) is for
   local development only. It MUST NOT send data anywhere or write it to persistent logs.
6. **Use placeholder names in examples.** Docs, docstrings, and generated summaries in
   examples use placeholder keys or names (`JA`, "Jimmy"), never real ones.

## Why

The tool exists to save an SLP time. One leaked data sheet would cost the SLP, the
student, and the district far more than that time is worth.
