#!/usr/bin/env python3
"""
Direct SQL Query Tool for CS 15 Tutor Database
"""

import sqlite3
import sys
import os

# Database file path
DB_PATH = "cs15_tutor_logs.db"

def run_query(sql):
    """Run a SQL query and display results"""
    if not os.path.exists(DB_PATH):
        print(f"❌ Database file not found: {DB_PATH}")
        return
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute(sql)
        
        # Get column names
        columns = [description[0] for description in cursor.description] if cursor.description else []
        
        # Get results
        results = cursor.fetchall()
        
        if not results:
            print("📭 No results found.")
            return
        
        # Print results in a nice format
        if columns:
            # Print header
            print(" | ".join(f"{col:15}" for col in columns))
            print("-" * (len(columns) * 17))
            
            # Print rows
            for row in results:
                print(" | ".join(f"{str(val)[:15]:15}" for val in row))
        else:
            for row in results:
                print(row)
                
        print(f"\n📊 {len(results)} rows returned")
        
    except sqlite3.Error as e:
        print(f"❌ SQL Error: {e}")
    finally:
        conn.close()

def show_schema():
    """Show database schema"""
    print("📋 Database Schema:")
    
    tables = [
        "anonymous_users",
        "conversations", 
        "messages",
        "user_sessions"
    ]
    
    for table in tables:
        print(f"\n🗂️  {table.upper()} table:")
        run_query(f"PRAGMA table_info({table})")

def common_queries():
    """Show some useful pre-written queries"""
    print("📊 Common Queries:")
    print("\n1. Count messages by type:")
    run_query("SELECT message_type, COUNT(*) as count FROM messages GROUP BY message_type")
    
    print("\n2. Platform usage:")
    run_query("SELECT platform, COUNT(*) as conversations FROM conversations GROUP BY platform")
    
    print("\n3. Most recent messages:")
    run_query("""
        SELECT m.created_at, au.anonymous_id, c.platform, m.message_type, 
               SUBSTR(m.content, 1, 50) as content_preview
        FROM messages m
        JOIN conversations c ON m.conversation_id = c.id
        JOIN anonymous_users au ON c.user_id = au.id
        ORDER BY m.created_at DESC
        LIMIT 10
    """)
    
    print("\n4. User activity summary:")
    run_query("""
        SELECT au.anonymous_id, 
               COUNT(DISTINCT c.id) as conversations,
               COUNT(m.id) as total_messages,
               MIN(m.created_at) as first_message,
               MAX(m.created_at) as last_message
        FROM anonymous_users au
        LEFT JOIN conversations c ON au.id = c.user_id
        LEFT JOIN messages m ON c.id = m.conversation_id
        GROUP BY au.id
    """)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("CS 15 Tutor Database SQL Query Tool")
        print("\nUsage:")
        print("  python run_sql.py 'SELECT * FROM messages'")
        print("  python run_sql.py schema")
        print("  python run_sql.py common")
        print("\nExamples:")
        print("  python run_sql.py 'SELECT COUNT(*) FROM anonymous_users'")
        print("  python run_sql.py 'SELECT * FROM conversations WHERE platform = \"vscode\"'")
        sys.exit(0)
    
    command = sys.argv[1]
    
    if command.lower() == "schema":
        show_schema()
    elif command.lower() == "common":
        common_queries()
    else:
        # Treat as SQL query
        run_query(command) 