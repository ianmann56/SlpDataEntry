import os
import queue
import threading
import tkinter as tk
import traceback
from collections.abc import Callable
from tkinter import filedialog, ttk

from interpretation.data_sheet_store import DataSheetStore
from interpretation.importing.sheet_import_batch import SheetImportBatch, SheetOutcome, SheetStatus
from tk_utils import error_handling

_IMAGE_FILE_TYPES = [("Images", "*.png *.PNG *.jpg *.JPG *.jpeg *.JPEG *.tif *.TIF *.tiff *.TIFF")]
_POLL_INTERVAL_MS = 100
_STATUS_LABELS = {
    SheetStatus.NOT_IMPORTED: "○ Not imported",
    SheetStatus.SUCCEEDED: "✓ Succeeded",
    SheetStatus.FAILED: "✗ Failed",
}
_IMPORTING_LABEL = "… Importing"

# Row tags, so each status has its own color as well as its own symbol
_STATUS_TAGS = {
    SheetStatus.NOT_IMPORTED: "not_imported",
    SheetStatus.SUCCEEDED: "succeeded",
    SheetStatus.FAILED: "failed",
}
_IMPORTING_TAG = "importing"
# Readable on both the light and dark sv-ttk themes. Other tags keep the theme's color.
_TAG_COLORS = {"succeeded": "#2e9d4f", "failed": "#d64545"}


