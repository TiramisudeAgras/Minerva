# app.py - Servidor Principal de Minerva Explorador de ICFES

import sqlite3
import os
from datetime import datetime
from collections import defaultdict
from flask import Flask, jsonify, render_template, request
import requests # Necesario para la verificación de Turnstile
import configparser

# --- Configuración Global ---
DATABASE_NAME = 'minerva_icfes_data.db'
LAST_UPDATED_FILE = 'minerva_last_updated.txt'
# Definimos las columnas de puntajes principales para referencia y consistencia con create_database.py.
SCORE_COLUMNS = ['punt_global', 'punt_lectura_critica', 'punt_matematicas', 'punt_c_naturales', 'punt_sociales_ciudadanas', 'punt_ingles']

# --- Cargar Clave Secreta de Cloudflare Turnstile desde Archivo ---
CLOUDFLARE_TURNSTILE_SECRET_KEY = None
SECRET_KEY_FILE_PATH = '/home/Chachalingo/mysite/crypto/.config_secrets.ini'

try:
    # Si usaste formato INI (Option B)
    config = configparser.ConfigParser()
    if os.path.exists(SECRET_KEY_FILE_PATH) and os.path.getsize(SECRET_KEY_FILE_PATH) > 0:
        config.read(SECRET_KEY_FILE_PATH)
        if 'CLOUDFLARE' in config and 'TURNSTILE_SECRET_KEY' in config['CLOUDFLARE']:
            CLOUDFLARE_TURNSTILE_SECRET_KEY = config['CLOUDFLARE']['TURNSTILE_SECRET_KEY']
        else:
            print(f"ADVERTENCIA: La sección [CLOUDFLARE] o la clave TURNSTILE_SECRET_KEY no se encontró en {SECRET_KEY_FILE_PATH}")
    else:
        print(f"ADVERTENCIA: Archivo de clave secreta no encontrado o vacío en {SECRET_KEY_FILE_PATH}")

except FileNotFoundError:
    print(f"ADVERTENCIA: Archivo de clave secreta no encontrado en {SECRET_KEY_FILE_PATH}")
except Exception as e:
    print(f"Error al leer el archivo de clave secreta ({SECRET_KEY_FILE_PATH}): {e}")

if not CLOUDFLARE_TURNSTILE_SECRET_KEY:
    print("ADVERTENCIA CRÍTICA: La Secret Key de Cloudflare Turnstile NO ESTÁ CARGADA.")
    print("La verificación de Turnstile probablemente fallará o será insegura si la app continúa.")
    raise RuntimeError("Falta la configuración de CLOUDFLARE_TURNSTILE_SECRET_KEY. La aplicación no puede iniciar de forma segura.")

