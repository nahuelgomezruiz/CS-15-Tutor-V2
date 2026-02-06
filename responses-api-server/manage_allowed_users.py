#!/usr/bin/env python3
"""
Manage allowed VSCode extension users
"""

import json
import os
import sys
from typing import List

ALLOWED_USERS_FILE = 'allowed_vscode_users.json'

def load_allowed_users() -> List[str]:
    """Load allowed users from JSON file"""
    try:
        with open(ALLOWED_USERS_FILE, 'r') as f:
            data = json.load(f)
            return data.get('allowed_users', [])
    except FileNotFoundError:
        return ["testuser", "demo_user", "student123"]
    except Exception as e:
        print(f"Error loading allowed users: {e}")
        return ["testuser"]

def save_allowed_users(users: List[str]) -> bool:
    """Save allowed users to JSON file"""
    try:
        data = {
            "allowed_users": users,
            "description": "List of usernames allowed to authenticate with the VSCode extension"
        }
        with open(ALLOWED_USERS_FILE, 'w') as f:
            json.dump(data, f, indent=2)
        return True
    except Exception as e:
        print(f"Error saving allowed users: {e}")
        return False

def list_allowed_users():
    """List all allowed users"""
    users = load_allowed_users()
    print("\nCurrently allowed VSCode users:")
    print("-" * 40)
    if users:
        for i, user in enumerate(users, 1):
            print(f"{i}. {user}")
    else:
        print("No users currently allowed")
    print("-" * 40)

def add_allowed_user():
    """Add a new allowed user"""
    users = load_allowed_users()
    
    username = input("Enter username to allow: ").strip().lower()
    if not username:
        print("Username cannot be empty")
        return
    
    if username in users:
        print(f"User '{username}' is already allowed")
        return
    
    # Validate username format
    if len(username) < 3:
        print("Username must be at least 3 characters long")
        return
    
    if not username[0].isalpha():
        print("Username must start with a letter")
        return
    
    if not all(c.isalnum() or c == '_' for c in username):
        print("Username can only contain letters, numbers, and underscores")
        return
    
    users.append(username)
    
    if save_allowed_users(users):
        print(f"User '{username}' added to allowed list")
    else:
        print("Failed to save allowed users")

def remove_allowed_user():
    """Remove an allowed user"""
    users = load_allowed_users()
    
    if not users:
        print("No users to remove")
        return
    
    print("\nCurrently allowed users:")
    for i, user in enumerate(users, 1):
        print(f"{i}. {user}")
    
    try:
        choice = int(input("\nEnter number of user to remove: ")) - 1
        if 0 <= choice < len(users):
            username = users[choice]
            confirm = input(f"Are you sure you want to remove '{username}'? (y/N): ").strip().lower()
            if confirm == 'y':
                users.pop(choice)
                if save_allowed_users(users):
                    print(f"User '{username}' removed from allowed list")
                else:
                    print("Failed to save allowed users")
            else:
                print("User removal cancelled")
        else:
            print("Invalid choice")
    except ValueError:
        print("Please enter a valid number")

def clear_all_users():
    """Clear all allowed users"""
    confirm = input("Are you sure you want to clear ALL allowed users? (y/N): ").strip().lower()
    if confirm == 'y':
        if save_allowed_users([]):
            print("All allowed users cleared")
        else:
            print("Failed to clear allowed users")
    else:
        print("Operation cancelled")

def reset_to_default():
    """Reset to default allowed users"""
    default_users = ["testuser", "demo_user", "student123"]
    confirm = input(f"Reset to default users: {', '.join(default_users)}? (y/N): ").strip().lower()
    if confirm == 'y':
        if save_allowed_users(default_users):
            print("Reset to default allowed users")
        else:
            print("Failed to reset allowed users")
    else:
        print("Operation cancelled")

def main():
    """Main function"""
    if not os.path.exists(ALLOWED_USERS_FILE):
        print(f"Creating new allowed users file: {ALLOWED_USERS_FILE}")
        save_allowed_users(["testuser", "demo_user", "student123"])
    
    while True:
        print("\nVSCode Extension Allowed Users Management")
        print("=" * 50)
        print("1. List allowed users")
        print("2. Add allowed user")
        print("3. Remove allowed user")
        print("4. Clear all users")
        print("5. Reset to default")
        print("6. Exit")
        
        choice = input("\nEnter your choice (1-6): ").strip()
        
        if choice == '1':
            list_allowed_users()
        elif choice == '2':
            add_allowed_user()
        elif choice == '3':
            remove_allowed_user()
        elif choice == '4':
            clear_all_users()
        elif choice == '5':
            reset_to_default()
        elif choice == '6':
            print("Goodbye!")
            break
        else:
            print("Invalid choice. Please enter 1-6.")

if __name__ == "__main__":
    main() 