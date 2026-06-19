import os
import csv
import time
import random
import sqlite3
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

DB_PATH = 'elections.db'
CSV_PATH = 'students.csv'

def init_and_seed_db():
    """Initializes the database schema and seeds voter data if empty."""
    if os.path.exists(DB_PATH) and os.path.getsize(DB_PATH) > 0:
        print("Database already initialized.")
        return

    print("No database found. Initializing schema and seeding voter data...")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS voters (
            matric_id TEXT PRIMARY KEY,
            registered_email TEXT,
            has_voted INTEGER DEFAULT 0
        )
    ''')
    
    if os.path.exists(CSV_PATH):
        with open(CSV_PATH, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                matric = row.get('matric_id', '').strip().upper()
                email = row.get('email', '').strip()
                
                if matric and email:
                    cursor.execute('''
                        INSERT OR IGNORE INTO voters (matric_id, registered_email, has_voted)
                        VALUES (?, ?, 0)
                    ''', (matric, email))
        print("Voter registry seeded successfully from CSV.")
    else:
        print(f"Warning: '{CSV_PATH}' not found. Database table created empty.")
        
    conn.commit()
    conn.close()

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/api/ballot-schema', methods=['GET'])
def get_ballot_schema():
    BALLOT_SCHEMA = {
        "status": "success",
        "positions": [
            {
                "id": "president",
                "title": "SUG PRESIDENT",
                "candidates": ["Candidate A", "Candidate B"]
            },
            {
                "id": "vp",
                "title": "VICE PRESIDENT",
                "candidates": ["Candidate C", "Candidate D"]
            }
        ]
    } 
    return jsonify(BALLOT_SCHEMA), 200

@app.route('/api/send-token', methods=['POST'])
def process_identity_and_mail():
    data = request.get_json() or {}
    matric = data.get("matric", "").strip().upper()
    
    if not matric:
        return jsonify({"message": "Malformed input payload."}), 400
        
    conn = get_db_connection()
    try:
        voter = conn.execute('SELECT * FROM voters WHERE matric_id = ?', (matric,)).fetchone()
        
        if not voter:
            return jsonify({"message": "Access Denied: Record missing from student registry."}), 404
            
        if voter['has_voted'] == 1:
            return jsonify({"message": "Access Denied: Voter registry tracks this ballot as cast."}), 403
            
        assigned_email = voter['registered_email']
        generated_pin = str(random.randint(100000, 999999))
        
        # Log token to terminal console for verification/debugging
        print(f"\n[SECURITY TOKEN DISPATCH] Matric: {matric} | Code: {generated_pin} | Sent to: {assigned_email}\n")
        
        # Masking the email for frontend privacy protection (e.g., g***r@gmail.com)
        parts = assigned_email.split('@')
        masked_email = f"{parts[0][0]}***{parts[0][-1]}@{parts[1]}" if len(parts[0]) > 2 else assigned_email
        
        return jsonify({
            "message": "Verification code dispatched successfully.",
            "target": masked_email
        }), 200
        
    except Exception as e:
        return jsonify({"message": f"Internal database error: {str(e)}"}), 500
    finally:
        conn.close()

# Safe production initialization hook for Gunicorn on Render
try:
    init_and_seed_db()
except Exception as err:
    print(f"Lifecycle setup error: {err}")

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=3000, debug=True)
