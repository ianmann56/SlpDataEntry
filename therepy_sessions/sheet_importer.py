from PIL import Image, ImageOps
import pytesseract
import os
import cv2
import numpy as np
import csv
import io
import re

# Use bash:
# $ tesseract sample_data/veriety_w_prompting.png output --oem 3 --psm 12 -l eng
# this will print the output to "output.txt"
# Also check out this issue on tesseract: https://github.com/tesseract-ocr/tesseract/issues/1979

def image_to_text_simple(image_path):
    og_image = Image.open(image_path)
    grayscale = ImageOps.grayscale(og_image)
    image = ImageOps.invert(grayscale.convert('RGB'))
    extracted_text = pytesseract.image_to_string(image)
    cleaned_text = extracted_text.strip()
    return cleaned_text

def image_to_text(image_path, language='eng'):
    """
    Converts an image to text using OCR (Optical Character Recognition).
    
    Args:
        image_path (str): Path to the image file
        language (str): Language code for OCR (default: 'eng' for English)
                       Common codes: 'eng', 'spa', 'fra', 'deu', etc.
    
    Returns:
        str: Extracted text from the image
    
    Raises:
        FileNotFoundError: If the image file doesn't exist
        Exception: If OCR processing fails
    """
    # Check if file exists
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image file not found: {image_path}")
    
    # Open the image
    image = Image.open(image_path)
    
    # Perform OCR
    extracted_text = pytesseract.image_to_string(image, lang=language)
    
    # Clean up the text (remove extra whitespace)
    cleaned_text = extracted_text.strip()
    
    print(f"Successfully extracted text from: {image_path}")
    print(f"Text length: {len(cleaned_text)} characters")
    
    return cleaned_text


def image_to_text_with_preprocessing(image_path, language='eng', enhance=True):
    """
    Converts an image to text with optional preprocessing for better OCR results.
    
    Args:
        image_path (str): Path to the image file
        language (str): Language code for OCR (default: 'eng' for English)
        enhance (bool): Whether to apply image enhancement preprocessing
    
    Returns:
        str: Extracted text from the image
    """
    # Check if file exists
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image file not found: {image_path}")
    
    # Open the image
    image = Image.open(image_path)
    print(image.size)
    image = image.resize((image.size[0]*2, image.size[1]*2))
    image.save('sample_data/out.png')
    
    # Apply preprocessing if requested
    if enhance:
        # Convert to grayscale for better OCR
        image = image.convert('L')
        
        # Optional: You can add more preprocessing here like:
        # - Resize for better resolution
        # - Apply filters to reduce noise
        # - Adjust contrast/brightness
    
    
    # Perform OCR with custom configuration for better accuracy
    custom_config = r'--oem 3 --psm 12'
    # print(pytesseract.image_to_boxes(image, lang=language, config=custom_config))
    # print(pytesseract.image_to_data(image, lang=language, config=custom_config))
    extracted_text = pytesseract.image_to_string(image, lang=language, config=custom_config)
    
    # Clean up the text
    cleaned_text = extracted_text.strip()
    
    return cleaned_text

def image_to_text_with_opencv(image_path):
    # Load image
    img = cv2.imread(image_path)

    # Preprocessing (grayscale, thresholding)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]

    # Line detection (conceptual - requires more complex logic for accurate cell detection)
    lines = cv2.HoughLinesP(thresh, 1, np.pi/180, 100, minLineLength=100, maxLineGap=10)
    print(lines)
    data_str = "\n".join(lines)

    # # Assuming you have identified cell bounding boxes (x, y, w, h)
    # cell_bounding_boxes = [(10, 10, 50, 20), (70, 10, 50, 20)] # Example bounding boxes

    # table_data = []
    # for (x, y, w, h) in cell_bounding_boxes:
    #     cell_roi = img[y:y+h, x:x+w]
    #     cell_text = pytesseract.image_to_string(cell_roi, config='--psm 6') # Use PSM 6 for single block of text
    #     table_data.append(cell_text.strip())

    # data_str = "\n".join(table_data)
    
    return data_str


