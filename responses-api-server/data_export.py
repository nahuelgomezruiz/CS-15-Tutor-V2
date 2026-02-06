#!/usr/bin/env python3
"""Unified database export tool with CLI and API interfaces."""

import os
import sys
import json
import csv
import sqlite3
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from database import db_manager, AnonymousUser, Conversation, Message, UserHealthPoints


def export_sqlite_to_json() -> Optional[str]:
    """Export all SQLite data to JSON."""
    if not os.path.exists('cs15_tutor_logs.db'):
        print("[ERROR] No SQLite database found (cs15_tutor_logs.db)")
        return None
    
    print("[INFO] Exporting SQLite database...")
    
    try:
        conn = sqlite3.connect('cs15_tutor_logs.db')
        conn.row_factory = sqlite3.Row
        
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cursor.fetchall()]
        
        print(f" Found tables: {tables}")
        
        export_data = {}
        total_records = 0
        
        for table in tables:
            print(f" Exporting table: {table}")
            cursor = conn.execute(f"SELECT * FROM {table}")
            columns = [description[0] for description in cursor.description]
            rows = cursor.fetchall()
            
            table_data = []
            for row in rows:
                row_dict = {columns[i]: value for i, value in enumerate(row)}
                table_data.append(row_dict)
            
            export_data[table] = table_data
            print(f"    {len(table_data)} records from {table}")
            total_records += len(table_data)
        
        conn.close()
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'sqlite_backup_{timestamp}.json'
        
        with open(filename, 'w') as f:
            json.dump(export_data, f, indent=2, default=str)
        
        print(f"\n Export completed!")
        print(f" File: {filename}")
        print(f" Total records: {total_records}")
        
        print(f"\n Export Summary:")
        for table, data in export_data.items():
            print(f"   {table}: {len(data)} records")
        
        return filename
        
    except Exception as e:
        print(f" Export failed: {e}")
        return None


def export_using_orm() -> Optional[str]:
    """Export data using ORM (structured, human-readable format)"""
    print(" Exporting using ORM...")
    
    try:
        db = db_manager.get_session()
        
        export_data = {}
        
        # Export Users
        users = db.query(AnonymousUser).all()
        export_data['users'] = [{
            'id': user.id,
            'utln_hash': user.utln_hash,
            'anonymous_id': user.anonymous_id,
            'created_at': str(user.created_at),
            'last_active': str(user.last_active)
        } for user in users]
        
        # Export Conversations
        conversations = db.query(Conversation).all()
        export_data['conversations'] = [{
            'id': convo.id,
            'conversation_id': convo.conversation_id,
            'user_id': convo.user_id,
            'platform': convo.platform,
            'created_at': str(convo.created_at),
            'last_message_at': str(convo.last_message_at),
            'message_count': convo.message_count,
            'is_active': convo.is_active
        } for convo in conversations]
        
        # Export Messages
        messages = db.query(Message).all()
        export_data['messages'] = [{
            'id': msg.id,
            'conversation_id': msg.conversation_id,
            'message_type': msg.message_type,
            'content': msg.content,
            'rag_context': msg.rag_context,
            'model_used': msg.model_used,
            'temperature': msg.temperature,
            'response_time_ms': msg.response_time_ms,
            'created_at': str(msg.created_at)
        } for msg in messages]
        
        # Export Health Points
        health_points = db.query(UserHealthPoints).all()
        export_data['health_points'] = [{
            'id': hp.id,
            'user_id': hp.user_id,
            'current_points': hp.current_points,
            'max_points': hp.max_points,
            'last_query_at': str(hp.last_query_at) if hp.last_query_at else None,
            'last_regeneration_at': str(hp.last_regeneration_at)
        } for hp in health_points]
        
        db.close()
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'orm_backup_{timestamp}.json'
        
        with open(filename, 'w') as f:
            json.dump(export_data, f, indent=2)
        
        total_records = sum(len(export_data[key]) for key in export_data)
        
        print(f"\n ORM Export completed!")
        print(f" File: {filename}")
        print(f" Total records: {total_records}")
        print(f"\n Breakdown:")
        for key in export_data:
            print(f"   {key}: {len(export_data[key])}")
        
        return filename
        
    except Exception as e:
        print(f" ORM Export failed: {e}")
        return None


