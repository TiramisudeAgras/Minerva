// static/js/main.js

document.addEventListener('DOMContentLoaded', () => {
    // --- DOM Element References ---
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

    let allSchoolsInPeriodDepartment = [];
    let currentHistogramChartInstance = null; 
    let currentEvolutionChartInstance = null;

    const MINERVA_ASCII = `
                ░░░░░░░░░░▒▒▒▒▒░▒▒▒▒▒▒▒░░░░▒░░░░░░░░▒░░░▒▒░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░
░░░░░░░░░░░░▒▒▒▒░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░
░░░░░░░░░░░░░▒▒▒▒░░░░░░░░░░░░░░░░░░░░░░░▒░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░
░░░░░░░░░░░░░░▒▒░░░░░░░░░░░░░░▓█▓▓▓▓▓░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░
░░░░░░░░░░░░░░░▒▒▒▒░░░░░░░▒▒▓▓▓██▓▓▓█▓▓▓░░░░▒░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░
░░░░░░░░░░░░░░░░▒▒░▒░░░░░▓███▓▓▓▓█▓▓▒▓▓█▒▓░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░
░░░░░░░░░░░░░░░░░▒▒░░░░░░░░███▓█▓▓▓▒▒▓▓█▓▒▓▓░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░
░░░░░░░░░░░░░░░░░░▒▒░▒▒░░░░░░██▓▓▓▓▓▒▓▓▓▒▓▒▒▒▓░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░
░░░░░░░░░░░░░░░░░░░▒▒░░░░░░░░░██▓▓▓▓▒▒▒▒▒▒▒▒▒▓░▒░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░
░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░█▓▒▒▓▒▓▒▓▒▓▒▓▒▓▓▒▓░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░
░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░▓▓▒▒▒▒▒▓▒▒▒▒▒▒▓▓▒▓░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░
░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░▓▓▒▒▒░░▒▒▒▒▓▒▒▓▒▒▒▓░░░░░░░░░░░░░░░░░░░░░░░░░░░░░
░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░▒▓█▓██▒▒▒▒▒▓▒▒▒▒▒▒▒▒░░░░░░░░░░░░░░░░░░░░░░░░░░░░
░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░▓██▒▒▒▒▒▒▒▒▒▒▓░░░░░░░░░░░░░░░░░░░░░░░░░░░░░
░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░▓█░░▒▓▓▒░░▒▒▓▒▒░▒▓░░░░░░░░░░░░░░░░░░░░░░░░░░
░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░▒▒▒▒▓░░░▒▓▒▓▓▓▒░░░░░░░░░░░░░░░░░░░░░░░░░
░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░▓▒▒▓▒▓▒▒░░░░▒▓░▒▒▓▓▒█▒░░░░░░░░░░░░░░░░░░░░░░░
░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░▒█▓░▒▓▓▒▒▓▒░░░░░▓░░▓▓▒▒▒░░░░░░░░░░░░░░░░░░░░░░
░░░░░░░░░░░░░░░░░░░░░░░░░░░░░▒▒▒▒░░░░▒▒░░░░░░░░░░░▓▓░▓░░▓▒░░░░░░░░░░░░░░░░░░░░░░
░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░█▒▓█▓▓▒░░░░░░░▒▒█░░▓█▓▒░░░░░░░░░░░░░░░░░░░░░
░░░░░░░░░░░░░░░░░░░░░░░░░▒░▓░░░░▒░░▒░░░░░░░░░░░░░░░░▒▓░░▒█▒░░░░░░░░░░░░░░░░░░░░░
░░░░░░░░░░░░░░░░░░░░░░░░░████████████████████▓░░░░░░░▓█▒░▓█▒░░░░░░░░░░░░░░░░░░░░
░░░░░░░░░░░░░░░░░░░░░░░▓███████░█████████████████ ░░░░▓█░░▒▓░░░░░░░░░░░░░░░░░░░░
░░░░░░░░░░░░░░░░░░░░░░█████████▓▒███████████████▓███░░▒▓▓▒█▒▒░░░░░░░░░░░░░░░░░░░
░░░░░░░░░░░░░░░░░░░░░░██████████▓███████████████▒▒▓███▒▓█▒█▓▓░░░░░░░░░░░░░░░░░░░
░░░░░░░░░░░░░░░░░░░░░▒████▓▓▓▓▓█████▓▓████▓▓███████████░█▒█▒▒░░░░░░░░░░░░░░░░░░░
░░░░░░░░░░░░░░░░░░░░░░█▓█▓▓██▓▓█████████▒▒▒▒▓▓███████████▒▓▒▓░░░░░░░░░░░░░░░░░░░
░░░░░░░░░░░░░░░░░░░░░░███▓████▓▓██████▓▓▒▒▓▓▓▒▓███████████▓▒▒░░░░░░░░░░░░░░░░░░░
░░░░░░░░░░░░░░░░░░░░░░░▓█▓▓▓██░▒▒▒██▓▓▓▓▓▓▓▓▓▓▓▓▓███████▓▒▒▒░░░░░░░░░░░░░░░░░░░░
░░░░░░░░░░░░░░░░░░░░░░░▒███▓▓▓▓████▓▓█▓▓▓▓▓▓▓▓▒▓▓███████▒░░▒░░░░░░░░░░░░░░░░░░░░
░░░░░░░░░░░░░░░░░░░░░░░█▓█▓▒▒▓████▒▒▒▓█▓▓▓▓▓▓▓▓▓▓▓▒░▒███░▒▓▓░░░░░░░░░░░░░░░░░░░░
░░░░░░░░░░░░░░░░░░░░░░█████▒▒▓▓▓▓█████▓▓▓▓▓▓▓▓▓▓▓▓▓█████▒▒▒░░░░░░░░░░░░░░░░░░░░░
░░░░░░░░░░░░░░░░░░░░░░░░███▓▒▒▓▓█▓▓██▓██▓▓▓▓▓▓▓▓▓▓▓▓████▓▒░░░░░░░░░░░░░░░░░░░░░░
░░░░░░░░░░░░░░░░░░░░░░░░░░██▒▒▒█▓██▓▓▓▒▓▓▓▓▓▓▓▓▓▓▓▓▓▓███▒░░░░░░░░░░░░░░░░░░░░░░░
░░░░░░░░░░░░░░░░░░░░░░░░░░░░░▒▒▓▒▒▒▓▓█▓▓▓▓██▓███▓▓▓▓▓██▓█░░░░░░░░░░░░░░░░░░░░░░░
░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░▒▒▒▓███████████████▓▓▓▒███▓░░░░░░░░░░░░░░░░░░░░░░░
░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░▓▓██████████████▓▓▓▓▓▒████░░░░░░░░░░░░░░░░░░░░░░
░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░▓▓█████████████▓▓▓▓▓▒███▒█░░░░░░░░░░░░░░░░░░░░░
░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░▓███████████▓▓▓▓▓▓▒██▓█▒░░░░░░░░░░░░░░░░░░░░░
░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░▓█▓▓█████████▓▓▓▓▓▓▒█▓█▓▓░░░░░░░░░░░░░░░░░░░░
░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░█▓█████████▓▓▓▓▓▓▓▓▒█▓██░░░░░░░░░░░░░░░░░░░░
░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░▓▓▓███████▓██▓█▓▓▓▓▒░▒███▓▒░░▒▓▒░░░░░░░░░░░░
░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░▓█▓████████████▓▓▓▓▒░ ░▒▒██████▒░░░█▓▓▓▓▒░░░
░░░░░░░░░░░░░░░▓██▓░░▒▓██░░░░░░░░░░░▓▓▓▓████████████▓▓▓▒░░░▒▒▒▒▒▒██▓▒████████▒▒░
░░░░░░░░░░░░░░░░░▓▒███░██░░░░░░░░▓██▓███████████████▓▓░░░▒▒▒▒░░░░▓▒░▒▓▒▒▓░▒▒▒▓▒▒
░░░░░░░░░░░░░░░░░██░▓████▓▒██▒███▒ ░▓▓██▓████████▓▓▓▒▓▒▒░░░░▒▒█▓▒▓▒▒▒▓▒█▒▓░▓▓▓▓▓
░░░░░░░░░░░░░░░░░░░▒▓██████▓▓█▒░ ░░░▒▒▒▓▓▓▓████▒░░░▒▒▓▓▒░▒▒▒█▒▒▒▓▒▒▓▒▒▒█▓░▓░▓▒▒▒
░░░░░░░░░░░░░░░░░▒█▓█████▒███▒░░░░░░  ▒▓██████▓▓▓▓▓▓▒▒▒▒▒▓█▒▒░▓▒▒▒▓░░▒▒▓█▓▒▓▓▓▓▓
░░░░░░░░░░░░░░░░░█▓▒▓████▓▓▓▓▓▓▓▒▓▓▓▓▓████████▓▓▓▒▒▒▒▒▒▓█▒▒░▓█▒▒▓▒░░░░▒▒██▒▓▓▓▓▓
░░░░░░░░░░░▒█▓▓▓░▒▓▓█▒▓▒█▓▒█▓▓▓▓▓▓▓▓▓▓▓▓▓█▓█▓▓▓▓▒░░▒▒██▓▒▒▒█▒▒▒▒░░▒░░░▒▒██▒▓█▒█▓
░░░░░░░░█▓▓▓█████▓██▒▒▒▒▒█▓▓▓░░░░▒▒▓▓▓▓▓▓▒▒░▒▒▒░░▒▓██▒▒▒░▒█▒▒▒▓░▒▒░░░▒▒▒▓█▓▓█▓▓▓
░░░░░░░░░░░░░▓▓█████▒▒░░▒▓██▓▓░░░░░░░░▒▓▓█▓▓▒░░▒██▓▓░▒▒▒█▒▒▒▒▒▒░░░░░░▒▒▒▓██▒▓█▓█
░░░░░░░░░░░░░▓░▓█████▒░▒░▒ ▒▒▒▒░▒░ ░░▒▒▒▒▒▒░░░███▓░▓▓▒▒█▒▒░▒▒▒░░░░░░▒▒▒▒▓██▓▓███
░░░░░░░░░░░▒▓▒▓▒█░▓▓▓█▓▓▓▒▒░░░▒█▓▒░░░░░░░░░░▓██▓▒▓▓▓▒▒█▓░░░░▒▒░░░░░░░▒▒▓▓██▓▓▓█▓
░░░░░░░░░░▒▓▓█▓██▒░░▒▒░░░▒░░▒▓▒▓▓███▒▒░░░▓███░▓██▓▒▒▓█▓░░▒░▒▒▒▒░░░░▒░░▒▒▓███▓▓██
░░░░░░░░░▒▓▓▓▓▓░░░▓▓▓▓░░▒░░▒▒▒▓▓▓▓█████▓▒░▓████▓▓▒▒▓█▓▓▒▒▒▒▒▓▒▒▒▒▒▒▒▓▓▒▒▓███▓▓██
░░░░░░░░▒▒▓▓▒▒▓██▓░▓▓▒█░▒▒▓▒▒▒▒▒▓▒███████▓▒▒▓████▓▓█▓█▒▒▒▓▓▓▓▓▓▓▓▓▓▓█▓█▓▓▓███▓▓█
░░░░░░▒▒▒▓▓█▒▓██░░░░░▒▓█▓▒▒▒▒▒▒█▓▓▓▓█████▓█▓░█▒░▓████▓▓▓▓▓▓█▓▓▓█▓▓▓██▓█▓█▓███▓▓▓
░▒▒▒░▒▓▓▓▓█▒▒▓█░░░░▒▒███▒▒▒▓▒▒░▓▒▓█▓████████▒███▓▓███▓▓▓▓██████████▓██▓▓███████▓
▒▒▒▒▒▒▓▓▓██▒▒█░▒▒▒▒▓▓▓▓▓████▓▓█▓▒▒█████████░░████▓▒░▒████▓▓▓▒█████▓█████████████
▒▒▒▒▒▓▓▓███▒▒▒▓▓▓▓▓▓▓████▒▒▒▓▓▓▓▓▓▓██▓███████████████▓░▓▓███▓▒▒▓▓█████▓█████████
▒▒▒▓▓▓▓████▒▓▓█▓▓▓▓▓▓▓██▓▓░▒▓▓▓▓▓▓▒████▓██▒▒▒▓▒▒▓████████▒▓██████████▓██████████
▒▒▒▓▓▓█████▓▓███▓▓▓▓▓▓▓███▓▓░▒▒▓█▓▓███▓▓█▓▓█▓▓▓█▓▓██████████████████████████████
▓▓▓░▓▓▓███▓▓▓████▓▓░▓▓██████▓░░▓▓▒▓████▒▓▓▓████▓████████████▓▒██████████████████
▓▒▓▓▓▓▓███▓▓▓████████▓████████▓▒▒ ▓▓██▓▓▓████▓▓██▓▓▓███████████▓▒▓██████████████
▓▓▓▓▓▓▓███▓▓▓████████▓█████████▓▒▓▒▒▒█▓█▓███▓░▒██▓▓████████████████▓▒▒▓█████████
    `;
    if (minervaAsciiArtDiv) minervaAsciiArtDiv.textContent = MINERVA_ASCII;
    if (copyrightYearSpan) copyrightYearSpan.textContent = new Date().getFullYear();


    const fetchData = async (url) => {
        if(mainLoader) mainLoader.style.display = 'block';
        try {
            const response = await fetch(url);
            if (!response.ok) throw new Error(`Error HTTP: ${response.status}`);
            return await response.json();
        } catch (error) {
            console.error("Error en fetchData:", error);
            if(resultsContent) resultsContent.innerHTML = `<p class="error">Error al cargar datos: ${error.message}. Verifique la consola del servidor Flask.</p>`;
            throw error; 
        } finally {
            if(mainLoader) mainLoader.style.display = 'none';
        }
    };

    const renderSchoolList = (schools) => {
        schoolListContainer.innerHTML = '';
        if (!schools || schools.length === 0) {
            schoolListContainer.innerHTML = '<small>No se encontraron colegios para los criterios seleccionados.</small>';
            return;
        }
        schools.forEach(school => {
            const schoolItem = document.createElement('a');
            schoolItem.href = '#';
            schoolItem.className = 'school-list-item';
            schoolItem.dataset.id = school.id; 
            schoolItem.dataset.displayName = school.name;
            schoolItem.innerHTML = `<h6>${school.name}</h6><p>Promedio Global: <strong>${school.mean.toFixed(2)}</strong> (${school.count} estudiantes)</p>`;
            schoolListContainer.appendChild(schoolItem);
        });
    };

    const renderResults = (data) => {
        const { school_name_display, student_list, benchmarks, performance_levels, histogram_data, historical_evolution } = data;
        schoolNameHeader.textContent = school_name_display;

        const benchmarksHtml = `
            <details open><summary><h5>Análisis Comparativo de Desempeño</h5></summary>
            <div class="overflow-auto"><table><thead><tr><th>Materia</th><th>Prom. Colegio</th><th>Prom. Depto.</th><th>Prom. Nacional</th></tr></thead><tbody>
            ${benchmarks.map(b => `<tr><td>${b.subject}</td><td>${b.school_avg.toFixed(2)}</td><td>${b.dept_avg.toFixed(2)}</td><td>${b.nat_avg.toFixed(2)}</td></tr>`).join('')}
            </tbody></table></div></details>`;

        const levelsHtml = `
            <details><summary><h5>Distribución de Niveles de Desempeño</h5></summary>
            <div class="overflow-auto"><table><thead><tr><th>Materia</th><th>Nivel 1/A-</th><th>Nivel 2/A1</th><th>Nivel 3/A2</th><th>Nivel 4/B1/B+</th></tr></thead><tbody>
            ${performance_levels.map(p => {
                if (p.type === 'english') return `<tr><td>${p.subject}</td><td>${p.levels['A-'] || 0}</td><td>${p.levels['A1'] || 0}</td><td>${p.levels['A2'] || 0}</td><td>${(p.levels['B1'] || 0) + (p.levels['B+'] || 0)}</td></tr>`;
                return `<tr><td>${p.subject}</td><td>${p.levels['1'] || 0}</td><td>${p.levels['2'] || 0}</td><td>${p.levels['3'] || 0}</td><td>${p.levels['4'] || 0}</td></tr>`;
            }).join('')}
            </tbody></table></div></details>`;
        
        const histogramHtml = `<details><summary><h5>Distribución de Puntajes Globales (Colegio)</h5></summary><div id="histogram-chart-container"><canvas id="histogram-chart"></canvas></div></details>`;
        
        const studentsHtml = `
            <details><summary><h5>Resultados Detallados de Estudiantes (${student_list.length})</h5></summary>
            <div class="overflow-auto"><table><thead><tr><th>Fecha de Nac.</th><th>Sexo</th><th>Nacionalidad</th><th>Puntaje Global</th><th>Percentil Global</th></tr></thead><tbody>
            ${student_list.map(s => `<tr><td>${s.estu_fechanacimiento || ''}</td><td>${s.estu_genero || ''}</td><td>${s.estu_nacionalidad || ''}</td><td>${s.punt_global || 0}</td><td>${s.percentil_global ? s.percentil_global + '%' : 'N/A'}</td></tr>`).join('')}
            </tbody></table></div></details>`;

        const evolutionHtml = `
            <details><summary><h5>Evolución Histórica (Promedio Global del Colegio)</h5></summary>
            <div class="overflow-auto">
                <div id="evolution-chart-container"><canvas id="evolution-chart"></canvas></div>
                <table><thead><tr><th>Periodo</th><th>Promedio Global</th></tr></thead><tbody>
                ${historical_evolution.slice().reverse().map(h => `<tr><td>${h.periodo}</td><td>${h.media === -1 ? 'Datos de periodo no disponibles' : (h.media === 0 ? 'Colegio no encontrado/sin datos' : h.media.toFixed(2))}</td></tr>`).join('')}
                </tbody></table>
            </div></details>`;

        resultsContent.innerHTML = benchmarksHtml + levelsHtml + histogramHtml + studentsHtml + evolutionHtml;
        renderHistogramChart(histogram_data);
        renderEvolutionChart(historical_evolution);
    };

    const renderHistogramChart = (scores) => {
        const canvas = document.getElementById('histogram-chart');
        if (!canvas) return;
        const ctx = canvas.getContext('2d');
        
        const bins = {}; const labels = [];
        for (let i = 0; i <= 450; i += 50) { const label = `${i}-${i + 49}`; labels.push(label); bins[label] = 0; }
        scores.forEach(score => {
            const binIndex = Math.floor(score / 50);
            const binLabel = `${binIndex * 50}-${binIndex * 50 + 49}`;
            if (bins[binLabel] !== undefined) bins[binLabel]++;
            else if (score === 500 && labels.length > 0) bins[labels[labels.length -1]]++;
        });
        if (currentHistogramChartInstance) currentHistogramChartInstance.destroy();
        currentHistogramChartInstance = new Chart(ctx, {
            type: 'bar',
            data: { labels: labels, datasets: [{ label: 'Número de Estudiantes', data: Object.values(bins), backgroundColor: 'rgba(255, 215, 0, 0.6)', borderColor: 'rgba(255, 215, 0, 1)', borderWidth: 1 }] },
            options: { responsive: true, maintainAspectRatio: false, scales: { y: { beginAtZero: true, title: { display: true, text: 'Cantidad de Estudiantes' } }, x: { title: { display: true, text: 'Rango de Puntaje Global' } } }, plugins: { legend: { display: false } } }
        });
    };
    
    const renderEvolutionChart = (historicalData) => {
        const canvas = document.getElementById('evolution-chart');
        if(!canvas) return;
        const ctx = canvas.getContext('2d');
        const validHistoricalData = historicalData.filter(d => d.media > 0).reverse(); 
        
        if (currentEvolutionChartInstance) currentEvolutionChartInstance.destroy();
        currentEvolutionChartInstance = new Chart(ctx, {
            type: 'line',
            data: {
                labels: validHistoricalData.map(d => d.periodo),
                datasets: [{
                    label: 'Promedio Global Histórico', data: validHistoricalData.map(d => d.media),
                    borderColor: 'var(--minerva-yellow-darker, #E6C200)', 
                    backgroundColor: 'rgba(255, 215, 0, 0.1)', fill: true, tension: 0.1
                }]
            },
            options: { responsive: true, maintainAspectRatio: false, scales: { y: { beginAtZero: false, title: { display: true, text: 'Promedio Global' } }, x: { title: { display: true, text: 'Periodo' } } }, plugins: { legend: { display: false } } }
        });
    };

    const handlePeriodChange = async (event) => {
        const periodo = event.target.value;
        departmentSelect.innerHTML = '<option value="">Cargando departamentos...</option>';
        departmentSelectLabel.style.display = 'none';
        schoolControls.style.display = 'none';
        resultsContainer.style.display = 'none';
        schoolListContainer.innerHTML = '<small>Seleccione un departamento.</small>';
        if (!periodo) return;
        try {
            const departments = await fetchData(`/api/departments/${periodo}`);
            departmentSelect.innerHTML = '<option value="" selected>Seleccione un departamento</option>';
            departments.forEach(dept => { const option = document.createElement('option'); option.value = dept; option.textContent = dept; departmentSelect.appendChild(option); });
            departmentSelectLabel.style.display = 'block'; departmentSelect.style.display = 'block';
        } catch (error) { departmentSelect.innerHTML = '<option value="">Error al cargar deptos.</option>'; }
    };
    
    const loadSchoolList = async () => {
        const department = departmentSelect.value;
        const periodo = periodSelect.value;
        const topN = topNSelect.value;

        schoolListContainer.innerHTML = '<small>Cargando colegios...</small>';
        resultsContainer.style.display = 'none';

        if (!department || !periodo) { schoolControls.style.display = 'none'; return; }
        
        schoolControls.style.display = 'block';
        let url = `/api/schools/${periodo}/${department}`;
        if (topN !== "0") url += `?top=${topN}`;

        try {
            allSchoolsInPeriodDepartment = await fetchData(url);
            renderSchoolList(allSchoolsInPeriodDepartment);
        } catch (error) { schoolListContainer.innerHTML = '<small>Error al cargar los colegios.</small>';}
    };

    const handleSchoolSearch = () => { 
        const query = schoolSearch.value.toLowerCase();
        if (!allSchoolsInPeriodDepartment) return;
        const filteredSchools = allSchoolsInPeriodDepartment.filter(school => school.raw_name.toLowerCase().includes(query));
        renderSchoolList(filteredSchools);
    };
    
    const handleSchoolClick = async (event) => {
        event.preventDefault();
        const target = event.target.closest('.school-list-item');
        if (!target) return;

        resultsContainer.style.display = 'block';
        resultsContent.innerHTML = ''; 
        if(mainLoader) mainLoader.style.display = 'block';
        schoolNameHeader.textContent = "Cargando detalles para: " + target.dataset.displayName;
        
        try {
            const periodo = periodSelect.value;
            const department = departmentSelect.value;
            const schoolId = target.dataset.id;
            const encodedSchoolId = encodeURIComponent(schoolId);
            const data = await fetchData(`/api/school_details/${periodo}/${department}/${encodedSchoolId}`);
            if(data.error){ resultsContent.innerHTML = `<p class="error">${data.error}</p>`; } 
            else { renderResults(data); }
        } catch (error) { resultsContent.innerHTML = '<p class="error">Error al cargar los detalles del colegio.</p>';
        } finally { if(mainLoader) mainLoader.style.display = 'none'; }
    };

    const handleTabClick = (event) => {
        event.preventDefault();
        tabs.forEach(tab => tab.classList.remove('active'));
        tabContents.forEach(content => content.classList.remove('active'));
        event.target.classList.add('active');
        const activeTabContent = document.getElementById(event.target.dataset.tab);
        if (activeTabContent) activeTabContent.classList.add('active');
    };
    
    const fetchAndUpdateDate = async () => {
        // This assumes you might create an API endpoint to serve the last_updated_date
        // For now, we'll just set it if the placeholder exists.
        // If `app.py` were to have a `/api/last_updated` endpoint:
        // const data = await fetchData('/api/last_updated');
        // if (lastUpdatedPlaceholder && data.date) lastUpdatedPlaceholder.textContent = data.date;
        // As `index.html` directly receives it from Flask now, this JS fetch might not be needed
        // unless you want to dynamically update it without page reload.
        // For now, this function is a placeholder if you decide to fetch it.
    };

    const initializeApp = async () => {
        if(initialLoader) initialLoader.style.display = 'block';
        if(controlsContainer) controlsContainer.style.display = 'none';
        try {
            const periods = await fetchData('/api/periods');
            if(initialLoader) initialLoader.style.display = 'none';
            if(controlsContainer) controlsContainer.style.display = 'block';
            periodSelect.innerHTML = '<option value="" selected>Seleccione un periodo</option>';
            periods.forEach(period => { const option = document.createElement('option'); option.value = period; option.textContent = period; periodSelect.appendChild(option); });
        } catch (error) {
            if(initialLoader) initialLoader.innerHTML = 'Error al cargar periodos iniciales. Intente recargar.';
        }

        periodSelect.addEventListener('change', handlePeriodChange);
        departmentSelect.addEventListener('change', loadSchoolList);
        topNSelect.addEventListener('change', loadSchoolList); 
        schoolSearch.addEventListener('input', handleSchoolSearch);
        schoolListContainer.addEventListener('click', handleSchoolClick);
        tabs.forEach(tab => tab.addEventListener('click', handleTabClick));
        
        // Set initial active tab based on URL hash if present, otherwise default to 'explorar'
        const currentHash = window.location.hash.substring(1);
        const activeTabLink = document.querySelector(`.tab-link[data-tab="${currentHash || 'explorar'}"]`);
        if (activeTabLink) {
            tabs.forEach(tab => tab.classList.remove('active'));
            tabContents.forEach(content => content.classList.remove('active'));
            activeTabLink.classList.add('active');
            const activeContent = document.getElementById(activeTabLink.dataset.tab);
            if (activeContent) activeContent.classList.add('active');
        }
    };

    initializeApp();
});