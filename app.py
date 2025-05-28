# app.py (Updated for historical evolution)

import sqlite3
from flask import Flask, jsonify, render_template, request
from collections import defaultdict
import statistics 
import os
import difflib 
from datetime import datetime

DATABASE_NAME = 'minerva_icfes_data.db'
LAST_UPDATED_FILE = 'minerva_last_updated.txt'
SCORE_COLUMNS = ['punt_global', 'punt_lectura_critica', 'punt_matematicas', 'punt_c_naturales', 'punt_sociales_ciudadanas', 'punt_ingles']
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

def get_db_connection():
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row 
    return conn

def get_last_updated_date():
    try:
        with open(LAST_UPDATED_FILE, 'r', encoding='utf-8') as f:
            return f.read().strip()
    except FileNotFoundError:
        return "Fecha no disponible" # Should be created by create_database.py
    except Exception:
        return "Error obteniendo fecha"

@app.route('/')
def index():
    last_updated = get_last_updated_date()
    return render_template('index.html', minerva_ascii_art=MINERVA_ASCII_ART_FOR_WEB, last_updated_date=last_updated)

@app.route('/api/periods')
def get_periods():
    conn = get_db_connection()
    periods_data = conn.execute("SELECT DISTINCT periodo FROM student_results WHERE periodo IS NOT NULL ORDER BY periodo DESC").fetchall()
    conn.close()
    return jsonify([row['periodo'] for row in periods_data])

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
    # Ensure CAST is used for punt_global if it's TEXT in DB, though create_database.py should make it INTEGER/REAL
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
        display_name_parts = [p for p in display_parts[1:] if p and p.strip()] # Collect non-empty parts for details
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
    # Ensure CAST is used for punt_global if it's TEXT in DB
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
    dept_bench_data = conn.execute("SELECT materia, promedio FROM departmental_benchmarks WHERE periodo = ? AND departamento = ?", (periodo, department_name)).fetchall()
    for row in dept_bench_data: dept_bench_map[row['materia']] = row['promedio']
    nat_bench_data = conn.execute("SELECT materia, promedio FROM national_benchmarks WHERE periodo = ?", (periodo,)).fetchall()
    for row in nat_bench_data: nat_bench_map[row['materia']] = row['promedio']

    score_display_map = [('Global', 'punt_global'), ('Matemáticas', 'punt_matematicas'), ('Lectura Crítica', 'punt_lectura_critica'), ('C. Naturales', 'punt_c_naturales'), ('Sociales y Ciu.', 'punt_sociales_ciudadanas'), ('Inglés', 'punt_ingles')]
    for display_name, data_key in score_display_map:
        # Ensure CAST is used for data_key if it's TEXT in DB
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
    current_period_suffix = periodo[-1] # e.g., "1" or "2"

    # MODIFIED: Include current year in historical evolution
    periods_to_check_for_history = [f"{year}{current_period_suffix}" for year in range(current_year_num, current_year_num - 6, -1)]

    for p_key in periods_to_check_for_history:
        year_display_for_history = f"{p_key[:-1]}-{p_key[-1]}" # For display like "2024-1"
        
        hist_query = f"""SELECT AVG(CAST(punt_global AS REAL)) as promedio_global FROM student_results
                         WHERE periodo = ? AND cole_depto_ubicacion_norm = ? AND cole_nombre_establecimiento = ? 
                               AND cole_mcpio_ubicacion = ? AND cole_naturaleza = ? AND cole_calendario = ? AND punt_global IS NOT NULL AND punt_global != '' """
        hist_data = conn.execute(hist_query, (p_key, department_name, cole_nombre, cole_mcpio, cole_nat, cole_cal)).fetchone()
        
        if hist_data and hist_data['promedio_global'] is not None:
            historical_evolution.append({'periodo': year_display_for_history, 'media': hist_data['promedio_global']})
        else:
            period_exists_check = conn.execute("SELECT 1 FROM national_benchmarks WHERE periodo = ? LIMIT 1", (p_key,)).fetchone()
            if period_exists_check:
                 historical_evolution.append({'periodo': year_display_for_history, 'media': 0}) 
            else:
                 historical_evolution.append({'periodo': year_display_for_history, 'media': -1}) 
    
    cole_genero_data = conn.execute("""SELECT DISTINCT cole_genero FROM student_results WHERE periodo = ? AND cole_nombre_establecimiento = ? 
                                    AND cole_mcpio_ubicacion = ? AND cole_naturaleza = ? AND cole_calendario = ? AND cole_genero IS NOT NULL AND cole_genero != '' LIMIT 1""", 
                                    (periodo, cole_nombre, cole_mcpio, cole_nat, cole_cal)).fetchone()
    cole_genero_display = cole_genero_data['cole_genero'] if cole_genero_data and cole_genero_data['cole_genero'] else ''

    conn.close()
    return jsonify({
        'school_name_display': f"{cole_nombre} ({cole_mcpio}{' - ' + cole_genero_display if cole_genero_display else ''} - {cole_nat} - {cole_cal}) | {periodo}",
        'student_list': student_list, 'benchmarks': benchmarking_results, 'performance_levels': performance_levels,
        'histogram_data': histogram_data, 'historical_evolution': historical_evolution
    })

if __name__ == '__main__':
    print("Para ejecutar la aplicación web, use el comando: flask run")
    print(f"Asegúrese de que la base de datos '{DATABASE_NAME}' existe y fue creada con 'create_database.py'.")
    # app.run(debug=True) # Descomentar para desarrollo directo con 'python app.py'