# create_database.py

import csv
import sqlite3
import glob
import os
from collections import defaultdict
import statistics # For calculating means if needed during database population (though mostly using SQL AGG)

# --- Configuration ---
DATABASE_NAME = 'icfes_data.db'
# Define which columns from the CSV you want to import.
# This helps in keeping the database focused and potentially smaller.
# Ensure all columns needed for display AND calculation are here.
COLUMNS_TO_IMPORT = [
    'periodo', 'estu_consecutivo', 'estu_genero', 'estu_nacionalidad', 
    'estu_fechanacimiento', 'cole_depto_ubicacion', 'cole_mcpio_ubicacion', 
    'cole_nombre_establecimiento', 'cole_naturaleza', 'cole_calendario',
    'estu_depto_presentacion', 'estu_mcpio_presentacion',
    'punt_global', 'percentil_global', 
    'punt_lectura_critica', 'desemp_lectura_critica',
    'punt_matematicas', 'desemp_matematicas',
    'punt_c_naturales', 'desemp_c_naturales',
    'punt_sociales_ciudadanas', 'desemp_sociales_ciudadanas',
    'punt_ingles', 'desemp_ingles'
    # Add any other estu_ or fami_ fields if you plan to display them
]
SCORE_COLUMNS = ['punt_global', 'punt_lectura_critica', 'punt_matematicas', 'punt_c_naturales', 'punt_sociales_ciudadanas', 'punt_ingles']

def normalize_department(dept_name):
    """Normalizes department names, especially for Bogotá."""
    if not dept_name:
        return None
    dept_upper = dept_name.strip().upper()
    if 'BOGOTA' in dept_upper:
        return 'BOGOTÁ'
    return dept_upper

def create_tables(conn):
    """Creates the necessary tables in the SQLite database."""
    cursor = conn.cursor()
    
    # Main table for all student results
    # We add normalized department columns for easier querying later
    cursor.execute(f"""
    CREATE TABLE IF NOT EXISTS student_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        {", ".join([f"{col} TEXT" for col in COLUMNS_TO_IMPORT])},
        cole_depto_ubicacion_norm TEXT,
        estu_depto_presentacion_norm TEXT,
        benchmark_dept_norm TEXT 
    )
    """)
    
    # Table for pre-calculated departmental benchmarks by period
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS departmental_benchmarks (
        periodo TEXT,
        departamento TEXT,
        materia TEXT,
        promedio REAL,
        PRIMARY KEY (periodo, departamento, materia)
    )
    """)

    # Table for pre-calculated national benchmarks by period
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS national_benchmarks (
        periodo TEXT,
        materia TEXT,
        promedio REAL,
        PRIMARY KEY (periodo, materia)
    )
    """)
    conn.commit()
    print("Tablas creadas (o ya existen).")

