# app.py - Servidor Principal de Minerva Explorador de ICFES

import sqlite3
import os
from datetime import datetime
from collections import defaultdict
from flask import Flask, jsonify, render_template, request, url_for # Ensure 'request' is here
import requests # Necesario para la verificación de Turnstile
import configparser
from urllib.parse import unquote

# 'thefuzz' ya no se usa aquí, la búsqueda será en el frontend
# from thefuzz import fuzz
# from thefuzz import process as fuzz_process

# --- Configuración Global ---
DATABASE_NAME = 'minerva_icfes_data.db'
LAST_UPDATED_FILE = 'minerva_last_updated.txt'
SCORE_COLUMNS = ['punt_global', 'punt_lectura_critica', 'punt_matematicas', 'punt_c_naturales', 'punt_sociales_ciudadanas', 'punt_ingles']
AVG_SCORE_PRECALCULATED_COLUMNS = {
    'punt_global': 'avg_punt_global',
    'punt_lectura_critica': 'avg_punt_lectura_critica',
    'punt_matematicas': 'avg_punt_matematicas',
    'punt_c_naturales': 'avg_punt_c_naturales',
    'punt_sociales_ciudadanas': 'avg_punt_sociales_ciudadanas',
    'punt_ingles': 'avg_punt_ingles'
}

# --- Cargar Clave Secreta de Cloudflare Turnstile ---
CLOUDFLARE_TURNSTILE_SECRET_KEY = None
SECRET_KEY_FILE_PATH = '/home/Chachalingo/mysite/crypto/.config_secrets.ini' # Ruta de PythonAnywhere
if not os.path.exists(SECRET_KEY_FILE_PATH) and 'PYTHONANYWHERE_DOMAIN' not in os.environ :
    SECRET_KEY_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.config_secrets.ini')

try:
    config = configparser.ConfigParser()
    if os.path.exists(SECRET_KEY_FILE_PATH) and os.path.getsize(SECRET_KEY_FILE_PATH) > 0:
        config.read(SECRET_KEY_FILE_PATH)
        if 'CLOUDFLARE' in config and 'TURNSTILE_SECRET_KEY' in config['CLOUDFLARE']:
            CLOUDFLARE_TURNSTILE_SECRET_KEY = config['CLOUDFLARE']['TURNSTILE_SECRET_KEY']
    else:
        print(f"ADVERTENCIA: Archivo de clave secreta no encontrado o vacío en {SECRET_KEY_FILE_PATH}")
except Exception as e:
    print(f"Error al leer el archivo de clave secreta ({SECRET_KEY_FILE_PATH}): {e}")

if not CLOUDFLARE_TURNSTILE_SECRET_KEY:
    print("ADVERTENCIA CRÍTICA: La Secret Key de Cloudflare Turnstile NO ESTÁ CARGADA.")


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
░░░░░░░░░░░░░▓░▓█████▒░▒░▒ ▒▒▒▒░▒░ ░░▒▒▒▒▒▒░░░███▓░▓▓▒▒█▒▒░▒▒▒░░░░░░▒▒▒▒▓██▓▓▓███
░░░░░░░░░░░▒▓▒▓▒█░▓▓▓█▓▓▓▒▒░░░▒█▓▒░░░░░░░░░░▓██▓▒▓▓▓▒▒█▓░░░░▒▒░░░░░░░▒▒▓▓███▓▓▓█▓
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
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def get_last_updated_date():
    try:
        with open(LAST_UPDATED_FILE, 'r', encoding='utf-8') as f: return f.read().strip()
    except FileNotFoundError: return "Fecha no disponible"
    except Exception as e: print(f"Error leyendo fecha: {e}"); return "Error"

def format_period_display(period_str):
    if isinstance(period_str, str) and len(period_str) == 5 and period_str.isdigit():
        return f"{period_str[:4]}-{period_str[4]}"
    return period_str

def verify_turnstile_token(turnstile_response_token):
    if not CLOUDFLARE_TURNSTILE_SECRET_KEY: return True # No verificar si no hay clave
    payload = {'secret': CLOUDFLARE_TURNSTILE_SECRET_KEY, 'response': turnstile_response_token}
    try:
        response = requests.post('https://challenges.cloudflare.com/turnstile/v0/siteverify', data=payload, timeout=10)
        response.raise_for_status()
        return response.json().get('success', False)
    except Exception as e: print(f"Error Turnstile: {e}"); return False

