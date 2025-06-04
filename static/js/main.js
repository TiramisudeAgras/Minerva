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
const mainLoader = document.getElementById('loader');
const copyrightYearSpan = document.getElementById('copyright-year');
const tabs = document.querySelectorAll('.tab-link');
const tabContents = document.querySelectorAll('.tab-content');

const turnstileChallengeContainer = document.getElementById('turnstile-challenge-container');
const turnstileStatusMessage = document.getElementById('turnstile-status-message');
const minervaAppContainer = document.getElementById('minerva-app-container');

const searchStatusMessage = document.getElementById('search-status-message'); // Added

// --- MODIFIED: Global variables for pagination and loading state ---
let allSchoolsInPeriodDepartment = [];
let fuseInstance = null;
const DEFAULT_DISPLAY_COUNT = 50; // Used for how many search results to show at once from Fuse
const SCHOOLS_PER_PAGE = 100; // Chunk size for API requests

let currentSchoolListPage = 1;
let totalSchoolListPages = 1;
let totalSchoolsInDepartment = 0;
let isLoadingMoreSchools = false; // For scroll-triggered or background loading
let allSchoolsLoadedForDepartment = false;
// --- END MODIFIED ---

let currentHistogramChartInstance = null;
let currentEvolutionChartInstance = null;
let searchDebounceTimer;

// --- NEW: Cycling loading messages ---
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
// --- END NEW ---

// --- Funciones de Turnstile ---
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

const fetchData = async (url) => {
    // Keep mainLoader for school details, not for list chunks generally
    // if(mainLoader) mainLoader.style.display = 'block'; // This might be too intrusive for list loading
    try {
        const response = await fetch(url);
        if (!response.ok) {
            let errorData = { message: `Error HTTP ${response.status} en ${url}.` };
            try { 
                const jsonError = await response.json(); 
                errorData.message = jsonError.error || errorData.message; 
                console.error("Server error response:", jsonError);
            }
            catch (e) { 
                console.error("Could not parse error response as JSON");
            }
            throw new Error(errorData.message);
        }
        return await response.json();
    } catch (error) {
        console.error("Error in fetchData:", error.message);
        console.error("Failed URL:", url);
        // Avoid showing main resultsContent error for list loading issues, handle in calling function
        // if(resultsContent && minervaAppContainer && minervaAppContainer.style.display === 'block') {
        //     resultsContent.innerHTML = `<p class="error">Error al cargar datos: ${error.message}<br>URL: ${url}<br>Por favor, intente de nuevo o contacte al administrador.</p>`;
        // }
        throw error;
    } finally {
        // if(mainLoader) mainLoader.style.display = 'none';
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
            } else if (!append) {
                 // This message will be overwritten by cycling loader if it's the initial load
                // schoolListContainer.innerHTML = '<p style="padding:1rem; text-align:center;"><small>No hay colegios para mostrar o cargar.</small></p>';
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
        schoolItem.innerHTML = `<h6>${school.name}${rankDisplay}</h6><p>Promedio Global: <strong>${school.mean.toFixed(2)}</strong> (${school.count} estudiantes)</p>`;
        fragment.appendChild(schoolItem);
    });
    schoolListContainer.appendChild(fragment);
};

