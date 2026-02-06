"""Dashboard sync service for syncing data to Google Sheets."""

from datetime import datetime, timedelta
from typing import List, Optional

from frontend.dashboard.sheets_client import GoogleSheetsClient
from adapters.database.base import BaseDatabaseAdapter
from adapters.database.render_postgres import (
    AnonymousUser, Conversation, Message, RenderPostgresAdapter
)


class DashboardSyncService:
    """Service for syncing CS 15 Tutor data to Google Sheets dashboard."""
    
    def __init__(
        self, 
        sheets_client: Optional[GoogleSheetsClient] = None,
        db_adapter: Optional[BaseDatabaseAdapter] = None
    ):
        """
        Initialize the sync service.
        
        Args:
            sheets_client: Google Sheets client
            db_adapter: Database adapter
        """
        self.sheets = sheets_client or GoogleSheetsClient()
        self.db = db_adapter or RenderPostgresAdapter()
    
    def is_available(self) -> bool:
        """Check if sync service is available."""
        return self.sheets.is_available()
    
    def sync_overview(self) -> None:
        """Sync system overview to Overview sheet."""
        if not self.is_available():
            print("[Sync] Sheets client not available")
            return
        
        print("[Sync] Syncing overview data...")
        
        session = self.db.get_session()
        try:
            total_users = session.query(AnonymousUser).count()
            total_conversations = session.query(Conversation).count()
            total_messages = session.query(Message).count()
            
            web_convos = session.query(Conversation).filter(
                Conversation.platform == 'web'
            ).count()
            vscode_convos = session.query(Conversation).filter(
                Conversation.platform == 'vscode'
            ).count()
            
            week_ago = datetime.utcnow() - timedelta(days=7)
            recent_users = session.query(AnonymousUser).filter(
                AnonymousUser.last_active >= week_ago
            ).count()
            
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
            ]
            
            self.sheets.clear_sheet("Overview")
            self.sheets.write_to_sheet("Overview", data)
            
        finally:
            session.close()
    
    def sync_users(self) -> None:
        """Sync user data to Users sheet."""
        if not self.is_available():
            return
        
        print("[Sync] Syncing users data...")
        
        session = self.db.get_session()
        try:
            users = session.query(AnonymousUser).all()
            
            data = [
                ["Anonymous ID", "Created At", "Last Active", "Days Since Created"]
            ]
            
            now = datetime.utcnow()
            for user in users:
                days_since_created = (now - user.created_at).days
                
                data.append([
                    user.anonymous_id,
                    user.created_at.strftime('%Y-%m-%d %H:%M'),
                    user.last_active.strftime('%Y-%m-%d %H:%M'),
                    days_since_created
                ])
            
            self.sheets.clear_sheet("Users")
            self.sheets.write_to_sheet("Users", data)
            
        finally:
            session.close()
    
    def sync_conversations(self) -> None:
        """Sync conversation data to Conversations sheet."""
        if not self.is_available():
            return
        
        print("[Sync] Syncing conversations data...")
        
        session = self.db.get_session()
        try:
            conversations = session.query(Conversation).all()
            
            data = [
                ["User ID", "Platform", "Created At", "Last Message", "Message Count"]
            ]
            
            for convo in conversations:
                data.append([
                    convo.user.anonymous_id,
                    convo.platform,
                    convo.created_at.strftime('%Y-%m-%d %H:%M'),
                    convo.last_message_at.strftime('%Y-%m-%d %H:%M'),
                    convo.message_count
                ])
            
            self.sheets.clear_sheet("Conversations")
            self.sheets.write_to_sheet("Conversations", data)
            
        finally:
            session.close()
    
    def sync_messages(self) -> None:
        """Sync message data to Messages sheet."""
        if not self.is_available():
            return
        
        print("[Sync] Syncing messages data...")
        
        session = self.db.get_session()
        try:
            messages = session.query(Message).all()
            
            data = [
                ["Timestamp", "User ID", "Platform", "Type", "Content", "Model", "Response Time (ms)"]
            ]
            
            for msg in messages:
                convo = msg.conversation
                
                data.append([
                    msg.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                    convo.user.anonymous_id,
                    convo.platform,
                    msg.message_type,
                    self.sheets.truncate_content(msg.content),
                    msg.model_used or 'N/A',
                    msg.response_time_ms or 0
                ])
            
            self.sheets.clear_sheet("Messages")
            self.sheets.write_to_sheet("Messages", data)
            
        finally:
            session.close()
    
    def sync_user_interactions(self) -> None:
        """Sync user interactions (query -> response pairs) to UserInteractions sheet."""
        if not self.is_available():
            return
        
        print("[Sync] Syncing user interactions...")
        
        session = self.db.get_session()
        try:
            conversations = session.query(Conversation).order_by(
                Conversation.created_at.desc()
            ).all()
            
            data = [
                ["User ID", "Platform", "Date", "Turn", "Query", "RAG Context", "Response", "Response Time (ms)"]
            ]
            
            for convo in conversations:
                messages = session.query(Message).filter(
                    Message.conversation_id == convo.id
                ).order_by(Message.created_at.asc()).all()
                
                query_msg = None
                turn_number = 0
                
                for msg in messages:
                    if msg.message_type == 'query':
                        query_msg = msg
                        turn_number += 1
                    elif msg.message_type == 'response' and query_msg:
                        data.append([
                            convo.user.anonymous_id,
                            convo.platform,
                            convo.created_at.strftime('%Y-%m-%d %H:%M'),
                            f"Turn {turn_number}",
                            self.sheets.truncate_content(query_msg.content),
                            self.sheets.truncate_content(msg.rag_context or "No RAG context"),
                            self.sheets.truncate_content(msg.content),
                            msg.response_time_ms or 0
                        ])
                        query_msg = None
            
            self.sheets.clear_sheet("UserInteractions")
            self.sheets.write_to_sheet("UserInteractions", data)
            
        finally:
            session.close()
    
    def full_sync(self) -> bool:
        """Perform a complete sync of all data."""
        if not self.is_available():
            print("[Sync] Cannot sync - sheets client not available")
            return False
        
        print("[Sync] Starting full sync to Google Sheets...")
        
        try:
            self.sync_overview()
            self.sync_users()
            self.sync_conversations()
            self.sync_messages()
            self.sync_user_interactions()
            
            print("[Sync] Full sync completed!")
            return True
            
        except Exception as e:
            print(f"[Sync] Sync failed: {e}")
            return False


def main():
    """Command-line interface for sync service."""
    import sys
    
    if len(sys.argv) < 2:
        print("Dashboard Sync for CS 15 Tutor")
        print("\nCommands:")
        print("  python -m frontend.dashboard.sync_service sync        - Full sync")
        print("  python -m frontend.dashboard.sync_service overview    - Sync overview only")
        print("  python -m frontend.dashboard.sync_service users       - Sync users only")
        print("  python -m frontend.dashboard.sync_service messages    - Sync messages only")
        print("  python -m frontend.dashboard.sync_service interactions - Sync user interactions")
        return
    
    command = sys.argv[1].lower()
    sync = DashboardSyncService()
    
    if not sync.is_available():
        print("Error: Dashboard sync not available. Check Google Sheets credentials.")
        return
    
    commands = {
        'sync': sync.full_sync,
        'overview': sync.sync_overview,
        'users': sync.sync_users,
        'messages': sync.sync_messages,
        'interactions': sync.sync_user_interactions,
    }
    
    if command in commands:
        commands[command]()
    else:
        print(f"Unknown command: {command}")


if __name__ == "__main__":
    main()
