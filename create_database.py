# create_database.py (Corrected f-string syntax)

import csv
import sqlite3
import glob
import os
from collections import defaultdict
import statistics

# --- Configuration ---
DATABASE_NAME = 'minerva_icfes_data.db'
COLUMNS_TO_IMPORT = [
    'periodo', 'estu_consecutivo', 'estu_genero', 'estu_nacionalidad',
    'estu_fechanacimiento', 'cole_depto_ubicacion', 'cole_mcpio_ubicacion',
    'cole_nombre_establecimiento', 'cole_naturaleza', 'cole_calendario', 'cole_genero',
    'estu_depto_presentacion', 'estu_mcpio_presentacion',
    'punt_global', 'percentil_global',
    'punt_lectura_critica', 'desemp_lectura_critica',
    'punt_matematicas', 'desemp_matematicas',
    'punt_c_naturales', 'desemp_c_naturales',
    'punt_sociales_ciudadanas', 'desemp_sociales_ciudadanas',
    'punt_ingles', 'desemp_ingles'
]
SCORE_COLUMNS = ['punt_global', 'punt_lectura_critica', 'punt_matematicas', 'punt_c_naturales', 'punt_sociales_ciudadanas', 'punt_ingles']

def normalize_department(dept_name):
    if not dept_name: return None
    dept_upper = dept_name.strip().upper()
    if 'BOGOTA' in dept_upper: return 'BOGOTÁ'
    return dept_upper

