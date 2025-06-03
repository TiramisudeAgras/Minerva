# app.py - Servidor Principal de Minerva Explorador de ICFES

import sqlite3
import os
from datetime import datetime
from collections import defaultdict
from flask import Flask, jsonify, render_template, request, url_for
import requests # Necesario para la verificación de Turnstile
import configparser

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
# TOP_N_DEFAULT ya no se usa aquí para la lista de colegios, el frontend mostrará su Top 50 inicial

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
    # El parámetro 'q' para búsqueda ya no se usa aquí, la búsqueda es frontend
    # El parámetro 'top' tampoco, el frontend mostrará su Top 50 inicial

    conn = get_db_connection()
    select_cols = """
        ss.cole_nombre_establecimiento, ss.cole_mcpio_ubicacion, ss.cole_naturaleza, 
        ss.cole_calendario, ss.cole_depto_ubicacion_norm,
        COALESCE(sr_distinct.cole_genero, '') as cole_genero,
        ss.avg_punt_global as promedio_global,
        ss.student_count as num_estudiantes,
        ss.rank_departmental, ss.rank_national
    """
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
    # Traer TODOS los colegios del departamento/periodo, ordenados por promedio global
    # El frontend se encargará de mostrar el Top 50 inicial y de la búsqueda/filtrado.
    query_sql = f"""
        SELECT {select_cols} FROM school_statistics ss {join_for_genero}
        WHERE ss.periodo = ? AND ss.cole_depto_ubicacion_norm = ?
              AND ss.cole_nombre_establecimiento IS NOT NULL AND TRIM(ss.cole_nombre_establecimiento) != ''
              AND ss.avg_punt_global IS NOT NULL 
        ORDER BY ss.avg_punt_global DESC
    """
    all_schools_rows = conn.execute(query_sql, (periodo, department_name)).fetchall()
    conn.close()

    schools_list = []
    for row_data in all_schools_rows:
        row = dict(row_data) 
        key_parts = [
            str(row.get('cole_nombre_establecimiento', '')), str(row.get('cole_mcpio_ubicacion', '')),
            str(row.get('cole_naturaleza', '')), str(row.get('cole_calendario', '')),
            str(row.get('cole_depto_ubicacion_norm', ''))
        ]
        school_id_str = "|".join(key_parts)
        display_parts = [
            str(row.get('cole_nombre_establecimiento', '')), str(row.get('cole_mcpio_ubicacion', '')),
            str(row.get('cole_genero', '')), str(row.get('cole_naturaleza', '')),
            str(row.get('cole_calendario', ''))
        ]
        display_name_parts = [p for p in display_parts[1:] if p and p.strip()]
        display_name = f"{display_parts[0]} ({' - '.join(display_name_parts)})"
        schools_list.append({
            'id': school_id_str, 'name': display_name,
            'raw_name': row.get('cole_nombre_establecimiento', ''), # Importante para la búsqueda en frontend
            'mean': row.get('promedio_global', 0) if row.get('promedio_global') is not None else 0,
            'count': row.get('num_estudiantes', 0),
            'rank_departmental': row.get('rank_departmental'),
            'rank_national': row.get('rank_national')
        })
    return jsonify(schools_list)


