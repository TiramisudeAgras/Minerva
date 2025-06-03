// static/js/main.js

// --- Variables Globales y Selectores de DOM (al inicio del archivo) ---
const initialLoader = document.getElementById('initial-loader');
const controlsContainer = document.getElementById('controls-container');
const periodSelect = document.getElementById('period-select');
const departmentSelect = document.getElementById('department-select');
const departmentSelectLabel = document.querySelector('label[for="department-select"]');
const schoolControls = document.getElementById('school-controls');
const schoolSearch = document.getElementById('school-search');
const topNSelect = document.getElementById('top-n-select');
const schoolListContainer = document.getElementById('school-list-container');
const resultsContainer = document.getElementById('results-container');
const schoolNameHeader = document.getElementById('school-name-header');
const resultsContent = document.getElementById('results-content');
const mainLoader = document.getElementById('loader');
const minervaAsciiArtDiv = document.getElementById('minervaAsciiArtContainer');
const lastUpdatedPlaceholder = document.getElementById('last-updated-placeholder');
const copyrightYearSpan = document.getElementById('copyright-year');
const tabs = document.querySelectorAll('.tab-link');
const tabContents = document.querySelectorAll('.tab-content');

// Nuevos selectores para Turnstile y contenido de la app
const turnstileChallengeContainer = document.getElementById('turnstile-challenge-container');
const turnstileStatusMessage = document.getElementById('turnstile-status-message');
const minervaAppContainer = document.getElementById('minerva-app-container');


let allSchoolsInPeriodDepartment = []; // Para guardar la lista de colegios y filtrar localmente
let currentHistogramChartInstance = null; // Para destruir el gráfico anterior antes de crear uno nuevo
let currentEvolutionChartInstance = null; // Igual para el gráfico de evolución

    // Este ASCII es el que se muestra en la cabecera, ya está definido en el HTML via Flask.
    // No es necesario duplicarlo aquí a menos que quieras cargarlo dinámicamente por alguna razón.
    // const MINERVA_ASCII = `... tu ASCII art ...`;


// --- Funciones de Turnstile ---
async function onTurnstileSuccess(token) {
    // Esta función es llamada por Cloudflare cuando el desafío se completa exitosamente.
    // console.log("Token de Turnstile recibido:", token); // Útil para depurar
    if (turnstileStatusMessage) {
        turnstileStatusMessage.textContent = "¡Eureka! Verificación exitosa. Cargando Minerva...";
        turnstileStatusMessage.style.color = "green";
        turnstileStatusMessage.style.display = "block";
    }

    try {
        const response = await fetch('/verify-access', { // Endpoint en nuestro backend Flask
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ turnstile_token: token }),
        });

        const data = await response.json();

        if (response.ok && data.success) {
            // Si el backend confirma, ocultamos el desafío y mostramos la app.
            if (turnstileChallengeContainer) turnstileChallengeContainer.style.display = 'none';
            if (minervaAppContainer) minervaAppContainer.style.display = 'block';

            // ¡Ahora sí, a inicializar la aplicación principal!
            initializeApp();
        } else {
            // Si el backend falla la verificación.
            console.error("Fallo en la verificación del token de Turnstile por el backend:", data.message);
            if (turnstileStatusMessage) {
                turnstileStatusMessage.textContent = `Error de verificación: ${data.message || 'Intenta recargar.'}`;
                turnstileStatusMessage.style.color = "red";
                turnstileStatusMessage.style.display = "block";
            }
            // Opcional: resetear el widget si la verificación falla, para que el usuario pueda reintentar
            if (typeof turnstile !== 'undefined' && turnstile.reset) {
                const widgetElement = document.querySelector('.cf-turnstile');
                if (widgetElement) turnstile.reset(widgetElement); // Resetea el widget de Turnstile
            }
        }
    } catch (error) {
        console.error("Error al enviar el token de Turnstile al backend:", error);
        if (turnstileStatusMessage) {
            turnstileStatusMessage.textContent = "Error de comunicación con el servidor. Intenta recargar.";
            turnstileStatusMessage.style.color = "red";
            turnstileStatusMessage.style.display = "block";
        }
    }
}