MINERVA_ASCII_ART_FOR_WEB = """
                                ░░░░░░░░░░▒▒▒▒▒░▒▒▒▒▒▒▒░░░░▒░░░░░░░░▒░░░▒▒░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░
░░░░░░░░░░░░▒▒▒▒░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░
░░░░░░░░░░░░░▒▒▒▒░░░░░░░░░░░░░░░░░░░░░░░▒░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░
░░░░░░░░░░░░░░▒▒░░░░░░░░░░░░░░▓█▓▓▓▓▓░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░
░░░░░░░░░░░░░░░▒▒▒▒░░░░░░░▒▒▓▓▓██▓▓▓█▓▓▓░░░░▒░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░
░░░░░░░░░░░░░░░░▒▒░▒░░░░░▓███▓▓▓▓█▓▓▒▓▓█▒▓░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░
░░░░░░░░░░░░░░░░░▒▒░░░░░░░░███▓█▓▓▓▒▒▓▓█▓▒▓▓░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░
░░░░░░░░░░░░░░░░░░▒▒░▒▒░░░░░░██▓▓▓▓▓▒▓▓▓▒▓▒▒▒▓░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░
░░░░░░░░░░░░░░░░░░░▒▒░░░░░░░░░██▓▓▓▓▒▒▒▒▒▒▒▒▒▓░▒░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░
░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░█▓▒▒▓▒▓▒▓▒▓▒▓▒▓▓▒▓░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░
░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░▓▓▒▒▒▒▒▓▒▒▒▒▒▒▓▓▒▓░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░
░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░▓▓▒▒▒░░▒▒▒▒▓▒▒▓▒▒▒▓░░░░░░░░░░░░░░░░░░░░░░░░░░░░░
░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░▒▓█▓██▒▒▒▒▒▓▒▒▒▒▒▒▒▒░░░░░░░░░░░░░░░░░░░░░░░░░░░░
░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░▓██▒▒▒▒▒▒▒▒▒▒▓░░░░░░░░░░░░░░░░░░░░░░░░░░░░░
░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░▓█░░▒▓▓▒░░▒▒▓▒▒░▒▓░░░░░░░░░░░░░░░░░░░░░░░░░░
░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░▒▒▒▒▓░░░▒▓▒▓▓▓▒░░░░░░░░░░░░░░░░░░░░░░░░░
░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░▓▒▒▓▒▓▒▒░░░░▒▓░▒▒▓▓▒█▒░░░░░░░░░░░░░░░░░░░░░░░
░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░▒█▓░▒▓▓▒▒▓▒░░░░░▓░░▓▓▒▒▒░░░░░░░░░░░░░░░░░░░░░░
░░░░░░░░░░░░░░░░░░░░░░░░░░░░░▒▒▒▒░░░░▒▒░░░░░░░░░░░▓▓░▓░░▓▒░░░░░░░░░░░░░░░░░░░░░░
░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░█▒▓█▓▓▒░░░░░░░▒▒█░░▓█▓▒░░░░░░░░░░░░░░░░░░░░░
░░░░░░░░░░░░░░░░░░░░░░░░░▒░▓░░░░▒░░▒░░░░░░░░░░░░░░░░▒▓░░▒█▒░░░░░░░░░░░░░░░░░░░░░
░░░░░░░░░░░░░░░░░░░░░░░░░████████████████████▓░░░░░░░▓█▒░▓█▒░░░░░░░░░░░░░░░░░░░░
░░░░░░░░░░░░░░░░░░░░░░░▓███████░█████████████████ ░░░░▓█░░▒▓░░░░░░░░░░░░░░░░░░░░
░░░░░░░░░░░░░░░░░░░░░░█████████▓▒███████████████▓███░░▒▓▓▒█▒▒░░░░░░░░░░░░░░░░░░░
░░░░░░░░░░░░░░░░░░░░░░██████████▓███████████████▒▒▓███▒▓█▒█▓▓░░░░░░░░░░░░░░░░░░░
░░░░░░░░░░░░░░░░░░░░░▒████▓▓▓▓▓█████▓▓████▓▓███████████░█▒█▒▒░░░░░░░░░░░░░░░░░░░
░░░░░░░░░░░░░░░░░░░░░░█▓█▓▓██▓▓█████████▒▒▒▒▓▓███████████▒▓▒▓░░░░░░░░░░░░░░░░░░░
░░░░░░░░░░░░░░░░░░░░░░███▓████▓▓██████▓▓▒▒▓▓▓▒▓███████████▓▒▒░░░░░░░░░░░░░░░░░░░
░░░░░░░░░░░░░░░░░░░░░░░▓█▓▓▓██░▒▒▒██▓▓▓▓▓▓▓▓▓▓▓▓▓███████▓▒▒▒░░░░░░░░░░░░░░░░░░░░
░░░░░░░░░░░░░░░░░░░░░░░▒███▓▓▓▓████▓▓█▓▓▓▓▓▓▓▓▒▓▓███████▒░░▒░░░░░░░░░░░░░░░░░░░░
░░░░░░░░░░░░░░░░░░░░░░░█▓█▓▒▒▓████▒▒▒▓█▓▓▓▓▓▓▓▓▓▓▓▒░▒███░▒▓▓░░░░░░░░░░░░░░░░░░░░
░░░░░░░░░░░░░░░░░░░░░░█████▒▒▓▓▓▓█████▓▓▓▓▓▓▓▓▓▓▓▓▓█████▒▒▒░░░░░░░░░░░░░░░░░░░░░
░░░░░░░░░░░░░░░░░░░░░░░░███▓▒▒▓▓█▓▓██▓██▓▓▓▓▓▓▓▓▓▓▓▓████▓▒░░░░░░░░░░░░░░░░░░░░░░
░░░░░░░░░░░░░░░░░░░░░░░░░░██▒▒▒█▓██▓▓▓▒▓▓▓▓▓▓▓▓▓▓▓▓▓▓███▒░░░░░░░░░░░░░░░░░░░░░░░
░░░░░░░░░░░░░░░░░░░░░░░░░░░░░▒▒▓▒▒▒▓▓█▓▓▓▓██▓███▓▓▓▓▓██▓█░░░░░░░░░░░░░░░░░░░░░░░
░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░▒▒▒▓███████████████▓▓▓▒███▓░░░░░░░░░░░░░░░░░░░░░░░
░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░▓▓██████████████▓▓▓▓▓▒████░░░░░░░░░░░░░░░░░░░░░░
░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░▓▓█████████████▓▓▓▓▓▒███▒█░░░░░░░░░░░░░░░░░░░░░
░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░▓███████████▓▓▓▓▓▓▒██▓█▒░░░░░░░░░░░░░░░░░░░░░
░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░▓█▓▓█████████▓▓▓▓▓▓▒█▓█▓▓░░░░░░░░░░░░░░░░░░░░
░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░█▓█████████▓▓▓▓▓▓▓▓▒█▓██░░░░░░░░░░░░░░░░░░░░
░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░▓▓▓███████▓██▓█▓▓▓▓▒░▒███▓▒░░▒▓▒░░░░░░░░░░░░
░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░▓█▓████████████▓▓▓▓▒░ ░▒▒██████▒░░░█▓▓▓▓▒░░░
░░░░░░░░░░░░░░░▓██▓░░▒▓██░░░░░░░░░░░▓▓▓▓████████████▓▓▓▒░░░▒▒▒▒▒▒██▓▒████████▒▒░
░░░░░░░░░░░░░░░░░▓▒███░██░░░░░░░░▓██▓███████████████▓▓░░░▒▒▒▒░░░░▓▒░▒▓▒▒▓░▒▒▒▓▒▒
░░░░░░░░░░░░░░░░░██░▓████▓▒██▒███▒ ░▓▓██▓████████▓▓▓▒▓▒▒░░░░▒▒█▓▒▓▒▒▒▓▒█▒▓░▓▓▓▓▓
░░░░░░░░░░░░░░░░░░░▒▓██████▓▓█▒░ ░░░▒▒▒▓▓▓▓████▒░░░▒▒▓▓▒░▒▒▒█▒▒▒▓▒▒▓▒▒▒█▓░▓░▓▒▒▒
░░░░░░░░░░░░░░░░░▒█▓█████▒███▒░░░░░░  ▒▓██████▓▓▓▓▓▓▒▒▒▒▒▓█▒▒░▓▒▒▒▓░░▒▒▓█▓▒▓▓▓▓▓
░░░░░░░░░░░░░░░░░█▓▒▓████▓▓▓▓▓▓▓▒▓▓▓▓▓████████▓▓▓▒▒▒▒▒▒▓█▒▒░▓█▒▒▓▒░░░░▒▒██▒▓▓▓▓▓
░░░░░░░░░░░▒█▓▓▓░▒▓▓█▒▓▒█▓▒█▓▓▓▓▓▓▓▓▓▓▓▓▓█▓█▓▓▓▓▒░░▒▒██▓▒▒▒█▒▒▒▒░░▒░░░▒▒██▒▓█▒█▓
░░░░░░░░█▓▓▓█████▓██▒▒▒▒▒█▓▓▓░░░░▒▒▓▓▓▓▓▓▒▒░▒▒▒░░▒▓██▒▒▒░▒█▒▒▒▓░▒▒░░░▒▒▒▓█▓▓█▓▓▓
░░░░░░░░░░░░░▓▓█████▒▒░░▒▓██▓▓░░░░░░░░▒▓▓█▓▓▒░░▒██▓▓░▒▒▒█▒▒▒▒▒▒░░░░░░▒▒▒▓██▒▓█▓█
░░░░░░░░░░░░░▓░▓█████▒░▒░▒ ▒▒▒▒░▒░ ░░▒▒▒▒▒▒░░░███▓░▓▓▒▒█▒▒░▒▒▒░░░░░░▒▒▒▒▓██▓▓███
░░░░░░░░░░░▒▓▒▓▒█░▓▓▓█▓▓▓▒▒░░░▒█▓▒░░░░░░░░░░▓██▓▒▓▓▓▒▒█▓░░░░▒▒░░░░░░░▒▒▓▓██▓▓▓█▓
░░░░░░░░░░▒▓▓█▓██▒░░▒▒░░░▒░░▒▓▒▓▓███▒▒░░░▓███░▓██▓▒▒▓█▓░░▒░▒▒▒▒░░░░▒░░▒▒▓███▓▓██
░░░░░░░░░▒▓▓▓▓▓░░░▓▓▓▓░░▒░░▒▒▒▓▓▓▓█████▓▒░▓████▓▓▒▒▓█▓▓▒▒▒▒▒▓▒▒▒▒▒▒▒▓▓▒▒▓███▓▓██
░░░░░░░░▒▒▓▓▒▒▓██▓░▓▓▒█░▒▒▓▒▒▒▒▒▓▒███████▓▒▒▓████▓▓█▓█▒▒▒▓▓▓▓▓▓▓▓▓▓▓█▓█▓▓▓███▓▓█
░░░░░░▒▒▒▓▓█▒▓██░░░░░▒▓█▓▒▒▒▒▒▒█▓▓▓▓█████▓█▓░█▒░▓████▓▓▓▓▓▓█▓▓▓█▓▓▓██▓█▓█▓███▓▓▓
░▒▒▒░▒▓▓▓▓█▒▒▓█░░░░▒▒███▒▒▒▓▒▒░▓▒▓█▓████████▒███▓▓███▓▓▓▓██████████▓██▓▓███████▓
▒▒▒▒▒▒▓▓▓██▒▒█░▒▒▒▒▓▓▓▓▓████▓▓█▓▒▒█████████░░████▓▒░▒████▓▓▓▒█████▓█████████████
▒▒▒▒▒▓▓▓███▒▒▒▓▓▓▓▓▓▓████▒▒▒▓▓▓▓▓▓▓██▓███████████████▓░▓▓███▓▒▒▓▓█████▓█████████
▒▒▒▓▓▓▓████▒▓▓█▓▓▓▓▓▓▓██▓▓░▒▓▓▓▓▓▓▒████▓██▒▒▒▓▒▒▓████████▒▓██████████▓██████████
▒▒▒▓▓▓█████▓▓███▓▓▓▓▓▓▓███▓▓░▒▒▓█▓▓███▓▓█▓▓█▓▓▓█▓▓██████████████████████████████
▓▓▓░▓▓▓███▓▓▓████▓▓░▓▓██████▓░░▓▓▒▓████▒▓▓▓████▓████████████▓▒██████████████████
▓▒▓▓▓▓▓███▓▓▓████████▓████████▓▒▒ ▓▓██▓▓▓████▓▓██▓▓▓███████████▓▒▓██████████████
▓▓▓▓▓▓▓███▓▓▓████████▓█████████▓▒▓▒▒▒█▓█▓███▓░▒██▓▓████████████████▓▒▒▓█████████
"""

