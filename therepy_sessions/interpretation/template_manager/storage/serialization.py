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
from interpretation.student_data_sheet import DataSheetScalarType
from interpretation.interpreter_types.table_interpreter import TableInterpreter
from interpretation.interpreter_types.running_tally_interpreter import RunningTallyInterpreter
from interpretation.interpreter_types.simple_form_interpreter import SimpleFormInterpreter, FieldConfiguration


class InterpreterSerializer(ABC):
    """Abstract base class for serializing SessionDataSectionInterpreterBase instances to JSON."""
    
    @abstractmethod
    def serialize(self, interpreter) -> dict:
        """
        Serialize a SessionDataSectionInterpreterBase instance to a dictionary.
        
        Args:
            interpreter: The SessionDataSectionInterpreterBase instance to serialize
            
        Returns:
            dict: Dictionary representation of the interpreter
        """
        pass

    @abstractmethod
    def deserialize(self, data: dict):
        """
        Deserialize a dictionary back to a SessionDataSectionInterpreterBase instance.
        
        Args:
            data: Dictionary representation of the interpreter
            
        Returns:
            SessionDataSectionInterpreterBase: The reconstructed interpreter instance
        """
        pass


class TableInterpreterSerializer(InterpreterSerializer):
    """Serializer for TableInterpreter instances."""
    
    def serialize(self, interpreter) -> dict:
        """
        Serialize a TableInterpreter to a dictionary.
        
        Args:
            interpreter: TableInterpreter instance
            
        Returns:
            dict: Dictionary containing type and column configuration
        """
        # Use the public properties
        columns = interpreter.columns

        return {
            'type': 'TableInterpreter',
            'id': interpreter.id,
            'title': interpreter.title,
            'config': {
                'columns': columns
            }
        }

    def deserialize(self, data: dict):
        """
        Deserialize a dictionary to a TableInterpreter instance.

        Args:
            data: Dictionary representation of the interpreter

        Returns:
            TableInterpreter: The reconstructed TableInterpreter instance
        """
        columns = data['config']['columns']
        title = data.get('title', '')
        return TableInterpreter(data['id'], title, columns)


class RunningTallyInterpreterSerializer(InterpreterSerializer):
    """Serializer for RunningTallyInterpreter instances."""
    
    def serialize(self, interpreter) -> dict:
        """
        Serialize a RunningTallyInterpreter to a dictionary.
        
        Args:
            interpreter: RunningTallyInterpreter instance
            
        Returns:
            dict: Dictionary containing type and tally configuration
        """
        # Use the public properties
        tally_type = interpreter.tally_type
        tally_choice_options = interpreter.tally_choice_options
        
        # Convert DataSheetScalarType to string for serialization
        tally_type_str = None
        if tally_type is not None:
            if hasattr(tally_type, 'name'):
                tally_type_str = tally_type.name
            else:
                tally_type_str = str(tally_type)
        
        return {
            'type': 'RunningTallyInterpreter',
            'id': interpreter.id,
            'title': interpreter.title,
            'config': {
                'tally_type': tally_type_str,
                'tally_choice_options': tally_choice_options if tally_choice_options else []
            }
        }

    def deserialize(self, data: dict):
        """
        Deserialize a dictionary to a RunningTallyInterpreter instance.
        
        Args:
            data: Dictionary representation of the interpreter
            
        Returns:
            RunningTallyInterpreter: The reconstructed RunningTallyInterpreter instance
        """
        config = data['config']
        
        # Convert string back to DataSheetScalarType
        tally_type_str = config['tally_type']
        tally_type = None
        if tally_type_str:
            tally_type = getattr(DataSheetScalarType, tally_type_str, None)
        
        tally_choice_options = config.get('tally_choice_options', [])
        title = data.get('title', '')

        return RunningTallyInterpreter(data['id'], title, tally_type, tally_choice_options)


class SimpleFormInterpreterSerializer(InterpreterSerializer):
    """Serializer for SimpleFormInterpreter instances."""
    
    def serialize(self, interpreter) -> dict:
        """
        Serialize a SimpleFormInterpreter to a dictionary.
        
        Args:
            interpreter: SimpleFormInterpreter instance
            
        Returns:
            dict: Dictionary containing type and field configurations
        """
        # Use the public property
        fields = interpreter.fields
        
        # Serialize field configurations
        serialized_fields = {}
        for field_name, field_config in fields.items():
            # Extract FieldConfiguration properties
            field_name_prop = getattr(field_config, 'name', field_name)
            field_type = getattr(field_config, 'fieldType', None)
            
            # Convert fieldType to string for serialization
            field_type_str = None
            if field_type is not None:
                if hasattr(field_type, 'name'):
                    field_type_str = field_type.name
                else:
                    field_type_str = str(field_type)
            
            serialized_fields[field_name] = {
                'name': field_name_prop,
                'fieldType': field_type_str
            }
        
        return {
            'type': 'SimpleFormInterpreter',
            'id': interpreter.id,
            'title': interpreter.title,
            'config': {
                'fields': serialized_fields
            }
        }

    def deserialize(self, data: dict):
        """
        Deserialize a dictionary to a SimpleFormInterpreter instance.
        
        Args:
            data: Dictionary representation of the interpreter
            
        Returns:
            SimpleFormInterpreter: The reconstructed SimpleFormInterpreter instance
        """
        serialized_fields = data['config']['fields']
        
        # Reconstruct FieldConfiguration objects
        fields = {}
        for field_name, field_data in serialized_fields.items():
            field_type_str = field_data['fieldType']
            field_type = None
            if field_type_str:
                field_type = getattr(DataSheetScalarType, field_type_str, None)
            
            fields[field_name] = FieldConfiguration(field_data['name'], field_type)

        title = data.get('title', '')
        return SimpleFormInterpreter(data['id'], title, fields)


class InterpreterSerializerRegistry:
    """Registry for managing interpreter serializers."""
    
    def __init__(self):
        """Initialize the registry with default serializers."""
        # Registry mapping interpreter types to their serializers
        self._serializers = {
            'TableInterpreter': TableInterpreterSerializer(),
            'RunningTallyInterpreter': RunningTallyInterpreterSerializer(),
            'SimpleFormInterpreter': SimpleFormInterpreterSerializer(),
        }
    
    def get_serializer(self, interpreter):
        """Get the appropriate serializer for an interpreter."""
        interpreter_type = type(interpreter).__name__
        
        if interpreter_type in self._serializers:
            return self._serializers[interpreter_type]
        
        raise ValueError(f"No serializer found for interpreter type: {interpreter_type}")
    
    def get_serializer_from_data(self, data: dict):
        """Get the appropriate serializer based on dictionary content."""
        interpreter_type = data.get('type')
        
        if not interpreter_type:
            raise ValueError("JSON missing 'type' field")
        
        if interpreter_type in self._serializers:
            return self._serializers[interpreter_type]
        
        raise ValueError(f"No serializer found for interpreter type: {interpreter_type}")


# Default registry instance
SERIALIZER_REGISTRY = InterpreterSerializerRegistry()


# API convenience functions
def serialize(interpreter) -> dict:
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


def deserialize(data: dict):
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