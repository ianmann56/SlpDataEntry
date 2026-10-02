import os
import queue
import threading
import tkinter as tk
from collections.abc import Callable
from tkinter import filedialog, ttk

from interpretation.importing.sheet_import_batch import SheetImportBatch, SheetOutcome, SheetStatus
from interpretation.student_data_sheet import StudentDataSheet
from tk_utils import error_handling

_IMAGE_FILE_TYPES = [("Images", "*.png *.PNG *.jpg *.JPG *.jpeg *.JPEG *.tif *.TIF *.tiff *.TIFF")]
_POLL_INTERVAL_MS = 100
_STATUS_LABELS = {
    SheetStatus.NOT_IMPORTED: "Not imported",
    SheetStatus.SUCCEEDED: "Succeeded",
    SheetStatus.FAILED: "Failed",
}


class ImportWindow:
    """
    Window for the import and interpret path.

    The SLP builds a list of data sheet images and presses Import. The import rules
    live in the injected SheetImportBatch; this window only shows the list, runs the
    batch on a worker thread so it stays responsive, and shows each file's outcome.

    Only the worker thread calls `batch.process_file`. Only the Tk thread touches
    widgets or calls `on_sheet_interpreted`. The worker reports progress through a
    queue that the Tk thread polls.
    """

    def __init__(
        self,
        master: tk.Toplevel,
        batch: SheetImportBatch,
        check_records_readable: Callable[[], None],
        on_sheet_interpreted: Callable[[StudentDataSheet], None],
        on_back: Callable[[], None],
        on_exit: Callable[[], None],
    ) -> None:
        """
        Initialize the import window.

        Args:
            master: Window the import window is built in
            batch: A new, empty batch holding the list and its import rules
            check_records_readable: Raises if the student or template records cannot be read
            on_sheet_interpreted: Called once per succeeded sheet, in list order
            on_back: Called when Back is pressed
            on_exit: Called when the window is closed from its title bar
        """
        self._window = master
        self._batch = batch
        self._check_records_readable = check_records_readable
        self._on_sheet_interpreted = on_sheet_interpreted
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
            ("status", "Status", 100),
            ("student_key", "Student Key", 90),
            ("template", "Template", 140),
            ("details", "Details", 420),
        ]:
            self._tree.heading(column, text=heading)
            self._tree.column(column, width=width, stretch=(column == "details"))
        self._tree.grid(row=0, column=0, sticky="nsew")
        self._tree.bind("<<TreeviewSelect>>", lambda _event: self._refresh_controls())

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
        """Process each file in turn on the worker thread. Never touches widgets."""
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
            if kind == "started":
                self._show_started(event[1])
            elif kind == "finished":
                self._show_finished(event[1], event[2].outcome)
                if event[2].data_sheet is not None:
                    self._on_sheet_interpreted(event[2].data_sheet)
            elif kind == "done":
                self._finish_run(event[1])
                return

        self._window.after(_POLL_INTERVAL_MS, self._poll)

    def _show_started(self, identity: str) -> None:
        self._run_started += 1
        self._tree.set(identity, "status", "Importing…")
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
