#!/usr/bin/env python3
"""
Quick script to create the flow table manually
Run this from the backend directory: python create_flow_table.py
"""

from open_webui.internal.db import engine, Base
from open_webui.models.flows import Flow

def create_flow_table():
    """Create the flow table if it doesn't exist"""
    try:
        print("Creating flow table...")
        # Import the Flow model to register it
        Base.metadata.create_all(bind=engine, tables=[Flow.__table__])
        print("✅ Flow table created successfully!")
        print("\nYou can now use the flows feature.")
        print("Navigate to /workspace/flows in the UI to get started.")
    except Exception as e:
        print(f"❌ Error creating flow table: {e}")
        raise

if __name__ == "__main__":
    create_flow_table()
