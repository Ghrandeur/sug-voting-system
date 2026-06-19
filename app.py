import os
import csv
import sqlite3

def init_and_seed_db():
    db_path = 'elections.db'
    # Check if database already exists; if it does, don't overwrite it
    if os.path.exists(db_path) and os.path.getsize(db_path) > 0:
        return

    print("No database found. Initializing schema and seeding voter data...")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 1. Create the voters table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS voters (
            matric_id TEXT PRIMARY KEY,
            registered_email TEXT,
            has_voted INTEGER DEFAULT 0
        )
    ''')
    
    # 2. Seed data from students.csv if it exists
    csv_path = 'students.csv'
    if os.path.exists(csv_path):
        with open(csv_path, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            # Ensure your CSV columns match these keys exactly (e.g., 'matric_id', 'email')
            for row in reader:
                cursor.execute('''
                    INSERT OR IGNORE INTO voters (matric_id, registered_email, has_voted)
                    VALUES (?, ?, 0)
                ''', (row['matric_id'].strip().upper(), row['email'].strip()))
    
    conn.commit()
    conn.close()
    print("Database initialization complete.")

# Call the function so it runs immediately when Render boots up the container
init_and_seed_db()
