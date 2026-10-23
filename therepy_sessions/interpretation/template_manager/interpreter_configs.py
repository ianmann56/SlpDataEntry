"""
Interpreter configuration classes for template creation.

Follows SOLID principles by separating configuration concerns and making 
interpreter types injectable and extensible.
"""

import tkinter as tk
from abc import ABC, abstractmethod
from collections.abc import Callable
from collections.abc import Sequence
from tkinter import ttk
from typing import Any, TypedDict

from interpretation.analysis.renames import PartKind, PartRename
from interpretation.templates.student_data_sheet_interpreter import SessionDataSectionInterpreterBase
from interpretation.interpreter_types.running_tally_interpreter import RunningTallyInterpreter
from interpretation.interpreter_types.simple_form_interpreter import SimpleFormInterpreter, FieldConfiguration
from interpretation.interpreter_types.table_interpreter import ColumnDefinition, TableInterpreter
from interpretation.template_manager.option_list_editor import OptionListEditor
from interpretation.template_manager.typed_item_editor import TypedItem, TypedItemEditor
from interpretation.value_types import COLUMN_TYPE_LABELS, FIELD_TYPES, ChoiceOption, ColumnType, TallyOption


class ConfigForm(TypedDict):
    """The configuration form an InterpreterConfig builds, and the functions that drive it."""

    frame: ttk.Frame
    # Returns the values filled out in the form, for construct_interpreter
    get_config: Callable[[], dict[str, Any]]
    # Clears the form so it's ready for a new interpreter
    reset: Callable[[], None]
    # Fills the form with an existing interpreter's title and configuration
    load: Callable[[SessionDataSectionInterpreterBase], None]


class InterpreterConfig(ABC):
    """Abstract base class for interpreter configurations."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """The display name of the interpreter type."""
        pass

    @property
    @abstractmethod
    def interpreter_type(self) -> type[SessionDataSectionInterpreterBase]:
        """The interpreter class this configuration builds, used to find the config for a saved interpreter."""
        pass
    
    @abstractmethod
    def create_config_form(self, parent_frame: tk.Misc) -> ConfigForm:
        """
        Create the configuration form for this interpreter type.
        
        Args:
            parent_frame: The parent tkinter frame to add widgets to
            
        Returns:
            The form's frame and the functions that read, clear, and fill it
        """
        pass

    @abstractmethod
    def construct_interpreter(self, id: str, config_values: dict[str, Any]) -> SessionDataSectionInterpreterBase:
        """
        Constructs a SessionDataInterpreterBase from the configs filled
        out in the form for this configuration.

        :param id: The unique id to assign to the constructed interpreter.
        :param config_values: The values filled out in the form which was
            constructed in create_config_form(...)
        """
        pass

    @abstractmethod
    def describe(self, interpreter: SessionDataSectionInterpreterBase) -> list[str]:
        """
        Describe an interpreter's configuration as readable lines for view mode,
        e.g. ["Columns: Sentence, Pitch"].
        """
        pass

    def renames(self, config_values: dict[str, Any]) -> list[PartRename]:
        """
        The columns, fields, and options the SLP renamed in place in the form, so
        calculations can follow them. A type whose form can rename nothing keeps the
        default, which reports none.
        """
        return []

    def _section_name(self, config_values: dict[str, Any]) -> str:
        """The Section Name the form's values give: the title, or the type's fallback name."""
        return self.construct_interpreter("", config_values).section_name

    def _item_renames(self, config_values: dict[str, Any]) -> list[PartRename]:
        """The renames a TypedItemEditor reported in the values: items first, then their options."""
        section = self._section_name(config_values)
        return [
            PartRename(PartKind.ITEM, section, "", old, new)
            for old, new in config_values.get('renames', [])
        ] + [
            PartRename(PartKind.OPTION, section, item, old, new)
            for item, old, new in config_values.get('option_renames', [])
        ]


def find_config(
    configs: list[InterpreterConfig], interpreter: SessionDataSectionInterpreterBase
) -> InterpreterConfig | None:
    """Return the config that builds this interpreter's type, or None if no config handles it."""
    return next((config for config in configs if isinstance(interpreter, config.interpreter_type)), None)


def _join_or_none(items: list[str]) -> str:
    """Join items for a description line, or say "(none)" when there are none."""
    return ", ".join(items) if items else "(none)"


def _describe_options(options: Sequence[tuple[str, str]]) -> str:
    """Options for a description line, e.g. "+ (correct), - (incorrect), P"."""
    return _join_or_none([f"{code} ({meaning})" if meaning else code for code, meaning in options])


def _describe_item(name: str, item_type: ColumnType, options: Sequence[tuple[str, str]]) -> str:
    """One column or field for view mode, e.g. "Trials — Integer" or "Accuracy — Choice: + (correct), -"."""
    label = COLUMN_TYPE_LABELS[item_type]
    if item_type in (ColumnType.CHOICE, ColumnType.TALLY):
        return f"{name} — {label}: {_describe_options(options)}"
    return f"{name} — {label}"


