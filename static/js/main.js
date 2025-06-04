// static/js/main.js

// --- Variables Globales y Selectores de DOM ---
const initialLoader = document.getElementById('initial-loader');
const controlsContainer = document.getElementById('controls-container');
const periodSelect = document.getElementById('period-select');
const departmentSelect = document.getElementById('department-select');
const departmentSelectLabel = document.querySelector('label[for="department-select"]');
const schoolControls = document.getElementById('school-controls');
const schoolSearch = document.getElementById('school-search');
const schoolListContainer = document.getElementById('school-list-container');
const resultsContainer = document.getElementById('results-container');
const schoolNameHeader = document.getElementById('school-name-header');
const resultsContent = document.getElementById('results-content');
const mainLoader = document.getElementById('loader'); // Loader for school details view
const copyrightYearSpan = document.getElementById('copyright-year');
const tabs = document.querySelectorAll('.tab-link');
const tabContents = document.querySelectorAll('.tab-content');

const turnstileChallengeContainer = document.getElementById('turnstile-challenge-container');
const turnstileStatusMessage = document.getElementById('turnstile-status-message');
const minervaAppContainer = document.getElementById('minerva-app-container');

const searchStatusMessage = document.getElementById('search-status-message');

// --- Global variables for pagination and loading state ---
let allSchoolsInPeriodDepartment = [];
let fuseInstance = null;
const DEFAULT_DISPLAY_COUNT = 50; // For Fuse search results display
const SCHOOLS_PER_PAGE = 100; // Must match what create_database.py uses for static JSONs
const STATIC_DATA_BASE_PATH = '/static/generated_school_data/schools'; // Adjust if your path is different

let currentSchoolListPage = 1; // Tracks the last successfully fetched page for the current list
let totalSchoolListPages = 1;
let totalSchoolsInDepartment = 0;
let isLoadingMoreSchools = false; 
let allSchoolsLoadedForDepartment = false;

let currentHistogramChartInstance = null;
let currentEvolutionChartInstance = null;
let searchDebounceTimer;

const LOADING_MESSAGES = [
    "Consultando los anales académicos...",
    "Desempolvando los pergaminos del ICFES...",
    "Ajustando el monóculo de Minerva...",
    "Filtrando colegios del departamento...",
    "Compilando la lista progresivamente...",
    "¡Preparando los primeros resultados!"
];
let cyclingMessageInterval;
let currentCyclingMessageIndex = 0;

// --- Funciones de Turnstile --- (Keep as is)
async function onTurnstileSuccess(token) {
    if (turnstileStatusMessage) {
        turnstileStatusMessage.textContent = "¡Eureka! Verificación exitosa. Cargando Minerva...";
        turnstileStatusMessage.style.color = "green"; turnstileStatusMessage.style.display = "block";
    }
    try {
        const response = await fetch('/verify-access', {
            method: 'POST', headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ turnstile_token: token }),
        });
        const data = await response.json();
        if (response.ok && data.success) {
            if (turnstileChallengeContainer) turnstileChallengeContainer.style.display = 'none';
            if (minervaAppContainer) minervaAppContainer.style.display = 'block';
            initializeApp();
        } else {
            console.error("Fallo en la verificación del token (backend):", data.message);
            if (turnstileStatusMessage) {
                turnstileStatusMessage.textContent = `Error de verificación: ${data.message || 'Intenta recargar.'}`;
                turnstileStatusMessage.style.color = "red";
            }
            if (typeof turnstile !== 'undefined' && turnstile.reset) {
                const widgetElement = document.querySelector('.cf-turnstile');
                if (widgetElement) turnstile.reset(widgetElement);
            }
        }
    } catch (error) {
        console.error("Error al enviar token de Turnstile al backend:", error);
        if (turnstileStatusMessage) {
            turnstileStatusMessage.textContent = "Error de comunicación con el servidor. Intenta recargar.";
            turnstileStatusMessage.style.color = "red";
        }
    }
}
function onTurnstileError(errorCode) {
    console.error("Error de Cloudflare Turnstile:", errorCode);
    if (turnstileStatusMessage) {
        turnstileStatusMessage.textContent = "Error al cargar el componente de seguridad. Verifica tu conexión e intenta recargar.";
        turnstileStatusMessage.style.color = "red"; turnstileStatusMessage.style.display = "block";
    }
}


