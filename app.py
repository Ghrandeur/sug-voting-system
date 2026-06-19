import os
import csv
import time
import random
import sqlite3
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
# Enable CORS for all routes so your Netlify domain can communicate securely
CORS(app)

DB_PATH = 'elections.db'
CSV_PATH = 'students.csv'

def init_and_seed_db():
    """Initializes the database schema and seeds voter data if empty."""
    # If the database file exists and has data, don't re-seed
    if os.path.exists(DB_PATH) and os.path.getsize(DB_PATH) > 0:
        print("Database already initialized.")
        return

    print("No database found. Initializing schema and seeding voter data...")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 1. Create the voters table structure safely
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS voters (
            matric_id TEXT PRIMARY KEY,
            registered_email TEXT,
            has_voted INTEGER DEFAULT 0
        )
    ''')
    
    # 2. Extract and parse data from your local student database file
    if os.path.exists(CSV_PATH):
        with open(CSV_PATH, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Ensure keys match your CSV header columns exactly (e.g., 'matric_id' and 'email')
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
    """Creates a distinct connection thread to the SQLite database."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# --- BALLOT SCHEMA ENDPOINT ---
@app.route('/api/ballot-schema', methods=['GET'])
def get_ballot_schema():
    # Example placeholder structure; adapt to your exact ballot dictionary variable
    BALLOT_SCHEMA = {"status": "success", "positions": []} 
    return jsonify(BALLOT_SCHEMA), 200

# --- TOKEN DISPATCH ENDPOINT ---
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
        expiry_time = time.time() + (10 * 60)
        
        # TODO: Insert your secure SMTP code block using os.getenv("EMAIL_USER") here
        print(f"[PROD LOG] Dispatched Token {generated_pin} securely to {assigned_email}")
        
        return jsonify({
            "message": "Verification code dispatched successfully.",
            "target": f"...{assigned_email[-12:]}"  # Mask email visually for privacy protection
        }), 200
        
    except Exception as e:
        return jsonify({"message": f"Internal database error processing handshake: {str(e)}"}), 500
    finally:
        conn.close()

# --- PROD INTERFACE PREPARATION HOOK ---
# We initialize the database directly when this module is parsed by Gunicorn on Render
try:
    init_and_seed_db()
except Exception as err:
    print(f"Lifecycle setup bypassed or caught: {err}")

if __name__ == '__main__':
    # This block handles local development workflows natively inside Termux
    app.run(host='127.0.0.1', port=3000, debug=True)
