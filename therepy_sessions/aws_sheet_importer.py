import boto3
import os
from botocore.exceptions import ClientError, NoCredentialsError


def _create_textract_client():
    """
    Creates and configures AWS Textract client.
    Handles credential setup and client configuration.
    
    Returns:
        boto3.client: Configured Textract client
        
    Raises:
        NoCredentialsError: If AWS credentials are not found
        ClientError: If there's an error creating the client
    """
    try:
        # Create Textract client
        # AWS credentials should be configured via:
        # 1. AWS credentials file (~/.aws/credentials)
        # 2. Environment variables (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)
        # 3. IAM roles (if running on EC2)
        # 4. AWS CLI configuration
        
        client = boto3.client(
            'textract',
            region_name=os.environ.get('AWS_DEFAULT_REGION', 'us-east-1')
        )
        
        return client
        
    except NoCredentialsError:
        raise NoCredentialsError("AWS credentials not found. Please configure your credentials.")
    except Exception as e:
        raise Exception(f"Error creating Textract client: {str(e)}")


def image_to_text(image_path):
    """
    Converts an image to text using AWS Textract.
    
    Args:
        image_path (str): Path to the image file
        
    Returns:
        str: Extracted text from the image
        
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
        textract_client = _create_textract_client()
        
        # Read image file
        with open(image_path, 'rb') as image_file:
            image_bytes = image_file.read()
        
        # Call Textract detect_document_text
        response = textract_client.detect_document_text(
            Document={'Bytes': image_bytes}
        )
        
        # Extract text from response
        extracted_text = ""
        for block in response.get('Blocks', []):
            if block['BlockType'] == 'LINE':
                extracted_text += block['Text'] + '\n'
        
        return extracted_text.strip()
        
    except FileNotFoundError:
        raise
    except ClientError as e:
        raise Exception(f"AWS Textract error: {str(e)}")
    except Exception as e:
        raise Exception(f"Error processing image {image_path}: {str(e)}")
