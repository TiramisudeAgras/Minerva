# app.py

import sqlite3
from flask import Flask, jsonify, render_template, request
from collections import defaultdict
import statistics 
import os
import difflib 

DATABASE_NAME = 'minerva_icfes_data.db'
SCORE_COLUMNS = ['punt_global', 'punt_lectura_critica', 'punt_matematicas', 'punt_c_naturales', 'punt_sociales_ciudadanas', 'punt_ingles']

app = Flask(__name__)

def get_db_connection():
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row 
    return conn

@app.route('/')
def index():
    return render_template('index.html')

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
        WHERE periodo = ? AND cole_depto_ubicacion_norm IS NOT NULL AND cole_nombre_establecimiento IS NOT NULL
        ORDER BY cole_depto_ubicacion_norm ASC
    """, (periodo,)).fetchall()
    conn.close()
    return jsonify([row['cole_depto_ubicacion_norm'] for row in departments_data])

@app.route('/api/schools/<periodo>/<department_name>')
def get_schools_for_department_period(periodo, department_name):
    top_n_filter = request.args.get('top', type=int, default=0) # For Top N feature

    conn = get_db_connection()
    query = """
        SELECT 
            cole_nombre_establecimiento, cole_mcpio_ubicacion, cole_naturaleza, cole_calendario, cole_genero,
            AVG(CAST(punt_global AS REAL)) as promedio_global,
            COUNT(id) as num_estudiantes
        FROM student_results
        WHERE periodo = ? AND cole_depto_ubicacion_norm = ? AND cole_nombre_establecimiento IS NOT NULL AND punt_global IS NOT NULL
        GROUP BY cole_nombre_establecimiento, cole_mcpio_ubicacion, cole_naturaleza, cole_calendario, cole_genero
        ORDER BY promedio_global DESC
    """
    if top_n_filter > 0:
        query += f" LIMIT {top_n_filter}"
        
    schools_data = conn.execute(query, (periodo, department_name)).fetchall()
    conn.close()
    
    schools_list = []
    for row in schools_data:
        # Filter out None values before joining for school_id_str and display name
        key_parts = [
            row['cole_nombre_establecimiento'],
            row['cole_mcpio_ubicacion'],
            row['cole_naturaleza'],
            row['cole_calendario']
        ]
        display_parts = [
            row['cole_nombre_establecimiento'],
            row['cole_mcpio_ubicacion'],
            row['cole_genero'], # Include gender in display name
            row['cole_naturaleza'],
            row['cole_calendario']
        ]

        school_id_str = "|".join(str(p) for p in key_parts if p is not None)
        display_name = f"{display_parts[0]} ({' - '.join(str(p) for p in display_parts[1:] if p is not None)})"
        
        schools_list.append({
            'id': school_id_str,
            'name': display_name,
            'raw_name': row['cole_nombre_establecimiento'],
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

    school_averages = {}
    for materia in SCORE_COLUMNS:
        avg_query = f"""
            SELECT AVG(CAST("{materia}" AS REAL)) as promedio
            FROM student_results
            WHERE periodo = ? AND cole_depto_ubicacion_norm = ? AND cole_nombre_establecimiento = ? 
                  AND cole_mcpio_ubicacion = ? AND cole_naturaleza = ? AND cole_calendario = ? AND "{materia}" IS NOT NULL
        """
        avg_data = conn.execute(avg_query, (periodo, department_name, cole_nombre, cole_mcpio, cole_nat, cole_cal)).fetchone()
        school_averages[materia] = avg_data['promedio'] if avg_data and avg_data['promedio'] is not None else 0

    benchmarking_results = []
    dept_bench_map, nat_bench_map = defaultdict(dict), defaultdict(float)
    dept_bench_data = conn.execute("SELECT materia, promedio FROM departmental_benchmarks WHERE periodo = ? AND departamento = ?", (periodo, department_name)).fetchall()
    for row in dept_bench_data: dept_bench_map[row['materia']] = row['promedio']
    nat_bench_data = conn.execute("SELECT materia, promedio FROM national_benchmarks WHERE periodo = ?", (periodo,)).fetchall()
    for row in nat_bench_data: nat_bench_map[row['materia']] = row['promedio']

    score_display_map = [('Global', 'punt_global'), ('Matemáticas', 'punt_matematicas'), ('Lectura Crítica', 'punt_lectura_critica'), ('C. Naturales', 'punt_c_naturales'), ('Sociales y Ciu.', 'punt_sociales_ciudadanas'), ('Inglés', 'punt_ingles')]
    for display_name, data_key in score_display_map:
        benchmarking_results.append({'subject': display_name, 'school_avg': school_averages.get(data_key, 0), 'dept_avg': dept_bench_map.get(data_key, 0), 'nat_avg': nat_bench_map.get(data_key, 0)})
        
    desemp_display_map = [('Lectura Crítica', 'desemp_lectura_critica'), ('Matemáticas', 'desemp_matematicas'), ('C. Naturales', 'desemp_c_naturales'), ('Sociales y Ciu.', 'desemp_sociales_ciudadanas'), ('Inglés', 'desemp_ingles')]
    performance_levels = []
    for display_name, data_key in desemp_display_map:
        levels_query = f"""
            SELECT "{data_key}" as nivel, COUNT(*) as conteo FROM student_results
            WHERE periodo = ? AND cole_depto_ubicacion_norm = ? AND cole_nombre_establecimiento = ? 
                  AND cole_mcpio_ubicacion = ? AND cole_naturaleza = ? AND cole_calendario = ? AND "{data_key}" IS NOT NULL
            GROUP BY "{data_key}"
        """
        levels_data = conn.execute(levels_query, (periodo, department_name, cole_nombre, cole_mcpio, cole_nat, cole_cal)).fetchall()
        performance_levels.append({'subject': display_name, 'levels': {row['nivel']: row['conteo'] for row in levels_data}, 'type': 'english' if 'ingles' in data_key else 'standard'})

    histogram_data = [s['punt_global'] for s in student_list if s['punt_global'] is not None]
    
    historical_evolution = []
    current_year_num = int(periodo[:-1])
    for i in range(1, 6):
        prev_year_num = current_year_num - i
        prev_periodo_key = f"{prev_year_num}1" 
        hist_query = f"""
            SELECT AVG(CAST(punt_global AS REAL)) as promedio_global FROM student_results
            WHERE periodo = ? AND cole_depto_ubicacion_norm = ? AND cole_nombre_establecimiento = ? 
                  AND cole_mcpio_ubicacion = ? AND cole_naturaleza = ? AND cole_calendario = ? AND punt_global IS NOT NULL
        """
        hist_data = conn.execute(hist_query, (prev_periodo_key, department_name, cole_nombre, cole_mcpio, cole_nat, cole_cal)).fetchone()
        if hist_data and hist_data['promedio_global'] is not None:
            historical_evolution.append({'periodo': f"{prev_year_num}-1", 'media': hist_data['promedio_global']})
        else:
            period_exists_check = conn.execute("SELECT 1 FROM national_benchmarks WHERE periodo = ? LIMIT 1", (prev_periodo_key,)).fetchone()
            historical_evolution.append({'periodo': f"{prev_year_num}-1", 'media': 0 if period_exists_check else -1})
    
    cole_genero_data = conn.execute("""SELECT DISTINCT cole_genero FROM student_results WHERE periodo = ? 
                                    AND cole_nombre_establecimiento = ? AND cole_mcpio_ubicacion = ? 
                                    AND cole_naturaleza = ? AND cole_calendario = ? LIMIT 1""", 
                                    (periodo, cole_nombre, cole_mcpio, cole_nat, cole_cal)).fetchone()
    cole_genero_display = cole_genero_data['cole_genero'] if cole_genero_data else ''


    conn.close()
    return jsonify({
        'school_name_display': f"{cole_nombre} ({cole_mcpio} - {cole_genero_display} - {cole_nat} - {cole_cal}) | {periodo}",
        'student_list': student_list,
        'benchmarks': benchmarking_results,
        'performance_levels': performance_levels,
        'histogram_data': histogram_data,
        'historical_evolution': historical_evolution
    })

if __name__ == '__main__':
    print("Para ejecutar la aplicación web, use el comando: flask run")
    print(f"Asegúrese de que la base de datos '{DATABASE_NAME}' existe y fue creada con 'create_database.py'.")
    # Para desarrollo, puede habilitar app.run(debug=True)
    # app.run(host='0.0.0.0', port=5000, debug=True)