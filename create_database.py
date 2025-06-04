# create_database.py

import csv
import sqlite3
import glob
import os
from collections import defaultdict
from datetime import datetime
import json # <-- NEW IMPORT

# --- Configuración ---
DATABASE_NAME = 'minerva_icfes_data.db'
LAST_UPDATED_FILE = 'minerva_last_updated.txt'
STATIC_DATA_PATH = 'static_data' # <-- NEW: Path for static JSON files (relative to where app.py runs, or adjust as needed)
SCHOOLS_PER_PAGE_STATIC_JSON = 100 # <-- NEW: Chunk size for static JSON pages

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
    if 'BOGOTA' in dept_upper or 'BOGOTÁ' in dept_upper : return 'BOGOTÁ'
    return dept_upper

def create_tables(conn):
    # ... (Keep existing create_tables function as is) ...
    cursor = conn.cursor()
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
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS school_statistics (
        periodo TEXT,
        cole_nombre_establecimiento TEXT,
        cole_mcpio_ubicacion TEXT,
        cole_naturaleza TEXT,
        cole_calendario TEXT,
        cole_depto_ubicacion_norm TEXT, 

        avg_punt_global REAL,
        avg_punt_lectura_critica REAL,
        avg_punt_matematicas REAL,
        avg_punt_c_naturales REAL,
        avg_punt_sociales_ciudadanas REAL,
        avg_punt_ingles REAL,

        student_count INTEGER,

        rank_departmental INTEGER, 
        rank_national INTEGER,   

        PRIMARY KEY (periodo, cole_nombre_establecimiento, cole_mcpio_ubicacion,
                     cole_naturaleza, cole_calendario, cole_depto_ubicacion_norm)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS school_performance_levels (
        periodo TEXT,
        cole_nombre_establecimiento TEXT,
        cole_mcpio_ubicacion TEXT,
        cole_naturaleza TEXT,
        cole_calendario TEXT,
        cole_depto_ubicacion_norm TEXT, 
        materia TEXT,
        nivel TEXT,
        count INTEGER,

        PRIMARY KEY (periodo, cole_nombre_establecimiento, cole_mcpio_ubicacion,
                     cole_naturaleza, cole_calendario, cole_depto_ubicacion_norm, materia, nivel)
    )
    """)

    conn.commit()
    print("Tablas creadas (o ya existen).")


def create_indexes(conn):
    # ... (Keep existing create_indexes function as is) ...
    cursor = conn.cursor()
    print("Creando índices para optimizar consultas...")
    cursor.execute("""CREATE INDEX IF NOT EXISTS idx_school_lookup ON student_results(
        periodo, cole_depto_ubicacion_norm, cole_nombre_establecimiento,
        cole_mcpio_ubicacion, cole_naturaleza, cole_calendario
    )""")
    for col in SCORE_COLUMNS:
        cursor.execute(f"CREATE INDEX IF NOT EXISTS idx_{col} ON student_results({col})")
    desemp_cols_for_index = ['desemp_lectura_critica', 'desemp_matematicas', 'desemp_c_naturales', 'desemp_sociales_ciudadanas', 'desemp_ingles']
    for col in desemp_cols_for_index:
        cursor.execute(f"CREATE INDEX IF NOT EXISTS idx_{col} ON student_results({col})")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_periodo_dept_student ON student_results(periodo, cole_depto_ubicacion_norm)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_benchmark_dept_student ON student_results(benchmark_dept_norm)")
    cursor.execute("""CREATE INDEX IF NOT EXISTS idx_school_stats_lookup ON school_statistics(
        periodo, cole_depto_ubicacion_norm, cole_nombre_establecimiento
    )""")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_school_stats_avg_global ON school_statistics(periodo, avg_punt_global DESC)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_school_stats_dept_avg_global ON school_statistics(periodo, cole_depto_ubicacion_norm, avg_punt_global DESC)")
    cursor.execute("""CREATE INDEX IF NOT EXISTS idx_school_perf_levels_lookup ON school_performance_levels(
        periodo, cole_depto_ubicacion_norm, cole_nombre_establecimiento, materia
    )""")
    conn.commit()
    print("¡Índices creados exitosamente! Las consultas ahora serán MUCHO más rápidas.")


def populate_student_results(conn, lista_rutas):
    # ... (Keep existing populate_student_results function as is) ...
    cursor = conn.cursor()
    print("Iniciando carga de datos de estudiantes en la base de datos...")
    total_rows_processed_all_files = 0
    cols_for_sql = ", ".join([f'"{col}"' for col in COLUMNS_TO_IMPORT])
    insert_sql = f"INSERT INTO student_results ({cols_for_sql}, cole_depto_ubicacion_norm, estu_depto_presentacion_norm, benchmark_dept_norm) VALUES ({','.join(['?']*(len(COLUMNS_TO_IMPORT) + 3))})"
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
                                try:
                                    data_values.append(int(val) if val and val.lower() != 'nan' else None)
                                except ValueError:
                                    data_values.append(None) 
                            else:
                                data_values.append(val if val else None) 
                        cole_depto_norm = normalize_department(fila.get('cole_depto_ubicacion', ''))
                        estu_depto_pres_norm = normalize_department(fila.get('estu_depto_presentacion', ''))
                        benchmark_dept = cole_depto_norm if cole_depto_norm else estu_depto_pres_norm
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
    # ... (Keep existing calculate_and_store_benchmarks function as is) ...
    cursor = conn.cursor()
    print("Calculando y almacenando benchmarks departamentales y nacionales...")
    cursor.execute("DELETE FROM departmental_benchmarks")
    cursor.execute("DELETE FROM national_benchmarks")
    for materia in SCORE_COLUMNS:
        materia_sql_safe = f'"{materia}"' 
        query_dept = f"""
        SELECT periodo, benchmark_dept_norm, AVG(CAST({materia_sql_safe} AS REAL))
        FROM student_results
        WHERE benchmark_dept_norm IS NOT NULL AND {materia_sql_safe} IS NOT NULL AND TRIM({materia_sql_safe}) != ''
        GROUP BY periodo, benchmark_dept_norm
        """
        cursor.execute(query_dept)
        for periodo, depto, promedio in cursor.fetchall():
            if depto and promedio is not None: 
                cursor.execute("INSERT INTO departmental_benchmarks VALUES (?, ?, ?, ?)", (periodo, depto, materia, promedio))
        query_nac = f"""
        SELECT periodo, AVG(CAST({materia_sql_safe} AS REAL))
        FROM student_results
        WHERE {materia_sql_safe} IS NOT NULL AND TRIM({materia_sql_safe}) != '' AND periodo IS NOT NULL
        GROUP BY periodo
        """
        cursor.execute(query_nac)
        for periodo, promedio in cursor.fetchall():
            if periodo and promedio is not None: 
                cursor.execute("INSERT INTO national_benchmarks VALUES (?, ?, ?)", (periodo, materia, promedio))
    conn.commit()
    print("Benchmarks calculados y almacenados.")


def precalculate_school_statistics(conn):
    # ... (Keep existing precalculate_school_statistics function as is) ...
    cursor = conn.cursor()
    print("Pre-calculando estadísticas por colegio (esto tomará unos minutos pero ahorrará MUCHO tiempo después)...")
    cursor.execute("DELETE FROM school_statistics")
    avg_score_expressions = []
    for col in SCORE_COLUMNS:
        avg_score_expressions.append(f"AVG(CASE WHEN \"{col}\" IS NOT NULL AND TRIM(\"{col}\") != '' THEN CAST(\"{col}\" AS REAL) ELSE NULL END) as avg_{col}")
    avg_scores_sql = ",\n        ".join(avg_score_expressions)
    insert_stats_sql = f"""
    INSERT INTO school_statistics (
        periodo, cole_nombre_establecimiento, cole_mcpio_ubicacion,
        cole_naturaleza, cole_calendario, cole_depto_ubicacion_norm,
        {', '.join([f'avg_{col}' for col in SCORE_COLUMNS])},
        student_count
    )
    SELECT
        periodo,
        cole_nombre_establecimiento,
        cole_mcpio_ubicacion,
        cole_naturaleza,
        cole_calendario,
        cole_depto_ubicacion_norm, 
        {avg_scores_sql},
        COUNT(id) as student_count 
    FROM student_results
    WHERE cole_nombre_establecimiento IS NOT NULL AND TRIM(cole_nombre_establecimiento) != ''
      AND cole_depto_ubicacion_norm IS NOT NULL 
    GROUP BY periodo, cole_nombre_establecimiento, cole_mcpio_ubicacion,
             cole_naturaleza, cole_calendario, cole_depto_ubicacion_norm
    """
    cursor.execute(insert_stats_sql)
    print(f"  Estadísticas de puntajes por colegio pre-calculadas: {cursor.rowcount} filas afectadas.")
    print("Pre-calculando niveles de desempeño por colegio...")
    cursor.execute("DELETE FROM school_performance_levels")
    desemp_columns_map = [
        ('desemp_lectura_critica', 'lectura_critica'),
        ('desemp_matematicas', 'matematicas'),
        ('desemp_c_naturales', 'c_naturales'),
        ('desemp_sociales_ciudadanas', 'sociales_ciudadanas'),
        ('desemp_ingles', 'ingles')
    ]
    for desemp_col_name, materia_alias in desemp_columns_map:
        print(f"  Procesando niveles de {materia_alias}...")
        insert_levels_sql = f"""
        INSERT INTO school_performance_levels (
            periodo, cole_nombre_establecimiento, cole_mcpio_ubicacion,
            cole_naturaleza, cole_calendario, cole_depto_ubicacion_norm,
            materia, nivel, count
        )
        SELECT
            periodo,
            cole_nombre_establecimiento,
            cole_mcpio_ubicacion,
            cole_naturaleza,
            cole_calendario,
            cole_depto_ubicacion_norm, 
            '{materia_alias}' as materia,
            "{desemp_col_name}" as nivel,
            COUNT(id) as count
        FROM student_results
        WHERE cole_nombre_establecimiento IS NOT NULL AND TRIM(cole_nombre_establecimiento) != ''
          AND cole_depto_ubicacion_norm IS NOT NULL 
          AND "{desemp_col_name}" IS NOT NULL AND TRIM("{desemp_col_name}") != ''
        GROUP BY periodo, cole_nombre_establecimiento, cole_mcpio_ubicacion,
                 cole_naturaleza, cole_calendario, cole_depto_ubicacion_norm, "{desemp_col_name}"
        """
        cursor.execute(insert_levels_sql)
        print(f"    Niveles para {materia_alias} pre-calculados: {cursor.rowcount} filas afectadas.")
    conn.commit()
    print("¡Estadísticas y niveles de desempeño pre-calculados exitosamente!")


def calculate_and_store_school_rankings(conn):
    # ... (Keep existing calculate_and_store_school_rankings function as is) ...
    cursor = conn.cursor()
    print("Calculando y almacenando rankings departamentales y nacionales...")
    sql_update_dept_rank = """
    WITH RankedSchools AS (
        SELECT
            periodo,
            cole_nombre_establecimiento,
            cole_mcpio_ubicacion,
            cole_naturaleza,
            cole_calendario,
            cole_depto_ubicacion_norm,
            RANK() OVER (PARTITION BY periodo, cole_depto_ubicacion_norm
                         ORDER BY avg_punt_global DESC) as calculated_rank
        FROM school_statistics
        WHERE avg_punt_global IS NOT NULL 
    )
    UPDATE school_statistics
    SET rank_departmental = (
        SELECT rs.calculated_rank
        FROM RankedSchools rs
        WHERE rs.periodo = school_statistics.periodo
          AND rs.cole_depto_ubicacion_norm = school_statistics.cole_depto_ubicacion_norm
          AND rs.cole_nombre_establecimiento = school_statistics.cole_nombre_establecimiento
          AND rs.cole_mcpio_ubicacion = school_statistics.cole_mcpio_ubicacion
          AND rs.cole_naturaleza = school_statistics.cole_naturaleza
          AND rs.cole_calendario = school_statistics.cole_calendario
    )
    WHERE EXISTS ( 
         SELECT 1
         FROM RankedSchools rs
         WHERE rs.periodo = school_statistics.periodo
           AND rs.cole_depto_ubicacion_norm = school_statistics.cole_depto_ubicacion_norm
           AND rs.cole_nombre_establecimiento = school_statistics.cole_nombre_establecimiento
           AND rs.cole_mcpio_ubicacion = school_statistics.cole_mcpio_ubicacion
           AND rs.cole_naturaleza = school_statistics.cole_naturaleza
           AND rs.cole_calendario = school_statistics.cole_calendario
    );
    """
    cursor.execute(sql_update_dept_rank)
    print(f"  Rankings departamentales actualizados: {cursor.rowcount} filas afectadas.")
    sql_update_nat_rank = """
    WITH RankedSchools AS (
        SELECT
            periodo,
            cole_nombre_establecimiento,
            cole_mcpio_ubicacion,
            cole_naturaleza,
            cole_calendario,
            cole_depto_ubicacion_norm, 
            RANK() OVER (PARTITION BY periodo
                         ORDER BY avg_punt_global DESC) as calculated_rank
        FROM school_statistics
        WHERE avg_punt_global IS NOT NULL
    )
    UPDATE school_statistics
    SET rank_national = (
        SELECT rs.calculated_rank
        FROM RankedSchools rs
        WHERE rs.periodo = school_statistics.periodo
          AND rs.cole_nombre_establecimiento = school_statistics.cole_nombre_establecimiento
          AND rs.cole_mcpio_ubicacion = school_statistics.cole_mcpio_ubicacion
          AND rs.cole_naturaleza = school_statistics.cole_naturaleza
          AND rs.cole_calendario = school_statistics.cole_calendario
          AND rs.cole_depto_ubicacion_norm = school_statistics.cole_depto_ubicacion_norm
    )
    WHERE EXISTS (
        SELECT 1
        FROM RankedSchools rs
        WHERE rs.periodo = school_statistics.periodo
          AND rs.cole_nombre_establecimiento = school_statistics.cole_nombre_establecimiento
          AND rs.cole_mcpio_ubicacion = school_statistics.cole_mcpio_ubicacion
          AND rs.cole_naturaleza = school_statistics.cole_naturaleza
          AND rs.cole_calendario = school_statistics.cole_calendario
          AND rs.cole_depto_ubicacion_norm = school_statistics.cole_depto_ubicacion_norm
    );
    """
    cursor.execute(sql_update_nat_rank)
    print(f"  Rankings nacionales actualizados: {cursor.rowcount} filas afectadas.")
    conn.commit()
    print("Rankings calculados y almacenados.")


def analyze_database_performance(conn):
    # ... (Keep existing analyze_database_performance function as is) ...
    cursor = conn.cursor()
    print("\n--- Análisis de rendimiento de la base de datos ---")
    total_rows = cursor.execute("SELECT COUNT(*) FROM student_results").fetchone()[0]
    print(f"Total de registros de estudiantes: {total_rows:,}")
    unique_schools_stats = cursor.execute("SELECT COUNT(*) FROM school_statistics").fetchone()[0]
    print(f"Entradas únicas en school_statistics (colegio-periodo-depto): {unique_schools_stats:,}")
    indexes = cursor.execute("SELECT name FROM sqlite_master WHERE type='index'").fetchall()
    print(f"Índices creados: {len(indexes)}")
    cursor.execute("PRAGMA page_count")
    page_count = cursor.fetchone()[0]
    cursor.execute("PRAGMA page_size")
    page_size = cursor.fetchone()[0]
    size_mb = (page_count * page_size) / (1024 * 1024)
    print(f"Tamaño de la base de datos: {size_mb:.1f} MB")

def record_last_updated_time():
    # ... (Keep existing record_last_updated_time function as is) ...
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        with open(LAST_UPDATED_FILE, 'w', encoding='utf-8') as f:
            f.write(now)
        print(f"Fecha de última actualización registrada: {now}")
    except Exception as e:
        print(f"Error al registrar fecha de actualización: {e}")

# --- NEW FUNCTION: To generate static JSON files for school lists ---
def generate_static_school_lists(conn):
    print("\n--- Generando archivos JSON estáticos para listas de colegios ---")
    cursor = conn.cursor()

    base_output_dir = os.path.join(STATIC_DATA_PATH, 'schools') # e.g., static_data/schools/
    if not os.path.exists(base_output_dir):
        os.makedirs(base_output_dir, exist_ok=True)
    print(f"Directorio base para JSONs: {os.path.abspath(base_output_dir)}")

    # Get distinct periodos
    cursor.execute("SELECT DISTINCT periodo FROM school_statistics ORDER BY periodo DESC")
    periodos = [row[0] for row in cursor.fetchall()]

    for periodo in periodos:
        periodo_dir = os.path.join(base_output_dir, str(periodo))
        if not os.path.exists(periodo_dir):
            os.makedirs(periodo_dir, exist_ok=True)

        cursor.execute("""
            SELECT DISTINCT cole_depto_ubicacion_norm 
            FROM school_statistics 
            WHERE periodo = ? AND cole_depto_ubicacion_norm IS NOT NULL
            ORDER BY cole_depto_ubicacion_norm ASC
        """, (periodo,))
        departamentos = [row[0] for row in cursor.fetchall()]

        for dept_norm in departamentos:
            print(f"  Procesando: Periodo {periodo}, Departamento {dept_norm}")

            # Query to get all schools for this periodo and departamento, including cole_genero
            # This query is similar to the one in app.py's get_schools_for_department_period
            # Note: Joining for cole_genero can be slow if student_results is very large.
            # Consider if cole_genero is essential for the list view or can be omitted/handled differently.
            query_all_schools = """
                SELECT 
                    ss.cole_nombre_establecimiento, ss.cole_mcpio_ubicacion, ss.cole_naturaleza, 
                    ss.cole_calendario, ss.cole_depto_ubicacion_norm,
                    COALESCE(sr_distinct.cole_genero, '') as cole_genero,
                    ss.avg_punt_global as promedio_global,
                    ss.student_count as num_estudiantes,
                    ss.rank_departmental, ss.rank_national
                FROM school_statistics ss
                LEFT JOIN (
                    SELECT DISTINCT cole_nombre_establecimiento, cole_mcpio_ubicacion, cole_naturaleza, 
                                    cole_calendario, periodo, cole_depto_ubicacion_norm, cole_genero
                    FROM student_results 
                    WHERE periodo = ? AND cole_depto_ubicacion_norm = ? AND cole_genero IS NOT NULL AND TRIM(cole_genero) != ''
                ) sr_distinct ON ss.cole_nombre_establecimiento = sr_distinct.cole_nombre_establecimiento
                           AND ss.cole_mcpio_ubicacion = sr_distinct.cole_mcpio_ubicacion
                           AND ss.cole_naturaleza = sr_distinct.cole_naturaleza
                           AND ss.cole_calendario = sr_distinct.cole_calendario
                           AND ss.periodo = sr_distinct.periodo
                           AND ss.cole_depto_ubicacion_norm = sr_distinct.cole_depto_ubicacion_norm
                WHERE ss.periodo = ? AND ss.cole_depto_ubicacion_norm = ?
                      AND ss.cole_nombre_establecimiento IS NOT NULL AND TRIM(ss.cole_nombre_establecimiento) != ''
                      AND ss.avg_punt_global IS NOT NULL 
                ORDER BY ss.avg_punt_global DESC
            """
            # Execute with specific parameters for the join subquery as well
            cursor.execute(query_all_schools, (periodo, dept_norm, periodo, dept_norm))
            all_school_rows_for_dept = cursor.fetchall()

            formatted_schools = []
            for row_data in all_school_rows_for_dept:
                # Formatting logic copied from app.py
                key_parts = [
                    str(row_data['cole_nombre_establecimiento'] or ''), str(row_data['cole_mcpio_ubicacion'] or ''),
                    str(row_data['cole_naturaleza'] or ''), str(row_data['cole_calendario'] or ''),
                    str(row_data['cole_depto_ubicacion_norm'] or '')
                ]
                school_id_str = "|".join(key_parts)
                
                display_parts = [
                    str(row_data['cole_nombre_establecimiento'] or ''),
                    str(row_data['cole_mcpio_ubicacion'] or ''),
                    str(row_data['cole_genero'] or ''), # From the join
                    str(row_data['cole_naturaleza'] or ''),
                    str(row_data['cole_calendario'] or '')
                ]
                display_name_parts = [p for p in display_parts[1:] if p and p.strip()]
                display_name = f"{display_parts[0]} ({' - '.join(display_name_parts)})"

                formatted_schools.append({
                    'id': school_id_str, 'name': display_name,
                    'raw_name': row_data['cole_nombre_establecimiento'] or '',
                    'mean': row_data['promedio_global'] if row_data['promedio_global'] is not None else 0,
                    'count': row_data['num_estudiantes'] or 0,
                    'rank_departmental': row_data['rank_departmental'],
                    'rank_national': row_data['rank_national']
                })
            
            total_count = len(formatted_schools)
            if total_count == 0:
                print(f"    No schools found for {periodo}-{dept_norm}. Skipping JSON generation.")
                continue

            total_pages = (total_count + SCHOOLS_PER_PAGE_STATIC_JSON - 1) // SCHOOLS_PER_PAGE_STATIC_JSON

            # Save metadata file
            dept_safe_name = dept_norm.replace(' ', '_').replace('/', '_') # Make filename safe
            meta_filename = os.path.join(periodo_dir, f"{dept_safe_name}_meta.json")
            meta_data = {
                'total_count': total_count,
                'total_pages': total_pages,
                'per_page': SCHOOLS_PER_PAGE_STATIC_JSON,
                'periodo': periodo,
                'departamento': dept_norm
            }
            with open(meta_filename, 'w', encoding='utf-8') as f_meta:
                json.dump(meta_data, f_meta)
            print(f"    Meta file saved: {meta_filename}")

            # Save paginated school list files
            for page_num in range(1, total_pages + 1):
                start_index = (page_num - 1) * SCHOOLS_PER_PAGE_STATIC_JSON
                end_index = start_index + SCHOOLS_PER_PAGE_STATIC_JSON
                page_data = formatted_schools[start_index:end_index]
                
                page_filename = os.path.join(periodo_dir, f"{dept_safe_name}_page_{page_num}.json")
                with open(page_filename, 'w', encoding='utf-8') as f_page:
                    json.dump({'schools': page_data}, f_page) # Wrap in a 'schools' key for consistency with previous API
            print(f"    Paginated files saved for {dept_norm} ({total_pages} pages)")
            
    print("--- Generación de archivos JSON estáticos completada ---")
# --- END NEW FUNCTION ---

def main():
    archivos_de_datos_p1 = glob.glob("Examen_Saber_11_*1.txt")
    archivos_de_datos_p2 = glob.glob("Examen_Saber_11_*2.txt")
    archivos_de_datos = sorted(list(set(archivos_de_datos_p1 + archivos_de_datos_p2)))

    if not archivos_de_datos:
        print("No se encontraron archivos de datos ('Examen_Saber_11_*.txt'). Revisa la carpeta.")
        return

    print("Archivos de datos que se procesarán:")
    for f_path in archivos_de_datos: print(f"  - {f_path}")

    if os.path.exists(DATABASE_NAME):
        print(f"Eliminando base de datos antigua: {DATABASE_NAME} (si existe)")
        try:
            os.remove(DATABASE_NAME)
            print("  Base de datos antigua eliminada.")
        except OSError as e:
            print(f"  Error eliminando la base de datos antigua: {e}. Puede que esté en uso.")
            return 

    conn = sqlite3.connect(DATABASE_NAME)
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    conn.execute("PRAGMA cache_size = -64000;") 
    conn.execute("PRAGMA temp_store = MEMORY;")

    create_tables(conn)
    populate_student_results(conn, archivos_de_datos)
    create_indexes(conn) # Create indexes AFTER data load
    calculate_and_store_benchmarks(conn)
    precalculate_school_statistics(conn)
    calculate_and_store_school_rankings(conn)

    # --- NEW: Call to generate static JSON files ---
    generate_static_school_lists(conn)
    # --- END NEW ---

    analyze_database_performance(conn)

    print("\nOptimizando la base de datos final (VACUUM)... Esto puede tardar un poco.")
    conn.execute("VACUUM;")
    conn.execute("ANALYZE;")

    conn.close()
    record_last_updated_time()
    print(f"\n¡Proceso completado! La base de datos '{DATABASE_NAME}' ha sido creada y optimizada.")
    print(f"Los archivos JSON estáticos para las listas de colegios se han generado en '{STATIC_DATA_PATH}'.")

if __name__ == '__main__':
    main()