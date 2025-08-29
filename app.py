from flask import Flask, request, jsonify
from datetime import datetime
import sqlite3
import hashlib

app = Flask(__name__)

DB_PATH = 'tuya_server.db'

def verify_user(username, password):
    hashed_password = hashlib.sha256(password.encode()).hexdigest()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username=? AND password=?", (username, hashed_password))
    user = c.fetchone()
    conn.close()
    return user is not None

def log_activation(username):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO logs (username, timestamp) VALUES (?, ?)", (username, timestamp))
    conn.commit()
    conn.close()
    return timestamp

@app.route('/activate', methods=['POST'])
def activate():
    data = request.json
    username = data.get('username')
    password = data.get('password')

    if verify_user(username, password):
        # Aquí iría la llamada real a la API de Tuya
        timestamp = log_activation(username)
        return jsonify({
            "status": "success",
            "message": f"Relé activado por {username}",
            "timestamp": timestamp
        })
    else:
        return jsonify({
            "status": "error",
            "message": "Credenciales inválidas"
        }), 401

@app.route('/logs', methods=['GET'])
def logs():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM logs ORDER BY timestamp DESC")
    registros = [{"username": row[0], "timestamp": row[1]} for row in c.fetchall()]
    conn.close()
    return jsonify(registros)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