function onTurnstileError(errorCode) {
    // Esta función es llamada por Cloudflare si hay un error con el widget mismo.
    console.error("Error de Cloudflare Turnstile:", errorCode);
    if (turnstileStatusMessage) {
        turnstileStatusMessage.textContent = "Error al cargar el componente de seguridad. Verifica tu conexión o extensiones del navegador e intenta recargar.";
        turnstileStatusMessage.style.color = "red";
        turnstileStatusMessage.style.display = "block";
    }
}


// --- Funciones Principales de la App ---

document.addEventListener('DOMContentLoaded', () => {
    // El ASCII art se carga desde el template de Flask directamente en el div.
    // if (minervaAsciiArtDiv && MINERVA_ASCII) {
    //     minervaAsciiArtDiv.textContent = MINERVA_ASCII;
    // }
    if (copyrightYearSpan) {
        copyrightYearSpan.textContent = new Date().getFullYear(); // Pone el año actual en el footer
    }
    // La inicialización de la app (initializeApp) ahora se llama DESPUÉS de que Turnstile sea exitoso (en onTurnstileSuccess).
});


const fetchData = async (url) => {
    if(mainLoader) mainLoader.style.display = 'block'; // Mostrar el loader principal
    try {
        const response = await fetch(url);
        if (!response.ok) {
            // Intentar obtener un mensaje de error más específico del JSON de respuesta, si existe
            let errorData = { message: `Error HTTP: ${response.status} al acceder a ${url}. Revisa la consola del servidor.` };
            try {
                const jsonError = await response.json(); // Intenta parsear el error como JSON
                errorData.message = jsonError.error || errorData.message; // Usa el error del JSON si está disponible
            } catch (e) { /* No hacer nada si el cuerpo del error no es JSON */ }
            throw new Error(errorData.message);
        }
        return await response.json(); // Parsear la respuesta JSON
    } catch (error) {
        console.error("Error en fetchData:", error.message);
        if(resultsContent && minervaAppContainer && minervaAppContainer.style.display === 'block') {
            resultsContent.innerHTML = `<p class="error">Error al cargar datos: ${error.message}. Por favor, revisa la consola para más detalles y asegúrate que el servidor Flask esté corriendo y accesible.</p>`;
        }
        throw error; // Propagar el error para que otras funciones puedan manejarlo si es necesario
    } finally {
        if(mainLoader) mainLoader.style.display = 'none'; // Ocultar el loader principal
    }
};

const renderSchoolList = (schools) => {
    schoolListContainer.innerHTML = ''; // Limpiar lista anterior
    if (!schools || schools.length === 0) {
        schoolListContainer.innerHTML = '<p style="padding:1rem; text-align:center;"><small>No se encontraron colegios para los criterios seleccionados. Prueba con otros filtros.</small></p>';
        return;
    }
    schools.forEach(school => {
        const schoolItem = document.createElement('a');
        schoolItem.href = '#results-container'; // Para que al hacer clic, scrollee a los resultados
        schoolItem.className = 'school-list-item';
        schoolItem.dataset.id = school.id; // ID único del colegio (nombre|mcpio|nat|cal|depto)
        schoolItem.dataset.displayName = school.name; // Nombre formateado para mostrar

        // NUEVO: Añadir el slash line de rankings
        let rankDisplay = '';
        if (school.rank_departmental !== null && school.rank_national !== null && school.rank_departmental !== undefined && school.rank_national !== undefined) {
            rankDisplay = `<span class="rank-slashline"> (Dep: ${school.rank_departmental} / Nac: ${school.rank_national})</span>`;
        }

        schoolItem.innerHTML = `<h6>${school.name}${rankDisplay}</h6><p>Promedio Global: <strong>${school.mean.toFixed(2)}</strong> (${school.count} estudiantes)</p>`;
        schoolListContainer.appendChild(schoolItem);
    });
};