def export_messages_to_csv(filename: str = "messages_export.csv", days: int = 30) -> bool:
    """Export recent messages to CSV for analysis"""
    print(f" Exporting messages to {filename} (last {days} days)")
    
    db = db_manager.get_session()
    try:
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        messages = db.query(
            Message.created_at,
            Message.message_type,
            Message.content,
            Message.model_used,
            Message.response_time_ms,
            AnonymousUser.anonymous_id,
            Conversation.platform,
            Conversation.conversation_id
        ).join(Conversation).join(AnonymousUser).filter(
            Message.created_at >= cutoff
        ).order_by(Message.created_at.desc()).all()
        
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow([
                'timestamp', 'message_type', 'anonymous_user', 'platform', 
                'conversation_id', 'model_used', 'response_time_ms', 'content_length'
            ])
            
            for msg in messages:
                writer.writerow([
                    msg.created_at.isoformat(),
                    msg.message_type,
                    msg.anonymous_id,
                    msg.platform,
                    msg.conversation_id[:8] + "...",
                    msg.model_used or 'N/A',
                    msg.response_time_ms or 0,
                    len(msg.content)
                ])
        
        print(f" Exported {len(messages)} messages to {filename}")
        db.close()
        return True
        
    except Exception as e:
        print(f" CSV Export failed: {e}")
        db.close()
        return False


# ANALYTICS & REPORTING FUNCTIONS

def print_separator(title: str = ""):
    """Print a nice separator"""
    print("\n" + "="*60)
    if title:
        print(f" {title}")
        print("="*60)


def get_system_overview():
    """Get high-level system statistics"""
    print_separator("SYSTEM OVERVIEW")
    
    db = db_manager.get_session()
    try:
        total_users = db.query(AnonymousUser).count()
        total_conversations = db.query(Conversation).count()
        total_messages = db.query(Message).count()
        
        web_convos = db.query(Conversation).filter(Conversation.platform == 'web').count()
        vscode_convos = db.query(Conversation).filter(Conversation.platform == 'vscode').count()
        
        queries = db.query(Message).filter(Message.message_type == 'query').count()
        responses = db.query(Message).filter(Message.message_type == 'response').count()
        
        week_ago = datetime.utcnow() - timedelta(days=7)
        recent_users = db.query(AnonymousUser).filter(AnonymousUser.last_active >= week_ago).count()
        recent_messages = db.query(Message).filter(Message.created_at >= week_ago).count()
        
        print(f" Total Anonymous Users: {total_users}")
        print(f" Total Conversations: {total_conversations}")
        print(f" Total Messages: {total_messages}")
        print(f"    Queries: {queries}")
        print(f"    Responses: {responses}")
        print()
        print(f" Platform Usage:")
        print(f"    Web App: {web_convos} conversations")
        print(f"    VSCode: {vscode_convos} conversations")
        print()
        print(f" Recent Activity (7 days):")
        print(f"    Active Users: {recent_users}")
        print(f"    Messages: {recent_messages}")
        
        if total_users > 0:
            avg_convos = total_conversations / total_users
            print(f"\n Averages:")
            print(f"    Conversations per user: {avg_convos:.2f}")
            if total_conversations > 0:
                avg_msgs = total_messages / total_conversations
                print(f"    Messages per conversation: {avg_msgs:.2f}")
                
    finally:
        db.close()


