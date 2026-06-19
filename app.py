import os, sqlite3, random
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

DB_PATH = 'elections.db'
CSV_PATH = 'students.csv'
# Temporary storage for tokens: {matric: token}
tokens = {}

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('DROP TABLE IF EXISTS voters')
    cursor.execute('CREATE TABLE voters (matric_id TEXT PRIMARY KEY, has_voted INTEGER DEFAULT 0)')
    # Import logic here (as defined previously)
    conn.commit()
    conn.close()

init_db()

@app.route('/api/send-token', methods=['POST'])
def send_token():
    matric = request.json.get('matric', '').upper()
    conn = sqlite3.connect(DB_PATH)
    voter = conn.execute('SELECT * FROM voters WHERE matric_id = ?', (matric,)).fetchone()
    
    if not voter or voter[1] == 1:
        return jsonify({"message": "Access Denied"}), 403
    
    token = str(random.randint(100000, 999999))
    tokens[matric] = token
    print(f"DEBUG: Token for {matric} is {token}")
    return jsonify({"message": "Token sent"})

@app.route('/api/verify-token', methods=['POST'])
def verify_token():
    data = request.json
    if tokens.get(data['matric']) == data['token']:
        return jsonify({"success": True})
    return jsonify({"success": False}), 401

@app.route('/api/cast-vote', methods=['POST'])
def cast_vote():
    matric = request.json.get('matric')
    conn = sqlite3.connect(DB_PATH)
    conn.execute('UPDATE voters SET has_voted = 1 WHERE matric_id = ?', (matric,))
    conn.commit()
    conn.close()
    return jsonify({"message": "Vote recorded!"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 3000)))
