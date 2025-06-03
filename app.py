# app.py - Servidor Principal de Minerva Explorador de ICFES

import sqlite3
import os
from datetime import datetime
from collections import defaultdict
from flask import Flask, jsonify, render_template, request, url_for
import requests # Necesario para la verificación de Turnstile
import configparser

# --- Configuración Global ---
DATABASE_NAME = 'minerva_icfes_data.db'
LAST_UPDATED_FILE = 'minerva_last_updated.txt'
# Definimos las columnas de puntajes principales para referencia y consistencia.
SCORE_COLUMNS = ['punt_global', 'punt_lectura_critica', 'punt_matematicas', 'punt_c_naturales', 'punt_sociales_ciudadanas', 'punt_ingles']
# Columnas de precalculados en school_statistics que corresponden a SCORE_COLUMNS
AVG_SCORE_PRECALCULATED_COLUMNS = {
    'punt_global': 'avg_punt_global',
    'punt_lectura_critica': 'avg_punt_lectura_critica',
    'punt_matematicas': 'avg_punt_matematicas',
    'punt_c_naturales': 'avg_punt_c_naturales',
    'punt_sociales_ciudadanas': 'avg_punt_sociales_ciudadanas',
    'punt_ingles': 'avg_punt_ingles'
}
# --- Cargar Clave Secreta de Cloudflare Turnstile desde Archivo ---
CLOUDFLARE_TURNSTILE_SECRET_KEY = None
SECRET_KEY_FILE_PATH = '/home/Chachalingo/mysite/crypto/.config_secrets.ini'

try:
    config = configparser.ConfigParser()
    if os.path.exists(SECRET_KEY_FILE_PATH) and os.path.getsize(SECRET_KEY_FILE_PATH) > 0:
        config.read(SECRET_KEY_FILE_PATH)
        if 'CLOUDFLARE' in config and 'TURNSTILE_SECRET_KEY' in config['CLOUDFLARE']:
            CLOUDFLARE_TURNSTILE_SECRET_KEY = config['CLOUDFLARE']['TURNSTILE_SECRET_KEY']
            print(f"Clave de Turnstile CARGADA desde: {SECRET_KEY_FILE_PATH}")
        else:
            print(f"ADVERTENCIA: La sección [CLOUDFLARE] o la clave TURNSTILE_SECRET_KEY no se encontró en {SECRET_KEY_FILE_PATH}")
    else:
        print(f"ADVERTENCIA: Archivo de clave secreta no encontrado o vacío en {SECRET_KEY_FILE_PATH}")

except Exception as e:
    print(f"Error al leer el archivo de clave secreta ({SECRET_KEY_FILE_PATH}): {e}")

if not CLOUDFLARE_TURNSTILE_SECRET_KEY:
    print("ADVERTENCIA CRÍTICA: La Secret Key de Cloudflare Turnstile NO ESTÁ CARGADA.")
    print("La verificación de Turnstile probablemente fallará o será insegura si la app continúa.")
    # En un entorno de producción, probablemente querrías que esto fuera un error fatal.
    # raise RuntimeError("Falta la configuración de CLOUDFLARE_TURNSTILE_SECRET_KEY. La aplicación no puede iniciar de forma segura.")


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
    conn.row_factory = sqlite3.Row # Para acceder a las columnas por nombre
    return conn

def get_last_updated_date():
    """Lee la fecha de la última actualización de la BD desde el archivo."""
    try:
        with open(LAST_UPDATED_FILE, 'r', encoding='utf-8') as f:
            return f.read().strip()
    except FileNotFoundError:
        return "Fecha no disponible"
    except Exception as e:
        print(f"Error leyendo fecha de actualización: {e}")
        return "Error obteniendo fecha"

def format_period_display(period_str):
    """Formatea un periodo como '20241' a '2024-1' para mostrarlo más bonito."""
    if isinstance(period_str, str) and len(period_str) == 5 and period_str.isdigit():
        return f"{period_str[:4]}-{period_str[4]}"
    return period_str # Si no cumple el formato, lo devuelve tal cual

