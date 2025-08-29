import csv
import os
import hashlib
import logging
from datetime import datetime
from flask import Flask, request, jsonify, render_template_string
from tuya_connector import TuyaOpenAPI, TUYA_LOGGER

app = Flask(__name__)

# Configuración de Tuya desde variables de entorno
ACCESS_ID = os.getenv("TUYA_ACCESS_ID", "ksnyvss88etnjpfr5sd3")
ACCESS_KEY = os.getenv("TUYA_ACCESS_KEY", "2a6375146abf4651bdcc08b5071db467")
API_ENDPOINT = os.getenv("TUYA_API_ENDPOINT", "https://openapi.tuyaus.com")
DEVICE_ID = os.getenv("TUYA_DEVICE_ID", "eb1867409b663fd0cdc1ev")

# Inicializar conexión con Tuya
TUYA_LOGGER.setLevel(logging.DEBUG)
openapi = TuyaOpenAPI(API_ENDPOINT, ACCESS_ID, ACCESS_KEY)
openapi.connect()

# Verificar usuario desde users.csv
def verify_user(username, password):
    hashed_password = hashlib.sha256(password.encode()).hexdigest()
    try:
        with open("users.csv", newline='') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['username'] == username and row['password_hash'] == hashed_password:
                    return True
    except FileNotFoundError:
        return False
    return False

# Registrar activación en logs.csv
def log_activation(username):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    file_exists = os.path.isfile("logs.csv")
    with open("logs.csv", "a", newline='') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["username", "timestamp"])
        writer.writerow([username, timestamp])
    return timestamp

# Activar relé Tuya
def activar_rele_tuya():
    comandos = {
        "commands": [
            {
                "code": "switch_1",
                "value": True
            }
        ]
    }
    respuesta = openapi.post(f"{API_ENDPOINT}/v1.0/devices/{DEVICE_ID}/commands", comandos)
    return respuesta

# Ruta principal con formulario HTML
@app.route('/', methods=['GET'])
def home():
    html_form = '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Activar Relé</title>
    </head>
    <body>
        <h2>Activar Relé Tuya</h2>
        <form id="activationForm">
            <label for="username">Usuario:</label><br>
            <input type="text" id="username" name="username" required><br><br>
            <label for="password">Contraseña:</label><br>
            <input type="password" id="password" name="password" required><br><br>
            <button type="submit">Activar</button>
        </form>
        <p id="response"></p>

        <script>
        document.getElementById('activationForm').addEventListener('submit', function(e) {
            e.preventDefault();
            const username = document.getElementById('username').value;
            const password = document.getElementById('password').value;

            fetch('/activate', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ username, password })
            })
            .then(response => response.json())
            .then(data => {
                document.getElementById('response').innerText = data.message || 'Error';
            })
            .catch(error => {
                document.getElementById('response').innerText = 'Error en la solicitud';
            });
        });
        </script>
    </body>
    </html>
    '''
    return render_template_string(html_form)

# Ruta para activar el relé
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

# Ruta para ver los logs
@app.route('/logs', methods=['GET'])
def logs():
    registros = []
    try:
        with open("logs.csv", newline='') as f:
            reader = csv.DictReader(f)
            for row in reader:
                registros.append({"username": row['username'], "timestamp": row['timestamp']})
    except FileNotFoundError:
        pass
    return jsonify(registros)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)))