class ImportWindow:
    """
    Window for the import and interpret path.

    The SLP builds a list of data sheet images and presses Import. The import rules
    live in the injected SheetImportBatch, which saves each sheet through the Data
    Sheet Store. This window only shows the list, runs the batch on a worker thread so
    it stays responsive, shows each file's outcome, and opens saved sessions.

    Only the worker thread calls `data_sheet_store.prepare` and `batch.process_file`,
    so every call to the store happens on that one thread. Only the Tk thread touches
    widgets. The worker reports progress through a queue that the Tk thread polls.
    """

    def __init__(
        self,
        master: tk.Toplevel,
        batch: SheetImportBatch,
        data_sheet_store: DataSheetStore,
        check_records_readable: Callable[[], None],
        open_url: Callable[[str], None],
        on_back: Callable[[], None],
        on_exit: Callable[[], None],
    ) -> None:
        """
        Initialize the import window.

        Args:
            master: Window the import window is built in
            batch: A new, empty batch holding the list and its import rules
            data_sheet_store: The store the batch saves to; prepared before each run
            check_records_readable: Raises if the student or template records cannot be read
            open_url: Opens a saved session in the web browser
            on_back: Called when Back is pressed
            on_exit: Called when the window is closed from its title bar
        """
        self._window = master
        self._batch = batch
        self._data_sheet_store = data_sheet_store
        self._check_records_readable = check_records_readable
        self._open_url = open_url
        self._on_back = on_back
        self._on_exit = on_exit

        self._running = False
        self._events: queue.Queue[tuple] = queue.Queue()
        self._stop = threading.Event()
        self._run_total = 0
        self._run_started = 0
        self._run_succeeded = 0
        self._run_failed = 0

        self._setup_window()
        self._create_widgets()
        self._refresh_controls()

    def _setup_window(self) -> None:
        """Configure the main window properties."""
        self._window.title("Import & Interpret Student Data Sheets")
        self._window.protocol("WM_DELETE_WINDOW", self._on_exit)

    def _create_widgets(self) -> None:
        """Create and layout the window widgets."""
        main_frame = ttk.Frame(self._window, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(0, weight=1)

        # File list
        list_frame = ttk.Frame(main_frame)
        list_frame.grid(row=0, column=0, sticky="nsew")
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)

        columns = ("file", "status", "student_key", "template", "details")
        self._tree = ttk.Treeview(list_frame, columns=columns, show="headings", selectmode="extended", height=12)
        for column, heading, width in [
            ("file", "File", 180),
            ("status", "Status", 120),
            ("student_key", "Student Key", 90),
            ("template", "Template", 140),
            ("details", "Details", 420),
        ]:
            self._tree.heading(column, text=heading)
            self._tree.column(column, width=width, stretch=(column == "details"))
        for tag, color in _TAG_COLORS.items():
            self._tree.tag_configure(tag, foreground=color)
        self._tree.grid(row=0, column=0, sticky="nsew")
        self._tree.bind("<<TreeviewSelect>>", lambda _event: self._refresh_controls())
        self._tree.bind("<Double-1>", self._on_double_click)

        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self._tree.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self._tree.configure(yscrollcommand=scrollbar.set)

        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=1, column=0, sticky="ew", pady=(10, 0))

        self._add_button = ttk.Button(button_frame, text="Add Files…", command=self._add_files)
        self._add_button.pack(side=tk.LEFT)
        self._remove_button = ttk.Button(button_frame, text="Remove Selected", command=self._remove_selected)
        self._remove_button.pack(side=tk.LEFT, padx=(10, 0))
        self._open_button = ttk.Button(button_frame, text="Open", command=self._open_selected)
        self._open_button.pack(side=tk.LEFT, padx=(10, 0))
        self._import_button = ttk.Button(button_frame, text="Import", command=self._start_import)
        self._import_button.pack(side=tk.LEFT, padx=(10, 0))
        self._cancel_button = ttk.Button(button_frame, text="Cancel", command=self._cancel_import)
        self._cancel_button.pack(side=tk.LEFT, padx=(10, 0))
        self._cancel_button.pack_forget()

        self._back_button = ttk.Button(button_frame, text="Back", command=self._on_back)
        self._back_button.pack(side=tk.RIGHT)

        # Progress and summary
        self._progress_frame = ttk.Frame(main_frame)
        self._progress_frame.grid(row=2, column=0, sticky="ew", pady=(10, 0))
        self._progress_frame.columnconfigure(0, weight=1)
        self._progress_bar = ttk.Progressbar(self._progress_frame, mode="determinate")
        self._progress_bar.grid(row=0, column=0, sticky="ew")
        self._progress_label = ttk.Label(self._progress_frame, text="")
        self._progress_label.grid(row=0, column=1, padx=(10, 0))
        self._progress_frame.grid_remove()

        self._summary_label = ttk.Label(main_frame, text="")
        self._summary_label.grid(row=3, column=0, sticky="w", pady=(10, 0))

    def _refresh_controls(self) -> None:
        """Enable or disable each control for the current window state."""
        idle = not self._running
        self._set_enabled(self._add_button, idle)
        self._set_enabled(self._back_button, idle)
        self._set_enabled(self._import_button, idle and bool(self._batch.files_to_process()))
        self._set_enabled(self._remove_button, idle and bool(self._tree.selection()))
        self._set_enabled(self._open_button, idle and self._selected_saved_url() is not None)

    @staticmethod
    def _set_enabled(button: ttk.Button, enabled: bool) -> None:
        button.state(["!disabled"] if enabled else ["disabled"])

    def _add_files(self) -> None:
        """Let the SLP pick images and append the new ones to the list."""
        paths = filedialog.askopenfilenames(
            parent=self._window,
            title="Add data sheet images",
            filetypes=_IMAGE_FILE_TYPES,
        )
        if not paths:
            return

        for selected in self._batch.add_files(list(paths)):
            self._tree.insert(
                "", tk.END, iid=selected.identity,
                values=(os.path.basename(selected.path), _STATUS_LABELS[SheetStatus.NOT_IMPORTED], "", "", selected.path),
                tags=(_STATUS_TAGS[SheetStatus.NOT_IMPORTED],),
            )
        # The summary describes the list as it was, so clear it once the list changes
        self._summary_label.config(text="")
        self._refresh_controls()

    def _remove_selected(self) -> None:
        """Remove the selected files from the list."""
        selection = self._tree.selection()
        if not selection:
            return
        self._batch.remove_files(selection)
        self._tree.delete(*selection)
        self._summary_label.config(text="")
        self._refresh_controls()

    def _selected_saved_url(self) -> str | None:
        """The saved session's URL when exactly one succeeded row is selected, otherwise None."""
        selection = self._tree.selection()
        if len(selection) != 1:
            return None
        for selected in self._batch.files:
            if selected.identity == selection[0]:
                outcome = selected.outcome
                if outcome.status == SheetStatus.SUCCEEDED and outcome.saved is not None:
                    return outcome.saved.location_url
                return None
        return None

    def _open_selected(self) -> None:
        """Open the selected row's saved session in the web browser."""
        if self._running:
            return
        url = self._selected_saved_url()
        if url is not None:
            self._open_url(url)

    def _on_double_click(self, event: tk.Event) -> None:
        """Open a succeeded row's saved session when the row is double-clicked."""
        if self._tree.identify_row(event.y):
            self._open_selected()

    def _start_import(self) -> None:
        """Check the records can be read, then process every file not yet succeeded."""
        try:
            self._check_records_readable()
        except Exception as e:
            error_handling.throw(e, "Cannot start the import")
            return

        ids = [selected.identity for selected in self._batch.files_to_process()]
        if not ids:
            return

        self._events = queue.Queue()
        self._stop = threading.Event()
        self._run_total = len(ids)
        self._run_started = 0
        self._run_succeeded = 0
        self._run_failed = 0
        self._running = True

        self._summary_label.config(text="")
        self._progress_bar.config(maximum=self._run_total, value=0)
        self._progress_frame.grid()
        self._cancel_button.config(text="Cancel")
        self._set_enabled(self._cancel_button, True)
        self._cancel_button.pack(side=tk.LEFT, padx=(10, 0), after=self._import_button)
        self._refresh_controls()

        threading.Thread(target=self._work, args=(ids, self._events, self._stop), daemon=True).start()
        self._window.after(_POLL_INTERVAL_MS, self._poll)

    def _cancel_import(self) -> None:
        """Stop after the file being processed now finishes."""
        self._stop.set()
        self._cancel_button.config(text="Cancelling…")
        self._set_enabled(self._cancel_button, False)

    def _work(self, ids: list[str], events: queue.Queue, stop: threading.Event) -> None:
        """
        Prepare the store, then process each file in turn, on the worker thread. Never
        touches widgets. If the store can't be prepared, no file is processed.
        """
        events.put(("preparing",))
        try:
            self._data_sheet_store.prepare()
        except Exception as e:
            traceback.print_exception(e)
            events.put(("prepare_failed", e))
            events.put(("done", False))
            return

        cancelled = False
        for identity in ids:
            if stop.is_set():
                cancelled = True
                break
            events.put(("started", identity))
            events.put(("finished", identity, self._batch.process_file(identity)))
        events.put(("done", cancelled))

    def _poll(self) -> None:
        """Apply the worker's events on the Tk thread."""
        if not self._window.winfo_exists():
            return

        while True:
            try:
                event = self._events.get_nowait()
            except queue.Empty:
                break

            kind = event[0]
            if kind == "preparing":
                self._progress_label.config(text="Connecting to Google Drive…")
            elif kind == "prepare_failed":
                error_handling.throw(event[1], "Cannot start the import")
            elif kind == "started":
                self._show_started(event[1])
            elif kind == "finished":
                self._show_finished(event[1], event[2].outcome)
            elif kind == "done":
                self._finish_run(event[1])
                return

        self._window.after(_POLL_INTERVAL_MS, self._poll)

    def _show_started(self, identity: str) -> None:
        self._run_started += 1
        self._tree.set(identity, "status", _IMPORTING_LABEL)
        self._tree.item(identity, tags=(_IMPORTING_TAG,))
        self._tree.see(identity)
        self._progress_label.config(text=f"Importing {self._run_started} of {self._run_total}…")

    def _show_finished(self, identity: str, outcome: SheetOutcome) -> None:
        if outcome.status == SheetStatus.SUCCEEDED:
            self._run_succeeded += 1
        else:
            self._run_failed += 1
        self._show_outcome(identity, outcome)
        self._progress_bar.config(value=self._run_succeeded + self._run_failed)

    def _show_outcome(self, identity: str, outcome: SheetOutcome) -> None:
        """Show a file's outcome in its row."""
        self._tree.set(identity, "status", _STATUS_LABELS[outcome.status])
        self._tree.item(identity, tags=(_STATUS_TAGS[outcome.status],))
        self._tree.set(identity, "student_key", outcome.student_key or "")
        self._tree.set(identity, "template", outcome.template_name or "")
        self._tree.set(identity, "details", outcome.message)

    def _finish_run(self, cancelled: bool) -> None:
        """Show the summary and give the SLP the controls back."""
        self._running = False
        self._progress_frame.grid_remove()
        self._cancel_button.pack_forget()
        self._cancel_button.config(text="Cancel")

        totals = self._batch.totals()
        summary = (
            f"This run: {self._run_succeeded} succeeded, {self._run_failed} failed · "
            f"Whole list: {totals.succeeded} succeeded, {totals.failed} failed, {totals.not_imported} not imported"
        )
        if cancelled:
            summary += " · Cancelled."
        self._summary_label.config(text=summary)
        self._refresh_controls()