const renderResults = (data) => {
    // Destructurar los datos recibidos del API
    const {
        school_name_display, rank_departmental, rank_national, // Nuevos campos de ranking
        student_list, benchmarks, performance_levels,
        histogram_data, historical_evolution
    } = data;

    // NUEVO: Añadir el slash line de rankings al encabezado del colegio
    let headerRankDisplay = '';
    if (rank_departmental !== null && rank_national !== null && rank_departmental !== undefined && rank_national !== undefined) {
        headerRankDisplay = ` <span class="rank-slashline">(Ranking Dept: ${rank_departmental} / Nac: ${rank_national})</span>`;
    }
    schoolNameHeader.innerHTML = school_name_display + headerRankDisplay; // Usar innerHTML para el span

    // --- HTML para cada sección de resultados ---
    const benchmarksHtml = `
        <details open><summary>Análisis Comparativo de Desempeño</summary>
        <div class="overflow-auto"><table><thead><tr><th>Materia</th><th>Prom. Colegio</th><th>Prom. Depto.</th><th>Prom. Nacional</th></tr></thead><tbody>
        ${benchmarks.map(b => `<tr><td>${b.subject}</td><td>${b.school_avg.toFixed(2)}</td><td>${b.dept_avg.toFixed(2)}</td><td>${b.nat_avg.toFixed(2)}</td></tr>`).join('')}
        </tbody></table></div></details>`;

    const levelsHtml = `
        <details><summary>Distribución de Niveles de Desempeño</summary>
        <div class="overflow-auto"><table><thead><tr><th>Materia</th><th>Nivel 1 (o A-)</th><th>Nivel 2 (o A1)</th><th>Nivel 3 (o A2)</th><th>Nivel 4 (o B1/B+)</th></tr></thead><tbody>
        ${performance_levels.map(p => {
            if (p.type === 'english') { // Para inglés, los niveles son diferentes
                return `<tr><td>${p.subject}</td><td>${p.levels['A-'] || 0}</td><td>${p.levels['A1'] || 0}</td><td>${p.levels['A2'] || 0}</td><td>${(p.levels['B1'] || 0) + (p.levels['B+'] || 0)}</td></tr>`;
            } // Sumamos B1 y B+ para el último nivel de inglés si es necesario
            return `<tr><td>${p.subject}</td><td>${p.levels['1'] || 0}</td><td>${p.levels['2'] || 0}</td><td>${p.levels['3'] || 0}</td><td>${p.levels['4'] || 0}</td></tr>`;
        }).join('')}
        </tbody></table></div></details>`;

    const histogramHtml = `<details><summary>Distribución de Puntajes Globales (Colegio)</summary><div id="histogram-chart-container"><canvas id="histogram-chart"></canvas></div></details>`;

    const studentsHtml = `
        <details><summary>Resultados Detallados de Estudiantes (${student_list.length})</summary>
        <div class="overflow-auto">
            <table><thead><tr><th>#</th><th>Fecha de Nac.</th><th>Sexo</th><th>Nacionalidad</th><th>Puntaje Global</th><th>Percentil Global</th></tr></thead><tbody>
            ${student_list.map((s, index) => `<tr><td>${index + 1}</td><td>${s.estu_fechanacimiento || 'N/D'}</td><td>${s.estu_genero || 'N/D'}</td><td>${s.estu_nacionalidad || 'N/D'}</td><td>${s.punt_global !== null ? s.punt_global : 'N/D'}</td><td>${s.percentil_global ? s.percentil_global + '%' : 'N/D'}</td></tr>`).join('')}
            </tbody></table></div></details>`;

    const evolutionHtml = `
        <details><summary>Evolución Histórica (Promedio Global del Colegio)</summary>
        <div class="overflow-auto">
            <div id="evolution-chart-container"><canvas id="evolution-chart"></canvas></div>
            <table><thead><tr><th>Periodo</th><th>Promedio Global</th></tr></thead><tbody>
            ${historical_evolution.map(h => `<tr><td>${h.periodo}</td><td>${h.media === -1 ? 'Datos de periodo no disponibles' : (h.media === 0 ? 'Colegio no encontrado/sin datos' : h.media.toFixed(2))}</td></tr>`).join('')}
            </tbody></table>
        </div></details>`;

    resultsContent.innerHTML = benchmarksHtml + levelsHtml + histogramHtml + studentsHtml + evolutionHtml;

    // Renderizar los gráficos
    renderHistogramChart(histogram_data);
    renderEvolutionChart(historical_evolution);
};