def get_user_activity():
    """Show user activity patterns"""
    print_separator("USER ACTIVITY PATTERNS")
    
    db = db_manager.get_session()
    try:
        print(" Top 10 Most Active Users:")
        users_with_message_counts = db.query(
            AnonymousUser.anonymous_id,
            AnonymousUser.created_at,
            AnonymousUser.last_active,
            db.func.count(Message.id).label('message_count')
        ).join(Conversation).join(Message).group_by(AnonymousUser.id).order_by(
            db.func.count(Message.id).desc()
        ).limit(10).all()
        
        for i, (anon_id, created, last_active, msg_count) in enumerate(users_with_message_counts, 1):
            days_active = (last_active - created).days
            print(f"{i:2}. {anon_id} - {msg_count} messages, {days_active} days active")
        
        print("\n Platform Preferences:")
        platform_users = db.query(
            Conversation.platform,
            db.func.count(db.func.distinct(AnonymousUser.id)).label('unique_users')
        ).join(AnonymousUser).group_by(Conversation.platform).all()
        
        for platform, user_count in platform_users:
            print(f"   {platform}: {user_count} unique users")
            
    finally:
        db.close()


def get_recent_conversations(days: int = 7):
    """Show recent conversation details"""
    print_separator(f"RECENT CONVERSATIONS (Last {days} days)")
    
    db = db_manager.get_session()
    try:
        cutoff = datetime.utcnow() - timedelta(days=days)
        recent_convos = db.query(Conversation).filter(
            Conversation.created_at >= cutoff
        ).order_by(Conversation.created_at.desc()).limit(20).all()
        
        print(f" Showing {len(recent_convos)} most recent conversations:")
        print()
        
        for convo in recent_convos:
            msg_count = db.query(Message).filter(Message.conversation_id == convo.id).count()
            duration = convo.last_message_at - convo.created_at
            duration_mins = int(duration.total_seconds() / 60)
            
            print(f"  {convo.user.anonymous_id} on {convo.platform}")
            print(f"    Started: {convo.created_at.strftime('%Y-%m-%d %H:%M')}")
            print(f"    Duration: {duration_mins} minutes")
            print(f"    Messages: {msg_count}")
            print(f"    ID: {convo.conversation_id[:8]}...")
            print()
            
    finally:
        db.close()


def get_analytics_summary():
    """Get comprehensive analytics for reporting"""
    print_separator("ANALYTICS SUMMARY")
    
    db = db_manager.get_session()
    try:
        now = datetime.utcnow()
        periods = [
            ("Today", now - timedelta(days=1)),
            ("This Week", now - timedelta(days=7)),
            ("This Month", now - timedelta(days=30))
        ]
        
        for period_name, cutoff in periods:
            users = db.query(AnonymousUser).filter(AnonymousUser.last_active >= cutoff).count()
            messages = db.query(Message).filter(Message.created_at >= cutoff).count()
            convos = db.query(Conversation).filter(Conversation.created_at >= cutoff).count()
            
            print(f" {period_name}:")
            print(f"    Active Users: {users}")
            print(f"    New Conversations: {convos}")
            print(f"    Messages: {messages}")
            print()
        
        avg_response_time = db.query(db.func.avg(Message.response_time_ms)).filter(
            Message.response_time_ms.isnot(None)
        ).scalar()
        
        if avg_response_time:
            print(f" Average Response Time: {avg_response_time:.0f}ms")
        
    finally:
        db.close()


def search_by_user(anonymous_id: str):
    """Find all data for a specific anonymous user"""
    print(f" Searching for user: {anonymous_id}")
    
    db = db_manager.get_session()
    try:
        user = db.query(AnonymousUser).filter(AnonymousUser.anonymous_id == anonymous_id).first()
        if not user:
            print(f" User {anonymous_id} not found")
            return
        
        print(f" User Details:")
        print(f"  Anonymous ID: {user.anonymous_id}")
        print(f"  Created: {user.created_at}")
        print(f"  Last Active: {user.last_active}")
        
        conversations = db.query(Conversation).filter(Conversation.user_id == user.id).all()
        print(f"\n Conversations ({len(conversations)}):")
        
        for convo in conversations:
            print(f"   {convo.platform} conversation")
            print(f"    Started: {convo.created_at}")
            print(f"    Messages: {convo.message_count}")
            
            messages = db.query(Message).filter(Message.conversation_id == convo.id).all()
            for msg in messages:
                preview = msg.content[:100] + ('...' if len(msg.content) > 100 else '')
                print(f"    {msg.message_type}: {preview}")
            print()
            
    finally:
        db.close()


