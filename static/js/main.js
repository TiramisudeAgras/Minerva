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

let allSchoolsInPeriodDepartment = [];
let fuseInstance = null;
const DEFAULT_DISPLAY_COUNT = 50;

let currentHistogramChartInstance = null;
let currentEvolutionChartInstance = null;
let searchDebounceTimer;

// --- Funciones de Turnstile ---
async function onTurnstileSuccess(token) { /* Sin cambios */
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
function onTurnstileError(errorCode) { /* Sin cambios */
    console.error("Error de Cloudflare Turnstile:", errorCode);
    if (turnstileStatusMessage) {
        turnstileStatusMessage.textContent = "Error al cargar el componente de seguridad. Verifica tu conexión e intenta recargar.";
        turnstileStatusMessage.style.color = "red"; turnstileStatusMessage.style.display = "block";
    }
}

// --- Funciones Principales de la App ---
document.addEventListener('DOMContentLoaded', () => {
    if (copyrightYearSpan) copyrightYearSpan.textContent = new Date().getFullYear();
    // Asegurar que el input de búsqueda esté deshabilitado al inicio si los controles están ocultos
    if (schoolSearch && schoolControls && schoolControls.style.display === 'none') {
        schoolSearch.disabled = true;
        schoolSearch.placeholder = "Seleccione periodo y depto...";
    }
});

const fetchData = async (url) => {
    if(mainLoader) mainLoader.style.display = 'block';
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
        if(resultsContent && minervaAppContainer && minervaAppContainer.style.display === 'block') {
            resultsContent.innerHTML = `<p class="error">Error al cargar datos: ${error.message}<br>URL: ${url}<br>Por favor, intente de nuevo o contacte al administrador.</p>`;
        }
        throw error;
    } finally {
        if(mainLoader) mainLoader.style.display = 'none';
    }
};

const renderSchoolList = (schoolsToDisplay, append = false) => {
    if (!append) {
        schoolListContainer.innerHTML = '';
    }
    
    if (!schoolsToDisplay || schoolsToDisplay.length === 0) {
        if (!append) {
            const searchTerm = schoolSearch.value.trim();
            if (searchTerm) {
                schoolListContainer.innerHTML = '<p style="padding:1rem; text-align:center;"><small>No se encontraron colegios que coincidan con tu búsqueda.</small></p>';
            } else {
                schoolListContainer.innerHTML = '<p style="padding:1rem; text-align:center;"><small>No hay colegios para mostrar.</small></p>';
            }
        }
        return;
    }
    
    // Si es append, crear un contenedor para los nuevos elementos
    const container = append ? document.createElement('div') : schoolListContainer;
    
    schoolsToDisplay.forEach(school => {
        const schoolItem = document.createElement('a');
        schoolItem.href = '#results-container'; 
        schoolItem.className = 'school-list-item';
        schoolItem.dataset.id = school.id; 
        schoolItem.dataset.displayName = school.name;
        
        let rankDisplay = '';
        if (school.rank_departmental != null && school.rank_national != null) {
            rankDisplay = `<span class="rank-slashline"> (Dep: ${school.rank_departmental} / Nac: ${school.rank_national})</span>`;
        }
        
        schoolItem.innerHTML = `<h6>${school.name}${rankDisplay}</h6><p>Promedio Global: <strong>${school.mean.toFixed(2)}</strong> (${school.count} estudiantes)</p>`;
        container.appendChild(schoolItem);
    });
    
    if (append) {
        schoolListContainer.appendChild(container);
    }
};

const displayInitialSchoolList = () => {
    if (allSchoolsInPeriodDepartment && allSchoolsInPeriodDepartment.length > 0) {
        renderSchoolList(allSchoolsInPeriodDepartment.slice(0, DEFAULT_DISPLAY_COUNT));
    } else {
        renderSchoolList([]);
    }
};

const renderResults = (data) => { /* Sin cambios */
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
};

