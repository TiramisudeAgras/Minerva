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
    // --- Funciones de Turnstile ---
async function onTurnstileSuccess(token) {
    // Esta función es llamada por Cloudflare cuando el desafío se completa.
    // console.log("Token de Turnstile recibido:", token);
    if (turnstileStatusMessage) {
        turnstileStatusMessage.textContent = "¡Eureka! Verificación exitosa. Cargando Minerva...";
        turnstileStatusMessage.style.color = "green";
        turnstileStatusMessage.style.display = "block";
    }

    try {
        const response = await fetch('/verify-access', {
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
            
            // Ahora sí, inicializamos la aplicación principal.
            initializeApp();
        } else {
            // Si el backend falla la verificación.
            console.error("Fallo en la verificación del token de Turnstile por el backend:", data.message);
            if (turnstileStatusMessage) {
                turnstileStatusMessage.textContent = `Error de verificación: ${data.message || 'Intente recargar.'}`;
                turnstileStatusMessage.style.color = "red";
                turnstileStatusMessage.style.display = "block";
            }
             // Opcional: resetear el widget si la verificación falla, para que el usuario pueda reintentar (si aplica)
            if (typeof turnstile !== 'undefined' && turnstile.reset) {
                const widgetElement = document.querySelector('.cf-turnstile');
                if (widgetElement) turnstile.reset(widgetElement);
            }
        }
    } catch (error) {
        console.error("Error al enviar el token de Turnstile al backend:", error);
        if (turnstileStatusMessage) {
            turnstileStatusMessage.textContent = "Error de comunicación con el servidor. Intente recargar.";
            turnstileStatusMessage.style.color = "red";
            turnstileStatusMessage.style.display = "block";
        }
    }
}

function onTurnstileError(errorCode) {
    // Esta función es llamada por Cloudflare si hay un error con el widget.
    console.error("Error de Cloudflare Turnstile:", errorCode);
    if (turnstileStatusMessage) {
        turnstileStatusMessage.textContent = "Error al cargar el componente de seguridad. Verifique su conexión o extensiones de navegador e intente recargar.";
        turnstileStatusMessage.style.color = "red";
        turnstileStatusMessage.style.display = "block";
    }
}


// --- Funciones Principales de la App (el resto de tu JS) ---

// No ejecutar initializeApp en DOMContentLoaded directamente.
// Se llamará después de la verificación de Turnstile.
document.addEventListener('DOMContentLoaded', () => {
    if (minervaAsciiArtDiv && MINERVA_ASCII) { // Solo si el div y el ASCII existen
        minervaAsciiArtDiv.textContent = MINERVA_ASCII;
    }
    if (copyrightYearSpan) {
        copyrightYearSpan.textContent = new Date().getFullYear();
    }
    // La inicialización de la app ahora se maneja por onTurnstileSuccess
    // initializeApp(); // No llamar aquí
});

// fetchData ya no necesita la opción de 'headers' para Turnstile en este modelo simple
const fetchData = async (url) => { 
    if(mainLoader) mainLoader.style.display = 'block';
    try {
        const response = await fetch(url); 
        if (!response.ok) {
            let errorData = { message: `Error HTTP: ${response.status} en ${url}` };
            try {
                const jsonError = await response.json();
                errorData.message = jsonError.error || errorData.message; 
            } catch (e) { /* No hacer nada si el cuerpo no es JSON */ }
            throw new Error(errorData.message);
        }
        return await response.json();
    } catch (error) {
        console.error("Error en fetchData:", error.message);
        // Es importante que resultsContent exista antes de intentar modificarlo.
        // Puede que no esté visible o disponible si la app no se ha inicializado.
        if(resultsContent && minervaAppContainer && minervaAppContainer.style.display === 'block') {
            resultsContent.innerHTML = `<p class="error">Error al cargar datos: ${error.message}. Verifique la consola del servidor Flask y la del navegador.</p>`;
        }
        throw error; 
    } finally {
        if(mainLoader) mainLoader.style.display = 'none';
    }
};

const renderSchoolList = (schools) => {
    // ... (lógica sin cambios)
    schoolListContainer.innerHTML = '';
    if (!schools || schools.length === 0) {
        schoolListContainer.innerHTML = '<p style="padding:1rem; text-align:center;"><small>No se encontraron colegios para los criterios seleccionados.</small></p>';
        return;
    }
    schools.forEach(school => {
        const schoolItem = document.createElement('a');
        schoolItem.href = '#results-container'; 
        schoolItem.className = 'school-list-item';
        schoolItem.dataset.id = school.id; 
        schoolItem.dataset.displayName = school.name;
        schoolItem.innerHTML = `<h6>${school.name}</h6><p>Promedio Global: <strong>${school.mean.toFixed(2)}</strong> (${school.count} estudiantes)</p>`;
        schoolListContainer.appendChild(schoolItem);
    });
};

const renderResults = (data) => {
    // ... (lógica sin cambios, incluyendo la columna de ranking #)
    const { school_name_display, student_list, benchmarks, performance_levels, histogram_data, historical_evolution } = data;
    schoolNameHeader.textContent = school_name_display;
    const benchmarksHtml = `
        <details open><summary>Análisis Comparativo de Desempeño</summary>
        <div class="overflow-auto"><table><thead><tr><th>Materia</th><th>Prom. Colegio</th><th>Prom. Depto.</th><th>Prom. Nacional</th></tr></thead><tbody>
        ${benchmarks.map(b => `<tr><td>${b.subject}</td><td>${b.school_avg.toFixed(2)}</td><td>${b.dept_avg.toFixed(2)}</td><td>${b.nat_avg.toFixed(2)}</td></tr>`).join('')}
        </tbody></table></div></details>`;
    const levelsHtml = `
        <details><summary>Distribución de Niveles de Desempeño</summary>
        <div class="overflow-auto"><table><thead><tr><th>Materia</th><th>Nivel 1/A-</th><th>Nivel 2/A1</th><th>Nivel 3/A2</th><th>Nivel 4/B1/B+</th></tr></thead><tbody>
        ${performance_levels.map(p => {
            if (p.type === 'english') return `<tr><td>${p.subject}</td><td>${p.levels['A-'] || 0}</td><td>${p.levels['A1'] || 0}</td><td>${p.levels['A2'] || 0}</td><td>${(p.levels['B1'] || 0) + (p.levels['B+'] || 0)}</td></tr>`;
            return `<tr><td>${p.subject}</td><td>${p.levels['1'] || 0}</td><td>${p.levels['2'] || 0}</td><td>${p.levels['3'] || 0}</td><td>${p.levels['4'] || 0}</td></tr>`;
        }).join('')}
        </tbody></table></div></details>`;
    const histogramHtml = `<details><summary>Distribución de Puntajes Globales (Colegio)</summary><div id="histogram-chart-container"><canvas id="histogram-chart"></canvas></div></details>`;
    const studentsHtml = `
        <details><summary>Resultados Detallados de Estudiantes (${student_list.length})</summary>
        <div class="overflow-auto">
            <table><thead><tr><th>#</th><th>Fecha de Nac.</th><th>Sexo</th><th>Nacionalidad</th><th>Puntaje Global</th><th>Percentil Global</th></tr></thead><tbody>
            ${student_list.map((s, index) => `<tr><td>${index + 1}</td><td>${s.estu_fechanacimiento || ''}</td><td>${s.estu_genero || ''}</td><td>${s.estu_nacionalidad || ''}</td><td>${s.punt_global || 0}</td><td>${s.percentil_global ? s.percentil_global + '%' : 'N/A'}</td></tr>`).join('')}
            </tbody></table></div></details>`;
    const evolutionHtml = `
        <details><summary>Evolución Histórica (Promedio Global del Colegio)</summary>
        <div class="overflow-auto"><div id="evolution-chart-container"><canvas id="evolution-chart"></canvas></div>
        <table><thead><tr><th>Periodo</th><th>Promedio Global</th></tr></thead><tbody>
        ${historical_evolution.map(h => `<tr><td>${h.periodo}</td><td>${h.media === -1 ? 'Datos de periodo no disponibles' : (h.media === 0 ? 'Colegio no encontrado/sin datos' : h.media.toFixed(2))}</td></tr>`).join('')}
        </tbody></table></div></details>`;
    resultsContent.innerHTML = benchmarksHtml + levelsHtml + histogramHtml + studentsHtml + evolutionHtml;
    renderHistogramChart(histogram_data);
    renderEvolutionChart(historical_evolution);
};

const renderHistogramChart = (scores) => { /* ... (sin cambios) ... */ 
    const canvasContainer = document.getElementById('histogram-chart-container');
    const canvas = document.getElementById('histogram-chart');
    if (!canvas || !canvasContainer) return;
    canvasContainer.style.height = '280px';
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
        data: { labels: labels, datasets: [{ label: 'Número de Estudiantes', data: Object.values(bins), backgroundColor: 'rgba(255, 193, 7, 0.7)', borderColor: 'rgba(255, 160, 0, 1)', borderWidth: 1 }] }, 
        options: { responsive: true, maintainAspectRatio: false, scales: { y: { beginAtZero: true, title: { display: true, text: 'Cantidad de Estudiantes' } }, x: { title: { display: true, text: 'Rango de Puntaje Global' } } }, plugins: { legend: { display: false } } }
    });
};