// --- Funciones Principales de la App ---
document.addEventListener('DOMContentLoaded', () => {
    if (copyrightYearSpan) copyrightYearSpan.textContent = new Date().getFullYear();
    if (schoolSearch && schoolControls && schoolControls.style.display === 'none') {
        schoolSearch.disabled = true;
        schoolSearch.placeholder = "Seleccione periodo y depto...";
    }
    schoolListContainer.addEventListener('scroll', handleSchoolListScroll);
});

const fetchData = async (url, isJson = true) => { // Added isJson flag
    try {
        const response = await fetch(url);
        if (!response.ok) {
            // For static JSON, a 404 is a common "error" if file doesn't exist
            if (response.status === 404) {
                console.warn(`FetchData: Recurso no encontrado (404) en ${url}`);
                throw new Error(`Recurso no encontrado: ${url.substring(url.lastIndexOf('/') + 1)}`);
            }
            let errorData = { message: `Error HTTP ${response.status} en ${url}.` };
            if (isJson) {
                try { 
                    const jsonError = await response.json(); 
                    errorData.message = jsonError.error || errorData.message; 
                    console.error("Server error response (JSON):", jsonError);
                }
                catch (e) { 
                    console.error("Could not parse error response as JSON, or response was not JSON.");
                     const textError = await response.text(); // Try to get text if not JSON
                     errorData.message += ` Contenido: ${textError.substring(0,100)}`;
                }
            } else {
                 const textError = await response.text();
                 errorData.message += ` Contenido: ${textError.substring(0,100)}`;
            }
            throw new Error(errorData.message);
        }
        return isJson ? await response.json() : await response.text();
    } catch (error) {
        console.error("Error en fetchData:", error.message);
        throw error; // Re-throw for the caller to handle
    }
};


const renderSchoolList = (schoolsToDisplay, append = false) => {
    if (!append) {
        schoolListContainer.innerHTML = ''; 
    }

    const loadingMoreMessage = schoolListContainer.querySelector('.loading-more-schools');
    if (loadingMoreMessage) {
        loadingMoreMessage.remove();
    }

    if (!schoolsToDisplay || schoolsToDisplay.length === 0) {
        if (!append || schoolListContainer.children.length === 0) {
            const searchTerm = schoolSearch.value.trim();
            if (searchTerm && !append) {
                schoolListContainer.innerHTML = '<p style="padding:1rem; text-align:center;"><small>No se encontraron colegios que coincidan con tu búsqueda actual.</small></p>';
            } else if (!append && !isLoadingMoreSchools) { // Avoid overwriting loading message
                 // schoolListContainer.innerHTML = '<p style="padding:1rem; text-align:center;"><small>No hay colegios para mostrar.</small></p>';
            }
        }
        return;
    }

    const fragment = document.createDocumentFragment();
    schoolsToDisplay.forEach(school => {
        const schoolItem = document.createElement('a');
        schoolItem.href = '#results-container'; schoolItem.className = 'school-list-item';
        schoolItem.dataset.id = school.id; schoolItem.dataset.displayName = school.name;
        let rankDisplay = '';
        if (school.rank_departmental != null && school.rank_national != null) {
            rankDisplay = `<span class="rank-slashline"> (Dep: ${school.rank_departmental} / Nac: ${school.rank_national})</span>`;
        }
        schoolItem.innerHTML = `<h6>${school.name}${rankDisplay}</h6><p>Promedio Global: <strong>${typeof school.mean === 'number' ? school.mean.toFixed(2) : 'N/D'}</strong> (${school.count} estudiantes)</p>`;
        fragment.appendChild(schoolItem);
    });
    schoolListContainer.appendChild(fragment);
};