def search_conversations(user_id: Optional[str] = None, platform: Optional[str] = None, days: Optional[int] = None):
    """Search for specific conversations"""
    print_separator("CONVERSATION SEARCH")
    
    db = db_manager.get_session()
    try:
        query = db.query(Conversation).join(AnonymousUser)
        
        if user_id:
            query = query.filter(AnonymousUser.anonymous_id == user_id)
            print(f" Filtering by user: {user_id}")
        
        if platform:
            query = query.filter(Conversation.platform == platform)
            print(f" Filtering by platform: {platform}")
        
        if days:
            cutoff = datetime.utcnow() - timedelta(days=days)
            query = query.filter(Conversation.created_at >= cutoff)
            print(f" Filtering by recency: last {days} days")
        
        conversations = query.order_by(Conversation.created_at.desc()).limit(50).all()
        
        print(f"\n Found {len(conversations)} conversations:")
        
        for convo in conversations:
            msg_count = db.query(Message).filter(Message.conversation_id == convo.id).count()
            print(f"  {convo.user.anonymous_id} | {convo.platform} | {msg_count} msgs | {convo.created_at.strftime('%Y-%m-%d %H:%M')}")
            
    finally:
        db.close()


def show_recent_activity(hours: int = 24):
    """Show activity from the last N hours"""
    print(f" Recent Activity (last {hours} hours)")
    
    db = db_manager.get_session()
    try:
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        recent_messages = db.query(Message).filter(Message.created_at >= cutoff).all()
        print(f" {len(recent_messages)} recent messages:")
        
        for msg in recent_messages:
            convo = msg.conversation
            preview = msg.content[:100] + ('...' if len(msg.content) > 100 else '')
            print(f"  {msg.created_at.strftime('%Y-%m-%d %H:%M')} - {convo.user.anonymous_id} ({convo.platform})")
            print(f"    {msg.message_type}: {preview}")
            print()
            
    finally:
        db.close()