const renderEvolutionChart = (historicalDataOriginalOrder) => { /* ... (sin cambios) ... */ 
    const canvasContainer = document.getElementById('evolution-chart-container');
    const canvas = document.getElementById('evolution-chart');
    if(!canvas || !canvasContainer) return;
    canvasContainer.style.height = '280px';
    const ctx = canvas.getContext('2d');
    const chartData = historicalDataOriginalOrder.filter(d => d.media > 0).sort((a, b) => {
        const yearA = parseInt(a.periodo.substring(0, 4));
        const periodSuffixA = parseInt(a.periodo.substring(5));
        const yearB = parseInt(b.periodo.substring(0, 4));
        const periodSuffixB = parseInt(b.periodo.substring(5));
        if (yearA !== yearB) return yearA - yearB;
        return periodSuffixA - periodSuffixB;
    });
    if (currentEvolutionChartInstance) currentEvolutionChartInstance.destroy();
    currentEvolutionChartInstance = new Chart(ctx, {
        type: 'line',
        data: {
            labels: chartData.map(d => d.periodo),
            datasets: [{
                label: 'Promedio Global Histórico', data: chartData.map(d => d.media),
                borderColor: 'var(--minerva-yellow-hover, #FFA000)', 
                backgroundColor: 'rgba(255, 193, 7, 0.2)', fill: true, tension: 0.1
            }]
        },
        options: { responsive: true, maintainAspectRatio: false, scales: { y: { beginAtZero: false, title: { display: true, text: 'Promedio Global' } }, x: { title: { display: true, text: 'Periodo' } } }, plugins: { legend: { display: false } } }
    });
};

