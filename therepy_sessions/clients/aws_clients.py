import os
import boto3
from botocore.exceptions import ClientError, NoCredentialsError

def construct_textract_client():
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