def create_tables(conn):
    cursor = conn.cursor()
    # Build column definitions string dynamically, ensuring column names are quoted
    column_defs = ", ".join([f'"{col}" TEXT' for col in COLUMNS_TO_IMPORT])
    
    cursor.execute(f"""
    CREATE TABLE IF NOT EXISTS student_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        {column_defs},
        cole_depto_ubicacion_norm TEXT,
        estu_depto_presentacion_norm TEXT,
        benchmark_dept_norm TEXT
    )
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS departmental_benchmarks (
        periodo TEXT, departamento TEXT, materia TEXT, promedio REAL,
        PRIMARY KEY (periodo, departamento, materia)
    )""")
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS national_benchmarks (
        periodo TEXT, materia TEXT, promedio REAL,
        PRIMARY KEY (periodo, materia)
    )""")
    conn.commit()
    print("Tablas creadas (o ya existen).")

def populate_student_results(conn, lista_rutas):
    cursor = conn.cursor()
    print("Iniciando carga de datos de estudiantes en la base de datos...")
    total_rows_processed_all_files = 0

    # --- CORRECTED SQL STRING CONSTRUCTION ---
    # Construct the column names part safely
    cols_for_sql = ", ".join([f'"{col}"' for col in COLUMNS_TO_IMPORT])
    # Construct the full SQL INSERT statement
    insert_sql = f"INSERT INTO student_results ({cols_for_sql}, cole_depto_ubicacion_norm, estu_depto_presentacion_norm, benchmark_dept_norm) VALUES ({','.join(['?']*(len(COLUMNS_TO_IMPORT) + 3))})"
    # --- END CORRECTION ---

    for ruta_archivo in lista_rutas:
        print(f"Procesando archivo para DB: {ruta_archivo}...")
        rows_in_file = 0
        try:
            with open(ruta_archivo, mode='r', encoding='utf-8') as infile:
                lector = csv.DictReader(infile, delimiter=';')
                rows_to_insert = []
                for i, fila in enumerate(lector):
                    rows_in_file = i + 1
                    try:
                        data_values = []
                        for col in COLUMNS_TO_IMPORT:
                            val = fila.get(col, '').strip()
                            if col in SCORE_COLUMNS:
                                data_values.append(int(val) if val else None)
                            else:
                                data_values.append(val if val else None)
                        
                        cole_depto_norm = normalize_department(fila.get('cole_depto_ubicacion', ''))
                        estu_depto_pres_norm = normalize_department(fila.get('estu_depto_presentacion', ''))
                        
                        benchmark_dept = cole_depto_norm
                        if not benchmark_dept: benchmark_dept = estu_depto_pres_norm
                        
                        data_values.extend([cole_depto_norm, estu_depto_pres_norm, benchmark_dept])
                        rows_to_insert.append(tuple(data_values))

                        if (i + 1) % 20000 == 0: 
                            print(f"  Insertando lote de {len(rows_to_insert)} filas de {ruta_archivo}...")
                            cursor.executemany(insert_sql, rows_to_insert)
                            conn.commit()
                            rows_to_insert = []
                            
                    except (ValueError, TypeError) as ve:
                        continue
                
                if rows_to_insert: 
                    print(f"  Insertando lote final de {len(rows_to_insert)} filas de {ruta_archivo}...")
                    cursor.executemany(insert_sql, rows_to_insert)
                    conn.commit()
                
                total_rows_processed_all_files += rows_in_file
                print(f"Finalizado procesamiento de {ruta_archivo}. Filas en archivo: {rows_in_file}")

        except FileNotFoundError: print(f"ADVERTENCIA: El archivo '{ruta_archivo}' no fue encontrado.")
        except Exception as e_file: print(f"ERROR FATAL procesando el archivo {ruta_archivo}: {e_file}")
            
    print(f"Carga de datos de estudiantes completada. Total filas procesadas: {total_rows_processed_all_files}")

def calculate_and_store_benchmarks(conn):
    cursor = conn.cursor()
    print("Calculando y almacenando benchmarks...")
    cursor.execute("DELETE FROM departmental_benchmarks")
    cursor.execute("DELETE FROM national_benchmarks")

    for materia in SCORE_COLUMNS:
        # Quoting the materia column name for safety if it contains special characters (though unlikely for these specific keys)
        materia_sql_safe = f'"{materia}"'

        query_dept = f"""
        SELECT periodo, benchmark_dept_norm, AVG(CAST({materia_sql_safe} AS REAL))
        FROM student_results
        WHERE benchmark_dept_norm IS NOT NULL AND {materia_sql_safe} IS NOT NULL AND {materia_sql_safe} != ''
        GROUP BY periodo, benchmark_dept_norm
        """
        cursor.execute(query_dept)
        for periodo, depto, promedio in cursor.fetchall():
            if depto:
                cursor.execute("INSERT INTO departmental_benchmarks VALUES (?, ?, ?, ?)", (periodo, depto, materia, promedio))
        
        query_nac = f"""
        SELECT periodo, AVG(CAST({materia_sql_safe} AS REAL))
        FROM student_results
        WHERE {materia_sql_safe} IS NOT NULL AND {materia_sql_safe} != '' AND periodo IS NOT NULL
        GROUP BY periodo
        """
        cursor.execute(query_nac)
        for periodo, promedio in cursor.fetchall():
             cursor.execute("INSERT INTO national_benchmarks VALUES (?, ?, ?)", (periodo, materia, promedio))
    conn.commit()
    print("Benchmarks calculados y almacenados.")

def main():
    archivos_de_datos_p1 = glob.glob("Examen_Saber_11_*1.txt")
    archivos_de_datos_p2 = glob.glob("Examen_Saber_11_*2.txt") 
    archivos_de_datos = sorted(list(set(archivos_de_datos_p1 + archivos_de_datos_p2)))

    if not archivos_de_datos:
        print("No se encontraron archivos de datos ('Examen_Saber_11_*.txt').")
        return

    print("Archivos de datos que se procesarán:")
    for f_path in archivos_de_datos: print(f"  - {f_path}")
    
    if os.path.exists(DATABASE_NAME):
        print(f"Eliminando base de datos antigua: {DATABASE_NAME}")
        os.remove(DATABASE_NAME)
        
    conn = sqlite3.connect(DATABASE_NAME)
    create_tables(conn)
    populate_student_results(conn, archivos_de_datos)
    calculate_and_store_benchmarks(conn)
    conn.close()
    print(f"\nProceso completado. La base de datos '{DATABASE_NAME}' ha sido creada/actualizada.")

if __name__ == '__main__':
    main()