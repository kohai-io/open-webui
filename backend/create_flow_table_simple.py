#!/usr/bin/env python3
"""
Simple script to create the flow table
Requires only sqlite3 (built into Python)
"""

import sqlite3
import os
from pathlib import Path

def find_database():
    """Find the database file"""
    # Common locations
    possible_paths = [
        Path("data/webui.db"),
        Path("backend/data/webui.db"),
        Path("../data/webui.db"),
    ]
    
    for path in possible_paths:
        if path.exists():
            return str(path)
    
    # Ask user for path
    print("Could not find database automatically.")
    print("Common locations:")
    print("  - backend/data/webui.db")
    print("  - data/webui.db")
    db_path = input("Enter the path to your webui.db file: ")
    return db_path

def create_table(db_path):
    """Create the flow table"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        print(f"Connected to database: {db_path}")
        
        # Create table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS flow (
            id VARCHAR PRIMARY KEY,
            user_id VARCHAR NOT NULL,
            name TEXT NOT NULL,
            description TEXT,
            nodes JSON NOT NULL,
            edges JSON NOT NULL,
            created_at BIGINT NOT NULL,
            updated_at BIGINT NOT NULL,
            meta JSON DEFAULT '{}'
        )
        """)
        
        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS flow_user_id_idx ON flow(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS flow_updated_at_idx ON flow(updated_at)")
        cursor.execute("CREATE INDEX IF NOT EXISTS flow_user_id_updated_at_idx ON flow(user_id, updated_at)")
        
        conn.commit()
        
        # Verify
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='flow'")
        if cursor.fetchone():
            print("\n✅ Success! Flow table created successfully!")
            print("\nYou can now:")
            print("  1. Restart your Open WebUI backend")
            print("  2. Navigate to /workspace/flows in the UI")
            print("  3. Create your first flow!")
        else:
            print("\n❌ Error: Table not found after creation")
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    print("=" * 60)
    print("Open WebUI - Flow Table Creator")
    print("=" * 60)
    print()
    
    db_path = find_database()
    
    if not os.path.exists(db_path):
        print(f"\n❌ Error: Database file not found at: {db_path}")
        print("\nMake sure the backend has been started at least once.")
        exit(1)
    
    create_table(db_path)