const renderResults = (data) => { /* Keep as is */ 
    if(mainLoader) mainLoader.style.display = 'block';
    const { school_name_display, rank_departmental, rank_national, student_list, benchmarks, performance_levels, histogram_data, historical_evolution } = data;
    let headerRankDisplay = '';
    if (rank_departmental != null && rank_national != null) {
        headerRankDisplay = ` <span class="rank-slashline">(Ranking Dept: ${rank_departmental} / Nac: ${rank_national})</span>`;
    }
    schoolNameHeader.innerHTML = school_name_display + headerRankDisplay;
    const benchmarksHtml = `<details open><summary>Análisis Comparativo</summary><div class="overflow-auto"><table><thead><tr><th>Materia</th><th>Prom. Colegio</th><th>Prom. Depto.</th><th>Prom. Nacional</th></tr></thead><tbody>${benchmarks.map(b => `<tr><td>${b.subject}</td><td>${b.school_avg.toFixed(2)}</td><td>${b.dept_avg.toFixed(2)}</td><td>${b.nat_avg.toFixed(2)}</td></tr>`).join('')}</tbody></table></div></details>`;
    const levelsHtml = `<details><summary>Niveles de Desempeño</summary><div class="overflow-auto"><table><thead><tr><th>Materia</th><th>Nivel 1 (A-)</th><th>Nivel 2 (A1)</th><th>Nivel 3 (A2)</th><th>Nivel 4 (B1/B+)</th></tr></thead><tbody>${performance_levels.map(p => p.type === 'english' ? `<tr><td>${p.subject}</td><td>${p.levels['A-']||0}</td><td>${p.levels['A1']||0}</td><td>${p.levels['A2']||0}</td><td>${(p.levels['B1']||0)+(p.levels['B+']||0)}</td></tr>` : `<tr><td>${p.subject}</td><td>${p.levels['1']||0}</td><td>${p.levels['2']||0}</td><td>${p.levels['3']||0}</td><td>${p.levels['4']||0}</td></tr>`).join('')}</tbody></table></div></details>`;
    const histogramHtml = `<details><summary>Distribución Puntajes Globales</summary><div id="histogram-chart-container"><canvas id="histogram-chart"></canvas></div></details>`;
    const studentsHtml = `<details><summary>Resultados Detallados (${student_list.length})</summary><div class="overflow-auto"><table><thead><tr><th>#</th><th>Nacimiento</th><th>Sexo</th><th>Nacionalidad</th><th>Punt. Global</th><th>Percentil Global</th></tr></thead><tbody>${student_list.map((s, i) => `<tr><td>${i+1}</td><td>${s.estu_fechanacimiento||'N/D'}</td><td>${s.estu_genero||'N/D'}</td><td>${s.estu_nacionalidad||'N/D'}</td><td>${s.punt_global!=null?s.punt_global:'N/D'}</td><td>${s.percentil_global?s.percentil_global+'%':'N/D'}</td></tr>`).join('')}</tbody></table></div></details>`;
    const evolutionHtml = `<details><summary>Evolución Histórica</summary><div class="overflow-auto"><div id="evolution-chart-container"><canvas id="evolution-chart"></canvas></div><table><thead><tr><th>Periodo</th><th>Prom. Global</th></tr></thead><tbody>${historical_evolution.map(h => `<tr><td>${h.periodo}</td><td>${h.media === -1 ? 'N/D Periodo' : (h.media === 0 ? 'N/D Colegio' : h.media.toFixed(2))}</td></tr>`).join('')}</tbody></table></div></details>`;
    resultsContent.innerHTML = benchmarksHtml + levelsHtml + histogramHtml + studentsHtml + evolutionHtml;
    renderHistogramChart(histogram_data);
    renderEvolutionChart(historical_evolution);
    if(mainLoader) mainLoader.style.display = 'none';
};
const renderHistogramChart = (scores) => { /* Keep as is */ const canvasContainer = document.getElementById('histogram-chart-container'); const canvas = document.getElementById('histogram-chart'); if (!canvas || !canvasContainer) return; canvasContainer.style.height = '280px'; const ctx = canvas.getContext('2d'); const bins = {}; const labels = []; for (let i = 0; i <= 450; i += 50) { const label = `${i}-${i + 49}`; labels.push(label); bins[label] = 0; } if (labels.length > 0) labels[labels.length - 1] = `450-500`; scores.forEach(score => { if (score === null || score === undefined) return; const binIndex = Math.floor(score / 50); let binLabel; if (score === 500) { binLabel = labels[labels.length -1]; } else { binLabel = `${binIndex*50}-${binIndex*50+49}`; } if (bins[binLabel] !== undefined) bins[binLabel]++; }); if (currentHistogramChartInstance) currentHistogramChartInstance.destroy(); currentHistogramChartInstance = new Chart(ctx, { type: 'bar', data: { labels: labels, datasets: [{ label: 'Número de Estudiantes', data: Object.values(bins), backgroundColor: 'rgba(255,193,7,0.7)', borderColor: 'rgba(255,160,0,1)', borderWidth: 1 }] }, options: { responsive: true, maintainAspectRatio: false, scales: { y: { beginAtZero: true, title: { display: true, text: 'Cantidad de Estudiantes'}}, x: { title: { display: true, text: 'Rango de Puntaje Global'}}}, plugins: { legend: { display: false }}}});};
const renderEvolutionChart = (historicalDataOriginalOrder) => { /* Keep as is */ const canvasContainer = document.getElementById('evolution-chart-container'); const canvas = document.getElementById('evolution-chart'); if(!canvas || !canvasContainer) return; canvasContainer.style.height = '280px'; const ctx = canvas.getContext('2d'); const chartData = historicalDataOriginalOrder.filter(d => d.media > 0).sort((a,b) => { const [yA,pA]=a.periodo.split('-').map(Number); const [yB,pB]=b.periodo.split('-').map(Number); if(yA!==yB)return yA-yB; return pA-pB; }); if (currentEvolutionChartInstance) currentEvolutionChartInstance.destroy(); currentEvolutionChartInstance = new Chart(ctx, { type: 'line', data: { labels: chartData.map(d=>d.periodo), datasets: [{ label: 'Promedio Global Histórico', data: chartData.map(d=>d.media), borderColor: 'var(--minerva-yellow-hover,#FFA000)', backgroundColor: 'rgba(255,193,7,0.2)', fill: true, tension: 0.1 }] }, options: { responsive: true, maintainAspectRatio: false, scales: { y: { beginAtZero: false, title: { display: true, text: 'Promedio Global'}}, x: { title: { display: true, text: 'Periodo'}}}, plugins: { legend: { display: false }}}});};


