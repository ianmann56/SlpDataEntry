import json
import os
from botocore.exceptions import ClientError, NoCredentialsError

from collection.collection_headers import StudentDataSheetImport

def image_to_text(image_path, inject_textract_client):
    """
    Converts an image to text using AWS Textract with table detection.
    
    Args:
        image_path (str): Path to the image file
        
    Returns:
        dict: Contains both raw text and structured table data
        
    Raises:
        FileNotFoundError: If the image file doesn't exist
        ClientError: If there's an AWS service error
        Exception: If processing fails
    """
    try:
        # Check if file exists
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image file not found: {image_path}")
        
        # Create Textract client
        textract_client = inject_textract_client()
        
        # Read image file
        with open(image_path, 'rb') as image_file:
            image_bytes = image_file.read()
        
        # Call Textract analyze_document with TABLES feature
        response = textract_client.analyze_document(
            Document={'Bytes': image_bytes},
            FeatureTypes=['FORMS', 'TABLES']
        )
        
        form_data = _extract_form_data(response)
        tables = _extract_table_data(response)
    
        return StudentDataSheetImport(form_data, tables)
        
    except FileNotFoundError:
        raise
    except ClientError as e:
        raise Exception(f"AWS Textract error: {str(e)}")
    except Exception as e:
        raise Exception(f"Error processing image {image_path}: {str(e)}")

def _extract_table_data(response):
    """
    Extracts tabular data from Textract response.
    
    Args:
        response: Full Textract response
        
    Returns:
        list: A list of 2D lists that represent each row in the table.
    """
    tables = []
    for block in response.get('Blocks', []):
        if block['BlockType'] == 'TABLE':
            table = _extract_table_from_block(response, block)
            tables.append(table)
    return tables


def _extract_form_data(response):
    """
    Extracts form data (key-value pairs) from Textract response.
    
    Args:
        response: Full Textract response
        
    Returns:
        dict: A dictionary of the form where the key is the field label and
              the value is the field value.
    """
    # Create lookup for blocks by ID
    blocks = {block['Id']: block for block in response['Blocks']}
    
    form_fields = {}
    
    for block in response.get('Blocks', []):
        if block['BlockType'] == 'KEY_VALUE_SET':
            if block.get('EntityTypes') and 'KEY' in block['EntityTypes']:
                # This is a key block, find its associated value
                key_text = _get_text_from_block(response, block)
                value_text = ""
                
                # Find the corresponding VALUE block
                if 'Relationships' in block:
                    for relationship in block['Relationships']:
                        if relationship['Type'] == 'VALUE':
                            for value_id in relationship['Ids']:
                                value_block = blocks[value_id]
                                if value_block['BlockType'] == 'KEY_VALUE_SET' and value_block.get('EntityTypes') and 'VALUE' in value_block['EntityTypes']:
                                    value_text = _get_text_from_block(response, value_block)
                                    break
                
                if key_text:
                    form_fields[key_text.removesuffix(":")] = value_text
    
    return form_fields


def _get_text_from_block(response, block):
    """
    Extracts text content from a block by following its child relationships.
    
    Args:
        response: Full Textract response
        block: Block to extract text from
        
    Returns:
        str: Text content of the block
    """
    blocks = {block['Id']: block for block in response['Blocks']}
    text = ""
    
    if 'Relationships' in block:
        for relationship in block['Relationships']:
            if relationship['Type'] == 'CHILD':
                for child_id in relationship['Ids']:
                    child_block = blocks[child_id]
                    if child_block['BlockType'] == 'WORD':
                        text += child_block['Text'] + ' '
    
    return text.strip()


def _extract_table_from_block(response, table_block):
    """
    Extracts structured table data from Textract response.
    
    Args:
        response: Full Textract response
        table_block: TABLE block from response
        
    Returns:
        list: 2D array representing the table
    """
    # Create lookup for blocks by ID
    blocks = {block['Id']: block for block in response['Blocks']}
    
    table_data = []
    
    if 'Relationships' in table_block:
        for relationship in table_block['Relationships']:
            if relationship['Type'] == 'CHILD':
                rows = {}
                
                # Get all CELL blocks for this table
                for cell_id in relationship['Ids']:
                    cell_block = blocks[cell_id]
                    if cell_block['BlockType'] == 'CELL':
                        row_index = cell_block['RowIndex'] - 1  # Convert to 0-based
                        col_index = cell_block['ColumnIndex'] - 1  # Convert to 0-based
                        
                        # Get cell text
                        cell_text = _get_cell_text(response, cell_block)
                        
                        # Initialize row if needed
                        if row_index not in rows:
                            rows[row_index] = {}
                        
                        rows[row_index][col_index] = cell_text
                
                # Convert to 2D array
                max_row = max(rows.keys()) if rows else -1
                for row_idx in range(max_row + 1):
                    if row_idx in rows:
                        max_col = max(rows[row_idx].keys()) if rows[row_idx] else -1
                        row_data = []
                        for col_idx in range(max_col + 1):
                            row_data.append(rows[row_idx].get(col_idx, ''))
                        table_data.append(row_data)
                    else:
                        table_data.append([])
    
    return table_data


def _get_cell_text(response, cell_block):
    """
    Extracts text from a cell block.
    
    Args:
        response: Full Textract response
        cell_block: CELL block
        
    Returns:
        str: Text content of the cell
    """
    blocks = {block['Id']: block for block in response['Blocks']}
    cell_text = ""
    
    if 'Relationships' in cell_block:
        for relationship in cell_block['Relationships']:
            if relationship['Type'] == 'CHILD':
                for word_id in relationship['Ids']:
                    word_block = blocks[word_id]
                    if word_block['BlockType'] == 'WORD':
                        cell_text += word_block['Text'] + ' '
    
    return cell_text.strip()
