# app.py

import sqlite3
from flask import Flask, jsonify, render_template
from collections import defaultdict
import statistics # Still needed for some school-level calculations if not pre-calculated fully
import os
import difflib # For fuzzy search of school names

SCORE_COLUMNS = ['punt_global', 'punt_lectura_critica', 'punt_matematicas', 'punt_c_naturales', 'punt_sociales_ciudadanas', 'punt_ingles']

# --- Configuration ---
DATABASE_NAME = 'icfes_data.db'

app = Flask(__name__)

# --- Helper Function to Connect to Database ---
def get_db_connection():
    """Establishes a connection to the SQLite database."""
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row # Allows accessing columns by name
    return conn

# --- API Endpoints to Provide Data to the Frontend ---

@app.route('/')
def index():
    """Render the main HTML page."""
    # The ASCII art could be passed here if you want to display it on the webpage too
    # For now, the HTML will handle its own title.
    return render_template('index.html')

@app.route('/api/periods')
def get_periods():
    """Provide a sorted list of all unique periodos from the database."""
    conn = get_db_connection()
    periods_data = conn.execute("SELECT DISTINCT periodo FROM student_results ORDER BY periodo DESC").fetchall()
    conn.close()
    periods = [row['periodo'] for row in periods_data]
    return jsonify(periods)

@app.route('/api/departments/<periodo>')
def get_departments_for_period(periodo):
    """Provide a sorted list of department names for a given periodo that have schools."""
    conn = get_db_connection()
    # We use cole_depto_ubicacion_norm as this is what schools are grouped by for display
    departments_data = conn.execute("""
        SELECT DISTINCT cole_depto_ubicacion_norm 
        FROM student_results 
        WHERE periodo = ? AND cole_depto_ubicacion_norm IS NOT NULL AND cole_nombre_establecimiento IS NOT NULL
        ORDER BY cole_depto_ubicacion_norm ASC
    """, (periodo,)).fetchall()
    conn.close()
    departments = [row['cole_depto_ubicacion_norm'] for row in departments_data]
    return jsonify(departments)

@app.route('/api/schools/<periodo>/<department_name>')
def get_schools_for_department_period(periodo, department_name):
    """Provide a ranked list of schools for a given department and periodo."""
    conn = get_db_connection()
    # Note: The unique school key in the DB might need reconstruction if we didn't store it directly.
    # For simplicity, we'll group by all components of the school's unique ID.
    # The 'id' for the frontend will be these components joined by '|'.
    schools_data = conn.execute("""
        SELECT 
            cole_nombre_establecimiento,
            cole_mcpio_ubicacion,
            cole_naturaleza,
            cole_calendario,
            AVG(punt_global) as promedio_global,
            COUNT(id) as num_estudiantes
        FROM student_results
        WHERE periodo = ? AND cole_depto_ubicacion_norm = ? 
              AND cole_nombre_establecimiento IS NOT NULL
        GROUP BY cole_nombre_establecimiento, cole_mcpio_ubicacion, cole_naturaleza, cole_calendario
        ORDER BY promedio_global DESC
    """, (periodo, department_name)).fetchall()
    conn.close()
    
    schools_list = []
    for row in schools_data:
        school_key_tuple = (row['cole_nombre_establecimiento'], row['cole_mcpio_ubicacion'], row['cole_naturaleza'], row['cole_calendario'])
        school_id_str = "|".join(filter(None, school_key_tuple)) # Filter out None before joining
        schools_list.append({
            'id': school_id_str,
            'name': f"{row['cole_nombre_establecimiento']} ({row['cole_mcpio_ubicacion']} - {row['cole_naturaleza']} - {row['cole_calendario']})",
            'raw_name': row['cole_nombre_establecimiento'], # For fuzzy search
            'mean': row['promedio_global'] if row['promedio_global'] is not None else 0,
            'count': row['num_estudiantes']
        })
    return jsonify(schools_list)