app = Flask(__name__)

# --- Funciones de Utilidad ---

def get_db_connection():
    """Establece conexión con la base de datos SQLite."""
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def get_last_updated_date():
    """Lee la fecha de la última actualización de la BD."""
    try:
        with open(LAST_UPDATED_FILE, 'r', encoding='utf-8') as f:
            return f.read().strip()
    except FileNotFoundError:
        return "Fecha no disponible"
    except Exception:
        return "Error obteniendo fecha"

def format_period_display(period_str):
    """Formatea un periodo como '20241' a '2024-1'."""
    if isinstance(period_str, str) and len(period_str) == 5 and period_str.isdigit():
        return f"{period_str[:4]}-{period_str[4]}"
    return period_str

def verify_turnstile_token(turnstile_response_token):
    """
    Verifica el token de Cloudflare Turnstile con la API de Cloudflare.
    Devuelve True si es válido, False en caso contrario.
    """
    if not CLOUDFLARE_TURNSTILE_SECRET_KEY:
        print("ADVERTENCIA: CLOUDFLARE_TURNSTILE_SECRET_KEY no está configurada. En producción, la verificación fallará.")
        # Para desarrollo local sin la clave, podríamos permitir el paso:
        return False 
        #return True # ¡OJO! SOLO PARA DESARROLLO LOCAL. Eliminar o cambiar a False para producción. ¡LEER ESTO POR FAVOR!

    payload = {
        'secret': CLOUDFLARE_TURNSTILE_SECRET_KEY,
        'response': turnstile_response_token,
        # 'remoteip': request.remote_addr # Opcional, pero recomendado.
    }
    try:
        response = requests.post('https://challenges.cloudflare.com/turnstile/v0/siteverify', data=payload, timeout=5)
        response.raise_for_status() 
        result = response.json()
        return result.get('success', False)
    except requests.exceptions.RequestException as e:
        print(f"Error de comunicación al verificar el token de Turnstile: {e}")
        return False

