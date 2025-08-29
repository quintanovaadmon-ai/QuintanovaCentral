import os
import sqlite3
from flask import Flask, request, jsonify
from datetime import datetime
import hashlib
import logging
from tuya_connector import TuyaOpenAPI, TUYA_LOGGER

app = Flask(__name__)
DB_PATH = 'tuya_server.db'

# Configuración de Tuya desde variables de entorno
ACCESS_ID = os.getenv("TUYA_ACCESS_ID", "ksnyvss88etnjpfr5sd3")
ACCESS_KEY = os.getenv("TUYA_ACCESS_KEY", "2a6375146abf4651bdcc08b5071db467")
API_ENDPOINT = os.getenv("TUYA_API_ENDPOINT", "https://openapi.tuyaus.com")
DEVICE_ID = os.getenv("TUYA_DEVICE_ID", "eb1867409b663fd0cdc1ev")

# Inicializar conexión con Tuya
TUYA_LOGGER.setLevel(logging.DEBUG)
openapi = TuyaOpenAPI(API_ENDPOINT, ACCESS_ID, ACCESS_KEY)
openapi.connect()

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

def activar_rele_tuya():
    comandos = {
        "commands": [
            {
                "code": "switch_1",
                "value": True
            }
        ]
    }
    respuesta = openapi.post(f"/v1.0/iot-03/devices/{DEVICE_ID}/commands", comandos)
    return respuesta

@app.route('/activate', methods=['POST'])
def activate():
    data = request.json
    username = data.get('username')
    password = data.get('password')

    if verify_user(username, password):
        respuesta_tuya = activar_rele_tuya()
        timestamp = log_activation(username)
        return jsonify({
            "status": "success",
            "message": f"Relé activado por {username}",
            "timestamp": timestamp,
            "tuya_response": respuesta_tuya
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

