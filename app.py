import os
import csv
import sqlite3
import random
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

DB_PATH = 'elections.db'
CSV_PATH = 'students.csv'

def initialize_database():
    """Drops the table and re-seeds from CSV to ensure synchronization."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Drop existing table to ensure fresh start
    cursor.execute('DROP TABLE IF EXISTS voters')
    
    # Recreate table structure
    cursor.execute('''
        CREATE TABLE voters (
            matric_id TEXT PRIMARY KEY,
            registered_email TEXT,
            has_voted INTEGER DEFAULT 0
        )
    ''')
    
    # Import fresh records from CSV
    if os.path.exists(CSV_PATH):
        with open(CSV_PATH, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            count = 0
            for row in reader:
                matric = row.get('matric_id', '').strip().upper()
                email = row.get('email', '').strip()
                
                if matric and email:
                    cursor.execute('INSERT INTO voters (matric_id, registered_email) VALUES (?, ?)', 
                                   (matric, email))
                    count += 1
            print(f"Registry initialized: {count} records successfully imported.")
    else:
        print("CRITICAL: students.csv file missing in root directory.")
        
    conn.commit()
    conn.close()

# Ensure DB is fresh on startup
initialize_database()

@app.route('/api/send-token', methods=['POST'])
def handle_verification():
    data = request.get_json() or {}
    matric = data.get("matric", "").strip().upper()
    
    if not matric:
        return jsonify({"message": "Invalid input: Matriculation number required."}), 400
        
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    voter = conn.execute('SELECT * FROM voters WHERE matric_id = ?', (matric,)).fetchone()
    
    if not voter:
        conn.close()
        return jsonify({"message": f"Access Denied: '{matric}' not found in registry."}), 404
        
    if voter['has_voted'] == 1:
        conn.close()
        return jsonify({"message": "Access Denied: Ballot already cast for this ID."}), 403
            
    # Success: Generate and log token
    token = str(random.randint(100000, 999999))
    email = voter['registered_email']
    
    # Mask email for user feedback
    masked_email = f"{email[0]}***@{email.split('@')[1]}"
    
    print(f"DISPATCHED: Matric {matric} | PIN {token} | To {email}")
    conn.close()
    
    return jsonify({
        "message": "Token generated.",
        "target": masked_email
    }), 200

if __name__ == '__main__':
    # Use environment port for Render compatibility
    port = int(os.environ.get("PORT", 3000))
    app.run(host='0.0.0.0', port=port)