# --- Rutas de la Interfaz y API ---

@app.route('/')
def index():
    """Renderiza la página principal (index.html)."""
    last_updated = get_last_updated_date()
    return render_template('index.html', minerva_ascii_art=MINERVA_ASCII_ART_FOR_WEB, last_updated_date=last_updated)

@app.route('/verify-access', methods=['POST'])
def verify_access():
    """
    Endpoint para verificar el token de Turnstile enviado desde el frontend
    después de que el usuario completa el desafío.
    """
    data = request.get_json()
    turnstile_token = data.get('turnstile_token')

    if not turnstile_token:
        return jsonify({"success": False, "message": "Token de Turnstile no proporcionado."}), 400

    if verify_turnstile_token(turnstile_token):
        return jsonify({"success": True, "message": "Verificación exitosa."})
    else:
        return jsonify({"success": False, "message": "Verificación de Turnstile fallida."}), 403

# --- API Endpoints (actualmente no protegidos por Turnstile en este ejemplo) ---

@app.route('/api/periods')
def get_periods():
    conn = get_db_connection()
    periods_data = conn.execute("SELECT DISTINCT periodo FROM student_results WHERE periodo IS NOT NULL ORDER BY periodo DESC").fetchall()
    conn.close()
    formatted_periods = []
    for row in periods_data:
        raw_period = row['periodo']
        formatted_periods.append({
            'value': raw_period,
            'display': format_period_display(raw_period)
        })
    return jsonify(formatted_periods)