# --- Rutas ---
@app.route('/')
def index():
    return render_template('index.html', minerva_ascii_art=MINERVA_ASCII_ART_FOR_WEB, last_updated_date=get_last_updated_date())

@app.route('/verify-access', methods=['POST'])
def verify_access():
    data = request.get_json(); token = data.get('turnstile_token')
    if not token: return jsonify({"success": False, "message": "Token no provisto."}), 400
    if verify_turnstile_token(token): return jsonify({"success": True, "message": "OK."})
    else: return jsonify({"success": False, "message": "Verificación fallida."}), 403

@app.route('/api/periods')
def get_periods():
    conn = get_db_connection()
    data = conn.execute("SELECT DISTINCT periodo FROM school_statistics ORDER BY periodo DESC").fetchall()
    if not data: data = conn.execute("SELECT DISTINCT periodo FROM student_results ORDER BY periodo DESC").fetchall()
    conn.close()
    return jsonify([{'value': str(r['periodo']), 'display': format_period_display(str(r['periodo']))} for r in data])

@app.route('/api/departments/<periodo>')
def get_departments_for_period(periodo):
    conn = get_db_connection()
    data = conn.execute("SELECT DISTINCT cole_depto_ubicacion_norm FROM school_statistics WHERE periodo = ? AND cole_depto_ubicacion_norm IS NOT NULL ORDER BY cole_depto_ubicacion_norm ASC", (periodo,)).fetchall()
    conn.close()
    return jsonify([r['cole_depto_ubicacion_norm'] for r in data])

@app.route('/api/schools/<periodo>/<department_name>')
def get_schools_for_department_period(periodo, department_name):
    conn = get_db_connection()

    page = request.args.get('page', 1, type=int)
    # Use a larger per_page for initial load if desired, or keep consistent
    per_page = request.args.get('per_page', 100, type=int) # Default 100 schools per chunk
    offset = (page - 1) * per_page

    # Query to get total count of unique schools for the given filters
    # The unique identifier for a school in school_statistics seems to be the combination used in its PRIMARY KEY
    count_query_sql = """
        SELECT COUNT(*) as total_count
        FROM school_statistics ss
        WHERE ss.periodo = ? AND ss.cole_depto_ubicacion_norm = ?
              AND ss.cole_nombre_establecimiento IS NOT NULL AND TRIM(ss.cole_nombre_establecimiento) != ''
              AND ss.avg_punt_global IS NOT NULL
    """
    total_count_result = conn.execute(count_query_sql, (periodo, department_name)).fetchone()
    total_count = total_count_result['total_count'] if total_count_result else 0
    
    total_pages = (total_count + per_page - 1) // per_page if per_page > 0 else 0


    select_cols = """
        ss.cole_nombre_establecimiento, ss.cole_mcpio_ubicacion, ss.cole_naturaleza,
        ss.cole_calendario, ss.cole_depto_ubicacion_norm,
        COALESCE(sr_distinct.cole_genero, '') as cole_genero, /* Ensure this join is efficient or consider removing if not critical for list */
        ss.avg_punt_global as promedio_global,
        ss.student_count as num_estudiantes,
        ss.rank_departmental, ss.rank_national
    """
    # The join for cole_genero might be slow if sr_distinct is large and not well-indexed for this join.
    # For a paginated list, consider if cole_genero is essential for the list view or can be fetched on detail view.
    # If it is kept, ensure relevant columns in student_results are indexed.
    join_for_genero = """
    LEFT JOIN (
        SELECT DISTINCT cole_nombre_establecimiento, cole_mcpio_ubicacion, cole_naturaleza,
                        cole_calendario, periodo, cole_depto_ubicacion_norm, cole_genero
        FROM student_results WHERE cole_genero IS NOT NULL AND TRIM(cole_genero) != ''
    ) sr_distinct ON ss.cole_nombre_establecimiento = sr_distinct.cole_nombre_establecimiento
               AND ss.cole_mcpio_ubicacion = sr_distinct.cole_mcpio_ubicacion
               AND ss.cole_naturaleza = sr_distinct.cole_naturaleza
               AND ss.cole_calendario = sr_distinct.cole_calendario
               AND ss.periodo = sr_distinct.periodo
               AND ss.cole_depto_ubicacion_norm = sr_distinct.cole_depto_ubicacion_norm
    """
    query_sql = f"""
        SELECT {select_cols} FROM school_statistics ss {join_for_genero}
        WHERE ss.periodo = ? AND ss.cole_depto_ubicacion_norm = ?
              AND ss.cole_nombre_establecimiento IS NOT NULL AND TRIM(ss.cole_nombre_establecimiento) != ''
              AND ss.avg_punt_global IS NOT NULL
        ORDER BY ss.avg_punt_global DESC
        LIMIT ? OFFSET ?
    """
    all_schools_rows = conn.execute(query_sql, (periodo, department_name, per_page, offset)).fetchall()
    conn.close()

    schools_list = []
    for row_data in all_schools_rows:
        row = dict(row_data)
        # Define school_id based on the primary key of school_statistics for consistency
        key_parts = [
            str(row.get('cole_nombre_establecimiento', '')),
            str(row.get('cole_mcpio_ubicacion', '')),
            str(row.get('cole_naturaleza', '')),
            str(row.get('cole_calendario', '')),
            str(row.get('cole_depto_ubicacion_norm', '')) # Department is part of the key
        ]
        school_id_str = "|".join(key_parts)

        display_parts = [
            str(row.get('cole_nombre_establecimiento', '')),
            str(row.get('cole_mcpio_ubicacion', '')),
            str(row.get('cole_genero', '')), # This comes from the potentially slow join
            str(row.get('cole_naturaleza', '')),
            str(row.get('cole_calendario', ''))
        ]
        display_name_parts = [p for p in display_parts[1:] if p and p.strip()] # Start from municipio
        display_name = f"{display_parts[0]} ({' - '.join(display_name_parts)})"

        schools_list.append({
            'id': school_id_str,
            'name': display_name, # This is the descriptive name for display
            'raw_name': row.get('cole_nombre_establecimiento', ''), # For searching
            'mean': row.get('promedio_global', 0) if row.get('promedio_global') is not None else 0,
            'count': row.get('num_estudiantes', 0),
            'rank_departmental': row.get('rank_departmental'),
            'rank_national': row.get('rank_national')
        })

    return jsonify({
        'schools': schools_list,
        'total_count': total_count,
        'page': page,
        'per_page': per_page,
        'total_pages': total_pages
    })