const handlePeriodChange = async (event) => { /* ... (sin cambios) ... */ 
    const periodo = event.target.value;
    departmentSelect.innerHTML = '<option value="">Cargando departamentos...</option>';
    if(departmentSelectLabel) departmentSelectLabel.style.display = 'none';
    if(schoolControls) schoolControls.style.display = 'none';
    resultsContainer.style.display = 'none';
    schoolListContainer.innerHTML = '<small>Seleccione un departamento.</small>';
    if (!periodo) return;
    try {
        const departments = await fetchData(`/api/departments/${periodo}`);
        departmentSelect.innerHTML = '<option value="" selected>Seleccione un departamento</option>';
        departments.forEach(dept => { const option = document.createElement('option'); option.value = dept; option.textContent = dept; departmentSelect.appendChild(option); });
        if(departmentSelectLabel) departmentSelectLabel.style.display = 'block'; 
        departmentSelect.style.display = 'block';
    } catch (error) { departmentSelect.innerHTML = '<option value="">Error al cargar deptos.</option>'; }
};

const loadSchoolList = async () => { /* ... (sin cambios) ... */ 
    const department = departmentSelect.value;
    const periodo = periodSelect.value;
    const topN = topNSelect.value;
    schoolListContainer.innerHTML = '<article aria-busy="true" style="text-align:center; padding:1rem;"></article>'; 
    resultsContainer.style.display = 'none';
    if (!department || !periodo) { 
        if(schoolControls) schoolControls.style.display = 'none'; 
        schoolListContainer.innerHTML = '<small>Seleccione periodo y departamento.</small>'; return; 
    }
    if(schoolControls) schoolControls.style.display = 'block';
    let url = `/api/schools/${periodo}/${department}`;
    if (topN !== "0") url += `?top=${topN}`;
    try {
        allSchoolsInPeriodDepartment = await fetchData(url);
        renderSchoolList(allSchoolsInPeriodDepartment);
    } catch (error) { schoolListContainer.innerHTML = '<small>Error al cargar los colegios.</small>';}
};

const handleSchoolSearch = () => { /* ... (sin cambios) ... */ 
    const query = schoolSearch.value.toLowerCase();
    if (!allSchoolsInPeriodDepartment) return;
    const filteredSchools = allSchoolsInPeriodDepartment.filter(school => school.raw_name.toLowerCase().includes(query));
    renderSchoolList(filteredSchools);
};