const renderResults = (data) => { 
    if(mainLoader) mainLoader.style.display = 'block'; // Show loader for details
    const { school_name_display, rank_departmental, rank_national, student_list, benchmarks, performance_levels, histogram_data, historical_evolution } = data;
    let headerRankDisplay = '';
    if (rank_departmental != null && rank_national != null) {
        headerRankDisplay = ` <span class="rank-slashline">(Ranking Dept: ${rank_departmental} / Nac: ${rank_national})</span>`;
    }
    schoolNameHeader.innerHTML = school_name_display + headerRankDisplay;
    const benchmarksHtml = `<details open><summary>Análisis Comparativo</summary><div class="overflow-auto"><table><thead><tr><th>Materia</th><th>Prom. Colegio</th><th>Prom. Depto.</th><th>Prom. Nacional</th></tr></thead><tbody>${benchmarks.map(b => `<tr><td><span class="math-inline">\{b\.subject\}</td\><td\></span>{b.school_avg.toFixed(2)}</td><td><span class="math-inline">\{b\.dept\_avg\.toFixed\(2\)\}</td\><td\></span>{b.nat_avg.toFixed(2)}</td></tr>`).join('')}</tbody></table></div></details>`;
    const levelsHtml = `<details><summary>Niveles de Desempeño</summary><div class="overflow-auto"><table><thead><tr><th>Materia</th><th>Nivel 1 (A-)</th><th>Nivel 2 (A1)</th><th>Nivel 3 (A2)</th><th>Nivel 4 (B1/B+)</th></tr></thead><tbody>${performance_levels.map(p => p.type === 'english' ? `<tr><td><span class="math-inline">\{p\.subject\}</td\><td\></span>{p.levels['A-']||0}</td><td><span class="math-inline">\{p\.levels\['A1'\]\|\|0\}</td\><td\></span>{p.levels['A2']||0}</td><td>${(p.levels['B1']||0)+(p.levels['B+']||0)}</td></tr>` : `<tr><td><span class="math-inline">\{p\.subject\}</td\><td\></span>{p.levels['1']||0}</td><td><span class="math-inline">\{p\.levels\['2'\]\|\|0\}</td\><td\></span>{p.levels['3']||0}</td><td>${p.levels['4']||0}</td></tr>`).join('')}</tbody></table></div></details>`;
    const histogramHtml = `<details><summary>Distribución Puntajes Globales</summary><div id="histogram-chart-container"><canvas id="histogram-chart"></canvas></div></details>`;
    const studentsHtml = `<details><summary>Resultados Detallados (${student_list.length})</summary><div class="overflow-auto"><table><thead><tr><th>#</th><th>Nacimiento</th><th>Sexo</th><th>Nacionalidad</th><th>Punt. Global</th><th>Percentil Global</th></tr></thead><tbody>${student_list.map((s, i) => `<tr><td><span class="math-inline">\{i\+1\}</td\><td\></span>{s.estu_fechanacimiento||'N/D'}</td><td><span class="math-inline">\{s\.estu\_genero\|\|'N/D'\}</td\><td\></span>{s.estu_nacionalidad||'N/D'}</td><td><span class="math-inline">\{s\.punt\_global\!\=null?s\.punt\_global\:'N/D'\}</td\><td\></span>{s.percentil_global?s.percentil_global+'%':'N/D'}</td></tr>`).join('')}</tbody></table></div></details>`;
    const evolutionHtml = `<details><summary>Evolución Histórica</summary><div class="overflow-auto"><div id="evolution-chart-container"><canvas id="evolution-chart"></canvas></div><table><thead><tr><th>Periodo</th><th>Prom. Global</th></tr></thead><tbody>${historical_evolution.map(h => `<tr><td><span class="math-inline">\{h\.periodo\}</td\><td\></span>{h.media === -1 ? 'N/D Periodo' : (h.media === 0 ? 'N/D Colegio' : h.media.toFixed(2))}</td></tr>`).join('')}</tbody></table></div></details>`;
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
    schoolListContainer.innerHTML = '<small>Seleccione un departamento.</small>';
    
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
    stopCyclingLoadingAnimation(); // Stop if it was running

    if (!periodo) return;
    try {
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
    
    // Ensure schoolListContainer is empty before putting loader message
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
    
    const messageElement = document.getElementById('cycling-loader-message'); // Get it after it's added
    if (!messageElement) return;

    cyclingMessageInterval = setInterval(() => {
        currentCyclingMessageIndex = (currentCyclingMessageIndex + 1) % LOADING_MESSAGES.length;
        messageElement.textContent = LOADING_MESSAGES[currentCyclingMessageIndex];
    }, 2500);
}

function stopCyclingLoadingAnimation() {
    clearInterval(cyclingMessageInterval);
    // The schoolListContainer will be cleared by renderSchoolList or before rendering new content
}

const loadSchoolList = async () => { // This function now INITIATES the loading process
    const department = departmentSelect.value;
    const periodo = periodSelect.value;

    allSchoolsInPeriodDepartment = [];
    fuseInstance = null;
    currentSchoolListPage = 1;
    totalSchoolListPages = 1;
    totalSchoolsInDepartment = 0;
    allSchoolsLoadedForDepartment = false;
    isLoadingMoreSchools = false;
    stopCyclingLoadingAnimation();
    if (schoolListContainer) schoolListContainer.innerHTML = ''; 

    if (schoolSearch) {
        schoolSearch.value = ''; 
        schoolSearch.disabled = true;
        schoolSearch.placeholder = "Cargando colegios...";
    }
    if (searchStatusMessage) searchStatusMessage.textContent = 'Iniciando carga de colegios...';
    resultsContainer.style.display = 'none';

    if (!department || !periodo) {
        if(schoolControls) schoolControls.style.display = 'none';
        if (schoolListContainer) schoolListContainer.innerHTML = '<small>Seleccione periodo y departamento primero.</small>';
        if (schoolSearch) schoolSearch.placeholder = "Seleccione periodo y depto...";
        if (searchStatusMessage) searchStatusMessage.textContent = '';
        return;
    }

    if(schoolControls) schoolControls.style.display = 'block';
    startCyclingLoadingAnimation(`Cargando colegios para ${department}...`);

    await fetchAndProcessSchoolChunk(periodo, department, 1, true); // Fetch first chunk
};

async function fetchAndProcessSchoolChunk(periodo, department, pageToFetch, isInitialCall = false) {
    if (isLoadingMoreSchools && !isInitialCall) return; 
    if (allSchoolsLoadedForDepartment && !isInitialCall) return;

    isLoadingMoreSchools = true;
    if (!isInitialCall && schoolListContainer) {
        let loadingMoreEl = schoolListContainer.querySelector('.loading-more-schools');
        if (!loadingMoreEl) {
            loadingMoreEl = document.createElement('p');
            loadingMoreEl.className = 'loading-more-schools';
            loadingMoreEl.style.textAlign = 'center';
            loadingMoreEl.innerHTML = '<small aria-busy="true">Cargando más colegios...</small>';
            schoolListContainer.appendChild(loadingMoreEl);
        }
    }
    if (searchStatusMessage && pageToFetch > 1) {
        searchStatusMessage.textContent = `Cargando más colegios (página ${pageToFetch})...`;
    }

    const encodedDepartment = encodeURIComponent(department);
    const url = `/api/schools/${periodo}/${encodedDepartment}?page=${pageToFetch}&per_page=${SCHOOLS_PER_PAGE}`;

    try {
        const data = await fetchData(url);
        const newSchools = data.schools;
        totalSchoolsInDepartment = data.total_count;
        totalSchoolListPages = data.total_pages;
        currentSchoolListPage = data.page; // API returns current page

        if (isInitialCall) {
            stopCyclingLoadingAnimation();
            // schoolListContainer.innerHTML = ''; // RenderSchoolList will clear if !append
        }
        
        allSchoolsInPeriodDepartment.push(...newSchools);

        if (typeof Fuse !== 'undefined' && allSchoolsInPeriodDepartment.length > 0) {
            fuseInstance = new Fuse(allSchoolsInPeriodDepartment, {
                keys: ['raw_name', 'name'], includeScore: true, threshold: 0.4, minMatchCharLength: 2,
            });
            console.log(`Fuse.js actualizado. Total colegios indexados: ${allSchoolsInPeriodDepartment.length}`);
        } else if (typeof Fuse === 'undefined') {
            console.error("Fuse.js no está cargado.");
        }
        
        renderSchoolList(newSchools, !isInitialCall); // Append if not initial

        if (currentSchoolListPage >= totalSchoolListPages) {
            allSchoolsLoadedForDepartment = true;
            if (searchStatusMessage) searchStatusMessage.textContent = `Se cargaron todos los ${totalSchoolsInDepartment} colegios.`;
            console.log("Todos los colegios del departamento han sido cargados.");
        } else {
            if (searchStatusMessage) {
                searchStatusMessage.textContent = `Mostrando ${allSchoolsInPeriodDepartment.length} de ${totalSchoolsInDepartment} colegios.`;
            }
            if (isInitialCall && !allSchoolsLoadedForDepartment) {
                setTimeout(() => { // Start background loading for next page
                    if (!allSchoolsLoadedForDepartment) { // Double check, state might have changed
                         fetchAndProcessSchoolChunk(periodo, department, pageToFetch + 1);
                    }
                }, 500); // Brief delay
            }
        }
        
        if (schoolSearch && schoolSearch.disabled && allSchoolsInPeriodDepartment.length > 0) {
            schoolSearch.disabled = false;
            schoolSearch.placeholder = "Buscar por nombre...";
        }

    } catch (error) {
        console.error(`Error al cargar la página ${pageToFetch} de colegios:`, error);
        if (isInitialCall) {
            stopCyclingLoadingAnimation();
            if (schoolListContainer) schoolListContainer.innerHTML = '<small>Error al cargar los colegios iniciales. Intente de nuevo.</small>';
        }
        if (searchStatusMessage) searchStatusMessage.textContent = 'Error al cargar datos de colegios.';
    } finally {
        isLoadingMoreSchools = false;
        const loadingMoreMessage = schoolListContainer.querySelector('.loading-more-schools');
        if (loadingMoreMessage) { // Ensure it's removed if processing is done for this chunk
            loadingMoreMessage.remove();
        }
    }
}

const handleSchoolListScroll = () => {
    if (isLoadingMoreSchools || allSchoolsLoadedForDepartment || !schoolListContainer) {
        return;
    }
    if (schoolListContainer.scrollTop + schoolListContainer.clientHeight >= schoolListContainer.scrollHeight - 300) { // Threshold
        const nextPageToFetch = currentSchoolListPage + 1; // currentSchoolListPage is the last fetched/processed page
        if (nextPageToFetch <= totalSchoolListPages) {
            console.log("Scroll detectado, cargando siguiente página:", nextPageToFetch);
            const periodo = periodSelect.value;
            const department = departmentSelect.value;
            fetchAndProcessSchoolChunk(periodo, department, nextPageToFetch);
        }
    }
};

const handleSchoolSearch = () => {
    clearTimeout(searchDebounceTimer);
    searchDebounceTimer = setTimeout(() => {
        if (!schoolSearch) return; // Guard clause

        if (schoolSearch.disabled) {
            if(searchStatusMessage) searchStatusMessage.textContent = "La búsqueda está deshabilitada mientras se cargan datos.";
            return;
        }
        if (!fuseInstance && allSchoolsInPeriodDepartment.length > 0) {
            if(searchStatusMessage) searchStatusMessage.textContent = "El índice de búsqueda se está preparando...";
            return; // Fuse instance not ready yet, but schools are loading/loaded
        }
        if (!fuseInstance) {
            if(searchStatusMessage && schoolListContainer.children.length > 0) searchStatusMessage.textContent = "Índice de búsqueda no disponible.";
            else if (searchStatusMessage) searchStatusMessage.textContent = "Seleccione periodo y departamento para cargar colegios.";
            renderSchoolList([], false); // Clear list if no fuse instance
            return;
        }

        const searchTerm = schoolSearch.value.trim().toLowerCase();

        if (!searchTerm) {
            // Show the first DEFAULT_DISPLAY_COUNT of all loaded schools when search is cleared
            renderSchoolList(allSchoolsInPeriodDepartment.slice(0, DEFAULT_DISPLAY_COUNT), false);
            if (searchStatusMessage) {
                if (allSchoolsLoadedForDepartment) {
                    searchStatusMessage.textContent = `Mostrando los primeros ${Math.min(DEFAULT_DISPLAY_COUNT, allSchoolsInPeriodDepartment.length)} de ${totalSchoolsInDepartment} colegios.`;
                } else {
                    searchStatusMessage.textContent = `Mostrando los primeros ${Math.min(DEFAULT_DISPLAY_COUNT, allSchoolsInPeriodDepartment.length)} de ${allSchoolsInPeriodDepartment.length} colegios cargados (de ${totalSchoolsInDepartment} total).`;
                }
            }
            return;
        }
        
        const fuseResults = fuseInstance.search(searchTerm);
        const filteredSchools = fuseResults.map(result => result.item);
        renderSchoolList(filteredSchools.slice(0, DEFAULT_DISPLAY_COUNT * 2), false); // Show up to 100 search results
        if (searchStatusMessage) searchStatusMessage.textContent = `Se encontraron ${filteredSchools.length} colegios para "${searchTerm}". Mostrando hasta ${DEFAULT_DISPLAY_COUNT * 2}.`;

    }, 300);
};

const handleSchoolClick = async (event) => {
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
        const department = departmentSelect.value; // department is department_name_param for the API
        const schoolId = target.dataset.id;
        
        const encodedDepartment = encodeURIComponent(department);
        const encodedSchoolId = encodeURIComponent(schoolId); // School ID might contain special chars like '|'
        
        const url = `/api/school_details/${periodo}/${encodedDepartment}/${encodedSchoolId}`;
        console.log("Fetching school details from URL:", url);
        
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
        loadSchoolList(); // This will reset states and start loading first chunk
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

// Ensure onTurnstileSuccess calls initializeApp after verification
// (already in your original code)