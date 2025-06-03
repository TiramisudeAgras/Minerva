# create_database.py

import csv
import sqlite3
import glob
import os
from collections import defaultdict
# import statistics # No lo estamos usando directamente aquí, pero puede ser útil para otros análisis
from datetime import datetime

# --- Configuración ---
DATABASE_NAME = 'minerva_icfes_data.db'
LAST_UPDATED_FILE = 'minerva_last_updated.txt' # Para guardar la fecha de la última actualización, ¡creo!

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
    if 'BOGOTA' in dept_upper or 'BOGOTÁ' in dept_upper : return 'BOGOTÁ' # Normalizamos Bogotá D.C.
    return dept_upper

def create_tables(conn):
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

    # TABLA NUEVA: Estadísticas pre-calculadas por colegio
    # OJO: La PK aquí es crucial. Si cole_depto_ubicacion_norm forma parte de la unicidad
    #      de un colegio (junto con nombre, municipio, etc.), debería estar en la PK y en el GROUP BY.
    #      La versión original del usuario en la primera pregunta tenía una PK sin cole_depto_ubicacion_norm
    #      pero lo incluía en el GROUP BY de precalculate_school_statistics.
    #      Para consistencia, la PK debe reflejar las columnas que definen una fila única.
    #      Aquí asumimos que la combinación original de la PK del usuario es la deseada para la unicidad
    #      de la fila de estadísticas del colegio.
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS school_statistics (
        periodo TEXT,
        cole_nombre_establecimiento TEXT,
        cole_mcpio_ubicacion TEXT,
        cole_naturaleza TEXT,
        cole_calendario TEXT,
        cole_depto_ubicacion_norm TEXT, -- Este es el departamento normalizado del colegio

        avg_punt_global REAL,
        avg_punt_lectura_critica REAL,
        avg_punt_matematicas REAL,
        avg_punt_c_naturales REAL,
        avg_punt_sociales_ciudadanas REAL,
        avg_punt_ingles REAL,

        student_count INTEGER,

        rank_departmental INTEGER, -- Nueva Columna para ranking departamental
        rank_national INTEGER,   -- Nueva Columna para ranking nacional

        PRIMARY KEY (periodo, cole_nombre_establecimiento, cole_mcpio_ubicacion,
                     cole_naturaleza, cole_calendario, cole_depto_ubicacion_norm)
    )
    """)


    # TABLA NUEVA: Cache de niveles de desempeño por colegio
    # Similar a school_statistics, la PK debe asegurar unicidad.
    # Si cole_depto_ubicacion_norm es necesario para la unicidad de los niveles de un colegio,
    # debería estar en la PK y en el GROUP BY.
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS school_performance_levels (
        periodo TEXT,
        cole_nombre_establecimiento TEXT,
        cole_mcpio_ubicacion TEXT,
        cole_naturaleza TEXT,
        cole_calendario TEXT,
        cole_depto_ubicacion_norm TEXT, -- Departamento normalizado del colegio
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
    """Crear índices para mejorar dramáticamente el rendimiento de las consultas"""
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

    # Índices para las tablas de estadísticas y niveles (SQLite crea índices para PKs automáticamente)
    # Índices adicionales para búsquedas comunes en school_statistics:
    cursor.execute("""CREATE INDEX IF NOT EXISTS idx_school_stats_lookup ON school_statistics(
        periodo, cole_depto_ubicacion_norm, cole_nombre_establecimiento
    )""")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_school_stats_avg_global ON school_statistics(periodo, avg_punt_global DESC)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_school_stats_dept_avg_global ON school_statistics(periodo, cole_depto_ubicacion_norm, avg_punt_global DESC)")

    # Índice para school_performance_levels (PK ya tiene índice, pero uno específico para lookups puede ayudar)
    cursor.execute("""CREATE INDEX IF NOT EXISTS idx_school_perf_levels_lookup ON school_performance_levels(
        periodo, cole_depto_ubicacion_norm, cole_nombre_establecimiento, materia
    )""")

    # NUEVO: Índices para búsqueda eficiente por nombre de colegio
    cursor.execute("""CREATE INDEX IF NOT EXISTS idx_school_name_search 
    ON school_statistics(periodo, cole_depto_ubicacion_norm, cole_nombre_establecimiento)""")
    
    # NUEVO: Este índice ayuda con el ORDER BY en las consultas de búsqueda
    cursor.execute("""CREATE INDEX IF NOT EXISTS idx_school_search_with_avg 
    ON school_statistics(periodo, cole_depto_ubicacion_norm, cole_nombre_establecimiento, avg_punt_global DESC)""")

    conn.commit()
    print("¡Índices creados exitosamente! Las consultas ahora serán MUCHO más rápidas.")


def populate_student_results(conn, lista_rutas):
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
                                # Asegurarnos que los puntajes sean enteros o None
                                try:
                                    data_values.append(int(val) if val and val.lower() != 'nan' else None)
                                except ValueError:
                                    data_values.append(None) # Si no se puede convertir a int, es None
                            else:
                                data_values.append(val if val else None) # Campos de texto pueden ser None si están vacíos

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
                        # print(f"  Advertencia: Error de datos en fila {i+1} del archivo {ruta_archivo}. Saltando fila. Error: {ve}")
                        continue # Saltar a la siguiente fila si hay error de conversión

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
    print("Calculando y almacenando benchmarks departamentales y nacionales...")
    cursor.execute("DELETE FROM departmental_benchmarks")
    cursor.execute("DELETE FROM national_benchmarks")

    for materia in SCORE_COLUMNS:
        materia_sql_safe = f'"{materia}"' # Para nombres de columna con espacios o caracteres especiales
        # Benchmarks Departamentales
        query_dept = f"""
        SELECT periodo, benchmark_dept_norm, AVG(CAST({materia_sql_safe} AS REAL))
        FROM student_results
        WHERE benchmark_dept_norm IS NOT NULL AND {materia_sql_safe} IS NOT NULL AND TRIM({materia_sql_safe}) != ''
        GROUP BY periodo, benchmark_dept_norm
        """
        cursor.execute(query_dept)
        for periodo, depto, promedio in cursor.fetchall():
            if depto and promedio is not None: # Solo insertar si hay departamento y promedio válido
                cursor.execute("INSERT INTO departmental_benchmarks VALUES (?, ?, ?, ?)", (periodo, depto, materia, promedio))

        # Benchmarks Nacionales
        query_nac = f"""
        SELECT periodo, AVG(CAST({materia_sql_safe} AS REAL))
        FROM student_results
        WHERE {materia_sql_safe} IS NOT NULL AND TRIM({materia_sql_safe}) != '' AND periodo IS NOT NULL
        GROUP BY periodo
        """
        cursor.execute(query_nac)
        for periodo, promedio in cursor.fetchall():
            if periodo and promedio is not None: # Solo insertar si hay periodo y promedio válido
                cursor.execute("INSERT INTO national_benchmarks VALUES (?, ?, ?)", (periodo, materia, promedio))
    conn.commit()
    print("Benchmarks calculados y almacenados.")

def precalculate_school_statistics(conn):
    """Pre-calcular estadísticas por colegio para evitar cálculos en tiempo real"""
    cursor = conn.cursor()
    print("Pre-calculando estadísticas por colegio (esto tomará unos minutos pero ahorrará MUCHO tiempo después)...")

    cursor.execute("DELETE FROM school_statistics")

    # Columnas de puntaje para el AVG. Nos aseguramos que sean REAL y manejamos NULLs/vacíos.
    avg_score_expressions = []
    for col in SCORE_COLUMNS:
        avg_score_expressions.append(f"AVG(CASE WHEN \"{col}\" IS NOT NULL AND TRIM(\"{col}\") != '' THEN CAST(\"{col}\" AS REAL) ELSE NULL END) as avg_{col}")
    avg_scores_sql = ",\n        ".join(avg_score_expressions)

    # Insertar estadísticas pre-calculadas
    # El GROUP BY debe incluir todas las columnas no agregadas del SELECT que definen un "colegio"
    # Esto incluye cole_depto_ubicacion_norm si un mismo nombre de colegio puede existir en diferentes deptos.
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
        cole_depto_ubicacion_norm, -- Es el departamento normalizado del colegio
        {avg_scores_sql},
        COUNT(id) as student_count -- Contamos todos los estudiantes asociados a este grupo
    FROM student_results
    WHERE cole_nombre_establecimiento IS NOT NULL AND TRIM(cole_nombre_establecimiento) != ''
      AND cole_depto_ubicacion_norm IS NOT NULL -- Aseguramos que el depto del colegio esté presente para agrupar
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
        # De nuevo, el GROUP BY debe ser consistente con la unicidad deseada.
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
            cole_depto_ubicacion_norm, -- Depto del colegio
            '{materia_alias}' as materia,
            "{desemp_col_name}" as nivel,
            COUNT(id) as count
        FROM student_results
        WHERE cole_nombre_establecimiento IS NOT NULL AND TRIM(cole_nombre_establecimiento) != ''
          AND cole_depto_ubicacion_norm IS NOT NULL -- Aseguramos que el depto del colegio esté
          AND "{desemp_col_name}" IS NOT NULL AND TRIM("{desemp_col_name}") != ''
        GROUP BY periodo, cole_nombre_establecimiento, cole_mcpio_ubicacion,
                 cole_naturaleza, cole_calendario, cole_depto_ubicacion_norm, "{desemp_col_name}"
        """
        cursor.execute(insert_levels_sql)
        print(f"    Niveles para {materia_alias} pre-calculados: {cursor.rowcount} filas afectadas.")

    conn.commit()
    print("¡Estadísticas y niveles de desempeño pre-calculados exitosamente!")