const handlePeriodChange = async (event) => {
    const periodo = event.target.value;
    departmentSelect.innerHTML = '<option value="">Cargando departamentos...</option>';
    if(departmentSelectLabel) departmentSelectLabel.style.display = 'none';
    if(schoolControls) schoolControls.style.display = 'none';
    resultsContainer.style.display = 'none';
    if (schoolListContainer) schoolListContainer.innerHTML = '<small>Seleccione un departamento.</small>';
    
    if (schoolSearch) {
        schoolSearch.value = '';
        schoolSearch.disabled = true;
        schoolSearch.placeholder = "Seleccione departamento...";
    }
    if (searchStatusMessage) searchStatusMessage.textContent = '';

    allSchoolsInPeriodDepartment = [];
    fuseInstance = null;
    currentSchoolListPage = 1;
    totalSchoolListPages = 1;
    totalSchoolsInDepartment = 0;
    allSchoolsLoadedForDepartment = false;
    isLoadingMoreSchools = false;
    stopCyclingLoadingAnimation();

    if (!periodo) return;
    try {
        // This API call for departments could also be a static JSON if departments per period are fixed
        const departments = await fetchData(`/api/departments/${periodo}`);
        departmentSelect.innerHTML = '<option value="" selected>Seleccione un departamento</option>';
        departments.forEach(dept => { const opt=document.createElement('option'); opt.value=dept; opt.textContent=dept; departmentSelect.appendChild(opt); });
        if(departmentSelectLabel) departmentSelectLabel.style.display = 'block';
        departmentSelect.style.display = 'block';
    } catch (error) { departmentSelect.innerHTML = '<option value="">Error al cargar deptos.</option>'; }
};

function startCyclingLoadingAnimation(initialMessage = "Cargando...") {
    stopCyclingLoadingAnimation(); 
    currentCyclingMessageIndex = 0;
    const messageToShow = LOADING_MESSAGES[currentCyclingMessageIndex] || initialMessage;
    
    if (schoolListContainer) schoolListContainer.innerHTML = ''; 
    
    const loaderArticle = document.createElement('article');
    loaderArticle.setAttribute('aria-busy', 'true');
    loaderArticle.style.textAlign = 'center';
    loaderArticle.style.padding = '1rem';
    
    const messageParagraph = document.createElement('p');
    messageParagraph.id = 'cycling-loader-message';
    messageParagraph.textContent = messageToShow;
    
    loaderArticle.appendChild(messageParagraph);
    if (schoolListContainer) schoolListContainer.appendChild(loaderArticle);
    
    const messageElement = document.getElementById('cycling-loader-message');
    if (!messageElement) { console.error("cycling-loader-message element not found after creation"); return; }

    cyclingMessageInterval = setInterval(() => {
        currentCyclingMessageIndex = (currentCyclingMessageIndex + 1) % LOADING_MESSAGES.length;
        messageElement.textContent = LOADING_MESSAGES[currentCyclingMessageIndex];
    }, 2500);
}