const renderHistogramChart = (scores) => {
    const canvasContainer = document.getElementById('histogram-chart-container');
    const canvas = document.getElementById('histogram-chart');
    if (!canvas || !canvasContainer) {
        console.warn("Canvas del histograma no encontrado.");
        return;
    }
    canvasContainer.style.height = '280px'; // Altura fija para el contenedor del canvas
    const ctx = canvas.getContext('2d');

    // Agrupar puntajes en rangos (bins)
    const bins = {};
    const labels = [];
    // Rangos de 0-49, 50-99, ..., 450-499 (o hasta 500 si es el máximo)
    for (let i = 0; i <= 450; i += 50) {
        const label = `${i}-${i + 49}`; // (ej. 0-49, 50-99)
        labels.push(label);
        bins[label] = 0;
    }
    // Si el puntaje máximo es 500, el último bin es 450-500.
    // Ajustamos el último label si es necesario.
    if (labels.length > 0) labels[labels.length - 1] = `450-500`;


    scores.forEach(score => {
        if (score === null || score === undefined) return; // Ignorar scores nulos
        const binIndex = Math.floor(score / 50);
        let binLabel;
        if (score === 500) { // Caso especial para el puntaje máximo
            binLabel = labels[labels.length -1]; // Asignar al último bin
        } else {
            binLabel = `${binIndex * 50}-${binIndex * 50 + 49}`;
        }

        if (bins[binLabel] !== undefined) {
            bins[binLabel]++;
        }
    });

    if (currentHistogramChartInstance) {
        currentHistogramChartInstance.destroy(); // Destruir instancia anterior para evitar conflictos
    }
    currentHistogramChartInstance = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Número de Estudiantes',
                data: Object.values(bins),
                backgroundColor: 'rgba(255, 193, 7, 0.7)', // Amarillo Minerva con transparencia
                borderColor: 'rgba(255, 160, 0, 1)', // Amarillo Minerva más oscuro para borde
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false, // Importante para que el canvas respete la altura del contenedor
            scales: {
                y: { beginAtZero: true, title: { display: true, text: 'Cantidad de Estudiantes' } },
                x: { title: { display: true, text: 'Rango de Puntaje Global' } }
            },
            plugins: { legend: { display: false } } // No necesitamos leyenda para un solo dataset
        }
    });
};

