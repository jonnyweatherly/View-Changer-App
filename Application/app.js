/**
 * View Changer App - Main Application Logic
 * 
 * Handles:
 * - Fetching and displaying view columns
 * - Table rendering
 * - Column chip rendering
 * - Toast notifications
 * 
 * Test locally by opening http://localhost:8000 after running:
 *   uvicorn main:app --reload --port 8000
 */

// --- State ---
const STATE = {
    viewColumns: [],
    availableColumns: [],
    patients: [],
    currentView: 'vwTitanium_WLAdmin'
};

// --- DOM Elements ---
const elements = {
    tableHeader: document.getElementById('tableHeader'),
    tableBody: document.getElementById('tableBody'),

    refreshBtn: document.getElementById('refreshBtn'),
    toastContainer: document.getElementById('toastContainer'),
    viewNameBadge: document.getElementById('viewNameBadge')
};

// --- API Functions ---

/**
 * Fetch the current view columns from the API
 */
async function fetchViewColumns() {
    try {
        const response = await fetch(`/api/view-columns?view_name=${STATE.currentView}`);
        const data = await response.json();
        STATE.viewColumns = data.columns || [];
        renderViewTable();

    } catch (error) {
        console.error('Error fetching view columns:', error);
        showToast('Failed to load view columns', 'error');
    }
}

/**
 * Fetch available patient columns from the API
 */
async function fetchAvailableColumns(search = '') {
    try {
        const url = search
            ? `/api/patient-columns?search=${encodeURIComponent(search)}`
            : '/api/patient-columns';
        const response = await fetch(url);
        const data = await response.json();
        STATE.availableColumns = data.columns || [];
        return STATE.availableColumns;
    } catch (error) {
        console.error('Error fetching available columns:', error);
        showToast('Failed to load available columns', 'error');
        return [];
    }
}


/**
 * Fetch patient data from the API
 */
async function fetchPatients() {
    try {
        const response = await fetch(`/api/patients?view_name=${STATE.currentView}`);
        const data = await response.json();
        STATE.patients = data.data || [];
        renderViewTable(); // Re-render with data
    } catch (error) {
        console.error('Error fetching patients:', error);
        showToast('Failed to load patient data', 'error');
    }
}

// --- Render Functions ---

/**
 * Render the view table headers
 */
function renderViewTable() {
    // Sort by grid_order
    const sortedColumns = [...STATE.viewColumns].sort((a, b) => a.grid_order - b.grid_order);

    // Render headers
    elements.tableHeader.innerHTML = sortedColumns.map(col => `
        <th style="width: ${col.grid_width}; ${col.is_right_aligned ? 'text-align: right;' : ''}">
            <div class="column-info">
                <span class="column-label">${escapeHtml(col.label)}</span>
                <span class="column-name">${escapeHtml(col.column_name)}</span>
            </div>
        </th>
    `).join('');


    // Render rows
    if (sortedColumns.length > 0 && STATE.patients && STATE.patients.length > 0) {
        elements.tableBody.innerHTML = STATE.patients.map(patient => `
            <tr>
                ${sortedColumns.map(col => {
            const value = patient[col.column_name];
            // Handle boolean checkboxes or nulls
            let displayValue = value;
            if (value === null || value === undefined) displayValue = '';
            else if (typeof value === 'boolean') displayValue = value ? 'Yes' : 'No';

            return `
                    <td class="${col.is_right_aligned ? 'right-aligned' : ''}" style="width: ${col.grid_width}">
                        ${escapeHtml(String(displayValue))}
                    </td>
                `}).join('')}
            </tr>
        `).join('');
    } else if (sortedColumns.length > 0) {
        // Show empty state if columns exist but no data
        elements.tableBody.innerHTML = `
             <tr>
                <td colspan="${sortedColumns.length}" style="text-align: center; padding: 2rem; color: var(--text-muted);">
                    No patient data available.
                </td>
            </tr>
        `;
    } else {
        elements.tableBody.innerHTML = `
            <tr>
                <td colspan="100" class="empty-state">
                    <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <rect x="3" y="3" width="18" height="18" rx="2"/>
                        <line x1="9" y1="3" x2="9" y2="21"/>
                        <line x1="3" y1="9" x2="21" y2="9"/>
                    </svg>
                    <p>No columns configured. Ask the AI to add some!</p>
                </td>
            </tr>
        `;
    }
}



// --- Toast Notifications ---

/**
 * Show a toast notification
 * @param {string} message - The message to display
 * @param {string} type - 'success', 'error', or 'info'
 */
function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            ${type === 'success'
            ? '<path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/>'
            : type === 'error'
                ? '<circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/>'
                : '<circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/>'
        }
        </svg>
        <span>${escapeHtml(message)}</span>
    `;

    elements.toastContainer.appendChild(toast);

    // Auto-remove after 4 seconds
    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(100px)';
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

// --- Utility Functions ---

/**
 * Escape HTML to prevent XSS
 */
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * Refresh data from the API
 */
async function refreshData() {
    await fetchViewColumns();
    await fetchPatients();
    showToast('View refreshed', 'success');
}

// --- Event Listeners ---

elements.refreshBtn?.addEventListener('click', refreshData);

// --- Initialize ---
document.addEventListener('DOMContentLoaded', async () => {
    await fetchViewColumns();
    fetchPatients();

    // Update view name badge
    if (elements.viewNameBadge) {
        elements.viewNameBadge.textContent = STATE.currentView;
    }
});

// Export for use in chat.js
window.APP = {
    STATE,
    fetchViewColumns,
    fetchAvailableColumns,
    showToast,
    refreshData
};