def verify_turnstile_token(turnstile_response_token):
    """
    Verifica el token de Cloudflare Turnstile con la API de Cloudflare.
    Devuelve True si es válido, False en caso contrario.
    """
    if not CLOUDFLARE_TURNSTILE_SECRET_KEY:
        print("ADVERTENCIA: CLOUDFLARE_TURNSTILE_SECRET_KEY no está configurada.")
        # Para desarrollo local sin la clave, podríamos permitir el paso, ¡PERO NO EN PRODUCCIÓN!
        return True # ¡OJO! SOLO PARA DESARROLLO LOCAL. CAMBIAR A FALSE PARA PRODUCCIÓN.
        #return False # En producción, la verificación DEBE fallar si no hay clave.

    payload = {
        'secret': CLOUDFLARE_TURNSTILE_SECRET_KEY,
        'response': turnstile_response_token,
        # 'remoteip': request.remote_addr # Opcional, pero recomendado por Cloudflare.
    }
    try:
        print("Enviando token de Turnstile para verificación...")
        response = requests.post('https://challenges.cloudflare.com/turnstile/v0/siteverify', data=payload, timeout=10) # Aumenté el timeout
        response.raise_for_status() # Lanza un error si la respuesta HTTP es 4xx o 5xx
        result = response.json()
        print(f"Respuesta de Turnstile: {result}")
        return result.get('success', False)
    except requests.exceptions.RequestException as e:
        print(f"Error de comunicación al verificar el token de Turnstile: {e}")
        return False
    except Exception as e_json: # Por si la respuesta no es JSON o hay otro error
        print(f"Error procesando la respuesta de Turnstile: {e_json}")
        return False


# --- Rutas de la Interfaz y API ---

@app.route('/')
def index():
    """Renderiza la página principal (index.html)."""
    last_updated = get_last_updated_date()
    # El ASCII art y la fecha de actualización se pasan al template
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
        # Podríamos querer dar un mensaje más genérico en producción
        return jsonify({"success": False, "message": "Falló la verificación de seguridad. Intenta recargar la página."}), 403


@app.route('/api/periods')
def get_periods():
    conn = get_db_connection()
    # Podemos consultar periodos de cualquier tabla que los tenga, como national_benchmarks o school_statistics
    # Usar school_statistics podría ser más representativo de los datos efectivamente procesados.
    periods_data = conn.execute("SELECT DISTINCT periodo FROM school_statistics WHERE periodo IS NOT NULL ORDER BY periodo DESC").fetchall()
    if not periods_data: # Fallback por si school_statistics está vacío pero student_results no
        periods_data = conn.execute("SELECT DISTINCT periodo FROM student_results WHERE periodo IS NOT NULL ORDER BY periodo DESC").fetchall()
    conn.close()

    formatted_periods = []
    for row in periods_data:
        raw_period = str(row['periodo']) # Aseguramos que sea string
        formatted_periods.append({
            'value': raw_period,
            'display': format_period_display(raw_period)
        })
    return jsonify(formatted_periods)

@app.route('/api/departments/<periodo>')
def get_departments_for_period(periodo):
    conn = get_db_connection()
    # Usamos school_statistics ya que tiene los deptos normalizados y asociados a colegios con datos.
    departments_data = conn.execute("""
        SELECT DISTINCT cole_depto_ubicacion_norm
        FROM school_statistics
        WHERE periodo = ? AND cole_depto_ubicacion_norm IS NOT NULL AND cole_nombre_establecimiento IS NOT NULL AND TRIM(cole_nombre_establecimiento) != ''
        ORDER BY cole_depto_ubicacion_norm ASC
    """, (periodo,)).fetchall()
    conn.close()
    return jsonify([row['cole_depto_ubicacion_norm'] for row in departments_data])