@app.route('/api/school_details/<periodo>/<department_name_param>/<path:school_id_str>')
def get_school_details(periodo, department_name_param, school_id_str):
    # Esta función no cambia su lógica fundamental, sigue trayendo detalles de un colegio específico.
    school_id_parts = school_id_str.split("|")
    if len(school_id_parts) != 5: return jsonify({"error": "ID de colegio inválido."}), 400
    cole_nombre, cole_mcpio, cole_nat, cole_cal, cole_depto_colegio_norm = school_id_parts
    conn = get_db_connection()
    student_list_q = """SELECT estu_fechanacimiento, estu_genero, estu_nacionalidad, punt_global, percentil_global
        FROM student_results WHERE periodo = ? AND cole_depto_ubicacion_norm = ? AND cole_nombre_establecimiento = ?
        AND cole_mcpio_ubicacion = ? AND cole_naturaleza = ? AND cole_calendario = ? AND punt_global IS NOT NULL
        ORDER BY CAST(punt_global AS REAL) DESC"""
    students_data = conn.execute(student_list_q, (periodo, cole_depto_colegio_norm, cole_nombre, cole_mcpio, cole_nat, cole_cal)).fetchall()
    student_list = [dict(r) for r in students_data]
    bench_res, d_bench, n_bench = [], defaultdict(float), defaultdict(float)
    for r in conn.execute("SELECT materia, promedio FROM departmental_benchmarks WHERE periodo = ? AND departamento = ?", (periodo, cole_depto_colegio_norm)).fetchall(): d_bench[r['materia']] = r['promedio']
    for r in conn.execute("SELECT materia, promedio FROM national_benchmarks WHERE periodo = ?", (periodo,)).fetchall(): n_bench[r['materia']] = r['promedio']
    
    s_stats_cols = ', '.join(AVG_SCORE_PRECALCULATED_COLUMNS.values())
    s_stats_q = f"SELECT {s_stats_cols}, rank_departmental, rank_national FROM school_statistics WHERE periodo = ? AND cole_nombre_establecimiento = ? AND cole_mcpio_ubicacion = ? AND cole_naturaleza = ? AND cole_calendario = ? AND cole_depto_ubicacion_norm = ?"
    s_avg_row = conn.execute(s_stats_q, (periodo, cole_nombre, cole_mcpio, cole_nat, cole_cal, cole_depto_colegio_norm)).fetchone()

    s_disp_map = [('Global', 'punt_global'), ('Matemáticas', 'punt_matematicas'), ('Lectura Crítica', 'punt_lectura_critica'), ('C. Naturales', 'punt_c_naturales'), ('Sociales y Ciu.', 'punt_sociales_ciudadanas'), ('Inglés', 'punt_ingles')]
    if s_avg_row:
        for disp_n, orig_k in s_disp_map:
            precalc_col = AVG_SCORE_PRECALCULATED_COLUMNS.get(orig_k)
            avg = s_avg_row[precalc_col] if precalc_col and s_avg_row[precalc_col] is not None else 0
            bench_res.append({'subject': disp_n, 'school_avg': avg, 'dept_avg': d_bench.get(orig_k,0), 'nat_avg': n_bench.get(orig_k,0)})
    else:
        for disp_n, orig_k in s_disp_map: bench_res.append({'subject': disp_n, 'school_avg': 0, 'dept_avg': d_bench.get(orig_k,0), 'nat_avg': n_bench.get(orig_k,0)})

    desemp_map = [('Lectura Crítica', 'lectura_critica'), ('Matemáticas', 'matematicas'), ('C. Naturales', 'c_naturales'), ('Sociales y Ciu.', 'sociales_ciudadanas'), ('Inglés', 'ingles')]
    perf_levels = []
    for disp_n, mat_k in desemp_map:
        lvl_q = "SELECT nivel, count FROM school_performance_levels WHERE periodo = ? AND cole_nombre_establecimiento = ? AND cole_mcpio_ubicacion = ? AND cole_naturaleza = ? AND cole_calendario = ? AND cole_depto_ubicacion_norm = ? AND materia = ?"
        lvl_data = conn.execute(lvl_q, (periodo, cole_nombre, cole_mcpio, cole_nat, cole_cal, cole_depto_colegio_norm, mat_k)).fetchall()
        perf_levels.append({'subject': disp_n, 'levels': {r['nivel']: r['count'] for r in lvl_data}, 'type': 'english' if 'ingles' == mat_k else 'standard'})
    
    hist_data = [s['punt_global'] for s in student_list if s['punt_global'] is not None]
    hist_evo = []
    try:
        curr_y, curr_p_sfx = int(periodo[:-1]), periodo[-1]
        for yr_key in [f"{y}{curr_p_sfx}" for y in range(curr_y, curr_y - 6, -1)]:
            yr_disp = format_period_display(yr_key)
            h_q = "SELECT avg_punt_global FROM school_statistics WHERE periodo = ? AND cole_nombre_establecimiento = ? AND cole_mcpio_ubicacion = ? AND cole_naturaleza = ? AND cole_calendario = ? AND cole_depto_ubicacion_norm = ?"
            h_row = conn.execute(h_q, (yr_key, cole_nombre, cole_mcpio, cole_nat, cole_cal, cole_depto_colegio_norm)).fetchone()
            if h_row and h_row['avg_punt_global'] is not None: hist_evo.append({'periodo': yr_disp, 'media': h_row['avg_punt_global']})
            else:
                p_exists = conn.execute("SELECT 1 FROM national_benchmarks WHERE periodo = ? LIMIT 1", (yr_key,)).fetchone()
                hist_evo.append({'periodo': yr_disp, 'media': 0 if p_exists else -1})
    except ValueError: pass # Si hay error parseando el periodo
    
    c_gen_row = conn.execute("SELECT DISTINCT cole_genero FROM student_results WHERE periodo = ? AND cole_nombre_establecimiento = ? AND cole_mcpio_ubicacion = ? AND cole_naturaleza = ? AND cole_calendario = ? AND cole_depto_ubicacion_norm = ? AND cole_genero IS NOT NULL AND TRIM(cole_genero) != '' LIMIT 1", (periodo, cole_nombre, cole_mcpio, cole_nat, cole_cal, cole_depto_colegio_norm)).fetchone()
    c_gen_disp = c_gen_row['cole_genero'] if c_gen_row and c_gen_row['cole_genero'] else ''
    conn.close()
    
    s_name_disp = f"{cole_nombre} ({cole_mcpio}{' - ' + c_gen_disp if c_gen_disp else ''} - {cole_nat} - {cole_cal}) | {format_period_display(periodo)}"
    return jsonify({
        'school_name_display': s_name_disp,
        'rank_departmental': s_avg_row['rank_departmental'] if s_avg_row else None,
        'rank_national': s_avg_row['rank_national'] if s_avg_row else None,
        'student_list': student_list, 'benchmarks': bench_res, 'performance_levels': perf_levels,
        'histogram_data': hist_data, 'historical_evolution': hist_evo
    })

if __name__ == '__main__':
    print("Para ejecutar la aplicación: flask --app app --debug run")
    print(f"BD: '{DATABASE_NAME}'. Asegúrate que exista y esté actualizada con 'create_database.py'.")
    