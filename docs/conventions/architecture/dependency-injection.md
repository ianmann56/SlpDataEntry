# Dependency Injection for External Services

Every call to AWS or Google goes through a client that the caller injects, so the logic
can run without network access or credentials.

## Rules

1. **Construct clients in `clients/`.** `construct_textract_client()` and
   `create_google_service()` are the only places that call `boto3.client(...)` or
   `googleapiclient.discovery.build(...)`.
2. **Accept a provider, not a global.** A function that needs a client takes a
   zero-argument provider, by convention named `inject_<client>`, and calls it only when
   it needs the client:

   ```python
   def image_to_text(image_path, inject_textract_client): ...
   def create_therapy_session_sheet(data, sheet_title, inject_google_service): ...

   image_to_text(path, lambda: textract_client)
   ```

   This keeps construction lazy and lets tests pass a fake.
3. **No module-level clients.** Modules MUST NOT build clients, read credentials, or
   start OAuth flows at import time.
4. **Read credentials from the environment.** AWS uses the standard boto3 chain
   (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_DEFAULT_REGION`). Google OAuth
   client-secret paths MUST point outside the repository. See
   [../../domain/student-data-privacy.md](../../domain/student-data-privacy.md).
5. **Translate vendor errors at the boundary.** Adapters catch SDK exceptions
   (`ClientError`, `NoCredentialsError`) and re-raise them with a message that explains
   what failed, e.g. "AWS Textract error: ...". UI code reports errors through
   `tk_utils.error_handling.throw`.
6. **Inject stores and config lists too.** Windows receive `TemplateStore`,
   `StudentStore`, their `InterpreterConfig` list, and providers such as
   `list_template_choices` through their constructors. They MUST NOT create their own.
   `program.py` builds the one `JsonStudentStore`.
   `ImportWindow` and `SheetImportBatch` receive the `StudentStore`, a template lookup,
   a sheet reader wrapping `image_to_text`, and a result sink through their
   constructors. `program.py` builds the Textract client lazily, on the first sheet
   read, so the app launches and runs Setup without AWS credentials.
   `DataSheetTemplateManagementWindow` and `TemplateDetailsWindow` receive
   `load_template_usage: Callable[[], TemplateUsage | None]`, and the management window
   also receives `clear_template_from_students: Callable[[str], list[str]]`. Both are
   wired in `program.py` from the one `StudentStore`. Template management never
   receives the `StudentStore` itself, so it imports nothing from `students/`.
