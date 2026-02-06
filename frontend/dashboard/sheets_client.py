"""Google Sheets API client."""

import os
import json
from typing import List, Optional

try:
    from google.oauth2.credentials import Credentials
    from google.oauth2.service_account import Credentials as ServiceAccountCredentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    GOOGLE_API_AVAILABLE = True
except ImportError:
    GOOGLE_API_AVAILABLE = False
    print("Warning: Google API libraries not installed. Dashboard sync will not work.")


SCOPES = ['https://www.googleapis.com/auth/spreadsheets']


class GoogleSheetsClient:
    """Client for Google Sheets API operations."""
    
    # Google Sheets has a 50,000 character limit per cell
    MAX_CELL_LENGTH = 45000
    
    def __init__(self, spreadsheet_id: Optional[str] = None):
        """
        Initialize the Google Sheets client.
        
        Args:
            spreadsheet_id: ID of the spreadsheet to use
        """
        self.spreadsheet_id = spreadsheet_id or os.getenv('SPREADSHEET_ID')
        self.service = None
        
        if GOOGLE_API_AVAILABLE:
            self._authenticate()
    
    def _authenticate(self) -> bool:
        """Authenticate with Google Sheets API."""
        # Try Service Account first (for server environments)
        if self._authenticate_service_account():
            return True
        
        # Fall back to OAuth (for local development)
        return self._authenticate_oauth()
    
    def _authenticate_service_account(self) -> bool:
        """Authenticate using Service Account."""
        try:
            service_account_json = os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON')
            
            if service_account_json:
                print("[Sheets] Using Service Account from environment variable")
                service_account_info = json.loads(service_account_json)
                creds = ServiceAccountCredentials.from_service_account_info(
                    service_account_info, scopes=SCOPES
                )
            elif os.path.exists('service-account.json'):
                print("[Sheets] Using Service Account from file")
                creds = ServiceAccountCredentials.from_service_account_file(
                    'service-account.json', scopes=SCOPES
                )
            else:
                return False
            
            self.service = build('sheets', 'v4', credentials=creds)
            print("[Sheets] Successfully authenticated with Service Account")
            return True
            
        except Exception as e:
            print(f"[Sheets] Service Account authentication failed: {e}")
            return False
    
    def _authenticate_oauth(self) -> bool:
        """Authenticate using OAuth (for local development)."""
        try:
            creds = None
            
            if os.path.exists('token.json'):
                creds = Credentials.from_authorized_user_file('token.json', SCOPES)
            
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    if not os.path.exists('credentials.json'):
                        print("[Sheets] No OAuth credentials found")
                        return False
                    
                    print("[Sheets] Using OAuth authentication")
                    flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
                    creds = flow.run_local_server(port=0)
                
                with open('token.json', 'w') as token:
                    token.write(creds.to_json())
            
            self.service = build('sheets', 'v4', credentials=creds)
            print("[Sheets] Successfully authenticated with OAuth")
            return True
            
        except Exception as e:
            print(f"[Sheets] OAuth authentication failed: {e}")
            return False
    
    def is_available(self) -> bool:
        """Check if the client is properly configured."""
        return GOOGLE_API_AVAILABLE and self.service is not None and self.spreadsheet_id is not None
    
    @staticmethod
    def truncate_content(content: str, max_length: int = None) -> str:
        """Truncate content to fit Google Sheets cell limit."""
        if not content:
            return content
        
        max_length = max_length or GoogleSheetsClient.MAX_CELL_LENGTH
        
        if len(content) <= max_length:
            return content
        
        truncated = content[:max_length - 50]
        truncated += f"\n\n... [TRUNCATED - Original length: {len(content)} chars]"
        return truncated
    
    def ensure_sheet_exists(self, sheet_name: str) -> None:
        """Ensure a sheet exists, create it if it doesn't."""
        if not self.is_available():
            return
        
        try:
            spreadsheet = self.service.spreadsheets().get(
                spreadsheetId=self.spreadsheet_id
            ).execute()
            existing_sheets = [
                sheet['properties']['title'] 
                for sheet in spreadsheet.get('sheets', [])
            ]
            
            if sheet_name not in existing_sheets:
                print(f"[Sheets] Creating sheet: {sheet_name}")
                requests = [{
                    "addSheet": {
                        "properties": {"title": sheet_name}
                    }
                }]
                
                self.service.spreadsheets().batchUpdate(
                    spreadsheetId=self.spreadsheet_id,
                    body={"requests": requests}
                ).execute()
                
        except HttpError as e:
            print(f"[Sheets] Error ensuring sheet exists: {e}")
    
    def clear_sheet(self, sheet_name: str) -> None:
        """Clear all data from a sheet."""
        if not self.is_available():
            return
        
        try:
            self.ensure_sheet_exists(sheet_name)
            
            range_name = f"{sheet_name}!A:Z"
            self.service.spreadsheets().values().clear(
                spreadsheetId=self.spreadsheet_id,
                range=range_name
            ).execute()
        except HttpError as e:
            print(f"[Sheets] Error clearing sheet: {e}")
    
    def write_to_sheet(
        self, 
        sheet_name: str, 
        data: List[List], 
        start_cell: str = "A1"
    ) -> None:
        """Write data to a sheet."""
        if not self.is_available():
            return
        
        try:
            self.ensure_sheet_exists(sheet_name)
            
            range_name = f"{sheet_name}!{start_cell}"
            body = {'values': data}
            
            result = self.service.spreadsheets().values().update(
                spreadsheetId=self.spreadsheet_id,
                range=range_name,
                valueInputOption='RAW',
                body=body
            ).execute()
            
            print(f"[Sheets] Updated {sheet_name}: {result.get('updatedCells')} cells")
            
        except HttpError as e:
            print(f"[Sheets] Error writing to sheet: {e}")
    
    def create_spreadsheet(self, title: str = "CS 15 Tutor Analytics") -> Optional[str]:
        """Create a new spreadsheet."""
        if not GOOGLE_API_AVAILABLE or not self.service:
            return None
        
        try:
            spreadsheet = {
                'properties': {'title': title},
                'sheets': [
                    {'properties': {'title': 'Overview'}},
                    {'properties': {'title': 'Users'}},
                    {'properties': {'title': 'Conversations'}},
                    {'properties': {'title': 'Messages'}},
                    {'properties': {'title': 'Analytics'}},
                    {'properties': {'title': 'UserInteractions'}},
                ]
            }
            
            result = self.service.spreadsheets().create(body=spreadsheet).execute()
            spreadsheet_id = result.get('spreadsheetId')
            
            print(f"[Sheets] Created spreadsheet: {title}")
            print(f"[Sheets] ID: {spreadsheet_id}")
            print(f"[Sheets] URL: https://docs.google.com/spreadsheets/d/{spreadsheet_id}")
            
            return spreadsheet_id
            
        except HttpError as e:
            print(f"[Sheets] Error creating spreadsheet: {e}")
            return None