def table_to_text(image_path, language='eng'):
    """
    Converts a table in an image to a 2D array.
    
    Args:
        image_path (str): Path to the image file containing the table
        language (str): Language code for OCR (default: 'eng' for English)
    
    Returns:
        list: 2D array where each inner list represents a row of table data
    
    Raises:
        FileNotFoundError: If the image file doesn't exist
        Exception: If OCR processing fails
    """
    try:
        # Check if file exists
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image file not found: {image_path}")
        
        # Load and preprocess the image for better table detection
        img = cv2.imread(image_path)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
        # img = img.resize((1506, 412))
        
        # Apply threshold to get better contrast for table lines
        thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
        
        # Use pytesseract to detect table structure with specific PSM mode
        # PSM 6 is good for uniform block of text (like tables)
        # custom_config = r'--oem 3 --psm 6 --dpi 300 -c tessedit_char_whitelist=0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz .,|-()'
        custom_config = r'--oem 3 --psm 12 --dpi 300'
        
        # Get detailed data with bounding boxes
        data = pytesseract.image_to_data(img, lang=language, config=custom_config, output_type=pytesseract.Output.DICT)
        print(data)
        
        # Extract text with positions to reconstruct table structure
        words_with_positions = []
        for i in range(len(data['text'])):
            if int(data['conf'][i]) > 30:  # Filter out low confidence detections
                text = data['text'][i].strip()
                if text:  # Only add non-empty text
                    words_with_positions.append({
                        'text': text,
                        'left': data['left'][i],
                        'top': data['top'][i],
                        'width': data['width'][i],
                        'height': data['height'][i]
                    })
        
        # Sort words by vertical position (top) first, then horizontal (left)
        words_with_positions.sort(key=lambda x: (x['top'], x['left']))
        
        # Group words into rows based on vertical position
        rows = []
        current_row = []
        row_threshold = 20  # Pixels tolerance for same row
        
        for word in words_with_positions:
            if not current_row:
                current_row.append(word)
            else:
                # Check if word belongs to current row (similar y-position)
                last_word_top = current_row[-1]['top']
                if abs(word['top'] - last_word_top) <= row_threshold:
                    current_row.append(word)
                else:
                    # Start new row
                    if current_row:
                        rows.append(sorted(current_row, key=lambda x: x['left']))
                    current_row = [word]
        
        # Add the last row
        if current_row:
            rows.append(sorted(current_row, key=lambda x: x['left']))
        
        # Convert rows to CSV format
        csv_rows = []
        for row in rows:
            # Group words that are close horizontally into cells
            cells = []
            current_cell_words = []
            cell_threshold = 50  # Pixels tolerance for same cell
            
            for word in row:
                if not current_cell_words:
                    current_cell_words.append(word)
                else:
                    last_word_right = current_cell_words[-1]['left'] + current_cell_words[-1]['width']
                    if word['left'] - last_word_right <= cell_threshold:
                        current_cell_words.append(word)
                    else:
                        # Create cell from current words
                        cell_text = ' '.join([w['text'] for w in current_cell_words])
                        cells.append(cell_text)
                        current_cell_words = [word]
            
            # Add the last cell
            if current_cell_words:
                cell_text = ' '.join([w['text'] for w in current_cell_words])
                cells.append(cell_text)
            
            if cells:  # Only add non-empty rows
                csv_rows.append(cells)
        
        print(f"Successfully extracted table from: {image_path}")
        print(f"Found {len(csv_rows)} rows of data")
        
        return csv_rows
        
    except FileNotFoundError:
        raise
    except Exception as error:
        print(f"Error processing table in image {image_path}: {error}")
        raise