const renderHistogramChart = (scores) => { /* Sin cambios */
    const canvasContainer = document.getElementById('histogram-chart-container'); const canvas = document.getElementById('histogram-chart'); if (!canvas || !canvasContainer) return; canvasContainer.style.height = '280px'; const ctx = canvas.getContext('2d'); const bins = {}; const labels = []; for (let i = 0; i <= 450; i += 50) { const label = `${i}-${i + 49}`; labels.push(label); bins[label] = 0; } if (labels.length > 0) labels[labels.length - 1] = `450-500`; scores.forEach(score => { if (score === null || score === undefined) return; const binIndex = Math.floor(score / 50); let binLabel; if (score === 500) { binLabel = labels[labels.length -1]; } else { binLabel = `${binIndex*50}-${binIndex*50+49}`; } if (bins[binLabel] !== undefined) bins[binLabel]++; }); if (currentHistogramChartInstance) currentHistogramChartInstance.destroy(); currentHistogramChartInstance = new Chart(ctx, { type: 'bar', data: { labels: labels, datasets: [{ label: 'Número de Estudiantes', data: Object.values(bins), backgroundColor: 'rgba(255,193,7,0.7)', borderColor: 'rgba(255,160,0,1)', borderWidth: 1 }] }, options: { responsive: true, maintainAspectRatio: false, scales: { y: { beginAtZero: true, title: { display: true, text: 'Cantidad de Estudiantes'}}, x: { title: { display: true, text: 'Rango de Puntaje Global'}}}, plugins: { legend: { display: false }}}});
};
const renderEvolutionChart = (historicalDataOriginalOrder) => { /* Sin cambios */
    const canvasContainer = document.getElementById('evolution-chart-container'); const canvas = document.getElementById('evolution-chart'); if(!canvas || !canvasContainer) return; canvasContainer.style.height = '280px'; const ctx = canvas.getContext('2d'); const chartData = historicalDataOriginalOrder.filter(d => d.media > 0).sort((a,b) => { const [yA,pA]=a.periodo.split('-').map(Number); const [yB,pB]=b.periodo.split('-').map(Number); if(yA!==yB)return yA-yB; return pA-pB; }); if (currentEvolutionChartInstance) currentEvolutionChartInstance.destroy(); currentEvolutionChartInstance = new Chart(ctx, { type: 'line', data: { labels: chartData.map(d=>d.periodo), datasets: [{ label: 'Promedio Global Histórico', data: chartData.map(d=>d.media), borderColor: 'var(--minerva-yellow-hover,#FFA000)', backgroundColor: 'rgba(255,193,7,0.2)', fill: true, tension: 0.1 }] }, options: { responsive: true, maintainAspectRatio: false, scales: { y: { beginAtZero: false, title: { display: true, text: 'Promedio Global'}}, x: { title: { display: true, text: 'Periodo'}}}, plugins: { legend: { display: false }}}});
};

const handlePeriodChange = async (event) => {
    const periodo = event.target.value;
    
    // NUEVO: Si no hay periodo, no hacer nada
    if (!periodo) {
        departmentSelect.innerHTML = '<option value="" selected>Primero seleccione un periodo</option>';
        departmentSelect.disabled = true;
        return;
    }
    
    departmentSelect.disabled = false;
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
    fuseInstance = null;
    allSchoolsInPeriodDepartment = [];

    try {
        const departments = await fetchData(`/api/departments/${periodo}`);
        departmentSelect.innerHTML = '<option value="" selected>Seleccione un departamento</option>';
        departments.forEach(dept => { 
            const opt = document.createElement('option'); 
            opt.value = dept; 
            opt.textContent = dept; 
            departmentSelect.appendChild(opt); 
        });
        if(departmentSelectLabel) departmentSelectLabel.style.display = 'block';
        departmentSelect.style.display = 'block';
    } catch (error) { 
        departmentSelect.innerHTML = '<option value="">Error al cargar deptos.</option>'; 
    }
};