@app.route('/api/schools/<periodo>/<department_name>')
def get_schools_for_department_period(periodo, department_name):
    top_n_filter = request.args.get('top', type=int, default=0) # Para mostrar "Top N" colegios
    conn = get_db_connection()

    # MODIFICADO: Query a school_statistics y se añade rank_departmental y rank_national
    # El cole_genero se trae con un LEFT JOIN a una subconsulta de student_results.
    # Esto asume que cole_genero es relativamente constante para un colegio.
    # Si cole_genero se agregara a school_statistics, este JOIN no sería necesario.
    query_parts = [
        "SELECT",
        "    ss.cole_nombre_establecimiento,",
        "    ss.cole_mcpio_ubicacion,",
        "    ss.cole_naturaleza,",
        "    ss.cole_calendario,",
        "    ss.cole_depto_ubicacion_norm, -- Incluido para claridad, aunque ya se filtra por él",
        "    COALESCE(sr_distinct.cole_genero, '') as cole_genero, -- Tomar cole_genero si existe",
        "    ss.avg_punt_global as promedio_global,",
        "    ss.student_count as num_estudiantes,",
        "    ss.rank_departmental,      -- Nueva columna de ranking",
        "    ss.rank_national           -- Nueva columna de ranking",
        "FROM school_statistics ss",
        "LEFT JOIN (",
        "    SELECT DISTINCT",
        "        cole_nombre_establecimiento, cole_mcpio_ubicacion, cole_naturaleza, cole_calendario, periodo, cole_depto_ubicacion_norm, cole_genero",
        "    FROM student_results",
        "    WHERE cole_genero IS NOT NULL AND TRIM(cole_genero) != ''",
        ") sr_distinct ON ss.cole_nombre_establecimiento = sr_distinct.cole_nombre_establecimiento",
        "           AND ss.cole_mcpio_ubicacion = sr_distinct.cole_mcpio_ubicacion",
        "           AND ss.cole_naturaleza = sr_distinct.cole_naturaleza",
        "           AND ss.cole_calendario = sr_distinct.cole_calendario",
        "           AND ss.periodo = sr_distinct.periodo",
        "           AND ss.cole_depto_ubicacion_norm = sr_distinct.cole_depto_ubicacion_norm",
        "WHERE ss.periodo = ? AND ss.cole_depto_ubicacion_norm = ?",
        "      AND ss.cole_nombre_establecimiento IS NOT NULL AND TRIM(ss.cole_nombre_establecimiento) != ''",
        "      AND ss.avg_punt_global IS NOT NULL", # Solo colegios con promedio calculado
        "ORDER BY ss.avg_punt_global DESC"
    ]

    if top_n_filter > 0:
        query_parts.append(f"LIMIT {top_n_filter}")

    query = "\n".join(query_parts)
    schools_data = conn.execute(query, (periodo, department_name)).fetchall()
    conn.close()

    schools_list = []
    for row in schools_data:
        # El ID del colegio se construye con estos 5 campos para ser único (incluyendo depto)
        key_parts = [
            str(row['cole_nombre_establecimiento'] or ''),
            str(row['cole_mcpio_ubicacion'] or ''),
            str(row['cole_naturaleza'] or ''),
            str(row['cole_calendario'] or ''),
            str(row['cole_depto_ubicacion_norm'] or '') # Añadido para unicidad del ID
        ]
        school_id_str = "|".join(key_parts)

        # Para mostrar el nombre del colegio
        display_parts = [
            str(row['cole_nombre_establecimiento'] or ''),
            str(row['cole_mcpio_ubicacion'] or ''),
            str(row['cole_genero'] or ''), # Viene del JOIN
            str(row['cole_naturaleza'] or ''),
            str(row['cole_calendario'] or '')
        ]
        # Construir el nombre a mostrar, omitiendo partes vacías
        display_name_parts = [p for p in display_parts[1:] if p and p.strip()] # Empezar desde municipio
        display_name = f"{display_parts[0]} ({' - '.join(display_name_parts)})"

        schools_list.append({
            'id': school_id_str,
            'name': display_name, # Nombre formateado para mostrar
            'raw_name': row['cole_nombre_establecimiento'], # Nombre crudo para búsquedas
            'mean': row['promedio_global'] if row['promedio_global'] is not None else 0,
            'count': row['num_estudiantes'],
            'rank_departmental': row['rank_departmental'], # Nuevo campo
            'rank_national': row['rank_national']        # Nuevo campo
        })
    return jsonify(schools_list)