def _column_options(column: ColumnDefinition) -> list[tuple[str, str]]:
    """A column's choices or tally options as (value, meaning)."""
    if column.column_type is ColumnType.TALLY:
        return [(option.mark, option.description) for option in column.tally_options]
    return [(choice.value, choice.description) for choice in column.choices]


def _title_row(frame: ttk.Frame) -> tk.StringVar:
    """Add the Title entry at the top of a config form."""
    ttk.Label(frame, text="Title:").grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
    title_var = tk.StringVar()
    ttk.Entry(frame, textvariable=title_var, width=20).grid(row=0, column=1, sticky=(tk.W, tk.E), pady=(0, 5))
    return title_var


class TableInterpreterConfig(InterpreterConfig):
    """Configuration for Table Interpreter - manages its columns and their types."""
    
    @property
    def name(self) -> str:
        return "Table Interpreter"

    @property
    def interpreter_type(self) -> type[SessionDataSectionInterpreterBase]:
        return TableInterpreter
    
    def create_config_form(self, parent_frame: tk.Misc) -> ConfigForm:
        """Create configuration form for Table Interpreter."""
        frame = ttk.Frame(parent_frame)
        frame.columnconfigure(1, weight=1)
        title_var = _title_row(frame)

        ttk.Label(frame, text="Columns:").grid(row=1, column=0, sticky=(tk.W, tk.N), pady=(0, 5))
        editor = TypedItemEditor(frame, "Column", list(ColumnType))
        editor.frame.grid(row=1, column=1, sticky=(tk.W, tk.E), pady=(0, 5))

        def reset() -> None:
            title_var.set('')
            editor.reset()

        def load(interpreter: SessionDataSectionInterpreterBase) -> None:
            reset()
            title_var.set(interpreter.title or '')
            editor.set([
                TypedItem(column.column_name, column.column_type, _column_options(column),
                          loaded_name=column.column_name)
                for column in interpreter.columns
            ])

        return {
            'frame': frame,
            'get_config': lambda: {
                'title': title_var.get().strip(),
                'columns': editor.get(),
                'renames': editor.renames(),
                'option_renames': editor.option_renames(),
            },
            'reset': reset,
            'load': load,
        }

    def construct_interpreter(self, id: str, config_values: dict[str, Any]) -> SessionDataSectionInterpreterBase:
        """
        Constructs a TableInterpreter from the configuration values.

        :param id: The unique id to assign to the constructed interpreter.
        :param config_values: Dictionary containing 'title' and 'columns', a list of TypedItem
        :return: TableInterpreter instance configured with the specified columns
        """
        title = config_values.get('title', '')
        items: list[TypedItem] = config_values.get('columns', [])
        column_defs = [
            ColumnDefinition(
                item.name.strip(),
                item.item_type,
                choices=[ChoiceOption(v, d) for v, d in item.options] if item.item_type is ColumnType.CHOICE else None,
                tally_options=[TallyOption(v, d) for v, d in item.options] if item.item_type is ColumnType.TALLY else None,
            )
            for item in items
        ]
        return TableInterpreter(id, title, column_defs)

    def renames(self, config_values: dict[str, Any]) -> list[PartRename]:
        """Columns and their choices or tally marks renamed in place."""
        return self._item_renames(config_values)

    def describe(self, interpreter: SessionDataSectionInterpreterBase) -> list[str]:
        lines = [
            _describe_item(column.column_name, column.column_type, _column_options(column))
            for column in interpreter.columns
        ]
        return lines or ["Columns: (none)"]


