# Minerva - Explorador de Resultados ICFES Saber 11

[Página Web de Mineva (¡Úsela Ahora!)] (https://minervasaber.cc)

Minerva es una aplicación web diseñada para facilitar la exploración, el análisis y la comparación de los resultados de las pruebas Saber 11 en Colombia. Su propósito es ofrecer una herramienta accesible e intuitiva para que administradores escolares, docentes, estudiantes y padres de familia puedan comprender y utilizar estos datos públicos de manera efectiva.

## Motivación

Los resultados de las pruebas Saber 11, publicados por el ICFES, son un recurso público de gran valor. Sin embargo, estos datos se distribuyen en archivos de texto masivos (microdatos) que son complejos de manejar, consultar y analizar sin herramientas especializadas o conocimientos técnicos. La tarea de descargar estos archivos, filtrar la información de un colegio específico y realizar cálculos para obtener promedios o tendencias históricas representa un obstáculo para muchos. Minerva fue creada para superar esta barrera, procesando y presentando la información de forma clara y útil.

## Características Principales

* **Exploración Interactiva:** Navegación por periodos, departamentos y colegios.
* **Análisis Detallado por Colegio:**
    * Comparativa de puntajes promedio (global y por materia) con benchmarks departamentales y nacionales.
    * Distribución de estudiantes por niveles de desempeño.
    * Evolución histórica del puntaje global promedio del colegio.
    * Histograma de la distribución de puntajes globales.
    * Listado anonimizado y ordenado de los resultados de los estudiantes (puntaje global, percentil, género, nacionalidad).
* **Acceso Seguro:** Protección de la carga inicial de la aplicación mediante Cloudflare Turnstile.
* **Interfaz Amigable:** Diseño limpio y responsivo para una fácil utilización en diferentes dispositivos.

## Pila Tecnológica

* **Backend:** Python 3, Flask (para la API y la lógica de servidor).
* **Base de Datos:** SQLite (para almacenar los datos procesados y benchmarks).
* **Frontend:** HTML5, CSS3 (utilizando el framework Pico.css), JavaScript (ECMAScript 6+).
* **Visualización de Datos:** Chart.js (para las gráficas interactivas).
* **Seguridad (CAPTCHA):** Cloudflare Turnstile (para proteger el acceso inicial).
* **Procesamiento de Datos:** Un script de Python (`create_database.py`) se encarga del procesamiento inicial de los datos crudos del ICFES para poblar la base de datos SQLite.

## Despliegue

La aplicación está diseñada para ser desplegada en plataformas como PythonAnywhere.
* La base de datos (`minerva_icfes_data.db`) es generada por el script `create_database.py` a partir de los archivos de datos del ICFES y luego puede ser desplegada junto con la aplicación.

## Licencia

Este proyecto se distribuye bajo la licencia GNU GPL. Remítase a la sección de licencias para más detalles.

## Contacto y Sugerencias

Para comentarios, sugerencias sobre nuevas funcionalidades, reporte de errores o cualquier consulta sobre Minerva, por favor contactar a través de la información proporcionada en la sección "Acerca de Minerva" dentro de la propia aplicación.