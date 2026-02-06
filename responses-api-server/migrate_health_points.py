#!/usr/bin/env python3
"""
Migration script to update health points to 12 for all existing users.
Run this on Render after deploying the updated code.
"""

from database import db_manager, UserHealthPoints

def migrate_health_points():
    """Update all users to have 12 max health points"""
    print("Starting health points migration...")
    
    db = db_manager.get_session()
    try:
        # Get all health point records
        all_health_points = db.query(UserHealthPoints).all()
        
        updated_count = 0
        for hp in all_health_points:
            if hp.max_points != 12:
                hp.max_points = 12
                # If current points exceed new max, cap them
                if hp.current_points > 12:
                    hp.current_points = 12
                updated_count += 1
        
        db.commit()
        
        print(f"✅ Migration complete!")
        print(f"   Updated {updated_count} users to 12 max points")
        print(f"   Total users: {len(all_health_points)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        db.rollback()
        return False
        
    finally:
        db.close()

if __name__ == "__main__":
    success = migrate_health_points()
    exit(0 if success else 1)