def populate_student_results(conn, lista_rutas):
    """Reads data from CSV files and populates the student_results table."""
    cursor = conn.cursor()
    print("Iniciando carga de datos de estudiantes...")
    total_rows_processed = 0

    for ruta_archivo in lista_rutas:
        print(f"Procesando archivo: {ruta_archivo}...")
        try:
            with open(ruta_archivo, mode='r', encoding='utf-8') as infile:
                lector = csv.DictReader(infile, delimiter=';')
                rows_to_insert = []
                for i, fila in enumerate(lector):
                    try:
                        # Prepare data for insertion
                        data_tuple = []
                        for col in COLUMNS_TO_IMPORT:
                            val = fila.get(col, '').strip()
                            if col in SCORE_COLUMNS: # Convert score columns to integer
                                data_tuple.append(int(val) if val else None)
                            else:
                                data_tuple.append(val if val else None)
                        
                        # Add normalized department names
                        cole_depto_norm = normalize_department(fila.get('cole_depto_ubicacion', ''))
                        estu_depto_pres_norm = normalize_department(fila.get('estu_depto_presentacion', ''))
                        
                        # Determine benchmark department using hybrid logic
                        benchmark_dept = cole_depto_norm
                        if not benchmark_dept:
                            benchmark_dept = estu_depto_pres_norm
                        
                        data_tuple.extend([cole_depto_norm, estu_depto_pres_norm, benchmark_dept])
                        rows_to_insert.append(tuple(data_tuple))

                        if (i + 1) % 10000 == 0: # Commit in batches for performance
                            print(f"  Procesadas {i+1} filas de {ruta_archivo}...")
                            cursor.executemany(f"""
                            INSERT INTO student_results ({", ".join(COLUMNS_TO_IMPORT)}, cole_depto_ubicacion_norm, estu_depto_presentacion_norm, benchmark_dept_norm)
                            VALUES ({",".join(["?"]*(len(COLUMNS_TO_IMPORT) + 3))})
                            """, rows_to_insert)
                            conn.commit()
                            rows_to_insert = []
                            
                    except ValueError as ve: # Catch errors converting scores to int
                        # print(f"Error de valor en fila {i+1} de {ruta_archivo}: {ve}. Fila: {dict(fila)}")
                        continue # Skip this row
                    except Exception as e_row:
                        # print(f"Error inesperado en fila {i+1} de {ruta_archivo}: {e_row}")
                        continue

                # Insert any remaining rows
                if rows_to_insert:
                    cursor.executemany(f"""
                    INSERT INTO student_results ({", ".join(COLUMNS_TO_IMPORT)}, cole_depto_ubicacion_norm, estu_depto_presentacion_norm, benchmark_dept_norm)
                    VALUES ({",".join(["?"]*(len(COLUMNS_TO_IMPORT) + 3))})
                    """, rows_to_insert)
                    conn.commit()
                total_rows_processed += (i + 1)
                print(f"Finalizado procesamiento de {ruta_archivo}. Total filas en archivo: {i+1}")

        except FileNotFoundError:
            print(f"ADVERTENCIA: El archivo '{ruta_archivo}' no fue encontrado.")
        except Exception as e_file:
            print(f"ERROR FATAL procesando el archivo {ruta_archivo}: {e_file}")
            
    print(f"Carga de datos de estudiantes completada. Total filas procesadas en todos los archivos: {total_rows_processed}")

def calculate_and_store_benchmarks(conn):
    """Calculates departmental and national benchmarks from the student_results table."""
    cursor = conn.cursor()
    print("Calculando y almacenando benchmarks departamentales...")

    # Clear existing benchmarks
    cursor.execute("DELETE FROM departmental_benchmarks")
    cursor.execute("DELETE FROM national_benchmarks")

    for materia in SCORE_COLUMNS:
        # Departmental benchmarks
        query_dept = f"""
        SELECT periodo, benchmark_dept_norm, AVG({materia})
        FROM student_results
        WHERE benchmark_dept_norm IS NOT NULL AND {materia} IS NOT NULL
        GROUP BY periodo, benchmark_dept_norm
        """
        cursor.execute(query_dept)
        for periodo, depto, promedio in cursor.fetchall():
            if depto: # Ensure department is not None
                cursor.execute("INSERT INTO departmental_benchmarks VALUES (?, ?, ?, ?)", (periodo, depto, materia, promedio))
        
        # National benchmarks (average of departmental averages - simple version)
        # A more accurate national average would be AVG({materia}) GROUP BY periodo from all students
        query_nac_direct = f"""
        SELECT periodo, AVG({materia})
        FROM student_results
        WHERE {materia} IS NOT NULL
        GROUP BY periodo
        """
        cursor.execute(query_nac_direct)
        for periodo, promedio in cursor.fetchall():
             cursor.execute("INSERT INTO national_benchmarks VALUES (?, ?, ?)", (periodo, materia, promedio))

    conn.commit()
    print("Benchmarks calculados y almacenados.")

def main():
    # --- AUTOMATIC FILE DETECTION ---
    archivos_de_datos_p1 = glob.glob("Examen_Saber_11_*1.txt")
    archivos_de_datos_p2 = glob.glob("Examen_Saber_11_*2.txt")
    archivos_de_datos = sorted(list(set(archivos_de_datos_p1 + archivos_de_datos_p2)), reverse=True)

    if not archivos_de_datos:
        print("No se encontraron archivos de datos con el patrón 'Examen_Saber_11_*.txt' en este directorio.")
        print("Por favor, asegúrese de que los archivos estén presentes y nombrados correctamente.")
        return

    print("Archivos de datos a procesar:")
    for f_path in archivos_de_datos:
        print(f"  - {f_path}")
    
    # Connect to (or create) the SQLite database
    conn = sqlite3.connect(DATABASE_NAME)
    
    create_tables(conn)
    populate_student_results(conn, archivos_de_datos)
    calculate_and_store_benchmarks(conn)
    
    conn.close()
    print(f"Proceso completado. La base de datos '{DATABASE_NAME}' ha sido creada/actualizada.")

if __name__ == '__main__':
    main()