// handleSchoolClick ya no necesita enviar el token de Turnstile en este modelo simple
const handleSchoolClick = async (event) => { 
    event.preventDefault();
    const target = event.target.closest('.school-list-item');
    if (!target) return;

    resultsContainer.style.display = 'block';
    resultsContent.innerHTML = ''; 
    if(mainLoader) mainLoader.style.display = 'block';
    schoolNameHeader.textContent = "Cargando detalles (¡Esto puede tomar algunos minutos!☕) para: " + target.dataset.displayName;
    resultsContainer.scrollIntoView({ behavior: 'smooth', block: 'start' });

    try {
        const periodo = periodSelect.value;
        const department = departmentSelect.value;
        const schoolId = target.dataset.id;
        const encodedSchoolId = encodeURIComponent(schoolId);
        
        // Ya no se envían cabeceras de Turnstile aquí
        const data = await fetchData(`/api/school_details/${periodo}/${department}/${encodedSchoolId}`);
        
        if(data.error){ 
            resultsContent.innerHTML = `<p class="error">${data.error}</p>`; 
        } else { 
            renderResults(data); 
        }
    } catch (error) { /* El error ya se maneja en fetchData */ } 
    finally { 
        if(mainLoader) mainLoader.style.display = 'none'; 
    }
};

const handleTabClick = (event) => { /* ... (sin cambios) ... */ 
    event.preventDefault();
    tabs.forEach(tab => tab.classList.remove('active'));
    tabContents.forEach(content => content.classList.remove('active'));
    const clickedTabLink = event.currentTarget;
    clickedTabLink.classList.add('active');
    const activeTabContentId = clickedTabLink.dataset.tab;
    const activeTabContent = document.getElementById(activeTabContentId);
    if (activeTabContent) activeTabContent.classList.add('active');
    window.location.hash = activeTabContentId;
};
    
// Esta es la función que ahora se llama DESPUÉS de la verificación de Turnstile
const initializeApp = async () => {
    // Esta función ahora se encarga de configurar la app una vez verificado el acceso.
    // El 'initialLoader' de la app principal (dentro de #minerva-app-container)
    if(initialLoader) initialLoader.style.display = 'block';
    if(controlsContainer) controlsContainer.style.display = 'none'; // Se mostrará después de cargar periodos

    try {
        const periods = await fetchData('/api/periods');
        if(initialLoader) initialLoader.style.display = 'none';
        if(controlsContainer) controlsContainer.style.display = 'block';
        periodSelect.innerHTML = '<option value="" selected>Seleccione un periodo</option>';
        
        periods.forEach(period => { 
            const option = document.createElement('option'); 
            option.value = period.value;
            option.textContent = period.display;
            periodSelect.appendChild(option); 
        });
        
        const lastUpdatedFromHTML = document.body.dataset.lastUpdatedDate; // Asumo que esto está en el body
        if (lastUpdatedPlaceholder) lastUpdatedPlaceholder.textContent = lastUpdatedFromHTML || "No disponible";

    } catch (error) {
        if(initialLoader) initialLoader.innerHTML = 'Error al cargar periodos iniciales. Intente recargar la página.';
    }

    periodSelect.addEventListener('change', handlePeriodChange);
    departmentSelect.addEventListener('change', loadSchoolList);
    topNSelect.addEventListener('change', loadSchoolList); 
    schoolSearch.addEventListener('input', handleSchoolSearch);
    schoolListContainer.addEventListener('click', handleSchoolClick);
    tabs.forEach(tab => tab.addEventListener('click', handleTabClick));
    
    const currentHash = window.location.hash.substring(1);
    const targetTab = currentHash || 'explorar';
    
    tabs.forEach(tab => tab.classList.remove('active'));
    tabContents.forEach(content => content.classList.remove('active'));

    const activeTabLink = document.querySelector(`.tab-link[data-tab="${targetTab}"]`);
    if (activeTabLink) {
        activeTabLink.classList.add('active');
        const activeContent = document.getElementById(targetTab);
        if (activeContent) activeContent.classList.add('active');
    } else {
        const defaultTabLink = document.querySelector('.tab-link[data-tab="explorar"]');
        if (defaultTabLink) defaultTabLink.classList.add('active');
        const defaultTabContent = document.getElementById('explorar');
        if (defaultTabContent) defaultTabContent.classList.add('active');
    }
};