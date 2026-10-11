"""
Serialization classes for SessionDataSectionInterpreterBase instances.

Provides abstract base class and concrete implementations for serializing
interpreter instances to JSON format for storage persistence.

Usage:
    For most use cases, simply import and use the convenience functions:

    ```python
    from interpretation.template_manager.storage.serialization import serialize, deserialize

    # Serialize an interpreter to a dictionary
    data_dict = serialize(my_interpreter)

    # Deserialize dictionary back to an interpreter
    restored_interpreter = deserialize(data_dict)
    ```

    These functions automatically handle finding the appropriate serializer
    based on the interpreter type and dictionary content respectively.

    For advanced use cases, you can work directly with the registry and
    individual serializers, but the convenience functions should cover
    most scenarios.
"""

import json
from abc import ABC, abstractmethod
from typing import Any
from interpretation.value_types import ChoiceOption, ColumnType, TallyOption
from interpretation.interpreter_types.table_interpreter import ColumnDefinition, TableInterpreter
from interpretation.interpreter_types.running_tally_interpreter import RunningTallyInterpreter
from interpretation.interpreter_types.simple_form_interpreter import SimpleFormInterpreter, FieldConfiguration
from interpretation.templates.student_data_sheet_interpreter import SessionDataSectionInterpreterBase


class InterpreterSerializer(ABC):
    """Abstract base class for serializing SessionDataSectionInterpreterBase instances to JSON."""
    
    @abstractmethod
    def serialize(self, interpreter: SessionDataSectionInterpreterBase) -> dict[str, Any]:
        """
        Serialize a SessionDataSectionInterpreterBase instance to a dictionary.
        
        Args:
            interpreter: The SessionDataSectionInterpreterBase instance to serialize
            
        Returns:
            dict: Dictionary representation of the interpreter
        """
        pass

    @abstractmethod
    def deserialize(self, data: dict[str, Any]) -> SessionDataSectionInterpreterBase:
        """
        Deserialize a dictionary back to a SessionDataSectionInterpreterBase instance.
        
        Args:
            data: Dictionary representation of the interpreter
            
        Returns:
            SessionDataSectionInterpreterBase: The reconstructed interpreter instance
        """
        pass


def _column_type_named(name: Any, default: ColumnType) -> ColumnType:
    """The ColumnType with this member name, or `default` when it is missing or unknown."""
    if isinstance(name, str) and name in ColumnType.__members__:
        return ColumnType[name]
    return default


def _saved_options(data: dict[str, Any]) -> list[tuple[str, str]]:
    """The (value, description) pairs saved under "options", or [] when there are none."""
    return [
        (str(option.get("value", "")), str(option.get("description", "")))
        for option in data.get("options") or []
    ]


class TableInterpreterSerializer(InterpreterSerializer):
    """Serializer for TableInterpreter instances."""
    
    def serialize(self, interpreter: SessionDataSectionInterpreterBase) -> dict[str, Any]:
        """
        Serialize a TableInterpreter to a dictionary.
        
        Args:
            interpreter: TableInterpreter instance
            
        Returns:
            dict: Dictionary containing type and column configuration
        """
        # Save each column in the shape deserialize() reads back
        columns = [column.to_json() for column in interpreter.columns]

        return {
            'type': 'TableInterpreter',
            'id': interpreter.id,
            'title': interpreter.title,
            'config': {
                'columns': columns
            }
        }

    def deserialize(self, data: dict[str, Any]) -> SessionDataSectionInterpreterBase:
        """
        Deserialize a dictionary to a TableInterpreter instance.

        Reads the current column shape ("column_type" and "options") and the older one
        ("column_choices" only): an older column is Choice when it has choices, and Text
        otherwise (FR-018). An unknown type loads as Text.

        Args:
            data: Dictionary representation of the interpreter

        Returns:
            TableInterpreter: The reconstructed TableInterpreter instance
        """
        column_defs_json: list[Any] = data['config']['columns']

        column_defs: list[ColumnDefinition] = [self._column_from_json(col) for col in column_defs_json]
        
        title = data.get('title', '')
        return TableInterpreter(data['id'], title, column_defs)

    @staticmethod
    def _column_from_json(col: dict[str, Any]) -> ColumnDefinition:
        old_choices = [str(choice) for choice in col.get("column_choices") or []]
        default_type = ColumnType.CHOICE if old_choices else ColumnType.TEXT
        column_type = _column_type_named(col.get("column_type"), default_type)
        options = _saved_options(col) if "options" in col else [(choice, "") for choice in old_choices]

        if column_type is ColumnType.CHOICE:
            return ColumnDefinition(col["column_name"], column_type, choices=[ChoiceOption(v, d) for v, d in options])
        if column_type is ColumnType.TALLY:
            return ColumnDefinition(col["column_name"], column_type, tally_options=[TallyOption(v, d) for v, d in options])
        return ColumnDefinition(col["column_name"], column_type)


