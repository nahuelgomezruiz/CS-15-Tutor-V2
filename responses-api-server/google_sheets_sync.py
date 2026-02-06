#!/usr/bin/env python3
"""Google Sheets sync for CS 15 Tutor database."""

import os
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any

try:
    from google.oauth2.credentials import Credentials
    from google.oauth2.service_account import Credentials as ServiceAccountCredentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
except ImportError:
    print(" Missing Google API libraries. Please install:")
    print("pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client")
    exit(1)

from database import db_manager, AnonymousUser, Conversation, Message, UserSession

# Google Sheets API scope
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

# Google Sheets configuration files
OAUTH_CREDENTIALS_FILE = 'credentials.json'
SERVICE_ACCOUNT_FILE = 'service-account.json'
TOKEN_FILE = 'token.json'
CONFIG_FILE = 'sheets_config.json'

class GoogleSheetsSync:
    """Handles syncing CS 15 Tutor data to Google Sheets"""
    
    # Google Sheets has a 50,000 character limit per cell
    MAX_CELL_LENGTH = 45000  # Use 45k to leave some buffer
    
    def __init__(self, spreadsheet_id: str = None):
        self.spreadsheet_id = spreadsheet_id
        self.service = None
        self.authenticate()
    
    @staticmethod
    def truncate_cell_content(content: str, max_length: int = None) -> str:
        """Truncate content to fit Google Sheets cell limit"""
        if not content:
            return content
        
        max_length = max_length or GoogleSheetsSync.MAX_CELL_LENGTH
        
        if len(content) <= max_length:
            return content
        
        # Truncate and add indicator
        truncated = content[:max_length - 50]  # Leave room for the truncation message
        truncated += f"\n\n... [TRUNCATED - Original length: {len(content)} chars]"
        return truncated
    
    def authenticate(self):
        """Authenticate with Google Sheets API using Service Account or OAuth"""
        
        # Try Service Account authentication first (for servers)
        if self._authenticate_service_account():
            return True
        
        # Fall back to OAuth (for local development)
        return self._authenticate_oauth()
    
    def _authenticate_service_account(self):
        """Authenticate using Service Account (for server environments)"""
        try:
            # Try environment variable first (for Render/production)
            service_account_json = os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON')
            
            if service_account_json:
                print(" Using Service Account from environment variable...")
                # Parse JSON from environment variable
                service_account_info = json.loads(service_account_json)
                creds = ServiceAccountCredentials.from_service_account_info(
                    service_account_info, scopes=SCOPES
                )
            elif os.path.exists(SERVICE_ACCOUNT_FILE):
                print(" Using Service Account from file...")
                # Use service account file
                creds = ServiceAccountCredentials.from_service_account_file(
                    SERVICE_ACCOUNT_FILE, scopes=SCOPES
                )
            else:
                return False
            
            self.service = build('sheets', 'v4', credentials=creds)
            print(" Successfully authenticated with Service Account")
            return True
            
        except Exception as e:
            print(f" Service Account authentication failed: {e}")
            return False
    
    def _authenticate_oauth(self):
        """Authenticate using OAuth (for local development)"""
        try:
            creds = None
            
            # Load existing token
            if os.path.exists(TOKEN_FILE):
                creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
            
            # If no valid credentials, authenticate
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    if not os.path.exists(OAUTH_CREDENTIALS_FILE):
                        print(f" Neither Service Account nor OAuth credentials found!")
                        print("\nFor server deployment (Render), set up Service Account:")
                        print("1. Go to https://console.cloud.google.com")
                        print("2. Create Service Account")
                        print("3. Download JSON key")
                        print("4. Set GOOGLE_SERVICE_ACCOUNT_JSON environment variable")
                        print("\nFor local development:")
                        print("1. Download OAuth credentials.json OR service-account.json")
                        return False
                    
                    print(" Using OAuth authentication...")
                    flow = InstalledAppFlow.from_client_secrets_file(OAUTH_CREDENTIALS_FILE, SCOPES)
                    creds = flow.run_local_server(port=0)
                
                # Save credentials for next run
                with open(TOKEN_FILE, 'w') as token:
                    token.write(creds.to_json())
            
            self.service = build('sheets', 'v4', credentials=creds)
            print(" Successfully authenticated with OAuth")
            return True
            
        except Exception as e:
            print(f" OAuth authentication failed: {e}")
            return False

    def create_spreadsheet(self, title: str = "CS 15 Tutor Analytics") -> str:
        """Create a new Google Spreadsheet"""
        try:
            spreadsheet = {
                'properties': {
                    'title': title
                },
                'sheets': [
                    {'properties': {'title': 'Overview'}},
                    {'properties': {'title': 'Users'}},
                    {'properties': {'title': 'Conversations'}},
                    {'properties': {'title': 'Messages'}},
                    {'properties': {'title': 'Analytics'}},
                    {'properties': {'title': 'DetailedConversations'}},
                    {'properties': {'title': 'RAGAnalysis'}},
                    {'properties': {'title': 'UserInteractions'}}
                ]
            }
            
            result = self.service.spreadsheets().create(body=spreadsheet).execute()
            spreadsheet_id = result.get('spreadsheetId')
            
            print(f" Created spreadsheet: {title}")
            print(f" Spreadsheet ID: {spreadsheet_id}")
            print(f" URL: https://docs.google.com/spreadsheets/d/{spreadsheet_id}")
            
            return spreadsheet_id
            
        except HttpError as e:
            print(f" Error creating spreadsheet: {e}")
            return None

    def ensure_sheet_exists(self, sheet_name: str):
        """Ensure a sheet exists, create it if it doesn't"""
        try:
            # Get spreadsheet metadata to check existing sheets
            spreadsheet = self.service.spreadsheets().get(spreadsheetId=self.spreadsheet_id).execute()
            existing_sheets = [sheet['properties']['title'] for sheet in spreadsheet.get('sheets', [])]
            
            if sheet_name not in existing_sheets:
                print(f" Creating missing sheet: {sheet_name}")
                # Add the new sheet
                requests = [{
                    "addSheet": {
                        "properties": {
                            "title": sheet_name
                        }
                    }
                }]
                
                body = {"requests": requests}
                self.service.spreadsheets().batchUpdate(
                    spreadsheetId=self.spreadsheet_id,
                    body=body
                ).execute()
                print(f" Created sheet: {sheet_name}")
                
        except HttpError as e:
            print(f" Error ensuring sheet {sheet_name} exists: {e}")

    def clear_sheet(self, sheet_name: str):
        """Clear all data from a sheet"""
        try:
            # Ensure sheet exists first
            self.ensure_sheet_exists(sheet_name)
            
            range_name = f"{sheet_name}!A:Z"
            self.service.spreadsheets().values().clear(
                spreadsheetId=self.spreadsheet_id,
                range=range_name
            ).execute()
        except HttpError as e:
            print(f" Error clearing sheet {sheet_name}: {e}")
    
    def write_to_sheet(self, sheet_name: str, data: List[List], start_cell: str = "A1"):
        """Write data to a specific sheet"""
        try:
            # Ensure sheet exists first
            self.ensure_sheet_exists(sheet_name)
            
            range_name = f"{sheet_name}!{start_cell}"
            body = {
                'values': data
            }
            
            result = self.service.spreadsheets().values().update(
                spreadsheetId=self.spreadsheet_id,
                range=range_name,
                valueInputOption='RAW',
                body=body
            ).execute()
            
            print(f" Updated {sheet_name}: {result.get('updatedCells')} cells")
            
        except HttpError as e:
            print(f" Error writing to sheet {sheet_name}: {e}")

    # ... existing code ...
    def sync_overview_data(self):
        """Sync system overview to Overview sheet"""
        print(" Syncing overview data...")
        
        db = db_manager.get_session()
        try:
            # Get basic stats
            total_users = db.query(AnonymousUser).count()
            total_conversations = db.query(Conversation).count() 
            total_messages = db.query(Message).count()
            
            # Platform breakdown
            web_convos = db.query(Conversation).filter(Conversation.platform == 'web').count()
            vscode_convos = db.query(Conversation).filter(Conversation.platform == 'vscode').count()
            
            # Recent activity
            week_ago = datetime.utcnow() - timedelta(days=7)
            recent_users = db.query(AnonymousUser).filter(AnonymousUser.last_active >= week_ago).count()
            recent_messages = db.query(Message).filter(Message.created_at >= week_ago).count()
            
            # Prepare data for sheets
            data = [
                ["CS 15 Tutor System Overview", f"Updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}"],
                [""],
                ["Metric", "Value", "Description"],
                ["Total Users", total_users, "Anonymous users who have used the system"],
                ["Total Conversations", total_conversations, "Individual chat sessions"],
                ["Total Messages", total_messages, "All queries and responses"],
                ["Web Conversations", web_convos, "Conversations via web app"],
                ["VSCode Conversations", vscode_convos, "Conversations via VSCode extension"],
                ["Active Users (7 days)", recent_users, "Users active in the last week"],
                ["Recent Messages (7 days)", recent_messages, "Messages sent in the last week"],
                [""],
                ["Platform Distribution"],
                ["Platform", "Conversations", "Percentage"],
                ["Web", web_convos, f"{(web_convos/total_conversations*100):.1f}%" if total_conversations > 0 else "0%"],
                ["VSCode", vscode_convos, f"{(vscode_convos/total_conversations*100):.1f}%" if total_conversations > 0 else "0%"]
            ]
            
            self.clear_sheet("Overview")
            self.write_to_sheet("Overview", data)
            
        finally:
            db.close()
    
    def sync_users_data(self):
        """Sync user data to Users sheet"""
        print(" Syncing users data...")
        
        db = db_manager.get_session()
        try:
            users = db.query(AnonymousUser).all()
            
            # Headers
            data = [
                ["Anonymous ID", "Created At", "Last Active", "Days Since Created", "Days Since Last Active"]
            ]
            
            # User data
            now = datetime.utcnow()
            for user in users:
                days_since_created = (now - user.created_at).days
                days_since_active = (now - user.last_active).days
                
                data.append([
                    user.anonymous_id,
                    user.created_at.strftime('%Y-%m-%d %H:%M'),
                    user.last_active.strftime('%Y-%m-%d %H:%M'),
                    days_since_created,
                    days_since_active
                ])
            
            self.clear_sheet("Users")
            self.write_to_sheet("Users", data)
            
        finally:
            db.close()
    
    def sync_conversations_data(self):
        """Sync conversation data to Conversations sheet"""
        print(" Syncing conversations data...")
        
        db = db_manager.get_session()
        try:
            conversations = db.query(Conversation).all()
            
            # Headers
            data = [
                ["User ID", "Platform", "Created At", "Last Message", "Message Count", "Duration (minutes)"]
            ]
            
            # Conversation data
            for convo in conversations:
                duration = (convo.last_message_at - convo.created_at).total_seconds() / 60
                
                data.append([
                    convo.user.anonymous_id,
                    convo.platform,
                    convo.created_at.strftime('%Y-%m-%d %H:%M'),
                    convo.last_message_at.strftime('%Y-%m-%d %H:%M'),
                    convo.message_count,
                    round(duration, 1)
                ])
            
            self.clear_sheet("Conversations")
            self.write_to_sheet("Conversations", data)
            
        finally:
            db.close()
    
    def sync_messages_summary(self):
        """Sync full message data to Messages sheet"""
        print(" Syncing full message data...")
        
        db = db_manager.get_session()
        try:
            messages = db.query(Message).all()
            
            # Headers
            data = [
                ["Timestamp", "User ID", "Platform", "Type", "Content (truncated if >45k)", "RAG Context (truncated if >45k)", "Content Length", "Model", "Response Time (ms)"]
            ]
            
            # Message data with truncated content for Google Sheets limits
            for msg in messages:
                convo = msg.conversation
                
                data.append([
                    msg.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                    convo.user.anonymous_id,
                    convo.platform,
                    msg.message_type,
                    self.truncate_cell_content(msg.content),
                    self.truncate_cell_content(msg.rag_context or "No RAG context"),
                    len(msg.content),
                    msg.model_used or 'N/A',
                    msg.response_time_ms or 0
                ])
            
            self.clear_sheet("Messages")
            self.write_to_sheet("Messages", data)
            
        finally:
            db.close()
    
    def sync_analytics_data(self):
        """Sync advanced analytics to Analytics sheet"""
        print(" Syncing analytics data...")
        
        db = db_manager.get_session()
        try:
            # Time-based analytics
            periods = [
                ("Last 24 hours", 1),
                ("Last 7 days", 7),
                ("Last 30 days", 30)
            ]
            
            data = [
                ["CS 15 Tutor Analytics Dashboard"],
                [""],
                ["Time Period", "Active Users", "New Conversations", "Total Messages", "Avg Response Time (ms)"]
            ]
            
            for period_name, days in periods:
                cutoff = datetime.utcnow() - timedelta(days=days)
                
                active_users = db.query(AnonymousUser).filter(AnonymousUser.last_active >= cutoff).count()
                new_conversations = db.query(Conversation).filter(Conversation.created_at >= cutoff).count()
                total_messages = db.query(Message).filter(Message.created_at >= cutoff).count()
                
                # Average response time
                avg_response = db.query(Message.response_time_ms).filter(
                    Message.created_at >= cutoff,
                    Message.response_time_ms.isnot(None)
                ).all()
                
                avg_ms = sum(r[0] for r in avg_response) / len(avg_response) if avg_response else 0
                
                data.append([
                    period_name,
                    active_users,
                    new_conversations,
                    total_messages,
                    round(avg_ms, 0)
                ])
            
            # Add platform usage
            data.extend([
                [""],
                ["Platform Usage"],
                ["Platform", "Total Conversations", "Unique Users"]
            ])
            
            platforms = ['web', 'vscode']
            for platform in platforms:
                platform_convos = db.query(Conversation).filter(Conversation.platform == platform).count()
                platform_users = db.query(AnonymousUser).join(Conversation).filter(
                    Conversation.platform == platform
                ).distinct().count()
                
                data.append([platform.title(), platform_convos, platform_users])
            
            self.clear_sheet("Analytics")
            self.write_to_sheet("Analytics", data)
            
        finally:
            db.close()
    
    def sync_detailed_conversations(self):
        """Sync detailed conversation threads with full content and RAG context"""
        print(" Syncing detailed conversations with full content...")
        
        db = db_manager.get_session()
        try:
            conversations = db.query(Conversation).order_by(Conversation.created_at.desc()).all()
            
            # Headers
            data = [
                ["Conversation Details - Content and RAG Context (truncated if >45k chars)"],
                [""],
                ["User ID", "Platform", "Conversation Start", "Message #", "Timestamp", "Type", "Content", "RAG Context", "Model", "Response Time (ms)", "Content Length"]
            ]
            
            for convo in conversations:
                # Get all messages for this conversation
                messages = db.query(Message).filter(
                    Message.conversation_id == convo.id
                ).order_by(Message.created_at.asc()).all()
                
                # Add conversation header
                data.append([
                    f"=== CONVERSATION: {convo.user.anonymous_id} ===",
                    convo.platform,
                    convo.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                    f"Duration: {((convo.last_message_at - convo.created_at).total_seconds() / 60):.1f} min",
                    f"Messages: {len(messages)}",
                    "",
                    "",
                    "",
                    "",
                    "",
                    ""
                ])
                
                # Add each message
                for i, msg in enumerate(messages, 1):
                    # Truncate content for Google Sheets cell limits
                    content = self.truncate_cell_content(msg.content)
                    
                    # Truncate RAG context for Google Sheets cell limits
                    rag_context = self.truncate_cell_content(msg.rag_context or "No RAG context")
                    
                    data.append([
                        convo.user.anonymous_id,
                        convo.platform,
                        convo.created_at.strftime('%Y-%m-%d %H:%M'),
                        f"Msg {i}",
                        msg.created_at.strftime('%H:%M:%S'),
                        msg.message_type.upper(),
                        content,
                        rag_context,
                        msg.model_used or 'N/A',
                        msg.response_time_ms or 0,
                        len(msg.content)
                    ])
                
                # Add separator between conversations
                data.append(["", "", "", "", "", "", "", "", "", "", ""])
            
            self.clear_sheet("DetailedConversations")
            self.write_to_sheet("DetailedConversations", data)
            
        finally:
            db.close()
    
    def sync_rag_context_analysis(self):
        """Sync RAG context analysis for understanding what content is being retrieved"""
        print("🧠 Syncing RAG context analysis...")
        
        db = db_manager.get_session()
        try:
            # Get all messages with RAG context
            messages_with_rag = db.query(Message).filter(
                Message.rag_context.isnot(None),
                Message.message_type == 'response'
            ).order_by(Message.created_at.desc()).all()
            
            data = [
                ["RAG Context Analysis (content truncated if >45k chars)"],
                [""],
                ["Timestamp", "User ID", "Platform", "Query", "Response", "RAG Context", "Model", "Response Time (ms)"]
            ]
            
            for msg in messages_with_rag:
                convo = msg.conversation
                
                # Find the corresponding query message
                query_msg = db.query(Message).filter(
                    Message.conversation_id == convo.id,
                    Message.message_type == 'query',
                    Message.created_at < msg.created_at
                ).order_by(Message.created_at.desc()).first()
                
                query_content = query_msg.content if query_msg else "No query found"
                
                # Truncate content for Google Sheets cell limits
                response_content = self.truncate_cell_content(msg.content)
                rag_context = self.truncate_cell_content(msg.rag_context)
                
                data.append([
                    msg.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                    convo.user.anonymous_id,
                    convo.platform,
                    self.truncate_cell_content(query_content),
                    response_content,
                    rag_context,
                    msg.model_used or 'N/A',
                    msg.response_time_ms or 0
                ])
            
            self.clear_sheet("RAGAnalysis")
            self.write_to_sheet("RAGAnalysis", data)
            
        finally:
            db.close()
    
    def sync_user_interactions(self):
        """Sync user interactions showing Query -> RAG Context -> Response for each user"""
        print(" Syncing user interactions (Query -> RAG -> Response)...")
        
        db = db_manager.get_session()
        try:
            # Get all conversations ordered by most recent
            conversations = db.query(Conversation).order_by(Conversation.created_at.desc()).all()
            
            data = [
                ["User Interactions - Queries, RAG Context, and Responses (truncated if >45k chars)"],
                [""],
                ["User ID", "Platform", "Conversation Date", "Turn #", "User Query", "RAG Context Retrieved", "Model Response", "Response Time (ms)", "Query Length", "Response Length"]
            ]
            
            for convo in conversations:
                # Get all messages for this conversation
                messages = db.query(Message).filter(
                    Message.conversation_id == convo.id
                ).order_by(Message.created_at.asc()).all()
                
                # Group messages into query-response pairs
                query_msg = None
                turn_number = 0
                
                for msg in messages:
                    if msg.message_type == 'query':
                        query_msg = msg
                        turn_number += 1
                    elif msg.message_type == 'response' and query_msg:
                        # We have a query-response pair
                        query_content = query_msg.content
                        response_content = msg.content
                        rag_context = msg.rag_context or "No RAG context retrieved"
                        
                        # Truncate content for Google Sheets cell limits
                        
                        data.append([
                            convo.user.anonymous_id,
                            convo.platform,
                            convo.created_at.strftime('%Y-%m-%d %H:%M'),
                            f"Turn {turn_number}",
                            self.truncate_cell_content(query_content),
                            self.truncate_cell_content(rag_context),
                            self.truncate_cell_content(response_content),
                            msg.response_time_ms or 0,
                            len(query_msg.content),
                            len(msg.content)
                        ])
                        
                        query_msg = None  # Reset for next pair
                
                # Add separator between conversations  
                if messages:  # Only add separator if conversation had messages
                    data.append(["---", "---", "---", "---", "---", "---", "---", "---", "---", "---"])
            
            self.clear_sheet("UserInteractions")
            self.write_to_sheet("UserInteractions", data)
            
        finally:
            db.close()
    
    def full_sync(self):
        """Perform a complete sync of all data"""
        print(" Starting full sync to Google Sheets...")
        
        if not self.service:
            print(" Not authenticated with Google Sheets API")
            return False
        
        if not self.spreadsheet_id:
            print(" No spreadsheet ID configured")
            return False
        
        try:
            self.sync_overview_data()
            self.sync_users_data()
            self.sync_conversations_data()
            self.sync_messages_summary()
            self.sync_analytics_data()
            self.sync_user_interactions()  # This is what the user wants to see!
            self.sync_detailed_conversations()
            self.sync_rag_context_analysis()
            
            print(f" Full sync completed!")
            print(f" View spreadsheet: https://docs.google.com/spreadsheets/d/{self.spreadsheet_id}")
            return True
            
        except Exception as e:
            print(f" Sync failed: {e}")
            return False