@app.route('/api/school_details/<periodo>/<department_name_param>/<path:school_id_str>')
def get_school_details(periodo, department_name_param, school_id_str):
    try:
        school_id_str = unquote(school_id_str)
        print(f"Received school details request: periodo={periodo}, dept={department_name_param}, school_id='{school_id_str}'")
        
        school_id_parts = school_id_str.split("|")
        if len(school_id_parts) != 5:
            print(f"Invalid school ID format: {school_id_str}. Parts: {school_id_parts}")
            return jsonify({"error": f"ID de colegio inválido. Formato incorrecto. Partes recibidas: {len(school_id_parts)}"}), 400
        
        cole_nombre, cole_mcpio, cole_nat, cole_cal, cole_depto_colegio_norm = school_id_parts
        
        print(f"Parsed ID: nombre='{cole_nombre}', mcpio='{cole_mcpio}', nat='{cole_nat}', cal='{cole_cal}', depto_colegio='{cole_depto_colegio_norm}'")

        conn = get_db_connection()
        
        # Verify school exists in student_results to ensure there's data to show
        # Note: cole_depto_ubicacion_norm in student_results should match cole_depto_colegio_norm from the ID
        verify_query = """
        SELECT COUNT(id) as count 
        FROM student_results 
        WHERE periodo = ? 
        AND cole_depto_ubicacion_norm = ?  /* This is the department of the school's location */
        AND cole_nombre_establecimiento = ?
        AND cole_mcpio_ubicacion = ? 
        AND cole_naturaleza = ? 
        AND cole_calendario = ?
        """
        verify_result = conn.execute(verify_query, (periodo, cole_depto_colegio_norm, cole_nombre, cole_mcpio, cole_nat, cole_cal)).fetchone()
        
        if verify_result is None or verify_result['count'] == 0:
            # Fallback: Check school_statistics if student_results somehow missed it (should not happen if DB is consistent)
            verify_stats_query = """
            SELECT COUNT(*) as count FROM school_statistics 
            WHERE periodo = ? AND cole_depto_ubicacion_norm = ? AND cole_nombre_establecimiento = ? 
            AND cole_mcpio_ubicacion = ? AND cole_naturaleza = ? AND cole_calendario = ?
            """
            verify_stats_result = conn.execute(verify_stats_query, (periodo, cole_depto_colegio_norm, cole_nombre, cole_mcpio, cole_nat, cole_cal)).fetchone()
            if verify_stats_result is None or verify_stats_result['count'] == 0:
                 print(f"No students or stats found for school: P={periodo}, D={cole_depto_colegio_norm}, N={cole_nombre}, M={cole_mcpio}, NAT={cole_nat}, CAL={cole_cal}")
                 return jsonify({"error": f"No se encontraron datos para el colegio: {cole_nombre} ({cole_mcpio})"}), 404

        student_list_q = """SELECT estu_fechanacimiento, estu_genero, estu_nacionalidad, punt_global, percentil_global
            FROM student_results WHERE periodo = ? AND cole_depto_ubicacion_norm = ? AND cole_nombre_establecimiento = ?
            AND cole_mcpio_ubicacion = ? AND cole_naturaleza = ? AND cole_calendario = ? AND punt_global IS NOT NULL
            ORDER BY CAST(punt_global AS REAL) DESC"""
        students_data = conn.execute(student_list_q, (periodo, cole_depto_colegio_norm, cole_nombre, cole_mcpio, cole_nat, cole_cal)).fetchall()
        student_list = [dict(r) for r in students_data]
        
        bench_res, d_bench, n_bench = [], defaultdict(float), defaultdict(float)
        # Department benchmark should use cole_depto_colegio_norm which is the school's actual department
        for r in conn.execute("SELECT materia, promedio FROM departmental_benchmarks WHERE periodo = ? AND departamento = ?", (periodo, cole_depto_colegio_norm)).fetchall(): 
            d_bench[r['materia']] = r['promedio']
        for r in conn.execute("SELECT materia, promedio FROM national_benchmarks WHERE periodo = ?", (periodo,)).fetchall(): 
            n_bench[r['materia']] = r['promedio']
        
        s_stats_cols = ', '.join(AVG_SCORE_PRECALCULATED_COLUMNS.values()) + ", rank_departmental, rank_national" # Add ranks here
        s_stats_q = f"SELECT {s_stats_cols} FROM school_statistics WHERE periodo = ? AND cole_nombre_establecimiento = ? AND cole_mcpio_ubicacion = ? AND cole_naturaleza = ? AND cole_calendario = ? AND cole_depto_ubicacion_norm = ?"
        s_avg_row = conn.execute(s_stats_q, (periodo, cole_nombre, cole_mcpio, cole_nat, cole_cal, cole_depto_colegio_norm)).fetchone()

        s_disp_map = [('Global', 'punt_global'), ('Matemáticas', 'punt_matematicas'), ('Lectura Crítica', 'punt_lectura_critica'), ('C. Naturales', 'punt_c_naturales'), ('Sociales y Ciu.', 'punt_sociales_ciudadanas'), ('Inglés', 'punt_ingles')]
        if s_avg_row:
            for disp_n, orig_k in s_disp_map:
                precalc_col = AVG_SCORE_PRECALCULATED_COLUMNS.get(orig_k)
                avg = s_avg_row[precalc_col] if precalc_col and s_avg_row[precalc_col] is not None else 0
                bench_res.append({'subject': disp_n, 'school_avg': avg, 'dept_avg': d_bench.get(orig_k,0), 'nat_avg': n_bench.get(orig_k,0)})
        else:
            print(f"No statistics row found for school: {cole_nombre} in school_statistics. This is unexpected.")
            # Fallback or default values if school_statistics entry is missing (should not happen with consistent DB)
            for disp_n, orig_k in s_disp_map: 
                bench_res.append({'subject': disp_n, 'school_avg': 0, 'dept_avg': d_bench.get(orig_k,0), 'nat_avg': n_bench.get(orig_k,0)})


        desemp_map = [('Lectura Crítica', 'lectura_critica'), ('Matemáticas', 'matematicas'), ('C. Naturales', 'c_naturales'), ('Sociales y Ciu.', 'sociales_ciudadanas'), ('Inglés', 'ingles')]
        perf_levels = []
        for disp_n, mat_k in desemp_map:
            lvl_q = "SELECT nivel, count FROM school_performance_levels WHERE periodo = ? AND cole_nombre_establecimiento = ? AND cole_mcpio_ubicacion = ? AND cole_naturaleza = ? AND cole_calendario = ? AND cole_depto_ubicacion_norm = ? AND materia = ?"
            lvl_data = conn.execute(lvl_q, (periodo, cole_nombre, cole_mcpio, cole_nat, cole_cal, cole_depto_colegio_norm, mat_k)).fetchall()
            perf_levels.append({'subject': disp_n, 'levels': {r['nivel']: r['count'] for r in lvl_data}, 'type': 'english' if 'ingles' == mat_k else 'standard'})
        
        hist_data_scores = [s['punt_global'] for s in student_list if s['punt_global'] is not None] # Renamed to avoid conflict
        hist_evo = []
        try:
            # Ensure periodo is a string like "20231"
            periodo_str = str(periodo)
            curr_y, curr_p_sfx = int(periodo_str[:-1]), periodo_str[-1]
            for yr_offset in range(6): # Look back up to 5 previous equivalent periods
                prev_yr = curr_y - yr_offset
                yr_key = f"{prev_yr}{curr_p_sfx}"
                yr_disp = format_period_display(yr_key)
                
                h_q = "SELECT avg_punt_global FROM school_statistics WHERE periodo = ? AND cole_nombre_establecimiento = ? AND cole_mcpio_ubicacion = ? AND cole_naturaleza = ? AND cole_calendario = ? AND cole_depto_ubicacion_norm = ?"
                h_row = conn.execute(h_q, (yr_key, cole_nombre, cole_mcpio, cole_nat, cole_cal, cole_depto_colegio_norm)).fetchone()
                
                if h_row and h_row['avg_punt_global'] is not None: 
                    hist_evo.append({'periodo': yr_disp, 'media': h_row['avg_punt_global']})
                else:
                    # Check if the period generally exists in the database to differentiate "No data for this school" vs "Period doesn't exist"
                    p_exists_q = "SELECT 1 FROM national_benchmarks WHERE periodo = ? LIMIT 1"
                    p_exists = conn.execute(p_exists_q, (yr_key,)).fetchone()
                    hist_evo.append({'periodo': yr_disp, 'media': 0 if p_exists else -1}) # 0 for "N/D Colegio", -1 for "N/D Periodo"
        except ValueError as e: 
            print(f"Error parsing period for historical evolution: {periodo_str} - {e}")
            # Add a placeholder if period parsing fails
            hist_evo.append({'periodo': format_period_display(periodo_str), 'media': -1})


        c_gen_row = conn.execute("SELECT DISTINCT cole_genero FROM student_results WHERE periodo = ? AND cole_nombre_establecimiento = ? AND cole_mcpio_ubicacion = ? AND cole_naturaleza = ? AND cole_calendario = ? AND cole_depto_ubicacion_norm = ? AND cole_genero IS NOT NULL AND TRIM(cole_genero) != '' LIMIT 1", (periodo, cole_nombre, cole_mcpio, cole_nat, cole_cal, cole_depto_colegio_norm)).fetchone()
        c_gen_disp = c_gen_row['cole_genero'] if c_gen_row and c_gen_row['cole_genero'] else ''
        conn.close()
        
        s_name_disp = f"{cole_nombre} ({cole_mcpio}{(' - ' + c_gen_disp) if c_gen_disp else ''} - {cole_nat} - {cole_cal}) | {format_period_display(str(periodo))}"
        
        rank_dept_val = s_avg_row['rank_departmental'] if s_avg_row and s_avg_row['rank_departmental'] is not None else None
        rank_nat_val = s_avg_row['rank_national'] if s_avg_row and s_avg_row['rank_national'] is not None else None

        return jsonify({
            'school_name_display': s_name_disp,
            'rank_departmental': rank_dept_val,
            'rank_national': rank_nat_val,
            'student_list': student_list,
            'benchmarks': bench_res,
            'performance_levels': perf_levels,
            'histogram_data': hist_data_scores, # Use the renamed variable
            'historical_evolution': sorted(hist_evo, key=lambda x: x['periodo']) # Sort by period for chart
        })
    except Exception as e:
        print(f"Error in get_school_details: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Error interno del servidor: {str(e)}"}), 500


if __name__ == '__main__':
    print("Para ejecutar la aplicación: flask --app app --debug run")
    print(f"BD: '{DATABASE_NAME}'. Asegúrate que exista y esté actualizada con 'create_database.py'.")