const renderEvolutionChart = (historicalDataOriginalOrder) => {
    const canvasContainer = document.getElementById('evolution-chart-container');
    const canvas = document.getElementById('evolution-chart');
    if(!canvas || !canvasContainer) {
        console.warn("Canvas del gráfico de evolución no encontrado.");
        return;
    }
    canvasContainer.style.height = '280px'; // Altura fija
    const ctx = canvas.getContext('2d');

    // Filtrar datos con media > 0 (o -1 que es nuestro placeholder de "no datos") y ordenar por periodo
    const chartData = historicalDataOriginalOrder
        .filter(d => d.media > 0) // Solo mostrar datos válidos
        .sort((a, b) => { // Ordenar por año y luego por semestre/periodo
            const [yearA, periodA] = a.periodo.split('-').map(Number);
            const [yearB, periodB] = b.periodo.split('-').map(Number);
            if (yearA !== yearB) return yearA - yearB;
            return periodA - periodB;
        });

    if (currentEvolutionChartInstance) {
        currentEvolutionChartInstance.destroy(); // Destruir instancia anterior
    }
    currentEvolutionChartInstance = new Chart(ctx, {
        type: 'line',
        data: {
            labels: chartData.map(d => d.periodo), // Ej. "2023-1", "2023-2"
            datasets: [{
                label: 'Promedio Global Histórico',
                data: chartData.map(d => d.media),
                borderColor: 'var(--minerva-yellow-hover, #FFA000)', // Usa la variable CSS si está definida
                backgroundColor: 'rgba(255, 193, 7, 0.2)', // Relleno con transparencia
                fill: true,
                tension: 0.1 // Un poco de curva en la línea
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: { beginAtZero: false, title: { display: true, text: 'Promedio Global' } },
                x: { title: { display: true, text: 'Periodo' } }
            },
            plugins: { legend: { display: false } }
        }
    });
};


const handlePeriodChange = async (event) => {
    const periodo = event.target.value;
    departmentSelect.innerHTML = '<option value="">Cargando departamentos...</option>'; // Feedback visual
    if(departmentSelectLabel) departmentSelectLabel.style.display = 'none';
    if(schoolControls) schoolControls.style.display = 'none'; // Ocultar controles de colegio
    resultsContainer.style.display = 'none'; // Ocultar resultados anteriores
    schoolListContainer.innerHTML = '<small>Seleccione un departamento.</small>'; // Mensaje inicial

    if (!periodo) return; // Si no hay periodo seleccionado, no hacer nada

    try {
        const departments = await fetchData(`/api/departments/${periodo}`);
        departmentSelect.innerHTML = '<option value="" selected>Seleccione un departamento</option>'; // Opción por defecto
        departments.forEach(dept => {
            const option = document.createElement('option');
            option.value = dept;
            option.textContent = dept;
            departmentSelect.appendChild(option);
        });
        if(departmentSelectLabel) departmentSelectLabel.style.display = 'block'; // Mostrar label y select de depto
        departmentSelect.style.display = 'block';
    } catch (error) {
        departmentSelect.innerHTML = '<option value="">Error al cargar deptos.</option>';
        console.error("Error cargando departamentos:", error);
    }
};

const loadSchoolList = async () => {
    const department = departmentSelect.value;
    const periodo = periodSelect.value;
    const topN = topNSelect.value; // Valor del filtro "Top N"

    schoolListContainer.innerHTML = '<article aria-busy="true" style="text-align:center; padding:1rem;">Cargando colegios...</article>'; // Feedback visual
    resultsContainer.style.display = 'none'; // Ocultar resultados anteriores

    if (!department || !periodo) {
        if(schoolControls) schoolControls.style.display = 'none';
        schoolListContainer.innerHTML = '<small>Seleccione periodo y departamento primero.</small>';
        return;
    }
    if(schoolControls) schoolControls.style.display = 'block'; // Mostrar controles de colegio

    let url = `/api/schools/${periodo}/${department}`;
    if (topN !== "0") { // Si no es "Todos"
        url += `?top=${topN}`; // Añadir parámetro 'top' a la URL
    }

    try {
        allSchoolsInPeriodDepartment = await fetchData(url); // Guardar la lista completa para filtrar
        renderSchoolList(allSchoolsInPeriodDepartment); // Mostrar la lista (filtrada por Top N si aplica)
    } catch (error) {
        schoolListContainer.innerHTML = '<small>Error al cargar los colegios. Intente de nuevo.</small>';
        console.error("Error cargando la lista de colegios:", error);
    }
};


const handleSchoolSearch = () => {
    const query = schoolSearch.value.toLowerCase().trim(); // Búsqueda insensible a mayúsculas/minúsculas y sin espacios extra
    if (!allSchoolsInPeriodDepartment) return; // No hay lista de colegios para filtrar

    // Filtrar la lista de colegios guardada (allSchoolsInPeriodDepartment)
    // Esta lista ya fue potencialmente filtrada por "Top N" en loadSchoolList
    const filteredSchools = allSchoolsInPeriodDepartment.filter(school =>
        school.raw_name.toLowerCase().includes(query) // Usar raw_name para la búsqueda
    );
    renderSchoolList(filteredSchools); // Volver a renderizar la lista con los colegios filtrados
};


const handleSchoolClick = async (event) => {
    event.preventDefault(); // Prevenir navegación si es un link <a>
    const target = event.target.closest('.school-list-item'); // Asegurarse que se hizo clic en un item de colegio
    if (!target) return; // Si no, no hacer nada

    resultsContainer.style.display = 'block'; // Mostrar el contenedor de resultados
    resultsContent.innerHTML = ''; // Limpiar contenido anterior
    if(mainLoader) mainLoader.style.display = 'block'; // Mostrar loader principal

    // Usar displayName del dataset para el mensaje de carga
    schoolNameHeader.textContent = "Cargando detalles (¡Esto puede tomar algunos segundos! ☕) para: " + target.dataset.displayName;
    resultsContainer.scrollIntoView({ behavior: 'smooth', block: 'start' }); // Scroll suave a los resultados

    try {
        const periodo = periodSelect.value;
        const department = departmentSelect.value; // Este es el depto del filtro, puede no ser el del colegio si se busca cross-depto (no implementado aquí)
        const schoolId = target.dataset.id; // ID único del colegio
        const encodedSchoolId = encodeURIComponent(schoolId); // Codificar por si hay caracteres especiales

        // El department en la URL es el del filtro. La info del depto del colegio va en el schoolId.
        const data = await fetchData(`/api/school_details/${periodo}/${department}/${encodedSchoolId}`);

        if(data.error){
            resultsContent.innerHTML = `<p class="error">${data.error}</p>`;
        } else {
            renderResults(data); // Mostrar los detalles del colegio
        }
    } catch (error) {
        // El error ya se maneja en fetchData, que actualiza resultsContent.
        // Aquí podríamos añadir un log extra si quisiéramos.
        console.error("Error al obtener detalles del colegio:", error);
    } finally {
        if(mainLoader) mainLoader.style.display = 'none'; // Ocultar loader principal
    }
};

// --- Navegación por Pestañas ---
const handleTabClick = (event) => {
    event.preventDefault();
    tabs.forEach(tab => tab.classList.remove('active')); // Quitar 'active' de todas las pestañas
    tabContents.forEach(content => content.classList.remove('active')); // Ocultar todo el contenido

    const clickedTabLink = event.currentTarget;
    clickedTabLink.classList.add('active'); // Marcar la pestaña clickeada como activa

    const activeTabContentId = clickedTabLink.dataset.tab; // Obtener el ID del contenido de la pestaña
    const activeTabContent = document.getElementById(activeTabContentId);
    if (activeTabContent) {
        activeTabContent.classList.add('active'); // Mostrar el contenido correspondiente
    }
    window.location.hash = activeTabContentId; // Actualizar el hash en la URL para deep linking
};

// Esta es la función que ahora se llama DESPUÉS de la verificación de Turnstile
const initializeApp = async () => {
    // Esta función se encarga de configurar la app una vez verificado el acceso.
    if(initialLoader) initialLoader.style.display = 'block'; // Mostrar loader inicial de la app
    if(controlsContainer) controlsContainer.style.display = 'none'; // Ocultar controles hasta cargar periodos

    try {
        const periods = await fetchData('/api/periods'); // Cargar periodos disponibles
        if(initialLoader) initialLoader.style.display = 'none'; // Ocultar loader inicial
        if(controlsContainer) controlsContainer.style.display = 'block'; // Mostrar controles
        periodSelect.innerHTML = '<option value="" selected>Seleccione un periodo</option>'; // Opción por defecto

        periods.forEach(period => {
            const option = document.createElement('option');
            option.value = period.value; // Ej: "20231"
            option.textContent = period.display; // Ej: "2023-1"
            periodSelect.appendChild(option);
        });

        // Cargar la fecha de "última actualización" desde el atributo data-* en el body (inyectado por Flask)
        const lastUpdatedFromHTML = document.body.dataset.lastUpdatedDate;
        if (lastUpdatedPlaceholder && lastUpdatedFromHTML) {
            lastUpdatedPlaceholder.textContent = lastUpdatedFromHTML;
        } else if (lastUpdatedPlaceholder) {
            lastUpdatedPlaceholder.textContent = "No disponible";
        }

    } catch (error) {
        if(initialLoader) initialLoader.innerHTML = 'Error al cargar periodos iniciales. Intente recargar la página.';
        console.error("Error fatal inicializando la app (cargando periodos):", error);
    }

    // --- Event Listeners ---
    periodSelect.addEventListener('change', handlePeriodChange);
    departmentSelect.addEventListener('change', loadSchoolList);
    topNSelect.addEventListener('change', loadSchoolList); // Recargar lista si cambia el Top N
    schoolSearch.addEventListener('input', handleSchoolSearch); // Filtrar mientras se escribe
    schoolListContainer.addEventListener('click', handleSchoolClick); // Cargar detalles al hacer clic en un colegio

    tabs.forEach(tab => tab.addEventListener('click', handleTabClick)); // Manejar clics en pestañas

    // Activar pestaña según el hash en la URL o la primera por defecto
    const currentHash = window.location.hash.substring(1); // Quitar el '#'
    const targetTab = currentHash || 'explorar'; // Si no hay hash, ir a 'explorar'

    tabs.forEach(tab => tab.classList.remove('active'));
    tabContents.forEach(content => content.classList.remove('active'));

    const activeTabLink = document.querySelector(`.tab-link[data-tab="${targetTab}"]`);
    if (activeTabLink) {
        activeTabLink.classList.add('active');
        const activeContent = document.getElementById(targetTab);
        if (activeContent) activeContent.classList.add('active');
    } else { // Fallback a la primera pestaña si el hash no es válido
        const defaultTabLink = document.querySelector('.tab-link[data-tab="explorar"]');
        if (defaultTabLink) defaultTabLink.classList.add('active');
        const defaultTabContent = document.getElementById('explorar');
        if (defaultTabContent) defaultTabContent.classList.add('active');
    }
};