class RunningTallyInterpreterSerializer(InterpreterSerializer):
    """Serializer for RunningTallyInterpreter instances."""
    
    def serialize(self, interpreter: SessionDataSectionInterpreterBase) -> dict[str, Any]:
        """
        Serialize a RunningTallyInterpreter to a dictionary.
        
        Args:
            interpreter: RunningTallyInterpreter instance
            
        Returns:
            dict: Dictionary containing type and tally configuration
        """
        return {
            'type': 'RunningTallyInterpreter',
            'id': interpreter.id,
            'title': interpreter.title,
            'config': {
                'tally_options': [
                    {'mark': option.mark, 'description': option.description}
                    for option in interpreter.tally_options
                ]
            }
        }

    def deserialize(self, data: dict[str, Any]) -> SessionDataSectionInterpreterBase:
        """
        Deserialize a dictionary to a RunningTallyInterpreter instance.

        Reads "tally_options", or else the older "tally_choice_options" strings with blank
        descriptions. The older "tally_type" is ignored: it was always CHOICE (FR-023).
        
        Args:
            data: Dictionary representation of the interpreter
            
        Returns:
            RunningTallyInterpreter: The reconstructed RunningTallyInterpreter instance
        """
        config = data['config']
        if 'tally_options' in config:
            tally_options = [
                TallyOption(str(option.get('mark', '')), str(option.get('description', '')))
                for option in config['tally_options'] or []
            ]
        else:
            tally_options = [TallyOption(str(mark)) for mark in config.get('tally_choice_options') or []]
        title = data.get('title', '')

        return RunningTallyInterpreter(data['id'], title, tally_options)


class SimpleFormInterpreterSerializer(InterpreterSerializer):
    """Serializer for SimpleFormInterpreter instances."""
    
    def serialize(self, interpreter: SessionDataSectionInterpreterBase) -> dict[str, Any]:
        """
        Serialize a SimpleFormInterpreter to a dictionary.
        
        Args:
            interpreter: SimpleFormInterpreter instance
            
        Returns:
            dict: Dictionary containing type and field configurations
        """
        serialized_fields = {
            field_name: {
                'name': field_config.name,
                'fieldType': field_config.field_type.name,
                'options': [
                    {'value': choice.value, 'description': choice.description}
                    for choice in field_config.choices
                ],
            }
            for field_name, field_config in interpreter.fields.items()
        }
        
        return {
            'type': 'SimpleFormInterpreter',
            'id': interpreter.id,
            'title': interpreter.title,
            'config': {
                'fields': serialized_fields
            }
        }

    def deserialize(self, data: dict[str, Any]) -> SessionDataSectionInterpreterBase:
        """
        Deserialize a dictionary to a SimpleFormInterpreter instance.

        A missing, null, or unknown "fieldType" loads as Text, and so does TALLY, which
        only columns can have (FR-019).
        
        Args:
            data: Dictionary representation of the interpreter
            
        Returns:
            SimpleFormInterpreter: The reconstructed SimpleFormInterpreter instance
        """
        serialized_fields = data['config']['fields']
        
        # Reconstruct FieldConfiguration objects
        fields: dict[str, FieldConfiguration] = {}
        for field_name, field_data in serialized_fields.items():
            field_type = _column_type_named(field_data.get('fieldType'), ColumnType.TEXT)
            if field_type is ColumnType.TALLY:
                field_type = ColumnType.TEXT
            choices = [ChoiceOption(v, d) for v, d in _saved_options(field_data)] if field_type is ColumnType.CHOICE else []
            fields[field_name] = FieldConfiguration(field_data.get('name', field_name), field_type, choices)

        title = data.get('title', '')
        return SimpleFormInterpreter(data['id'], title, fields)


class InterpreterSerializerRegistry:
    """Registry for managing interpreter serializers."""
    
    def __init__(self) -> None:
        """Initialize the registry with default serializers."""
        # Registry mapping interpreter types to their serializers
        self._serializers = {
            'TableInterpreter': TableInterpreterSerializer(),
            'RunningTallyInterpreter': RunningTallyInterpreterSerializer(),
            'SimpleFormInterpreter': SimpleFormInterpreterSerializer(),
        }
    
    def get_serializer(self, interpreter: SessionDataSectionInterpreterBase) -> InterpreterSerializer:
        """Get the appropriate serializer for an interpreter."""
        interpreter_type = type(interpreter).__name__
        
        if interpreter_type in self._serializers:
            return self._serializers[interpreter_type]
        
        raise ValueError(f"No serializer found for interpreter type: {interpreter_type}")
    
    def get_serializer_from_data(self, data: dict[str, Any]) -> InterpreterSerializer:
        """Get the appropriate serializer based on dictionary content."""
        interpreter_type = data.get('type')
        
        if not interpreter_type:
            raise ValueError("JSON missing 'type' field")
        
        if interpreter_type in self._serializers:
            return self._serializers[interpreter_type]
        
        raise ValueError(f"No serializer found for interpreter type: {interpreter_type}")


# Default registry instance
SERIALIZER_REGISTRY: InterpreterSerializerRegistry = InterpreterSerializerRegistry()


# API convenience functions
def serialize(interpreter: SessionDataSectionInterpreterBase) -> dict[str, Any]:
    """
    Serialize an interpreter instance to a dictionary.
    
    This is a convenience function that automatically finds the appropriate
    serializer and serializes the interpreter.
    
    Args:
        interpreter: SessionDataSectionInterpreterBase instance to serialize
        
    Returns:
        dict: Dictionary representation of the interpreter
        
    Raises:
        ValueError: If no serializer is found for the interpreter type
    """
    serializer = SERIALIZER_REGISTRY.get_serializer(interpreter)
    return serializer.serialize(interpreter)


def deserialize(data: dict[str, Any]) -> SessionDataSectionInterpreterBase:
    """
    Deserialize a dictionary to an interpreter instance.
    
    This is a convenience function that automatically determines the appropriate
    serializer based on the dictionary content and deserializes the interpreter.
    
    Args:
        data: Dictionary representation of an interpreter
        
    Returns:
        SessionDataSectionInterpreterBase: The reconstructed interpreter instance
        
    Raises:
        ValueError: If no serializer is found for the interpreter type in dictionary
    """
    serializer = SERIALIZER_REGISTRY.get_serializer_from_data(data)
    return serializer.deserialize(data)