def get_spreadsheet_id():
    """Get spreadsheet ID from environment variable or config file"""
    # Try environment variable first (for Render)
    spreadsheet_id = os.getenv('SPREADSHEET_ID')
    if spreadsheet_id:
        return spreadsheet_id
    
    # Try config file (for local development)
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
            return config.get('spreadsheet_id')
    
    return None

def setup_google_sheets():
    """Interactive setup for Google Sheets integration"""
    print(" Google Sheets Setup for CS 15 Tutor")
    print("=====================================")
    
    # Check authentication method
    if os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON') or os.path.exists(SERVICE_ACCOUNT_FILE):
        print(" Service Account credentials found")
        sync = GoogleSheetsSync()
    elif os.path.exists(OAUTH_CREDENTIALS_FILE):
        print(" OAuth credentials found") 
        sync = GoogleSheetsSync()
    else:
        print("\n No credentials found!")
        print("\nFor server deployment (Render):")
        print("1. Create Service Account in Google Cloud Console")
        print("2. Download JSON key file")
        print("3. Set GOOGLE_SERVICE_ACCOUNT_JSON environment variable")
        print("4. Set SPREADSHEET_ID environment variable")
        print("\nFor local development:")
        print("1. Place service-account.json OR credentials.json in this directory")
        return
    
    if not sync.service:
        return
    
    # Create spreadsheet
    print("\n Creating new spreadsheet...")
    spreadsheet_id = sync.create_spreadsheet("CS 15 Tutor Analytics Dashboard")
    
    if spreadsheet_id:
        # Save spreadsheet ID locally
        config = {"spreadsheet_id": spreadsheet_id}
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f)
        
        print(f"\n Setup complete!")
        print(f" Spreadsheet ID: {spreadsheet_id}")
        print(f" Spreadsheet: https://docs.google.com/spreadsheets/d/{spreadsheet_id}")
        print(f"\nFor Render deployment, set this environment variable:")
        print(f"SPREADSHEET_ID={spreadsheet_id}")
        
        # Perform initial sync
        sync.spreadsheet_id = spreadsheet_id
        sync.full_sync()

