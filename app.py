import os
import random
import time
import smtplib
import sqlite3
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)

DB_FILE = 'elections.db'

# HARDCODED BALLOT SCHEMA: 20 Positions, 2 Candidates per position (40 total contestants)
BALLOT_SCHEMA = {
    "president": {
        "title": "President",
        "candidates": ["Emmanuel Udoh", "Victoria Asuquo"]
    },
    "vice_president": {
        "title": "Vice President",
        "candidates": ["Abasiama Archibong", "Blessing Ekong"]
    },
    "sec_gen": {
        "title": "Secretary General",
        "candidates": ["Samuel Akpan", "Aniefiok Effiong"]
    },
    "assistant_sec_gen": {
        "title": "Assistant Secretary General",
        "candidates": ["Idara Udo", "Nisong Marcus"]
    },
    "financial_sec": {
        "title": "Financial Secretary",
        "candidates": ["Etiini Joshua", "Utibe Friday"]
    },
    "treasurer": {
        "title": "Treasurer",
        "candidates": ["Emem Okon", "Kufre Bassey"]
    },
    "director_of_welfare": {
        "title": "Director of Welfare",
        "candidates": ["Iniobong Sunday", "Nsikak Udofia"]
    },
    "director_of_socials": {
        "title": "Director of Socials",
        "candidates": ["Salvation Elijah", "Edidiong Asuquo"]
    },
    "director_of_sports": {
        "title": "Director of Sports",
        "candidates": ["Goodnews Linus", "Ubong Patrick"]
    },
    "public_relations_officer": {
        "title": "Public Relations Officer (PRO)",
        "candidates": ["Peace Emmanuel", "Aniekan Clement"]
    },
    "director_of_protocols": {
        "title": "Director of Protocols",
        "candidates": ["Praise Godspower", "Mfoniso Edet"]
    },
    "auditor_general": {
        "title": "Auditor General",
        "candidates": ["Itemobong Moses", "Saviour Monday"]
    },
    "director_of_info": {
        "title": "Director of Information",
        "candidates": ["Daniel Jack", "Ekemini Victor"]
    },
    "provost_marshal": {
        "title": "Provost Marshal",
        "candidates": ["Promise Etok", "Sammy Bro"]
    },
    "director_of_training": {
        "title": "Director of Training",
        "candidates": ["Gideon Silas", "Faith Joseph"]
    },
    "director_of_health": {
        "title": "Director of Health",
        "candidates": ["Mercy Christopher", "Hope William"]
    },
    "academic_director": {
        "title": "Academic Director",
        "candidates": ["Elijah Paul", "Queen Thompson"]
    },
    "director_of_transport": {
        "title": "Director of Transport",
        "candidates": ["David Solomon", "Marvelous John"]
    },
    "editor_in_chief": {
        "title": "Editor-in-Chief",
        "candidates": ["Collins George", "Esther Isaac"]
    },
    "chief_judge": {
        "title": "Chief Judge",
        "candidates": ["Justice Eyo", "Dignity Frank"]
    }
}

