data = [
  [ "Word", "Times Prompted", "Times w/out Prompt" ],
  [ "Request", 3, 4 ],
  [ "Surrender", 2, 1 ],
  [ "Stare", 1, 2 ],
  [ "Holler", 0, 2 ],
  [ "Gallop", 0, 1 ]
]

FOLDER_PATH = r'<Folder Path>'

def create_therapy_session_sheet(data, sheet_title, inject_google_service):
    """
    Creates a Google Sheet with therapy session data.
    
    Args:
        service: Google Sheets API service object
        sheet_title: Title for the new spreadsheet
        
    Returns:
        dict: Response containing spreadsheet ID and other details
    """
    # Dependency Injection
    service = inject_google_service()
    
    # Create a new spreadsheet
    spreadsheet = {
        'properties': {
            'title': sheet_title
        }
    }

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
    
    # Add pie chart data starting at E1
    chart_data = [
        ["Category", "Count"],
        ["Times Prompted", times_prompted],
        ["Times On Own", times_on_own]
    ]
    
    chart_body = {
        'values': chart_data
    }
    
    # Insert chart data at E1
    service.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        range='Sheet1!E1',
        valueInputOption='RAW',
        body=chart_body
    ).execute()
    
    # Create the pie chart
    chart_request = {
        "addChart": {
            "chart": {
                "spec": {
                    "title": "Times Prompted vs Times On Own",
                    "pieChart": {
                        "legendPosition": "RIGHT_LEGEND",
                        "domain": {
                            "sourceRange": {
                                "sources": [{
                                    "sheetId": 0,
                                    "startRowIndex": 1,  # Skip header row
                                    "endRowIndex": 3,    # Include both data rows
                                    "startColumnIndex": 4,  # Column E (Category labels)
                                    "endColumnIndex": 5     # Just column E
                                }]
                            }
                        },
                        "series": {
                            "sourceRange": {
                                "sources": [{
                                    "sheetId": 0,
                                    "startRowIndex": 1,  # Skip header row
                                    "endRowIndex": 3,    # Include both data rows
                                    "startColumnIndex": 5,  # Column F (Count values)
                                    "endColumnIndex": 6     # Just column F
                                }]
                            }
                        }
                    }
                },
                "position": {
                    "overlayPosition": {
                        "anchorCell": {
                            "sheetId": 0,
                            "rowIndex": 4,     # Start at row 5
                            "columnIndex": 4   # Column E
                        }
                    }
                }
            }
        }
    }
    
    # Execute the chart creation request
    service.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id,
        body={'requests': [chart_request]}
    ).execute()
    
    return {
        'spreadsheet_id': spreadsheet_id,
        'url': f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}",
        'updated_cells': result.get('updatedCells'),
        'updated_rows': result.get('updatedRows'),
        'times_prompted': times_prompted,
        'times_on_own': times_on_own
    }