@app.route('/api/school_details/<periodo>/<department_name_param>/<path:school_id_str>')
def get_school_details(periodo, department_name_param, school_id_str):
    # school_id_str ahora contiene 5 partes: nombre, mcpio, nat, cal, depto_norm_colegio
    school_id_parts = school_id_str.split("|")
    if len(school_id_parts) != 5:
        return jsonify({"error": "Formato de ID de colegio inválido. Se esperaban 5 partes."}), 400
    cole_nombre, cole_mcpio, cole_nat, cole_cal, cole_depto_colegio_norm = school_id_parts

    # department_name_param es el departamento seleccionado en el filtro,
    # cole_depto_colegio_norm es el departamento real del colegio según la BD. Deberían coincidir.
    # Usaremos cole_depto_colegio_norm para las búsquedas específicas del colegio.

    conn = get_db_connection()

    # 1. Lista de Estudiantes (sigue viniendo de student_results)
    # Filtrar por cole_depto_ubicacion_norm del colegio específico.
    student_list_query = f"""
        SELECT estu_fechanacimiento, estu_genero, estu_nacionalidad, punt_global, percentil_global
        FROM student_results
        WHERE periodo = ? AND cole_depto_ubicacion_norm = ? AND cole_nombre_establecimiento = ?
              AND cole_mcpio_ubicacion = ? AND cole_naturaleza = ? AND cole_calendario = ?
              AND punt_global IS NOT NULL AND TRIM(punt_global) != ''
        ORDER BY CAST(punt_global AS REAL) DESC
    """
    students_data = conn.execute(student_list_query, (periodo, cole_depto_colegio_norm, cole_nombre, cole_mcpio, cole_nat, cole_cal)).fetchall()
    student_list = [dict(row) for row in students_data]

    # 2. Resultados de Benchmarking (Promedios del colegio desde school_statistics)
    benchmarking_results = []
    # Los benchmarks departamentales y nacionales se obtienen igual, pero el departamental usa el depto del colegio.
    dept_bench_map = defaultdict(float) # Usar float para evitar errores si no hay datos
    nat_bench_map = defaultdict(float)

    dept_bench_data = conn.execute("SELECT materia, promedio FROM departmental_benchmarks WHERE periodo = ? AND departamento = ?", (periodo, cole_depto_colegio_norm)).fetchall()
    for row in dept_bench_data: dept_bench_map[row['materia']] = row['promedio']

    nat_bench_data = conn.execute("SELECT materia, promedio FROM national_benchmarks WHERE periodo = ?", (periodo,)).fetchall()
    for row in nat_bench_data: nat_bench_map[row['materia']] = row['promedio']

    # MODIFICADO: Obtener promedios del colegio y rankings desde school_statistics
    # La PK de school_statistics ahora incluye cole_depto_ubicacion_norm
    school_stats_query = f"""
        SELECT {', '.join(AVG_SCORE_PRECALCULATED_COLUMNS.values())},
               rank_departmental, rank_national, student_count
        FROM school_statistics
        WHERE periodo = ? AND cole_nombre_establecimiento = ?
              AND cole_mcpio_ubicacion = ? AND cole_naturaleza = ? AND cole_calendario = ?
              AND cole_depto_ubicacion_norm = ?
    """
    school_avg_scores_row = conn.execute(school_stats_query, (periodo, cole_nombre, cole_mcpio, cole_nat, cole_cal, cole_depto_colegio_norm)).fetchone()

    # Mapeo para mostrar nombres amigables y acceder a las columnas correctas
    score_display_map_for_details = [
        ('Global', 'punt_global'), ('Matemáticas', 'punt_matematicas'),
        ('Lectura Crítica', 'punt_lectura_critica'), ('C. Naturales', 'punt_c_naturales'),
        ('Sociales y Ciu.', 'punt_sociales_ciudadanas'), ('Inglés', 'punt_ingles')
    ]

    if school_avg_scores_row:
        for display_name, original_score_key in score_display_map_for_details:
            precalculated_col_name = AVG_SCORE_PRECALCULATED_COLUMNS.get(original_score_key)
            current_school_avg = school_avg_scores_row[precalculated_col_name] if precalculated_col_name and school_avg_scores_row[precalculated_col_name] is not None else 0
            benchmarking_results.append({
                'subject': display_name,
                'school_avg': current_school_avg,
                'dept_avg': dept_bench_map.get(original_score_key, 0), # Clave original para benchmarks
                'nat_avg': nat_bench_map.get(original_score_key, 0)
            })
    else: # Si no hay datos en school_statistics para este colegio (debería ser raro)
        print(f"ADVERTENCIA: No se encontraron estadísticas precalculadas para {cole_nombre} en periodo {periodo}, depto {cole_depto_colegio_norm}")
        for display_name, original_score_key in score_display_map_for_details:
             benchmarking_results.append({'subject': display_name, 'school_avg': 0, 'dept_avg': dept_bench_map.get(original_score_key, 0), 'nat_avg': nat_bench_map.get(original_score_key, 0)})


    # 3. Niveles de Desempeño (desde school_performance_levels)
    # La PK de school_performance_levels ahora incluye cole_depto_ubicacion_norm
    desemp_display_map_for_levels = [
        ('Lectura Crítica', 'lectura_critica'), ('Matemáticas', 'matematicas'),
        ('C. Naturales', 'c_naturales'), ('Sociales y Ciu.', 'sociales_ciudadanas'),
        ('Inglés', 'ingles')
    ]
    performance_levels = []
    for display_name, materia_key_in_table in desemp_display_map_for_levels:
        levels_query = """
            SELECT nivel, count
            FROM school_performance_levels
            WHERE periodo = ? AND cole_nombre_establecimiento = ?
                  AND cole_mcpio_ubicacion = ? AND cole_naturaleza = ? AND cole_calendario = ?
                  AND cole_depto_ubicacion_norm = ? AND materia = ?
        """
        levels_data = conn.execute(levels_query, (periodo, cole_nombre, cole_mcpio, cole_nat, cole_cal, cole_depto_colegio_norm, materia_key_in_table)).fetchall()
        performance_levels.append({
            'subject': display_name,
            'levels': {row['nivel']: row['count'] for row in levels_data},
            'type': 'english' if 'ingles' == materia_key_in_table else 'standard'
        })

    # 4. Datos del Histograma (sigue de student_list)
    histogram_data = [s['punt_global'] for s in student_list if s['punt_global'] is not None]

    # 5. Evolución Histórica (desde school_statistics avg_punt_global)
    # La PK de school_statistics ahora incluye cole_depto_ubicacion_norm
    historical_evolution = []
    try:
        current_year_num = int(periodo[:-1]) # Asume formato AAAA S
        current_period_suffix = periodo[-1]
        periods_to_check_for_history = [f"{year}{current_period_suffix}" for year in range(current_year_num, current_year_num - 6, -1)]

        for p_key in periods_to_check_for_history:
            year_display_for_history = format_period_display(p_key)
            hist_query = """
                SELECT avg_punt_global
                FROM school_statistics
                WHERE periodo = ? AND cole_nombre_establecimiento = ?
                      AND cole_mcpio_ubicacion = ? AND cole_naturaleza = ? AND cole_calendario = ?
                      AND cole_depto_ubicacion_norm = ?
            """
            hist_data_row = conn.execute(hist_query, (p_key, cole_nombre, cole_mcpio, cole_nat, cole_cal, cole_depto_colegio_norm)).fetchone()

            if hist_data_row and hist_data_row['avg_punt_global'] is not None:
                historical_evolution.append({'periodo': year_display_for_history, 'media': hist_data_row['avg_punt_global']})
            else:
                period_exists_check = conn.execute("SELECT 1 FROM national_benchmarks WHERE periodo = ? LIMIT 1", (p_key,)).fetchone()
                if period_exists_check:
                    historical_evolution.append({'periodo': year_display_for_history, 'media': 0}) # Colegio no encontrado o sin datos para ese periodo
                else:
                    historical_evolution.append({'periodo': year_display_for_history, 'media': -1})# El periodo en sí no existe en el sistema
    except ValueError:
        print(f"Error parseando el periodo '{periodo}' para la evolución histórica.")
        # Dejar historical_evolution vacío o con un mensaje de error
        pass


    # Para el nombre a mostrar en el detalle del colegio, tomamos el cole_genero de student_results (si existe)
    # Esto podría mejorarse si cole_genero fuera parte de school_statistics.
    cole_genero_data = conn.execute("""
        SELECT DISTINCT cole_genero FROM student_results
        WHERE periodo = ? AND cole_nombre_establecimiento = ?
              AND cole_mcpio_ubicacion = ? AND cole_naturaleza = ? AND cole_calendario = ?
              AND cole_depto_ubicacion_norm = ?
              AND cole_genero IS NOT NULL AND TRIM(cole_genero) != ''
        LIMIT 1
    """, (periodo, cole_nombre, cole_mcpio, cole_nat, cole_cal, cole_depto_colegio_norm)).fetchone()
    cole_genero_display = cole_genero_data['cole_genero'] if cole_genero_data and cole_genero_data['cole_genero'] else ''

    conn.close()
    formatted_period_display_for_header = format_period_display(periodo)
    
    # Nombre base del colegio para el display
    school_name_base_for_display = f"{cole_nombre} ({cole_mcpio}{' - ' + cole_genero_display if cole_genero_display else ''} - {cole_nat} - {cole_cal}) | {formatted_period_display_for_header}"

    return jsonify({
        'school_name_display': school_name_base_for_display, # Nombre para el encabezado
        'rank_departmental': school_avg_scores_row['rank_departmental'] if school_avg_scores_row else None,
        'rank_national': school_avg_scores_row['rank_national'] if school_avg_scores_row else None,
        'student_list': student_list,
        'benchmarks': benchmarking_results,
        'performance_levels': performance_levels,
        'histogram_data': histogram_data,
        'historical_evolution': historical_evolution
    })

if __name__ == '__main__':
    print("Para ejecutar la aplicación web en desarrollo local, usa el comando: flask --app app --debug run")
    print(f"Asegúrate de que la base de datos '{DATABASE_NAME}' existe y fue creada/actualizada con la última versión de 'create_database.py'.")
    print("Si estás en producción (ej. PythonAnywhere), la configuración del servidor WSGI se encargará de esto.")
    # Para desarrollo directo, podrías usar:
    # app.run(debug=True)
    # Pero `flask run` es preferido.