def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def send_secure_email(target_recipient, matric_id, tracking_pin):
    sender_account = os.getenv("EMAIL_USER")
    sender_password = os.getenv("EMAIL_PASS")
    if not sender_account or not sender_password:
        raise ValueError("Security Failure: Outbound SMTP credentials missing from environment.")

    message = MIMEMultipart("alternative")
    message["Subject"] = "🔒 SECURE ACCESS TOKEN: SUG Electoral Portal"
    message["From"] = f'"SUG Electoral Bureau" <{sender_account}>'
    message["To"] = target_recipient

    plain_text = f"Your single-use electoral access token is: {tracking_pin}."
    html_markup = f"""
    <div style="font-family: Arial, sans-serif; padding: 25px; border: 1px solid #e2e8f0; border-radius: 12px; max-width: 480px; margin: auto;">
        <h2 style="color: #0f172a; margin-top: 0; border-bottom: 2px solid #f1f5f9; padding-bottom: 10px;">Electoral Verification System</h2>
        <p style="color: #334155;">An access token was generated for your academic registry footprint:</p>
        <p style="font-size: 0.9rem; color: #64748b;"><b>Matric ID:</b> {matric_id}</p>
        <div style="background: #0f172a; color: #ffffff; padding: 18px; font-size: 1.75rem; font-weight: bold; text-align: center; letter-spacing: 6px; border-radius: 8px; margin: 20px 0;">
            {tracking_pin}
        </div>
        <p style="font-size: 0.8rem; color: #94a3b8; text-align: center; margin: 0;">This security credential expires strictly in 10 minutes.</p>
    </div>
    """
    message.attach(MIMEText(plain_text, "plain"))
    message.attach(MIMEText(html_markup, "html"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(sender_account, sender_password)
        server.sendmail(sender_account, target_recipient, message.as_string())

@app.route('/')
def serve_portal():
    try:
        with open('index.html', 'r', encoding='utf-8') as file:
            return file.read()
    except FileNotFoundError:
        return jsonify({"message": "Critical Error: Core interface file missing."}), 404

@app.route('/api/ballot-schema', methods=['GET'])
def get_ballot_schema():
    return jsonify(BALLOT_SCHEMA), 200

@app.route('/api/send-token', methods=['POST'])
def process_identity_and_mail():
    data = request.get_json() or {}
    matric = data.get("matric", "").strip().upper()

    if not matric:
        return jsonify({"message": "Malformed input payload."}), 400

    conn = get_db_connection()
    voter = conn.execute('SELECT * FROM voters WHERE matric_id = ?', (matric,)).fetchone()

    if not voter:
        conn.close()
        return jsonify({"message": "Access Denied: Record missing from official register."}), 403

    if voter['has_voted'] == 1:
        conn.close()
        return jsonify({"message": "Access Denied: Voter registry track shows closed/ballot cast."}), 403

    assigned_email = voter['registered_email']
    generated_pin = str(random.randint(100000, 999999))
    expiry_time = time.time() + (10 * 60)

    conn.execute('''
        UPDATE voters 
        SET active_token = ?, token_expires = ? 
        WHERE matric_id = ?
    ''', (generated_pin, expiry_time, matric))
    
    conn.commit()
    conn.close()

    try:
        send_secure_email(assigned_email, matric, generated_pin)
        return jsonify({"message": "Token successfully pushed to registered address."}), 200
    except Exception as e:
        return jsonify({"message": "Outbound delivery subsystem failed."}), 500

@app.route('/api/verify-token', methods=['POST'])
def check_received_pin_token():
    data = request.get_json() or {}
    matric = data.get("matric", "").strip().upper()
    token = data.get("token", "").strip()

    conn = get_db_connection()
    voter = conn.execute('SELECT * FROM voters WHERE matric_id = ?', (matric,)).fetchone()

    if not voter or voter['has_voted'] == 1:
        conn.close()
        return jsonify({"message": "Session invalidated."}), 403

    if not voter['active_token'] or voter['active_token'] != token:
        conn.close()
        return jsonify({"message": "Security parameter error: Token mismatch."}), 401

    if time.time() > voter['token_expires']:
        conn.close()
        return jsonify({"message": "Security parameter error: Token expired."}), 401

    conn.close()
    return jsonify({"message": "Token status authorized."}), 200

@app.route('/api/commit-ballot', methods=['POST'])
def commit_ballot():
    data = request.get_json() or {}
    matric = data.get("matric", "").strip().upper()
    token = data.get("token", "").strip()
    votes = data.get("votes", {}) # Contains their selections

    conn = get_db_connection()
    voter = conn.execute('SELECT * FROM voters WHERE matric_id = ?', (matric,)).fetchone()

    if not voter or voter['has_voted'] == 1:
        conn.close()
        return jsonify({"message": "Fraud Vector Detected: Session context closed."}), 403

    if not voter['active_token'] or voter['active_token'] != token:
        conn.close()
        return jsonify({"message": "API Tampering Blocked: Token authorization invalid."}), 401

    if time.time() > voter['token_expires']:
        conn.close()
        return jsonify({"message": "Ballot window expired. Refresh authentication token."}), 401

    # SECURE TRANSACTION PROCESSING:
    # Here, you would record the contents of `votes` into a separate anonymous poll tally table.
    print(f"Verified Audit Log: Secure ballot submitted for context {matric}: {votes}")

    conn.execute('''
        UPDATE voters 
        SET has_voted = 1, active_token = NULL, token_expires = NULL 
        WHERE matric_id = ?
    ''', (matric,))
    
    conn.commit()
    conn.close()
    return jsonify({"message": "Secure state locked. Transaction finalized."}), 200

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=3000, debug=True)