class RunningTallyInterpreterConfig(InterpreterConfig):
    """Configuration for Running Tally Interpreter - manages its tally options."""
    
    @property
    def name(self) -> str:
        return "Running Tally Interpreter"

    @property
    def interpreter_type(self) -> type[SessionDataSectionInterpreterBase]:
        return RunningTallyInterpreter
    
    def create_config_form(self, parent_frame: tk.Misc) -> ConfigForm:
        """Create configuration form for Running Tally Interpreter."""
        frame = ttk.Frame(parent_frame)
        frame.columnconfigure(1, weight=1)
        title_var = _title_row(frame)

        ttk.Label(frame, text="Tally Options:").grid(row=1, column=0, sticky=(tk.W, tk.N), pady=(0, 5))
        editor = OptionListEditor(frame, ColumnType.TALLY)
        editor.frame.grid(row=1, column=1, sticky=(tk.W, tk.E), pady=(0, 5))

        def reset() -> None:
            title_var.set('')
            editor.set([])

        def load(interpreter: SessionDataSectionInterpreterBase) -> None:
            reset()
            title_var.set(interpreter.title or '')
            editor.set([(option.mark, option.description) for option in interpreter.tally_options])

        return {
            'frame': frame,
            'get_config': lambda: {
                'title': title_var.get().strip(),
                'tally_options': editor.get(),
                'renames': editor.renames(),
            },
            'reset': reset,
            'load': load,
        }

    def construct_interpreter(self, id: str, config_values: dict[str, Any]) -> SessionDataSectionInterpreterBase:
        """
        Constructs a RunningTallyInterpreter from the configuration values.

        :param id: The unique id to assign to the constructed interpreter.
        :param config_values: Dictionary containing 'title' and 'tally_options', a list of (mark, meaning)
        :return: RunningTallyInterpreter instance configured with those tally options
        """
        title = config_values.get('title', '')
        tally_options = [TallyOption(mark, meaning) for mark, meaning in config_values.get('tally_options', [])]
        return RunningTallyInterpreter(id, title, tally_options)

    def renames(self, config_values: dict[str, Any]) -> list[PartRename]:
        """Tally marks renamed in place. They have no column, so `item` is ""."""
        section = self._section_name(config_values)
        return [PartRename(PartKind.OPTION, section, "", old, new) for old, new in config_values.get('renames', [])]

    def describe(self, interpreter: SessionDataSectionInterpreterBase) -> list[str]:
        options = [(option.mark, option.description) for option in interpreter.tally_options]
        return ["Tally options: " + _describe_options(options)]


class SimpleFormInterpreterConfig(InterpreterConfig):
    """Configuration for Simple Form Interpreter - manages its form fields and their types."""
    
    @property
    def name(self) -> str:
        return "Simple Form Interpreter"

    @property
    def interpreter_type(self) -> type[SessionDataSectionInterpreterBase]:
        return SimpleFormInterpreter
    
    def create_config_form(self, parent_frame: tk.Misc) -> ConfigForm:
        """Create configuration form for Simple Form Interpreter."""
        frame = ttk.Frame(parent_frame)
        frame.columnconfigure(1, weight=1)
        title_var = _title_row(frame)

        ttk.Label(frame, text="Form Fields:").grid(row=1, column=0, sticky=(tk.W, tk.N), pady=(0, 5))
        editor = TypedItemEditor(frame, "Field", FIELD_TYPES)
        editor.frame.grid(row=1, column=1, sticky=(tk.W, tk.E), pady=(0, 5))

        def reset() -> None:
            title_var.set('')
            editor.reset()

        def load(interpreter: SessionDataSectionInterpreterBase) -> None:
            reset()
            title_var.set(interpreter.title or '')
            editor.set([
                TypedItem(field.name, field.field_type, [(choice.value, choice.description) for choice in field.choices],
                          loaded_name=field.name)
                for field in interpreter.fields.values()
            ])

        return {
            'frame': frame,
            'get_config': lambda: {
                'title': title_var.get().strip(),
                'fields': editor.get(),
                'renames': editor.renames(),
                'option_renames': editor.option_renames(),
            },
            'reset': reset,
            'load': load,
        }

    def construct_interpreter(self, id: str, config_values: dict[str, Any]) -> SessionDataSectionInterpreterBase:
        """
        Constructs a SimpleFormInterpreter from the configuration values.

        :param id: The unique id to assign to the constructed interpreter.
        :param config_values: Dictionary containing 'title' and 'fields', a list of TypedItem
        :return: SimpleFormInterpreter instance configured with FieldConfiguration dictionary, in field order
        """
        title = config_values.get('title', '')
        items: list[TypedItem] = config_values.get('fields', [])
        field_configs: dict[str, FieldConfiguration] = {}
        for index, item in enumerate(items):
            name = item.name.strip()
            choices = [ChoiceOption(v, d) for v, d in item.options] if item.item_type is ColumnType.CHOICE else None
            # A repeated name is kept under a stand-in key, so config_problems() reports it
            # and the form refuses to apply, instead of one field silently replacing the other
            key = name if name not in field_configs else f"{name}#{index}"
            field_configs[key] = FieldConfiguration(name, item.item_type, choices)
        return SimpleFormInterpreter(id, title, field_configs)

    def renames(self, config_values: dict[str, Any]) -> list[PartRename]:
        """Fields and their choices renamed in place."""
        return self._item_renames(config_values)

    def describe(self, interpreter: SessionDataSectionInterpreterBase) -> list[str]:
        lines = [
            _describe_item(field.name, field.field_type, [(choice.value, choice.description) for choice in field.choices])
            for field in interpreter.fields.values()
        ]
        return lines or ["Fields: (none)"]


# Default configuration list - can be easily extended or modified
STUB_INTERPRETER_CONFIGS: list[InterpreterConfig] = [
    TableInterpreterConfig(),
    RunningTallyInterpreterConfig(),
    SimpleFormInterpreterConfig(),
]