@app.route('/api/school_details/<periodo>/<department_name>/<path:school_id_str>')
def get_school_details(periodo, department_name, school_id_str):
    """Provide the full, comprehensive analysis for a single school for a given period."""
    # Decode the string ID back into the tuple key components
    # The school_id_str is URL encoded, Flask handles decoding it.
    # school_id_parts will be [name, municipality, nature, calendar]
    school_id_parts = school_id_str.split("|")
    if len(school_id_parts) != 4:
        return jsonify({"error": "Invalid school identifier format"}), 400

    cole_nombre, cole_mcpio, cole_nat, cole_cal = school_id_parts
    
    conn = get_db_connection()

    # 1. Get student list for this school and period
    student_list_query = f"""
        SELECT estu_fechanacimiento, estu_genero, estu_nacionalidad, punt_global, percentil_global
        FROM student_results
        WHERE periodo = ? 
          AND cole_depto_ubicacion_norm = ?
          AND cole_nombre_establecimiento = ?
          AND cole_mcpio_ubicacion = ?
          AND cole_naturaleza = ?
          AND cole_calendario = ?
        ORDER BY punt_global DESC
    """
    students_data = conn.execute(student_list_query, (periodo, department_name, cole_nombre, cole_mcpio, cole_nat, cole_cal)).fetchall()
    student_list = [dict(row) for row in students_data]

    # 2. Get school average scores for subjects
    school_averages = {}
    for materia in SCORE_COLUMNS: # SCORE_COLUMNS defined in create_database.py, redefine here or pass
        score_cols_for_sql = ['punt_global', 'punt_lectura_critica', 'punt_matematicas', 'punt_c_naturales', 'punt_sociales_ciudadanas', 'punt_ingles']
        avg_query = f"""
            SELECT AVG({materia}) as promedio
            FROM student_results
            WHERE periodo = ? AND cole_depto_ubicacion_norm = ?
              AND cole_nombre_establecimiento = ? AND cole_mcpio_ubicacion = ?
              AND cole_naturaleza = ? AND cole_calendario = ? AND {materia} IS NOT NULL
        """
        avg_data = conn.execute(avg_query, (periodo, department_name, cole_nombre, cole_mcpio, cole_nat, cole_cal)).fetchone()
        school_averages[materia] = avg_data['promedio'] if avg_data and avg_data['promedio'] is not None else 0

    # 3. Get benchmark data (departmental and national)
    benchmarking_results = []
    dept_bench_map = defaultdict(dict)
    nat_bench_map = defaultdict(float)

    dept_bench_data = conn.execute("SELECT materia, promedio FROM departmental_benchmarks WHERE periodo = ? AND departamento = ?", (periodo, department_name)).fetchall()
    for row in dept_bench_data: dept_bench_map[row['materia']] = row['promedio']
    
    nat_bench_data = conn.execute("SELECT materia, promedio FROM national_benchmarks WHERE periodo = ?", (periodo,)).fetchall()
    for row in nat_bench_data: nat_bench_map[row['materia']] = row['promedio']

    score_display_map = [
        ('Global', 'punt_global'), ('Matemáticas', 'punt_matematicas'), ('Lectura Crítica', 'punt_lectura_critica'),
        ('C. Naturales', 'punt_c_naturales'), ('Sociales y Ciu.', 'punt_sociales_ciudadanas'), ('Inglés', 'punt_ingles')
    ]
    for display_name, data_key in score_display_map:
        benchmarking_results.append({
            'subject': display_name,
            'school_avg': school_averages.get(data_key, 0),
            'dept_avg': dept_bench_map.get(data_key, 0),
            'nat_avg': nat_bench_map.get(data_key, 0)
        })
        
    # 4. Performance Levels
    desemp_cols = ['desemp_lectura_critica', 'desemp_matematicas', 'desemp_c_naturales', 'desemp_sociales_ciudadanas', 'desemp_ingles']
    desemp_display_map = [
        ('Lectura Crítica', 'desemp_lectura_critica'), ('Matemáticas', 'desemp_matematicas'),
        ('C. Naturales', 'desemp_c_naturales'), ('Sociales y Ciu.', 'desemp_sociales_ciudadanas'), ('Inglés', 'desemp_ingles')
    ]
    performance_levels = []
    for display_name, data_key in desemp_display_map:
        levels_query = f"""
            SELECT {data_key} as nivel, COUNT(*) as conteo
            FROM student_results
            WHERE periodo = ? AND cole_depto_ubicacion_norm = ?
              AND cole_nombre_establecimiento = ? AND cole_mcpio_ubicacion = ?
              AND cole_naturaleza = ? AND cole_calendario = ? AND {data_key} IS NOT NULL
            GROUP BY {data_key}
        """
        levels_data = conn.execute(levels_query, (periodo, department_name, cole_nombre, cole_mcpio, cole_nat, cole_cal)).fetchall()
        levels_dict = {row['nivel']: row['conteo'] for row in levels_data}
        performance_levels.append({'subject': display_name, 'levels': levels_dict, 'type': 'english' if 'ingles' in data_key else 'standard'})

    # 5. Histogram data (just global scores)
    histogram_data = [s['punt_global'] for s in student_list if s['punt_global'] is not None]
    
    # 6. Historical data
    historical_evolution = []
    current_year_num = int(periodo[:-1]) # "20241" -> 2024
    for i in range(1, 6): # Look back 5 years
        prev_year_num = current_year_num - i
        # Assuming we only care about the first period ('1') of previous years for historical comparison
        prev_periodo_key = f"{prev_year_num}1" 
        
        hist_query = f"""
            SELECT AVG(punt_global) as promedio_global
            FROM student_results
            WHERE periodo = ? AND cole_depto_ubicacion_norm = ? 
              AND cole_nombre_establecimiento = ? AND cole_mcpio_ubicacion = ?
              AND cole_naturaleza = ? AND cole_calendario = ? AND punt_global IS NOT NULL
        """
        hist_data = conn.execute(hist_query, (prev_periodo_key, department_name, cole_nombre, cole_mcpio, cole_nat, cole_cal)).fetchone()
        
        if hist_data and hist_data['promedio_global'] is not None:
            historical_evolution.append({'periodo': f"{prev_year_num}-1", 'media': hist_data['promedio_global']})
        else:
            # Check if data for that period exists at all to differentiate
            period_exists_check = conn.execute("SELECT 1 FROM national_benchmarks WHERE periodo = ? LIMIT 1", (prev_periodo_key,)).fetchone()
            if period_exists_check:
                 historical_evolution.append({'periodo': f"{prev_year_num}-1", 'media': 0}) # School not found or no data
            else:
                 historical_evolution.append({'periodo': f"{prev_year_num}-1", 'media': -1}) # Period data not available


    conn.close()

    return jsonify({
        'school_name_display': f"{cole_nombre} ({cole_mcpio} - {cole_nat} - {cole_cal}) | {periodo}",
        'student_list': student_list,
        'benchmarks': benchmarking_results,
        'performance_levels': performance_levels,
        'histogram_data': histogram_data,
        'historical_evolution': historical_evolution
    })


if __name__ == '__main__':
    # Make sure an 'instance' folder exists for SQLite if running in certain environments
    # For development, SQLite will create the .db file in the current directory
    # os.makedirs(os.path.join(app.instance_path, 'db'), exist_ok=True) 
    print("Para ejecutar la aplicación web, use el comando: flask run")
    print(f"Asegúrese de que la base de datos '{DATABASE_NAME}' existe en este directorio y fue creada con 'create_database.py'.")
    # To run directly for development:
    # app.run(debug=True)