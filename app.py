import csv
import hashlib
import logging
import os
from datetime import datetime
from flask import Flask, request, jsonify, render_template_string
from tuya_connector import TuyaOpenAPI, TUYA_LOGGER

app = Flask(__name__)

ACCESS_ID = os.getenv("TUYA_ACCESS_ID", "ksnyvss88etnjpfr5sd3")
ACCESS_KEY = os.getenv("TUYA_ACCESS_KEY", "2a6375146abf4651bdcc08b5071db467")
API_ENDPOINT = os.getenv("TUYA_API_ENDPOINT", "https://openapi.tuyaus.com")
DEVICE_ID = os.getenv("TUYA_DEVICE_ID", "eb1867409b663fd0cdc1ev")

TUYA_LOGGER.setLevel(logging.DEBUG)
openapi = TuyaOpenAPI(API_ENDPOINT, ACCESS_ID, ACCESS_KEY)
openapi.connect()

def verify_user(username, password):
    try:
        with open("users.csv", newline='') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['username'] == username and row['password'] == password:
                    return True
    except FileNotFoundError:
        return False
    return False

def log_activation(username):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    file_exists = os.path.isfile("logs.csv")
    with open("logs.csv", "a", newline='') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["username", "timestamp"])
        writer.writerow([username, timestamp])
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
    respuesta = openapi.post(f"/v1.0/devices/{DEVICE_ID}/commands", comandos)
    return respuesta

@app.route('/', methods=['GET'])
def home():
    html_form = """
    <!DOCTYPE html>
    <html>
    <head><title>Activar Relé</title></head>
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
    """
    return render_template_string(html_form)

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
    registros = []
    try:
        with open("logs.csv", newline='') as f:
            reader = csv.DictReader(f)
            for row in reader:
                registros.append({"username": row['username'], "timestamp": row['timestamp']})
    except FileNotFoundError:
        pass
    return jsonify(registros)

@app.route('/manage', methods=['GET'])
def manage_users():
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Gestión de Usuarios</title></head>
    <body>
        <h2>Agregar Nuevo Usuario</h2>
        <form action="/add_user" method="post">
            Usuario: <input type="text" name="new_username" required><br>
            Contraseña: <input type="password" name="new_password" required><br>
            <button type="submit">Agregar</button>
        </form>

        <h2>Cambiar Contraseña</h2>
        <form action="/change_password" method="post">
            Usuario: <input type="text" name="username" required><br>
            Contraseña Actual: <input type="password" name="old_password" required><br>
            Nueva Contraseña: <input type="password" name="new_password" required><br>
            <button type="submit">Cambiar</button>
        </form>
    </body>
    </html>
    """
    return render_template_string(html)

@app.route('/add_user', methods=['POST'])
def add_user():
    username = request.form['new_username']
    password = request.form['new_password']
    password_hash = hashlib.sha256(password.encode()).hexdigest()

    try:
        with open("users.csv", newline='') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['username'] == username:
                    return "Usuario ya existe", 400
    except FileNotFoundError:
        pass

    with open("users.csv", "a", newline='') as f:
        writer = csv.writer(f)
        writer.writerow([username, password, password_hash])
    return "Usuario agregado exitosamente"

@app.route('/change_password', methods=['POST'])
def change_password():
    username = request.form['username']
    old_password = request.form['old_password']
    new_password = request.form['new_password']
    new_hash = hashlib.sha256(new_password.encode()).hexdigest()

    updated = False
    users = []

    try:
        with open("users.csv", newline='') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['username'] == username and row['password'] == old_password:
                    row['password'] = new_password
                    row['password_hash'] = new_hash
                    updated = True
                users.append(row)
    except FileNotFoundError:
        return "Archivo de usuarios no encontrado", 500

    if updated:
        with open("users.csv", "w", newline='') as f:
            writer = csv.DictWriter(f, fieldnames=["username", "password", "password_hash"])
            writer.writeheader()
            writer.writerows(users)
        return "Contraseña actualizada correctamente"
    else:
        return "Credenciales incorrectas", 401

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)))
