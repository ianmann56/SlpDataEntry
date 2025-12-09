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
            FeatureTypes=['TABLES']
        )
        
        # Extract regular text
        extracted_text = ""
        for block in response.get('Blocks', []):
            if block['BlockType'] == 'LINE':
                extracted_text += block['Text'] + '\n'
        
        # Extract table data
        tables = []
        for block in response.get('Blocks', []):
            if block['BlockType'] == 'TABLE':
                table = _extract_table_from_block(response, block)
                tables.append(table)
    
        return StudentDataSheetImport(extracted_text.strip(), tables)
        
    except FileNotFoundError:
        raise
    except ClientError as e:
        raise Exception(f"AWS Textract error: {str(e)}")
    except Exception as e:
        raise Exception(f"Error processing image {image_path}: {str(e)}")


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