// ADICIONAL: Guardar el estado en sessionStorage para prevenir pérdidas
const saveFormState = () => {
    const state = {
        periodo: periodSelect.value,
        department: departmentSelect.value,
        timestamp: Date.now()
    };
    sessionStorage.setItem('minerva_form_state', JSON.stringify(state));
};

const restoreFormState = () => {
    const savedState = sessionStorage.getItem('minerva_form_state');
    if (savedState) {
        try {
            const state = JSON.parse(savedState);
            // Solo restaurar si fue guardado en los últimos 30 minutos
            if (Date.now() - state.timestamp < 30 * 60 * 1000) {
                if (state.periodo && periodSelect.querySelector(`option[value="${state.periodo}"]`)) {
                    periodSelect.value = state.periodo;
                    // Trigger change event to load departments
                    periodSelect.dispatchEvent(new Event('change'));
                    
                    // Esperar y luego seleccionar departamento
                    setTimeout(() => {
                        if (state.department && departmentSelect.querySelector(`option[value="${state.department}"]`)) {
                            departmentSelect.value = state.department;
                            departmentSelect.dispatchEvent(new Event('change'));
                        }
                    }, 1000);
                }
            }
        } catch (e) {
            console.error("Error restoring form state:", e);
        }
    }
};

// MODIFICADO: `loadSchoolList` para manejar el estado de carga del input de búsqueda
const loadSchoolList = async (searchQuery = '') => {
    const department = departmentSelect.value;
    const periodo = periodSelect.value;
    
<<<<<<< HEAD
    fuseInstance = null;
    allSchoolsInPeriodDepartment = [];

=======
>>>>>>> parent of f6b5640 (Sistema de Carga con Animaciones)
    if (!department || !periodo) {
        if(schoolControls) schoolControls.style.display = 'none';
        schoolListContainer.innerHTML = '<small>Seleccione periodo y departamento primero.</small>';
        if (schoolSearch) {
            schoolSearch.disabled = true;
            schoolSearch.placeholder = "Seleccione periodo y depto...";
        }
        return;
    }
    
    if(schoolControls) schoolControls.style.display = 'block';
<<<<<<< HEAD
    
    // CAMBIO CLAVE: Habilitar búsqueda inmediatamente
    if (schoolSearch) {
        schoolSearch.disabled = false;
        schoolSearch.value = '';
        schoolSearch.placeholder = "Cargando top colegios...";
    }
=======
>>>>>>> parent of f6b5640 (Sistema de Carga con Animaciones)
    
    // NUEVO: No deshabilitar la búsqueda durante la carga
    if (schoolSearch && !searchQuery) {
        schoolSearch.disabled = false;
        schoolSearch.placeholder = "Buscar colegio...";
    }
    
    // Mostrar indicador de carga
    if (!searchQuery) {
        schoolListContainer.innerHTML = `<article aria-busy="true" style="text-align:center; padding:1rem;">Cargando top colegios...</article>`;
    }
    
    resultsContainer.style.display = 'none';

    const encodedDepartment = encodeURIComponent(department);
    let url = `/api/schools/${periodo}/${encodedDepartment}?limit=50`;
    
<<<<<<< HEAD
    // Mostrar indicador de carga
    schoolListContainer.innerHTML = `<article aria-busy="true" style="text-align:center; padding:1rem;">Cargando mejores colegios...</article>`;
    resultsContainer.style.display = 'none';

    try {
        // CAMBIO CLAVE: Cargar solo primera página (100 colegios)
        const firstPageUrl = `/api/schools/${periodo}/${encodedDepartment}?page=1&per_page=100`;
        const firstResponse = await fetchData(firstPageUrl);
        
        allSchoolsInPeriodDepartment = firstResponse.schools;
        const totalSchools = firstResponse.pagination.total;
        
        // Mostrar resultados inmediatamente
        renderSchoolList(firstResponse.schools);
        
        // Si hay más colegios, agregar botón para cargar todos
        if (totalSchools > 100) {
            const loadMoreDiv = document.createElement('div');
            loadMoreDiv.id = 'load-more-container';
            loadMoreDiv.style.cssText = 'text-align:center; padding:1.5rem; background-color: var(--pico-card-background-color); border-radius: var(--pico-border-radius); margin-top:1rem;';
            loadMoreDiv.innerHTML = `
                <p style="margin-bottom:1rem;">
                    <strong>Mostrando top 100 de ${totalSchools.toLocaleString()} colegios</strong><br>
                    <small style="color: var(--pico-secondary);">Para buscar entre TODOS los colegios, cargue la lista completa</small>
                </p>
                <button id="load-all-schools" style="margin:0 auto;">
                    🔍 Cargar todos para búsqueda completa
                </button>
            `;
            schoolListContainer.appendChild(loadMoreDiv);
            
            // Inicializar Fuse con datos parciales
            if (typeof Fuse !== 'undefined') {
                fuseInstance = new Fuse(allSchoolsInPeriodDepartment, {
                    keys: ['raw_name', 'name'],
                    threshold: 0.4,
                    minMatchCharLength: 2
                });
                schoolSearch.placeholder = `Buscar en top 100 (o cargar todos)`;
            }
            
            // Evento para cargar todos
            document.getElementById('load-all-schools').addEventListener('click', async () => {
                const button = document.getElementById('load-all-schools');
                button.disabled = true;
                
                // Crear animación de carga mejorada
                loadMoreDiv.innerHTML = `
                    <article aria-busy="true"></article>
                    <p style="margin:1rem 0;">
                        <strong id="loading-status">Cargando resto de colegios...</strong><br>
                        <small>Esto puede tomar un momento para departamentos grandes</small>
                    </p>
                    <progress id="loading-progress" value="0" max="100" style="width:100%;"></progress>
                    <p id="loading-count" style="margin-top:0.5rem; font-size:0.9rem;">
                        ${allSchoolsInPeriodDepartment.length} de ${totalSchools} colegios
                    </p>
                `;
                
                // Cargar páginas restantes
                await loadRemainingSchools(periodo, encodedDepartment, 2, firstResponse.pagination);
                
                // Remover el contenedor de carga
                loadMoreDiv.remove();
                
                // Actualizar placeholder
                if (schoolSearch) {
                    schoolSearch.placeholder = `Buscar entre ${allSchoolsInPeriodDepartment.length} colegios...`;
                }
            });
        } else {
            // Si hay 100 o menos, ya tenemos todos
            if (typeof Fuse !== 'undefined') {
                fuseInstance = new Fuse(allSchoolsInPeriodDepartment, {
                    keys: ['raw_name', 'name'],
                    threshold: 0.4,
                    minMatchCharLength: 2
                });
            }
            if (schoolSearch) {
                schoolSearch.placeholder = `Buscar entre ${totalSchools} colegios...`;
            }
=======
    if (searchQuery) {
        url += `&q=${encodeURIComponent(searchQuery)}`;
    }

    try {
        const response = await fetchData(url);
        
        // Manejar la nueva respuesta
        let schools = response.schools || response; // Compatibilidad con formato anterior
        
        if (searchQuery && response.total_results > response.displayed_results) {
            // Mostrar mensaje si hay más resultados
            const moreResults = response.total_results - response.displayed_results;
            schoolListContainer.innerHTML = `<p style="padding:0.5rem; text-align:center; background-color: var(--pico-card-background-color);"><small>Mostrando ${response.displayed_results} de ${response.total_results} resultados. Refine su búsqueda para ver más.</small></p>`;
            renderSchoolList(schools, true); // true = append to existing content
        } else {
            renderSchoolList(schools);
>>>>>>> parent of f6b5640 (Sistema de Carga con Animaciones)
        }
        
    } catch (error) {
        console.error("Error loading schools:", error);
<<<<<<< HEAD
        schoolListContainer.innerHTML = `
            <div style="text-align:center; padding:2rem;">
                <p style="color: var(--pico-color);">😕 Error al cargar los colegios</p>
                <p><small>${error.message}</small></p>
                <button onclick="loadSchoolList()" style="margin-top:1rem;">Reintentar</button>
            </div>
        `;
        if (schoolSearch) {
            schoolSearch.disabled = true;
            schoolSearch.placeholder = "Error al cargar colegios";
        }
=======
        schoolListContainer.innerHTML = '<small>Error al cargar los colegios. Intente de nuevo.</small>';
>>>>>>> parent of f6b5640 (Sistema de Carga con Animaciones)
    }
};


const loadRemainingSchools = async (periodo, encodedDepartment, startPage, paginationInfo) => {
    const totalPages = paginationInfo.total_pages;
    const totalSchools = paginationInfo.total;
    
    for (let page = startPage; page <= totalPages; page++) {
        try {
            const url = `/api/schools/${periodo}/${encodedDepartment}?page=${page}&per_page=500`;
            const response = await fetchData(url);
            
            // Agregar nuevos colegios
            allSchoolsInPeriodDepartment = allSchoolsInPeriodDepartment.concat(response.schools);
            
            // Actualizar progreso
            const progress = Math.round(((page - 1) / (totalPages - 1)) * 100);
            const progressBar = document.getElementById('loading-progress');
            const countEl = document.getElementById('loading-count');
            
            if (progressBar) progressBar.value = progress;
            if (countEl) countEl.textContent = `${allSchoolsInPeriodDepartment.length} de ${totalSchools} colegios`;
            
            // Pequeña pausa para no saturar
            await new Promise(resolve => setTimeout(resolve, 50));
            
        } catch (error) {
            console.error(`Error loading page ${page}:`, error);
            // Continuar con las otras páginas
        }
    }
    
    // Actualizar Fuse con todos los datos
    if (typeof Fuse !== 'undefined') {
        fuseInstance = new Fuse(allSchoolsInPeriodDepartment, {
            keys: ['raw_name', 'name'],
            threshold: 0.4,
            minMatchCharLength: 2
        });
    }
};

const handleSchoolSearch = () => {
    clearTimeout(searchDebounceTimer);
    searchDebounceTimer = setTimeout(() => {
        if (!schoolSearch || !departmentSelect.value || !periodSelect.value) {
            return;
        }

        const searchTerm = schoolSearch.value.trim();

        if (!searchTerm) {
            // Si no hay búsqueda, cargar top 50
            loadSchoolList();
            return;
        }

        // Si hay al menos 2 caracteres, buscar
        if (searchTerm.length >= 2) {
            schoolListContainer.innerHTML = `<article aria-busy="true" style="text-align:center; padding:0.5rem;">Buscando "${searchTerm}"...</article>`;
            loadSchoolList(searchTerm);
        }
    }, 300); // 300ms debounce
};


const handleSchoolClick = async (event) => {
    event.preventDefault(); 
    const target = event.target.closest('.school-list-item'); 
    if (!target) return;
    
    // NUEVO: Validar que periodo y department tengan valores
    const periodo = periodSelect.value;
    const department = departmentSelect.value;
    
    if (!periodo || !department) {
        console.error("Missing periodo or department:", { periodo, department });
        resultsContent.innerHTML = `<p class="error">Error: Debe seleccionar un periodo y departamento antes de ver detalles.</p>`;
        return;
    }
    
    resultsContainer.style.display = 'block'; 
    resultsContent.innerHTML = ''; 
    if(mainLoader) mainLoader.style.display = 'block';
    schoolNameHeader.textContent = "Cargando detalles para: " + target.dataset.displayName + "... ☕";
    resultsContainer.scrollIntoView({ behavior: 'smooth', block: 'start' });
    
    try {
        const schoolId = target.dataset.id;
        
        // Debug: Log para verificar valores
        console.log("Periodo:", periodo);
        console.log("Department:", department);
        console.log("School ID:", schoolId);
        console.log("School ID parts:", schoolId.split("|"));
        
        // Asegurar codificación correcta
        const encodedDepartment = encodeURIComponent(department);
        const encodedSchoolId = encodeURIComponent(schoolId);
        
        const url = `/api/school_details/${periodo}/${encodedDepartment}/${encodedSchoolId}`;
        console.log("Fetching from URL:", url);
        
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


const handleTabClick = (event) => { /* Sin cambios */
    event.preventDefault(); tabs.forEach(t=>t.classList.remove('active')); tabContents.forEach(c=>c.classList.remove('active'));
    const clkT = event.currentTarget; clkT.classList.add('active'); const activeId = clkT.dataset.tab;
    const activeCont = document.getElementById(activeId); if(activeCont)activeCont.classList.add('active'); window.location.hash=activeId;
};

const initializeApp = async () => {
    if(initialLoader) initialLoader.style.display = 'block'; 
    if(controlsContainer) controlsContainer.style.display = 'none';
    
    try {
        // 1. PRIMERO: Cargar los periodos
        const periods = await fetchData('/api/periods');
        if(initialLoader) initialLoader.style.display = 'none'; 
        if(controlsContainer) controlsContainer.style.display = 'block';
        
        periodSelect.innerHTML = '<option value="" selected>Seleccione un periodo</option>';
        periods.forEach(p => { 
            const o = document.createElement('option'); 
            o.value = p.value; 
            o.textContent = p.display; 
            periodSelect.appendChild(o); 
        });
        
        const lastUpd = document.body.dataset.lastUpdatedDate;
        if (typeof lastUpdatedPlaceholder !== 'undefined' && lastUpdatedPlaceholder) {
            lastUpdatedPlaceholder.textContent = lastUpd || "No disponible";
        }
    } catch (error) { 
        if(initialLoader) initialLoader.innerHTML = 'Error al cargar periodos. Intente recargar.'; 
        return; // No continuar si no se pueden cargar los periodos
    }

    // 2. SEGUNDO: Agregar todos los event listeners
    // Event listener para cambio de periodo (con guardado de estado)
    periodSelect.addEventListener('change', (e) => {
        handlePeriodChange(e);
        saveFormState();
    });
    
    // Event listener para cambio de departamento (con guardado de estado)
    departmentSelect.addEventListener('change', () => {
        schoolSearch.value = '';
        fuseInstance = null;
        allSchoolsInPeriodDepartment = [];
        if (schoolSearch) {
            schoolSearch.disabled = true;
            schoolSearch.placeholder = "Cargando colegios...";
        }
        loadSchoolList();
        saveFormState();
    });
    
    // Event listener para búsqueda de escuelas
    schoolSearch.addEventListener('input', handleSchoolSearch);
    
    // Event listener para click en escuela
    schoolListContainer.addEventListener('click', handleSchoolClick);
    
    // Event listeners para las pestañas
    tabs.forEach(tab => tab.addEventListener('click', handleTabClick));

    // 3. TERCERO: Manejar navegación por hash/pestañas
    const currentHash = window.location.hash.substring(1); 
    const targetTab = currentHash || 'explorar';
    tabs.forEach(t => t.classList.remove('active')); 
    tabContents.forEach(c => c.classList.remove('active'));
    
    const activeLink = document.querySelector(`.tab-link[data-tab="${targetTab}"]`);
    if(activeLink) {
        activeLink.classList.add('active');
        const actCont = document.getElementById(targetTab);
        if(actCont) actCont.classList.add('active');
    } else {
        const defLink = document.querySelector('.tab-link[data-tab="explorar"]');
        if(defLink) defLink.classList.add('active');
        const defCont = document.getElementById('explorar');
        if(defCont) defCont.classList.add('active');
    }
    
    // 4. CUARTO: Intentar restaurar el estado guardado (si existe)
    // Esto debe ir AL FINAL para que todos los listeners ya estén configurados
    setTimeout(() => {
        restoreFormState();
    }, 100); // Pequeño delay para asegurar que todo esté listo
};