def main():
    """Main function"""
    import sys
    
    if len(sys.argv) < 2:
        print("Google Sheets Sync for CS 15 Tutor Database")
        print("\nCommands:")
        print("  python google_sheets_sync.py setup       - Initial setup")
        print("  python google_sheets_sync.py sync        - Full sync")
        print("  python google_sheets_sync.py queries     - Sync user interactions (queries)")
        print("  python google_sheets_sync.py overview    - Sync overview only")
        print("  python google_sheets_sync.py users       - Sync users only")
        print("  python google_sheets_sync.py messages    - Sync messages only")
        return
    
    command = sys.argv[1].lower()
    
    if command == "setup":
        setup_google_sheets()
        return
    
    # Get spreadsheet ID
    spreadsheet_id = get_spreadsheet_id()
    if not spreadsheet_id:
        print(" No spreadsheet ID found!")
        print("Set SPREADSHEET_ID environment variable or run setup:")
        print("python google_sheets_sync.py setup")
        return
    
    # Create sync instance
    sync = GoogleSheetsSync(spreadsheet_id)
    if not sync.service:
        print(" Authentication failed")
        return
    
    if command == "sync":
        sync.full_sync()
    elif command == "queries":
        sync.sync_user_interactions()
    elif command == "overview":
        sync.sync_overview_data()
    elif command == "users":
        sync.sync_users_data()
    elif command == "messages":
        sync.sync_messages_summary()
    else:
        print(f" Unknown command: {command}")

if __name__ == "__main__":
    main()