@app.route('/api/departments/<periodo>')
def get_departments_for_period(periodo):
    conn = get_db_connection()
    departments_data = conn.execute("""
        SELECT DISTINCT cole_depto_ubicacion_norm
        FROM student_results
        WHERE periodo = ? AND cole_depto_ubicacion_norm IS NOT NULL AND cole_nombre_establecimiento IS NOT NULL AND cole_nombre_establecimiento != ''
        ORDER BY cole_depto_ubicacion_norm ASC
    """, (periodo,)).fetchall()
    conn.close()
    return jsonify([row['cole_depto_ubicacion_norm'] for row in departments_data])

@app.route('/api/schools/<periodo>/<department_name>')
def get_schools_for_department_period(periodo, department_name):
    top_n_filter = request.args.get('top', type=int, default=0)
    conn = get_db_connection()
    query = """
        SELECT
            cole_nombre_establecimiento, cole_mcpio_ubicacion, cole_naturaleza, cole_calendario, cole_genero,
            AVG(CAST(punt_global AS REAL)) as promedio_global,
            COUNT(id) as num_estudiantes
        FROM student_results
        WHERE periodo = ? AND cole_depto_ubicacion_norm = ? AND cole_nombre_establecimiento IS NOT NULL AND cole_nombre_establecimiento != '' AND punt_global IS NOT NULL
        GROUP BY cole_nombre_establecimiento, cole_mcpio_ubicacion, cole_naturaleza, cole_calendario, cole_genero
        ORDER BY promedio_global DESC
    """
    if top_n_filter > 0: query += f" LIMIT {top_n_filter}"
    schools_data = conn.execute(query, (periodo, department_name)).fetchall()
    conn.close()
    schools_list = []
    for row in schools_data:
        key_parts = [str(row[col] or '') for col in ['cole_nombre_establecimiento', 'cole_mcpio_ubicacion', 'cole_naturaleza', 'cole_calendario']]
        display_parts = [str(row[col] or '') for col in ['cole_nombre_establecimiento', 'cole_mcpio_ubicacion', 'cole_genero', 'cole_naturaleza', 'cole_calendario']]
        school_id_str = "|".join(key_parts)
        display_name_parts = [p for p in display_parts[1:] if p and p.strip()]
        display_name = f"{display_parts[0]} ({' - '.join(display_name_parts)})"
        schools_list.append({
            'id': school_id_str, 'name': display_name, 'raw_name': row['cole_nombre_establecimiento'],
            'mean': row['promedio_global'] if row['promedio_global'] is not None else 0,
            'count': row['num_estudiantes']
        })
    return jsonify(schools_list)

