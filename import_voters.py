import csv
import sqlite3

DB_FILE = 'elections.db'
CSV_FILE = 'students.csv'

def initialize_and_import():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # Step 1: Build the hardened schema table ledger
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS voters (
            matric_id TEXT PRIMARY KEY,
            registered_email TEXT NOT NULL,
            has_voted INTEGER DEFAULT 0,
            active_token TEXT,
            token_expires REAL
        )
    ''')
    conn.commit()

    # Step 2: Read from CSV and stream into the database
    try:
        with open(CSV_FILE, mode='r', encoding='utf-8') as file:
            csv_reader = csv.reader(file)
            voter_records = []
            
            for row in csv_reader:
                if len(row) >= 2:
                    matric = row[0].strip().upper()
                    email = row[1].strip()
                    voter_records.append((matric, email))

            # INSERT OR IGNORE safely drops duplicates if script runs multiple times
            cursor.executemany('''
                INSERT OR IGNORE INTO voters (matric_id, registered_email) 
                VALUES (?, ?)
            ''', voter_records)
            
        conn.commit()
        print(f"⚙️ Success: Database synchronized! Total rows processed: {cursor.rowcount}")
    except FileNotFoundError:
        print(f"❌ Error: Code mapping failed. '{CSV_FILE}' was not detected.")
    finally:
        conn.close()

if __name__ == '__main__':
    initialize_and_import()
