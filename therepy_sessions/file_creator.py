data = [
  [ "Word", "Times Prompted", "Times w/out Prompt" ],
  [ "Request", 3, 4 ],
  [ "Surrender", 2, 1 ],
  [ "Stare", 1, 2 ],
  [ "Holler", 0, 2 ],
  [ "Gallop", 0, 1 ]
]


def create_therapy_session_sheet(service, sheet_title):
    """
    Creates a Google Sheet with therapy session data.
    
    Args:
        service: Google Sheets API service object
        sheet_title: Title for the new spreadsheet
        
    Returns:
        dict: Response containing spreadsheet ID and other details
    """
    # Create a new spreadsheet
    spreadsheet = {
        'properties': {
            'title': sheet_title
        }
    }
    
    try:
        # Create the spreadsheet
        spreadsheet_result = service.spreadsheets().create(body=spreadsheet).execute()
        spreadsheet_id = spreadsheet_result.get('spreadsheetId')
        
        # Prepare the data for insertion
        values = data

        times_prompted_per_word = [ word_row[1] for word_row in data[1:] ]
        times_prompted = sum(times_prompted_per_word)

        times_on_own_per_word = [ word_row[2] for word_row in data[1:] ]
        times_on_own = sum(times_on_own_per_word)

        values = values + [
            [],
            [],
            [ f"Jimmy was prompted {times_prompted} times but said the word himself {times_on_own} times." ]
        ]
        
        # Define the range where data will be inserted (starting from A1)
        range_name = 'Sheet1!A1'
        
        # Prepare the request body
        value_input_option = 'RAW'  # or 'USER_ENTERED' if you want Google Sheets to parse the data
        
        body = {
            'values': values
        }
        
        # Insert the data into the spreadsheet
        result = service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=range_name,
            valueInputOption=value_input_option,
            body=body
        ).execute()
        
        print(f"Successfully created spreadsheet with ID: {spreadsheet_id}")
        print(f"Updated {result.get('updatedCells')} cells")
        print(f"Spreadsheet URL: https://docs.google.com/spreadsheets/d/{spreadsheet_id}")
        
        return {
            'spreadsheet_id': spreadsheet_id,
            'url': f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}",
            'updated_cells': result.get('updatedCells'),
            'updated_rows': result.get('updatedRows')
        }
        
    except Exception as error:
        print(f"An error occurred: {error}")
        return None