@app.route('/api/school_details/<periodo>/<department_name>/<path:school_id_str>')
def get_school_details(periodo, department_name, school_id_str):
    school_id_parts = school_id_str.split("|")
    if len(school_id_parts) != 4: return jsonify({"error": "Formato de ID de colegio inválido"}), 400
    cole_nombre, cole_mcpio, cole_nat, cole_cal = school_id_parts
    
    conn = get_db_connection()
    student_list_query = f"""
        SELECT estu_fechanacimiento, estu_genero, estu_nacionalidad, punt_global, percentil_global
        FROM student_results
        WHERE periodo = ? AND cole_depto_ubicacion_norm = ? AND cole_nombre_establecimiento = ? 
              AND cole_mcpio_ubicacion = ? AND cole_naturaleza = ? AND cole_calendario = ? AND punt_global IS NOT NULL
        ORDER BY CAST(punt_global AS REAL) DESC
    """
    students_data = conn.execute(student_list_query, (periodo, department_name, cole_nombre, cole_mcpio, cole_nat, cole_cal)).fetchall()
    student_list = [dict(row) for row in students_data]

    benchmarking_results = []
    dept_bench_map, nat_bench_map = defaultdict(dict), defaultdict(float)
    # Usamos las columnas de puntaje para cargar los benchmarks
    dept_bench_data = conn.execute("SELECT materia, promedio FROM departmental_benchmarks WHERE periodo = ? AND departamento = ?", (periodo, department_name)).fetchall()
    for row in dept_bench_data: dept_bench_map[row['materia']] = row['promedio']
    nat_bench_data = conn.execute("SELECT materia, promedio FROM national_benchmarks WHERE periodo = ?", (periodo,)).fetchall()
    for row in nat_bench_data: nat_bench_map[row['materia']] = row['promedio']

    score_display_map_for_details = [('Global', 'punt_global'), ('Matemáticas', 'punt_matematicas'), ('Lectura Crítica', 'punt_lectura_critica'), ('C. Naturales', 'punt_c_naturales'), ('Sociales y Ciu.', 'punt_sociales_ciudadanas'), ('Inglés', 'punt_ingles')]
    
    for display_name, data_key in score_display_map_for_details: # Renombrado para evitar confusión con SCORE_COLUMNS global si se usara directamente aquí
        avg_query = f"""SELECT AVG(CAST("{data_key}" AS REAL)) as promedio FROM student_results
                         WHERE periodo = ? AND cole_depto_ubicacion_norm = ? AND cole_nombre_establecimiento = ? 
                               AND cole_mcpio_ubicacion = ? AND cole_naturaleza = ? AND cole_calendario = ? AND "{data_key}" IS NOT NULL AND "{data_key}" != ''"""
        avg_data = conn.execute(avg_query, (periodo, department_name, cole_nombre, cole_mcpio, cole_nat, cole_cal)).fetchone()
        current_school_avg = avg_data['promedio'] if avg_data and avg_data['promedio'] is not None else 0
        benchmarking_results.append({'subject': display_name, 'school_avg': current_school_avg, 'dept_avg': dept_bench_map.get(data_key, 0), 'nat_avg': nat_bench_map.get(data_key, 0)})
        
    desemp_display_map = [('Lectura Crítica', 'desemp_lectura_critica'), ('Matemáticas', 'desemp_matematicas'), ('C. Naturales', 'desemp_c_naturales'), ('Sociales y Ciu.', 'desemp_sociales_ciudadanas'), ('Inglés', 'desemp_ingles')]
    performance_levels = []
    for display_name, data_key in desemp_display_map:
        levels_query = f"""SELECT "{data_key}" as nivel, COUNT(*) as conteo FROM student_results
                            WHERE periodo = ? AND cole_depto_ubicacion_norm = ? AND cole_nombre_establecimiento = ? 
                                  AND cole_mcpio_ubicacion = ? AND cole_naturaleza = ? AND cole_calendario = ? AND "{data_key}" IS NOT NULL AND "{data_key}" != '' GROUP BY "{data_key}" """
        levels_data = conn.execute(levels_query, (periodo, department_name, cole_nombre, cole_mcpio, cole_nat, cole_cal)).fetchall()
        performance_levels.append({'subject': display_name, 'levels': {row['nivel']: row['conteo'] for row in levels_data}, 'type': 'english' if 'ingles' in data_key else 'standard'})

    histogram_data = [s['punt_global'] for s in student_list if s['punt_global'] is not None]
    
    historical_evolution = []
    current_year_num = int(periodo[:-1])
    current_period_suffix = periodo[-1] 
    periods_to_check_for_history = [f"{year}{current_period_suffix}" for year in range(current_year_num, current_year_num - 6, -1)]
    for p_key in periods_to_check_for_history:
        year_display_for_history = format_period_display(p_key)
        hist_query = f"""SELECT AVG(CAST(punt_global AS REAL)) as promedio_global FROM student_results
                           WHERE periodo = ? AND cole_depto_ubicacion_norm = ? AND cole_nombre_establecimiento = ? 
                                 AND cole_mcpio_ubicacion = ? AND cole_naturaleza = ? AND cole_calendario = ? AND punt_global IS NOT NULL AND punt_global != '' """
        hist_data = conn.execute(hist_query, (p_key, department_name, cole_nombre, cole_mcpio, cole_nat, cole_cal)).fetchone()
        if hist_data and hist_data['promedio_global'] is not None: historical_evolution.append({'periodo': year_display_for_history, 'media': hist_data['promedio_global']})
        else:
            period_exists_check = conn.execute("SELECT 1 FROM national_benchmarks WHERE periodo = ? LIMIT 1", (p_key,)).fetchone()
            if period_exists_check: historical_evolution.append({'periodo': year_display_for_history, 'media': 0}) 
            else: historical_evolution.append({'periodo': year_display_for_history, 'media': -1}) 
    
    cole_genero_data = conn.execute("""SELECT DISTINCT cole_genero FROM student_results WHERE periodo = ? AND cole_nombre_establecimiento = ? 
                                     AND cole_mcpio_ubicacion = ? AND cole_naturaleza = ? AND cole_calendario = ? AND cole_genero IS NOT NULL AND cole_genero != '' LIMIT 1""", 
                                     (periodo, cole_nombre, cole_mcpio, cole_nat, cole_cal)).fetchone()
    cole_genero_display = cole_genero_data['cole_genero'] if cole_genero_data and cole_genero_data['cole_genero'] else ''

    conn.close()
    formatted_period_display = format_period_display(periodo)
    
    return jsonify({
        'school_name_display': f"{cole_nombre} ({cole_mcpio}{' - ' + cole_genero_display if cole_genero_display else ''} - {cole_nat} - {cole_cal}) | {formatted_period_display}",
        'student_list': student_list, 'benchmarks': benchmarking_results, 'performance_levels': performance_levels,
        'histogram_data': histogram_data, 'historical_evolution': historical_evolution
    })

if __name__ == '__main__':
    print("Para ejecutar la aplicación web, use el comando: flask run")
    print(f"Asegúrese de que la base de datos '{DATABASE_NAME}' existe y fue creada con 'create_database.py'.")
    print("Recuerde configurar la variable de entorno CLOUDFLARE_TURNSTILE_SECRET_KEY si desea probar la verificación de Turnstile localmente.")
    # Descomentar para desarrollo directo:
    # app.run(debug=True)