def calculate_and_store_school_rankings(conn):
    cursor = conn.cursor()
    print("Calculando y almacenando rankings departamentales y nacionales...")

    # Calcular Rank Departamental
    # Usamos RANK() por si hay empates en avg_punt_global.
    # Los colegios con avg_punt_global NULL no se rankean (o se rankean al final, dependiendo del NULLS LAST/FIRST de SQLite).
    # Por defecto, DESC pone NULLS al final, que es lo que usualmente se quiere.
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
        WHERE avg_punt_global IS NOT NULL -- Solo rankear colegios con promedio global
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
          -- AND rs.cole_depto_ubicacion_norm = school_statistics.cole_depto_ubicacion_norm -- Ya está en el where exterior
    )
    WHERE EXISTS ( -- Solo actualizar filas que existen en RankedSchools (es decir, tienen avg_punt_global)
         SELECT 1
         FROM RankedSchools rs
         WHERE rs.periodo = school_statistics.periodo
           AND rs.cole_depto_ubicacion_norm = school_statistics.cole_depto_ubicacion_norm
           AND rs.cole_nombre_establecimiento = school_statistics.cole_nombre_establecimiento
           AND rs.cole_mcpio_ubicacion = school_statistics.cole_mcpio_ubicacion
           AND rs.cole_naturaleza = school_statistics.cole_naturaleza
           AND rs.cole_calendario = school_statistics.cole_calendario
           -- AND rs.cole_depto_ubicacion_norm = school_statistics.cole_depto_ubicacion_norm
    );
    """
    cursor.execute(sql_update_dept_rank)
    print(f"  Rankings departamentales actualizados: {cursor.rowcount} filas afectadas.")

    # Calcular Rank Nacional
    sql_update_nat_rank = """
    WITH RankedSchools AS (
        SELECT
            periodo,
            cole_nombre_establecimiento,
            cole_mcpio_ubicacion,
            cole_naturaleza,
            cole_calendario,
            cole_depto_ubicacion_norm, -- Necesario para el join de abajo
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
    """Función auxiliar para verificar el impacto de las optimizaciones"""
    cursor = conn.cursor()
    print("\n--- Análisis de rendimiento de la base de datos ---")

    total_rows = cursor.execute("SELECT COUNT(*) FROM student_results").fetchone()[0]
    print(f"Total de registros de estudiantes: {total_rows:,}")

    # Contar colegios únicos basados en la PK de school_statistics
    unique_schools_stats = cursor.execute("""
        SELECT COUNT(*) FROM school_statistics
    """).fetchone()[0]
    print(f"Entradas únicas en school_statistics (colegio-periodo-depto): {unique_schools_stats:,}")

    indexes = cursor.execute("SELECT name FROM sqlite_master WHERE type='index'").fetchall()
    print(f"Índices creados: {len(indexes)}")
    # for index in indexes: print(f"  - {index['name']}") # Descomentar para ver nombres de índices

    cursor.execute("PRAGMA page_count")
    page_count = cursor.fetchone()[0]
    cursor.execute("PRAGMA page_size")
    page_size = cursor.fetchone()[0]
    size_mb = (page_count * page_size) / (1024 * 1024)
    print(f"Tamaño de la base de datos: {size_mb:.1f} MB")

def record_last_updated_time():
    """Registrar la hora de última actualización"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        with open(LAST_UPDATED_FILE, 'w', encoding='utf-8') as f:
            f.write(now)
        print(f"Fecha de última actualización registrada: {now}")
    except Exception as e:
        print(f"Error al registrar fecha de actualización: {e}")

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
            return # No continuar si no se puede eliminar

    conn = sqlite3.connect(DATABASE_NAME)

    # Configurar SQLite para mejor rendimiento durante la carga masiva
    conn.execute("PRAGMA journal_mode = WAL;")   # Write-Ahead Logging para mejor concurrencia y menos bloqueos
    conn.execute("PRAGMA synchronous = NORMAL;") # Un buen balance entre seguridad y velocidad para inserts masivos
    conn.execute("PRAGMA cache_size = -64000;")  # Cache de 64MB (SQLite usa KiloBytes, el negativo es para KB)
    conn.execute("PRAGMA temp_store = MEMORY;") # Usar memoria para tablas temporales si es posible

    create_tables(conn)
    populate_student_results(conn, archivos_de_datos) # Carga los datos crudos

    # Crear índices DESPUÉS de cargar todos los datos es usualmente más eficiente
    create_indexes(conn)

    calculate_and_store_benchmarks(conn) # Calcula benchmarks nacionales/departamentales

    # NUEVO: Pre-calcular estadísticas detalladas por colegio y niveles de desempeño
    precalculate_school_statistics(conn)

    # NUEVO: Calcular y almacenar rankings
    calculate_and_store_school_rankings(conn)

    analyze_database_performance(conn) # Muestra algunas estadísticas de la BD

    print("\nOptimizando la base de datos final (VACUUM)... Esto puede tardar un poco.")
    conn.execute("VACUUM;") # Reconstruye la BD para optimizar espacio y fragmentación
    conn.execute("ANALYZE;")# Asegura que SQLite tenga estadísticas actualizadas para el query planner

    conn.close()
    record_last_updated_time()
    print(f"\n¡Proceso completado! La base de datos '{DATABASE_NAME}' ha sido creada y optimizada con todos los cálculos.")

if __name__ == '__main__':
    main()