def check_database() -> Dict[str, Any]:
    """Check what data exists in current database"""
    try:
        db = db_manager.get_session()
        
        user_count = db.query(AnonymousUser).count()
        conversation_count = db.query(Conversation).count()
        message_count = db.query(Message).count()
        query_count = db.query(Message).filter(Message.message_type == 'query').count()
        response_count = db.query(Message).filter(Message.message_type == 'response').count()
        
        db.close()
        
        return {
            "database_type": "SQLite" if "sqlite" in str(db_manager.engine.url) else "PostgreSQL",
            "database_file_exists": os.path.exists('cs15_tutor_logs.db'),
            "counts": {
                "users": user_count,
                "conversations": conversation_count,
                "total_messages": message_count,
                "student_queries": query_count,
                "ai_responses": response_count
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        return {
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


# CLI INTERFACE

def print_help():
    """Print help message"""
    print("""
CS 15 Tutor Unified Data Export Tool
=====================================

EXPORT COMMANDS:
  export sqlite          - Export raw SQLite database to JSON
  export orm             - Export using ORM (structured format)
  export csv [days]      - Export messages to CSV (default: 30 days)
  export all             - Run all export methods

ANALYTICS COMMANDS:
  overview               - System overview and statistics
  users                  - User activity patterns
  recent [days]          - Recent conversations (default: 7 days)
  analytics              - Full analytics report
  activity [hours]       - Recent activity (default: 24 hours)

SEARCH COMMANDS:
  search user <id>       - Search by anonymous user ID
  search [user] [platform] [days] - Advanced conversation search

DATABASE COMMANDS:
  check                  - Check database status and counts

EXAMPLES:
  python data_export.py export all
  python data_export.py overview
  python data_export.py recent 3
  python data_export.py export csv 14
  python data_export.py search user aaaaaa00
  python data_export.py search '' web 7
  python data_export.py activity 12
""")


def main():
    """Main CLI entry point"""
    if len(sys.argv) < 2:
        print_help()
        return
    
    command = sys.argv[1].lower()
    
    try:
        # Export commands
        if command == "export":
            if len(sys.argv) < 3:
                print(" Specify export type: sqlite, orm, csv, or all")
                return
            
            export_type = sys.argv[2].lower()
            
            if export_type == "sqlite":
                export_sqlite_to_json()
            elif export_type == "orm":
                export_using_orm()
            elif export_type == "csv":
                days = int(sys.argv[3]) if len(sys.argv) > 3 else 30
                export_messages_to_csv(f"cs15_messages_{days}days.csv", days)
            elif export_type == "all":
                print(" Running all export methods...\n")
                sqlite_file = export_sqlite_to_json()
                print()
                orm_file = export_using_orm()
                print()
                export_messages_to_csv()
                print(f"\n All exports complete!")
                if sqlite_file:
                    print(f"    {sqlite_file}")
                if orm_file:
                    print(f"    {orm_file}")
                print(f"    cs15_messages_30days.csv")
            else:
                print(f" Unknown export type: {export_type}")
        
        # Analytics commands
        elif command == "overview":
            get_system_overview()
        
        elif command == "users":
            get_user_activity()
        
        elif command == "recent":
            days = int(sys.argv[2]) if len(sys.argv) > 2 else 7
            get_recent_conversations(days)
        
        elif command == "analytics":
            get_analytics_summary()
            get_system_overview()
            get_user_activity()
        
        elif command == "activity":
            hours = int(sys.argv[2]) if len(sys.argv) > 2 else 24
            show_recent_activity(hours)
        
        # Search commands
        elif command == "search":
            if len(sys.argv) < 3:
                print(" Specify 'user <id>' or provide search filters")
                return
            
            if sys.argv[2].lower() == "user":
                if len(sys.argv) < 4:
                    print(" Please provide a user ID")
                else:
                    search_by_user(sys.argv[3])
            else:
                user_id = sys.argv[2] if sys.argv[2] else None
                platform = sys.argv[3] if len(sys.argv) > 3 and sys.argv[3] else None
                days = int(sys.argv[4]) if len(sys.argv) > 4 else None
                search_conversations(user_id, platform, days)
        
        # Database commands
        elif command == "check":
            result = check_database()
            print(json.dumps(result, indent=2))
        
        else:
            print(f" Unknown command: {command}")
            print("Run with no arguments for help")
            
    except Exception as e:
        print(f" Error: {e}")
        import traceback
        traceback.print_exc()


# API INTERFACE (for Flask integration)

def get_export_api_routes():
    """
    Returns Flask route functions for API integration.
    Import this in your main Flask app:
    
        from data_export import get_export_api_routes
        routes = get_export_api_routes()
        app.add_url_rule('/admin/export-data', 'export_data', routes['export_data'], methods=['GET'])
    """
    from flask import jsonify, send_file
    
    def export_data_endpoint():
        """Export SQLite data and return download link"""
        try:
            print(" Starting data export...")
            
            sqlite_file = export_sqlite_to_json()
            orm_file = export_using_orm()
            
            result = {
                "success": True,
                "timestamp": datetime.now().isoformat(),
                "files": []
            }
            
            if sqlite_file:
                result["files"].append({
                    "type": "sqlite_direct",
                    "filename": sqlite_file,
                    "size": os.path.getsize(sqlite_file) if os.path.exists(sqlite_file) else 0
                })
            
            if orm_file:
                result["files"].append({
                    "type": "orm_export", 
                    "filename": orm_file,
                    "size": os.path.getsize(orm_file) if os.path.exists(orm_file) else 0
                })
            
            return jsonify(result)
            
        except Exception as e:
            return jsonify({
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }), 500
    
    def download_file_endpoint(filename):
        """Download exported file"""
        try:
            if os.path.exists(filename):
                return send_file(filename, as_attachment=True)
            else:
                return jsonify({"error": "File not found"}), 404
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    def check_database_endpoint():
        """Check what data exists in current database"""
        result = check_database()
        if "error" in result:
            return jsonify(result), 500
        return jsonify(result)
    
    return {
        'export_data': export_data_endpoint,
        'download_file': download_file_endpoint,
        'check_database': check_database_endpoint
    }


if __name__ == "__main__":
    main()

