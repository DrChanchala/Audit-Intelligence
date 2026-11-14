/**
 * QC Lead Console — Inspections Directory Controller.
 * Lists all allocations with real-time status filtering, project filtering,
 * text search, and drawer inspection detail viewing.
 */
import { api } from '../shared/api.js';
import { html, render } from '../shared/html.js';
import { formatDate } from '../shared/format.js';
import { openInspectionDrawer } from './dossier.js';

let allAllocations = [];
let allProjects = [];
let selectedProjectId = 'all';
let selectedStatus = 'all';
let searchQuery = '';

export async function initInspections(container, defaultProjectId = 'all') {
  selectedProjectId = defaultProjectId;

  render(container, html`
    <div class="card">
      <div class="card-header">
        <div class="filter-row">
          <h2 class="card-title">Field Inspections Directory</h2>

          <select id="inspProjectFilter" class="form-select select-compact">
            <option value="all">All Projects</option>
          </select>

          <select id="inspStatusFilter" class="form-select select-compact">
            <option value="all">All Statuses</option>
            <option value="Allocated">Allocated</option>
            <option value="In progress">In Progress</option>
            <option value="Pending review">Pending Review</option>
            <option value="Report issued">Report Issued</option>
            <option value="Returned">Returned for Reinspection</option>
          </select>

          <input
            type="search"
            id="inspSearchInput"
            class="form-control select-compact"
            placeholder="Search allocation ID, engineer, location..."
          >
        </div>

        <button type="button" class="btn btn-secondary btn-sm" id="btnRefreshInspections">
          ↻ Refresh
        </button>
      </div>

      <div class="table-wrap">
        <table class="data-table" id="inspectionsTable">
          <thead>
            <tr>
              <th>Allocation ID</th>
              <th>Inspection Title / Scope</th>
              <th>Project</th>
              <th>Location</th>
              <th>Assigned Engineer</th>
              <th>Priority</th>
              <th>Due Date</th>
              <th>Status</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody id="inspectionsTableBody">
            <tr><td colspan="9" class="muted table-empty-cell">Loading inspections...</td></tr>
          </tbody>
        </table>
      </div>
    </div>
  `);

  attachFilterEvents(container);
  await loadInspectionsData(container);
}

function getPriorityBadge(priority) {
  const p = (priority || '').toUpperCase();
  if (p === 'HIGH' || p === 'H') return html`<span class="badge badge-crit font-xs">High</span>`;
  if (p === 'MEDIUM' || p === 'M') return html`<span class="badge badge-major font-xs">Medium</span>`;
  if (p === 'LOW' || p === 'L') return html`<span class="badge badge-minor font-xs">Low</span>`;
  return html`<span class="badge badge-neutral font-xs">${priority || 'Normal'}</span>`;
}

function getStatusBadge(status) {
  const s = (status || '').toLowerCase();
  if (s === 'allocated') return html`<span class="badge badge-minor">Allocated</span>`;
  if (s === 'in progress') return html`<span class="badge badge-minor">In Progress</span>`;
  if (s === 'pending review') return html`<span class="badge badge-major">Pending Review</span>`;
  if (s === 'report issued' || s === 'approved') return html`<span class="badge badge-mint">Report Issued</span>`;
  if (s === 'returned' || s.includes('reinspection')) return html`<span class="badge badge-crit">Returned</span>`;
  return html`<span class="badge badge-neutral">${status}</span>`;
}

async function loadInspectionsData(container) {
  try {
    const [pResp, aResp] = await Promise.all([
      api.get('/api/projects'),
      api.get('/api/allocations'),
    ]);

    allProjects = Array.isArray(pResp) ? pResp : (pResp.projects || []);
    allAllocations = Array.isArray(aResp) ? aResp : (aResp.allocations || []);

    // Populate project filter
    const projSelect = container.querySelector('#inspProjectFilter');
    if (projSelect) {
      render(projSelect, html`
        <option value="all" ${selectedProjectId === 'all' ? 'selected' : ''}>All Projects</option>
        ${allProjects.map(p => html`
          <option value="${p.id}" ${p.id === selectedProjectId ? 'selected' : ''}>
            ${p.name}
          </option>
        `)}
      `);
    }

    renderFilteredTable(container);
  } catch (err) {
    console.error('Failed to load inspections:', err);
    const tbody = container.querySelector('#inspectionsTableBody');
    if (tbody) {
      render(tbody, html`
        <tr>
          <td colspan="9" class="table-error-cell">
            Failed to load inspections. Please refresh.
          </td>
        </tr>
      `);
    }
  }
}

