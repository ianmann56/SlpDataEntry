"""
Interpreter configuration classes for template creation.

Follows SOLID principles by separating configuration concerns and making 
interpreter types injectable and extensible.
"""

import tkinter as tk
from abc import ABC, abstractmethod
from tkinter import ttk, messagebox

from interpretation.student_data_sheet import DataSheetScalarType
from interpretation.interpreter_types.running_tally_interpreter import RunningTallyInterpreter
from interpretation.interpreter_types.simple_form_interpreter import SimpleFormInterpreter, FieldConfiguration
from interpretation.interpreter_types.table_interpreter import TableInterpreter


class InterpreterConfig(ABC):
    """Abstract base class for interpreter configurations."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """The display name of the interpreter type."""
        pass
    
    @abstractmethod
    def create_config_form(self, parent_frame) -> dict:
        """
        Create the configuration form for this interpreter type.
        
        Args:
            parent_frame: The parent tkinter frame to add widgets to
            
        Returns:
            dict: Configuration form data with keys:
                - 'frame': The main frame containing all widgets
                - 'get_config': Function to retrieve configuration data
                - 'reset': Function to clear the form so it's ready for a new interpreter
                - Additional implementation-specific keys
        """
        pass

    @abstractmethod
    def construct_interpreter(self, id, config_values):
        """
        Constructs a SessionDataInterpreterBase from the configs filled
        out in the form for this configuration.

        :param id: The unique id to assign to the constructed interpreter.
        :param config_values: The values filled out in the form which was
            constructed in create_config_form(...)
        """
        pass

class TableInterpreterConfig(InterpreterConfig):
    """Configuration for Table Interpreter - manages column names."""
    
    @property
    def name(self) -> str:
        return "Table Interpreter"
    
    def create_config_form(self, parent_frame) -> dict:
        """Create configuration form for Table Interpreter."""
        frame = ttk.Frame(parent_frame)

        ttk.Label(frame, text="Title:").grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        title_var = tk.StringVar()
        title_entry = ttk.Entry(frame, textvariable=title_var, width=20)
        title_entry.grid(row=0, column=1, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 5))

        ttk.Label(frame, text="Column Names:").grid(row=1, column=0, sticky=tk.W, pady=(0, 5))

        # Listbox for columns
        columns_listbox = tk.Listbox(frame, height=3)
        columns_listbox.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 5))

        # Entry and button for adding columns
        column_var = tk.StringVar()
        column_entry = ttk.Entry(frame, textvariable=column_var, width=20)
        column_entry.grid(row=3, column=0, sticky=(tk.W, tk.E), padx=(0, 5))

        add_column_btn = ttk.Button(frame, text="Add Column",
                                   command=lambda: self._add_config_item(columns_listbox, column_var))
        add_column_btn.grid(row=3, column=1, padx=(0, 5))

        remove_column_btn = ttk.Button(frame, text="Remove",
                                      command=lambda: self._remove_config_item(columns_listbox))
        remove_column_btn.grid(row=3, column=2)

        frame.columnconfigure(0, weight=1)

        def reset():
            title_var.set('')
            columns_listbox.delete(0, tk.END)

        return {
            'frame': frame,
            'listbox': columns_listbox,
            'entry_var': column_var,
            'get_config': lambda: {
                'title': title_var.get().strip(),
                'column_names': list(columns_listbox.get(0, tk.END))
            },
            'reset': reset
        }

    def construct_interpreter(self, id, config_values):
        """
        Constructs a TableInterpreter from the configuration values.

        :param id: The unique id to assign to the constructed interpreter.
        :param config_values: Dictionary containing 'title' and 'column_names' list
        :return: TableInterpreter instance configured with the specified columns
        """
        title = config_values.get('title', '')
        column_names = config_values.get('column_names', [])
        return TableInterpreter(id, title, column_names)
    
    def _add_config_item(self, listbox, entry_var):
        """Add an item to the configuration listbox."""
        item = entry_var.get().strip()
        if item:
            # Check for duplicates
            items = list(listbox.get(0, tk.END))
            if item not in items:
                listbox.insert(tk.END, item)
                entry_var.set("")  # Clear the entry
            else:
                messagebox.showwarning("Duplicate Item", f"'{item}' is already in the list.")
        else:
            messagebox.showwarning("Empty Item", "Please enter a value.")
            
    def _remove_config_item(self, listbox):
        """Remove selected item from the configuration listbox."""
        selection = listbox.curselection()
        if selection:
            listbox.delete(selection[0])
        else:
            messagebox.showwarning("No Selection", "Please select an item to remove.")


class RunningTallyInterpreterConfig(InterpreterConfig):
    """Configuration for Running Tally Interpreter - manages tally characters."""
    
    @property
    def name(self) -> str:
        return "Running Tally Interpreter"
    
    def create_config_form(self, parent_frame) -> dict:
        """Create configuration form for Running Tally Interpreter."""
        frame = ttk.Frame(parent_frame)

        ttk.Label(frame, text="Title:").grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        title_var = tk.StringVar()
        title_entry = ttk.Entry(frame, textvariable=title_var, width=20)
        title_entry.grid(row=0, column=1, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 5))

        ttk.Label(frame, text="Tally Characters:").grid(row=1, column=0, sticky=tk.W, pady=(0, 5))

        # Listbox for tally characters
        tally_listbox = tk.Listbox(frame, height=3)
        tally_listbox.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 5))

        # Entry and button for adding characters
        char_var = tk.StringVar()
        char_entry = ttk.Entry(frame, textvariable=char_var, width=20)
        char_entry.grid(row=3, column=0, sticky=(tk.W, tk.E), padx=(0, 5))

        add_char_btn = ttk.Button(frame, text="Add Character",
                                 command=lambda: self._add_config_item(tally_listbox, char_var))
        add_char_btn.grid(row=3, column=1, padx=(0, 5))

        remove_char_btn = ttk.Button(frame, text="Remove",
                                    command=lambda: self._remove_config_item(tally_listbox))
        remove_char_btn.grid(row=3, column=2)

        frame.columnconfigure(0, weight=1)

        def reset():
            title_var.set('')
            tally_listbox.delete(0, tk.END)

        return {
            'frame': frame,
            'listbox': tally_listbox,
            'entry_var': char_var,
            'get_config': lambda: {
                'title': title_var.get().strip(),
                'tally_characters': list(tally_listbox.get(0, tk.END))
            },
            'reset': reset
        }

    def construct_interpreter(self, id, config_values):
        """
        Constructs a RunningTallyInterpreter from the configuration values.

        :param id: The unique id to assign to the constructed interpreter.
        :param config_values: Dictionary containing 'title' and 'tally_characters' list
        :return: RunningTallyInterpreter instance configured with CHOICE type and tally characters as choices
        """
        title = config_values.get('title', '')
        tally_characters = config_values.get('tally_characters', [])
        return RunningTallyInterpreter(id, title, DataSheetScalarType.CHOICE, tally_characters)
    
    def _add_config_item(self, listbox, entry_var):
        """Add an item to the configuration listbox."""
        item = entry_var.get().strip()
        if item:
            # Check for duplicates
            items = list(listbox.get(0, tk.END))
            if item not in items:
                listbox.insert(tk.END, item)
                entry_var.set("")  # Clear the entry
            else:
                messagebox.showwarning("Duplicate Item", f"'{item}' is already in the list.")
        else:
            messagebox.showwarning("Empty Item", "Please enter a value.")
            
    def _remove_config_item(self, listbox):
        """Remove selected item from the configuration listbox."""
        selection = listbox.curselection()
        if selection:
            listbox.delete(selection[0])
        else:
            messagebox.showwarning("No Selection", "Please select an item to remove.")


class SimpleFormInterpreterConfig(InterpreterConfig):
    """Configuration for Simple Form Interpreter - manages form field names."""
    
    @property
    def name(self) -> str:
        return "Simple Form Interpreter"
    
    def create_config_form(self, parent_frame) -> dict:
        """Create configuration form for Simple Form Interpreter."""
        frame = ttk.Frame(parent_frame)

        ttk.Label(frame, text="Title:").grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        title_var = tk.StringVar()
        title_entry = ttk.Entry(frame, textvariable=title_var, width=20)
        title_entry.grid(row=0, column=1, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 5))

        ttk.Label(frame, text="Form Field Names:").grid(row=1, column=0, sticky=tk.W, pady=(0, 5))

        # Listbox for field names
        fields_listbox = tk.Listbox(frame, height=3)
        fields_listbox.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 5))

        # Entry and button for adding fields
        field_var = tk.StringVar()
        field_entry = ttk.Entry(frame, textvariable=field_var, width=20)
        field_entry.grid(row=3, column=0, sticky=(tk.W, tk.E), padx=(0, 5))

        add_field_btn = ttk.Button(frame, text="Add Field",
                                  command=lambda: self._add_config_item(fields_listbox, field_var))
        add_field_btn.grid(row=3, column=1, padx=(0, 5))

        remove_field_btn = ttk.Button(frame, text="Remove",
                                     command=lambda: self._remove_config_item(fields_listbox))
        remove_field_btn.grid(row=3, column=2)

        frame.columnconfigure(0, weight=1)

        def reset():
            title_var.set('')
            fields_listbox.delete(0, tk.END)

        return {
            'frame': frame,
            'listbox': fields_listbox,
            'entry_var': field_var,
            'get_config': lambda: {
                'title': title_var.get().strip(),
                'field_names': list(fields_listbox.get(0, tk.END))
            },
            'reset': reset
        }

    def construct_interpreter(self, id, config_values):
        """
        Constructs a SimpleFormInterpreter from the configuration values.

        :param id: The unique id to assign to the constructed interpreter.
        :param config_values: Dictionary containing 'title' and 'field_names' list
        :return: SimpleFormInterpreter instance configured with FieldConfiguration dictionary
        """
        title = config_values.get('title', '')
        field_names = config_values.get('field_names', [])

        # Create FieldConfiguration dictionary with TEXT type as default
        field_configs = {
            name: FieldConfiguration(name, DataSheetScalarType.TEXT)
            for name in field_names
        }

        return SimpleFormInterpreter(id, title, field_configs)
    
    def _add_config_item(self, listbox, entry_var):
        """Add an item to the configuration listbox."""
        item = entry_var.get().strip()
        if item:
            # Check for duplicates
            items = list(listbox.get(0, tk.END))
            if item not in items:
                listbox.insert(tk.END, item)
                entry_var.set("")  # Clear the entry
            else:
                messagebox.showwarning("Duplicate Item", f"'{item}' is already in the list.")
        else:
            messagebox.showwarning("Empty Item", "Please enter a value.")
            
    def _remove_config_item(self, listbox):
        """Remove selected item from the configuration listbox."""
        selection = listbox.curselection()
        if selection:
            listbox.delete(selection[0])
        else:
            messagebox.showwarning("No Selection", "Please select an item to remove.")


# Default configuration list - can be easily extended or modified
STUB_INTERPRETER_CONFIGS = [
    TableInterpreterConfig(),
    RunningTallyInterpreterConfig(),
    SimpleFormInterpreterConfig(),
]