def table_to_text_complex(image_path, language='eng'):
    """
    Converts a table in an image to a 2D array with improved table detection.
    
    Args:
        image_path (str): Path to the image file containing the table
        language (str): Language code for OCR (default: 'eng' for English)
    
    Returns:
        list: 2D array where each inner list represents a row of table data
    
    Raises:
        FileNotFoundError: If the image file doesn't exist
        Exception: If OCR processing fails
    """
    try:
        # Check if file exists
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image file not found: {image_path}")
        
        # Load and preprocess the image for better table detection
        img = cv2.imread(image_path)
        if img is None:
            raise Exception("Could not load image")
        
        # Resize image if it's too small for better OCR
        height, width = img.shape[:2]
        if width < 800:
            scale_factor = 800 / width
            new_width = int(width * scale_factor)
            new_height = int(height * scale_factor)
            img = cv2.resize(img, (new_width, new_height), interpolation=cv2.INTER_CUBIC)
        
        # Convert to grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Apply Gaussian blur to reduce noise
        blurred = cv2.GaussianBlur(gray, (3, 3), 0)
        
        # Apply adaptive threshold for better contrast
        thresh = cv2.adaptiveThreshold(blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                     cv2.THRESH_BINARY, 11, 2)
        
        # Invert the image (make text black on white background)
        thresh = cv2.bitwise_not(thresh)
        
        # Use PSM 4 (single column) or PSM 12 (sparse text with OSD) for better table detection
        # Remove character whitelist to allow all characters
        custom_config = r'--oem 3 --psm 12'
        
        # Get detailed data with bounding boxes
        data = pytesseract.image_to_data(thresh, lang=language, config=custom_config, 
                                       output_type=pytesseract.Output.DICT)
        
        print(data)
        
        # Extract text with positions - use lower confidence threshold
        words_with_positions = []
        for i in range(len(data['text'])):
            if int(data['conf'][i]) > 10:  # Lowered confidence threshold
                text = data['text'][i].strip()
                if text and len(text) > 0:  # Only add non-empty text
                    words_with_positions.append({
                        'text': text,
                        'left': data['left'][i],
                        'top': data['top'][i],
                        'width': data['width'][i],
                        'height': data['height'][i],
                        'right': data['left'][i] + data['width'][i],
                        'bottom': data['top'][i] + data['height'][i]
                    })
        
        if not words_with_positions:
            print("No text detected. Trying alternative OCR approach...")
            # Fallback: try with different PSM
            custom_config = r'--oem 3 --psm 6'
            text = pytesseract.image_to_string(thresh, lang=language, config=custom_config)
            if text.strip():
                # Simple line-based parsing as fallback
                lines = [line.strip() for line in text.split('\n') if line.strip()]
                return [line.split() for line in lines]
            else:
                return []
        
        # Sort words by vertical position (top) first, then horizontal (left)
        words_with_positions.sort(key=lambda x: (x['top'], x['left']))
        
        # Group words into rows based on vertical position with improved logic
        rows = []
        current_row = []
        row_threshold = 30  # Increased tolerance for same row
        
        for word in words_with_positions:
            if not current_row:
                current_row.append(word)
            else:
                # Check if word belongs to current row using center y-position
                current_row_avg_y = sum(w['top'] + w['height']//2 for w in current_row) / len(current_row)
                word_center_y = word['top'] + word['height']//2
                
                if abs(word_center_y - current_row_avg_y) <= row_threshold:
                    current_row.append(word)
                else:
                    # Start new row
                    if current_row:
                        rows.append(sorted(current_row, key=lambda x: x['left']))
                    current_row = [word]
        
        # Add the last row
        if current_row:
            rows.append(sorted(current_row, key=lambda x: x['left']))
        
        # Convert rows to table structure with improved cell detection
        table_rows = []
        for row in rows:
            # Detect natural column boundaries based on gaps
            if len(row) <= 1:
                table_rows.append([word['text'] for word in row])
                continue
                
            # Calculate gaps between words
            gaps = []
            for i in range(len(row) - 1):
                gap = row[i+1]['left'] - row[i]['right']
                gaps.append(gap)
            
            # Determine column boundaries (larger gaps indicate column separations)
            if gaps:
                avg_gap = sum(gaps) / len(gaps)
                large_gap_threshold = max(avg_gap * 1.5, 20)  # At least 20 pixels or 1.5x average
                
                cells = []
                current_cell_words = [row[0]]
                
                for i, gap in enumerate(gaps):
                    if gap >= large_gap_threshold:
                        # End current cell and start new one
                        cell_text = ' '.join([w['text'] for w in current_cell_words])
                        cells.append(cell_text)
                        current_cell_words = [row[i + 1]]
                    else:
                        # Continue current cell
                        current_cell_words.append(row[i + 1])
                
                # Add the last cell
                if current_cell_words:
                    cell_text = ' '.join([w['text'] for w in current_cell_words])
                    cells.append(cell_text)
                
                table_rows.append(cells)
            else:
                # Single cell row
                table_rows.append([' '.join([w['text'] for w in row])])
        
        print(f"Successfully extracted table from: {image_path}")
        print(f"Found {len(table_rows)} rows of data")
        print("Extracted data preview:")
        for i, row in enumerate(table_rows[:5]):  # Show first 5 rows
            print(f"Row {i}: {row}")
        
        return table_rows
        
    except FileNotFoundError:
        raise
    except Exception as error:
        print(f"Error processing table in image {image_path}: {error}")
        raise