function renderFilteredTable(container) {
  const tbody = container.querySelector('#inspectionsTableBody');
  if (!tbody) return;

  const filtered = allAllocations.filter(a => {
    if (selectedProjectId !== 'all' && a.project_id !== selectedProjectId) return false;
    if (selectedStatus !== 'all' && (a.status || '').toLowerCase() !== selectedStatus.toLowerCase()) return false;
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      const match = (
        (a.allocation_id || '').toLowerCase().includes(q) ||
        (a.title || '').toLowerCase().includes(q) ||
        (a.engineer_name || '').toLowerCase().includes(q) ||
        (a.location_hierarchy || '').toLowerCase().includes(q) ||
        (a.tower_block || '').toLowerCase().includes(q)
      );
      if (!match) return false;
    }
    return true;
  });

  if (filtered.length === 0) {
    render(tbody, html`
      <tr>
        <td colspan="9" class="muted table-empty-cell">
          No inspections match the selected filters.
        </td>
      </tr>
    `);
    return;
  }

  render(tbody, html`
    ${filtered.map(a => html`
      <tr class="inspection-row cursor-pointer" data-id="${a.allocation_id}">
        <td><strong class="num">${a.allocation_id}</strong></td>
        <td>
          <div class="fw-600">${a.title || 'Field Quality Inspection'}</div>
          <div class="muted font-xs">${a.checkpoint_count || a.total_checkpoints || 0} checkpoints</div>
        </td>
        <td>${a.project_name || a.project_id}</td>
        <td class="font-xs">${a.location_hierarchy || [a.tower_block, a.floor_level, a.zone_area].filter(Boolean).join(' • ') || '—'}</td>
        <td>${a.engineer_name || a.engineer_id || '—'}</td>
        <td>${getPriorityBadge(a.priority)}</td>
        <td class="num font-xs">${formatDate(a.due_date)}</td>
        <td>${getStatusBadge(a.status)}</td>
        <td>
          <button type="button" class="btn btn-secondary btn-sm btn-open-drawer" data-id="${a.allocation_id}">
            View Details →
          </button>
        </td>
      </tr>
    `)}
  `);

  // Attach drawer openers
  tbody.querySelectorAll('.btn-open-drawer').forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      const id = btn.getAttribute('data-id');
      if (id) openInspectionDrawer(id);
    });
  });

  tbody.querySelectorAll('.inspection-row').forEach(row => {
    row.addEventListener('click', () => {
      const id = row.getAttribute('data-id');
      if (id) openInspectionDrawer(id);
    });
  });
}

function attachFilterEvents(container) {
  const pSelect = container.querySelector('#inspProjectFilter');
  if (pSelect) {
    pSelect.addEventListener('change', (e) => {
      selectedProjectId = e.target.value;
      renderFilteredTable(container);
    });
  }

  const sSelect = container.querySelector('#inspStatusFilter');
  if (sSelect) {
    sSelect.addEventListener('change', (e) => {
      selectedStatus = e.target.value;
      renderFilteredTable(container);
    });
  }

  const sInput = container.querySelector('#inspSearchInput');
  if (sInput) {
    sInput.addEventListener('input', (e) => {
      searchQuery = e.target.value;
      renderFilteredTable(container);
    });
  }

  const refreshBtn = container.querySelector('#btnRefreshInspections');
  if (refreshBtn) {
    refreshBtn.addEventListener('click', () => {
      loadInspectionsData(container);
    });
  }
}