function stopCyclingLoadingAnimation() {
    clearInterval(cyclingMessageInterval);
}

const loadSchoolList = async () => { 
    const department = departmentSelect.value;
    const periodo = periodSelect.value;

    allSchoolsInPeriodDepartment = [];
    fuseInstance = null;
    currentSchoolListPage = 1; // Reset to page 1 for new selection
    totalSchoolListPages = 1;
    totalSchoolsInDepartment = 0;
    allSchoolsLoadedForDepartment = false;
    isLoadingMoreSchools = false; 
    stopCyclingLoadingAnimation();
    if (schoolListContainer) schoolListContainer.innerHTML = ''; 

    if (schoolSearch) {
        schoolSearch.value = ''; 
        schoolSearch.disabled = true;
        schoolSearch.placeholder = "Cargando información...";
    }
    if (searchStatusMessage) searchStatusMessage.textContent = 'Iniciando carga de metadatos...';
    resultsContainer.style.display = 'none';

    if (!department || !periodo) {
        if(schoolControls) schoolControls.style.display = 'none';
        if (schoolListContainer) schoolListContainer.innerHTML = '<small>Seleccione periodo y departamento primero.</small>';
        if (schoolSearch) schoolSearch.placeholder = "Seleccione periodo y depto...";
        if (searchStatusMessage) searchStatusMessage.textContent = '';
        return;
    }

    if(schoolControls) schoolControls.style.display = 'block';
    startCyclingLoadingAnimation(`Obteniendo metadatos para ${department}...`);

    const encodedDepartment = department.replace(/ /g, '_').replace(/\//g, '_'); // Make it filename safe
    const metaFileUrl = `${STATIC_DATA_BASE_PATH}/${periodo}/${encodedDepartment}_meta.json`;

    try {
        const metaData = await fetchData(metaFileUrl);
        totalSchoolsInDepartment = metaData.total_count;
        totalSchoolListPages = metaData.total_pages;
        // SCHOOLS_PER_PAGE is already a global const, metaData.per_page should match it.

        if (totalSchoolsInDepartment === 0 || totalSchoolListPages === 0) {
            stopCyclingLoadingAnimation();
            if (schoolListContainer) schoolListContainer.innerHTML = `<p style="padding:1rem; text-align:center;"><small>No hay datos de colegios disponibles para ${department} en el periodo ${periodo}.</small></p>`;
            if (searchStatusMessage) searchStatusMessage.textContent = 'No hay datos disponibles.';
            if (schoolSearch) schoolSearch.placeholder = "No hay datos";
            return;
        }
        
        // Now start fetching the first chunk of actual school data
        startCyclingLoadingAnimation(`Cargando primera página de colegios para ${department}...`);
        await fetchAndProcessSchoolChunk(periodo, encodedDepartment, 1, true);

    } catch (error) {
        console.error(`Error al cargar metadatos desde ${metaFileUrl}:`, error);
        stopCyclingLoadingAnimation();
        if (schoolListContainer) schoolListContainer.innerHTML = `<small>Error al cargar información de colegios para ${department}. Es posible que no haya datos pregenerados. (${error.message})</small>`;
        if (searchStatusMessage) searchStatusMessage.textContent = 'Error al cargar metadatos.';
        if (schoolSearch) {
            schoolSearch.placeholder = "Error de carga";
            schoolSearch.disabled = true;
        }
    }
};

async function fetchAndProcessSchoolChunk(periodo, encodedDepartment, pageToFetch, isInitialOverallCall = false) {
    // isInitialOverallCall refers to the very first chunk for a new department/period selection
    
    // This check prevents re-fetching the same page if multiple triggers (scroll, background) occur closely.
    // isLoadingMoreSchools is set to true at the start of this function and false at the end.
    if (isLoadingMoreSchools && !isInitialOverallCall) {
      // console.log(`fetchAndProcessSchoolChunk: Already loading, request for page ${pageToFetch} ignored.`);
      return;
    }
    if (allSchoolsLoadedForDepartment && !isInitialOverallCall) {
      // console.log(`fetchAndProcessSchoolChunk: All schools already loaded, request for page ${pageToFetch} ignored.`);
      return;
    }

    isLoadingMoreSchools = true; // Set loading flag

    if (!isInitialOverallCall && schoolListContainer) {
        let loadingMoreEl = schoolListContainer.querySelector('.loading-more-schools');
        if (!loadingMoreEl) {
            loadingMoreEl = document.createElement('p');
            loadingMoreEl.className = 'loading-more-schools';
            loadingMoreEl.style.textAlign = 'center';
            loadingMoreEl.innerHTML = '<small aria-busy="true">Cargando más colegios...</small>';
            schoolListContainer.appendChild(loadingMoreEl);
        }
    }
    if (searchStatusMessage && pageToFetch > 1) { // Only update for subsequent pages
        searchStatusMessage.textContent = `Cargando página ${pageToFetch} de ${totalSchoolListPages}...`;
    }

    const pageFileUrl = `${STATIC_DATA_BASE_PATH}/${periodo}/${encodedDepartment}_page_${pageToFetch}.json`;

    try {
        const pageData = await fetchData(pageFileUrl);
        const newSchools = pageData.schools; // Assuming static JSONs have a "schools" key

        if (isInitialOverallCall) { // This was the first chunk of a new department selection
            stopCyclingLoadingAnimation();
            if (schoolListContainer) schoolListContainer.innerHTML = ''; // Clear cycling animation
        }
        
        allSchoolsInPeriodDepartment.push(...newSchools);
        currentSchoolListPage = pageToFetch; // Update to the page number just fetched

        if (typeof Fuse !== 'undefined' && allSchoolsInPeriodDepartment.length > 0) {
            fuseInstance = new Fuse(allSchoolsInPeriodDepartment, {
                keys: ['raw_name', 'name'], includeScore: true, threshold: 0.4, minMatchCharLength: 2,
            });
            console.log(`Fuse.js actualizado. Total colegios indexados: ${allSchoolsInPeriodDepartment.length}`);
        } else if (typeof Fuse === 'undefined') {
            console.error("Fuse.js no está cargado.");
        }
        
        renderSchoolList(newSchools, !isInitialOverallCall); 

        if (currentSchoolListPage >= totalSchoolListPages) {
            allSchoolsLoadedForDepartment = true;
            if (searchStatusMessage) searchStatusMessage.textContent = `Se cargaron todos los ${totalSchoolsInDepartment} colegios.`;
            console.log("Todos los colegios del departamento han sido cargados.");
            const loadMoreButton = schoolListContainer.querySelector('.load-more-schools-button');
            if (loadMoreButton) loadMoreButton.remove();

        } else {
            if (searchStatusMessage) {
                 searchStatusMessage.textContent = `Mostrando ${allSchoolsInPeriodDepartment.length} de ${totalSchoolsInDepartment} colegios.`;
            }
            // --- Chain background loading for the next chunk ---
            if (!allSchoolsLoadedForDepartment) {
                const nextPageForBackground = currentSchoolListPage + 1;
                setTimeout(() => { 
                    if (!isLoadingMoreSchools && !allSchoolsLoadedForDepartment && nextPageForBackground <= totalSchoolListPages) {
                        fetchAndProcessSchoolChunk(periodo, encodedDepartment, nextPageForBackground, false);
                    }
                }, 250); 
            }
            // --- End Chain ---
        }
        
        if (schoolSearch && schoolSearch.disabled && allSchoolsInPeriodDepartment.length > 0) {
            schoolSearch.disabled = false;
            schoolSearch.placeholder = "Buscar por nombre...";
        }

    } catch (error) {
        console.error(`Error al cargar la página de colegios ${pageToFetch} desde ${pageFileUrl}:`, error);
        if (isInitialOverallCall) {
            stopCyclingLoadingAnimation();
            if (schoolListContainer) schoolListContainer.innerHTML = `<small>Error al cargar la lista inicial de colegios. (${error.message})</small>`;
        }
        if (searchStatusMessage) searchStatusMessage.textContent = 'Error al cargar página de colegios.';
    } finally {
        isLoadingMoreSchools = false;
        const loadingMoreMsgEl = schoolListContainer.querySelector('.loading-more-schools');
        if (loadingMoreMsgEl) { 
            loadingMoreMsgEl.remove();
        }
    }
}

const handleSchoolListScroll = () => {
    if (isLoadingMoreSchools || allSchoolsLoadedForDepartment || !schoolListContainer || totalSchoolListPages <= currentSchoolListPage) {
        return;
    }
    if (schoolListContainer.scrollTop + schoolListContainer.clientHeight >= schoolListContainer.scrollHeight - 300) {
        const nextPageToFetch = currentSchoolListPage + 1;
        if (nextPageToFetch <= totalSchoolListPages) {
            console.log("Scroll detectado, cargando siguiente página:", nextPageToFetch);
            const periodo = periodSelect.value;
            const department = departmentSelect.value;
            const encodedDepartment = department.replace(/ /g, '_').replace(/\//g, '_');
            fetchAndProcessSchoolChunk(periodo, encodedDepartment, nextPageToFetch, false);
        }
    }
};

const handleSchoolSearch = () => {
    clearTimeout(searchDebounceTimer);
    searchDebounceTimer = setTimeout(() => {
        if (!schoolSearch) return;

        const existingLoadMoreButton = schoolListContainer.querySelector('.load-more-schools-button');
        if (existingLoadMoreButton) {
            existingLoadMoreButton.remove();
        }

        if (schoolSearch.disabled) {
            if(searchStatusMessage) searchStatusMessage.textContent = "La búsqueda está deshabilitada.";
            return;
        }
        if (!fuseInstance && allSchoolsInPeriodDepartment.length > 0) {
            if(searchStatusMessage) searchStatusMessage.textContent = "El índice de búsqueda se está preparando...";
            return; 
        }
        if (!fuseInstance) {
            if(searchStatusMessage && schoolListContainer && schoolListContainer.children.length > 0) searchStatusMessage.textContent = "Índice de búsqueda no disponible.";
            else if (searchStatusMessage) searchStatusMessage.textContent = "Seleccione periodo y departamento.";
            renderSchoolList([], false); 
            return;
        }

        const searchTerm = schoolSearch.value.trim().toLowerCase();

        if (!searchTerm) {
            renderSchoolList(allSchoolsInPeriodDepartment.slice(0, DEFAULT_DISPLAY_COUNT), false);
            if (searchStatusMessage) {
                if (allSchoolsLoadedForDepartment) {
                    searchStatusMessage.textContent = `Mostrando ${Math.min(DEFAULT_DISPLAY_COUNT, allSchoolsInPeriodDepartment.length)} de ${totalSchoolsInDepartment} colegios.`;
                } else {
                    searchStatusMessage.textContent = `Mostrando ${Math.min(DEFAULT_DISPLAY_COUNT, allSchoolsInPeriodDepartment.length)} de ${allSchoolsInPeriodDepartment.length} colegios cargados (de ${totalSchoolsInDepartment} total).`;
                }
            }
            return;
        }
        
        const fuseResults = fuseInstance.search(searchTerm);
        const filteredSchools = fuseResults.map(result => result.item);
        renderSchoolList(filteredSchools.slice(0, DEFAULT_DISPLAY_COUNT * 2), false); 
        
        if (searchStatusMessage) {
            searchStatusMessage.textContent = `Se encontraron ${filteredSchools.length} colegios para "${searchTerm}". Mostrando hasta ${DEFAULT_DISPLAY_COUNT * 2}.`;
        }

        if (filteredSchools.length < 5 && !allSchoolsLoadedForDepartment && !isLoadingMoreSchools) {
            const loadMoreButton = document.createElement('button');
            loadMoreButton.textContent = `Cargar más colegios (${allSchoolsInPeriodDepartment.length} de ${totalSchoolsInDepartment} cargados)`;
            loadMoreButton.className = 'load-more-schools-button outline';
            loadMoreButton.style.marginTop = '1rem'; loadMoreButton.style.display = 'block';
            loadMoreButton.style.marginLeft = 'auto'; loadMoreButton.style.marginRight = 'auto';

            loadMoreButton.addEventListener('click', async () => {
                loadMoreButton.setAttribute('aria-busy', 'true');
                loadMoreButton.textContent = 'Cargando...';
                const nextPageToFetch = currentSchoolListPage + 1;
                if (nextPageToFetch <= totalSchoolListPages) {
                    const periodo = periodSelect.value;
                    const department = departmentSelect.value;
                    const encodedDepartment = department.replace(/ /g, '_').replace(/\//g, '_');
                    await fetchAndProcessSchoolChunk(periodo, encodedDepartment, nextPageToFetch, false);
                }
                if (allSchoolsLoadedForDepartment && loadMoreButton.parentElement) {
                     loadMoreButton.remove();
                } else if (loadMoreButton.parentElement) {
                    loadMoreButton.setAttribute('aria-busy', 'false');
                     if (!allSchoolsLoadedForDepartment) {
                        loadMoreButton.textContent = `Cargar más (${allSchoolsInPeriodDepartment.length} de ${totalSchoolsInDepartment} cargados)`;
                     } else {
                        loadMoreButton.remove();
                     }
                }
            });
            if (schoolListContainer) schoolListContainer.appendChild(loadMoreButton);
        }

    }, 300);
};


const handleSchoolClick = async (event) => { /* Keep as is */ 
    event.preventDefault(); 
    const target = event.target.closest('.school-list-item'); 
    if (!target) return;
    
    resultsContainer.style.display = 'block'; 
    resultsContent.innerHTML = ''; 
    if(mainLoader) mainLoader.style.display = 'block';
    schoolNameHeader.textContent = "Cargando detalles para: " + target.dataset.displayName + "... ☕";
    resultsContainer.scrollIntoView({ behavior: 'smooth', block: 'start' });
    
    try {
        const periodo = periodSelect.value; 
        const department = departmentSelect.value; 
        const schoolId = target.dataset.id;
        
        const encodedDepartment = encodeURIComponent(department); // Department name for API
        const encodedSchoolId = encodeURIComponent(schoolId);
        
        const url = `/api/school_details/${periodo}/${encodedDepartment}/${encodedSchoolId}`;
        
        const data = await fetchData(url);
        
        if(data.error) { 
            resultsContent.innerHTML = `<p class="error">${data.error}</p>`; 
        } else { 
            renderResults(data); 
        }
    } catch (error) { 
        console.error("Error in handleSchoolClick:", error);
        resultsContent.innerHTML = `<p class="error">Error al cargar los detalles del colegio: ${error.message}</p>`;
    } finally { 
        if(mainLoader) mainLoader.style.display = 'none'; 
    }
};

const handleTabClick = (event) => { /* Keep as is */ event.preventDefault(); tabs.forEach(t=>t.classList.remove('active')); tabContents.forEach(c=>c.classList.remove('active')); const clkT = event.currentTarget; clkT.classList.add('active'); const activeId = clkT.dataset.tab; const activeCont = document.getElementById(activeId); if(activeCont)activeCont.classList.add('active'); window.location.hash=activeId;};

const initializeApp = async () => {
    if(initialLoader) initialLoader.style.display = 'block'; 
    if(controlsContainer) controlsContainer.style.display = 'none';
    if(searchStatusMessage) searchStatusMessage.textContent = '';

    try {
        const periods = await fetchData('/api/periods');
        if(initialLoader) initialLoader.style.display = 'none'; 
        if(controlsContainer) controlsContainer.style.display = 'block';
        periodSelect.innerHTML = '<option value="" selected>Seleccione un periodo</option>';
        periods.forEach(p => { const o=document.createElement('option'); o.value=p.value; o.textContent=p.display; periodSelect.appendChild(o); });
        
    } catch (error) {
        if(initialLoader) initialLoader.innerHTML = 'Error al cargar periodos. Intente recargar.';
    }

    periodSelect.addEventListener('change', handlePeriodChange);
    departmentSelect.addEventListener('change', () => {
        loadSchoolList(); 
    });
    schoolSearch.addEventListener('input', handleSchoolSearch);
    schoolListContainer.addEventListener('click', handleSchoolClick);
    tabs.forEach(tab => tab.addEventListener('click', handleTabClick));

    const currentHash = window.location.hash.substring(1); const targetTab = currentHash || 'explorar';
    tabs.forEach(t=>t.classList.remove('active')); tabContents.forEach(c=>c.classList.remove('active'));
    const activeLink = document.querySelector(`.tab-link[data-tab="${targetTab}"]`);
    if(activeLink){activeLink.classList.add('active');const actCont=document.getElementById(targetTab);if(actCont)actCont.classList.add('active');}
    else{const defLink=document.querySelector('.tab-link[data-tab="explorar"]');if(defLink)defLink.classList.add('active');const defCont=document.getElementById('explorar');if(defCont)defCont.classList.add('active');}
};