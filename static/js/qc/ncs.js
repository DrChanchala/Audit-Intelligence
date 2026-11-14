/**
 * QC Lead Console — Non-Conformities (NCs) Controller.
 * Lists all raised defects across projects with filters for severity and status,
 * and allows QC Leads to verify, close, reopen, or remind field teams.
 */
import { api } from '../shared/api.js';
import { html, render } from '../shared/html.js';
import { formatDate } from '../shared/format.js';
import { showToast } from '../shared/ui.js';

let allNCs = [];
let selectedSeverity = 'all';
let selectedStatus = 'all';

export async function initNCs(container) {
  render(container, html`
    <div class="card">
      <div class="card-header">
        <div class="filter-row">
          <h2 class="card-title">Non-Conformities (NCs) Quality Register</h2>

          <select id="ncSeverityFilter" class="form-select select-compact">
            <option value="all">All Severities</option>
            <option value="critical">Critical</option>
            <option value="major">Major</option>
            <option value="minor">Minor</option>
            <option value="ofi">OFI (Observation)</option>
          </select>

          <select id="ncStatusFilter" class="form-select select-compact">
            <option value="all">All Statuses</option>
            <option value="open">Open</option>
            <option value="verified">Verified</option>
            <option value="closed">Closed</option>
          </select>
        </div>

        <button type="button" class="btn btn-secondary btn-sm" id="btnRefreshNCs">
          ↻ Refresh
        </button>
      </div>

      <div class="table-wrap">
        <table class="data-table" id="ncsTable">
          <thead>
            <tr>
              <th>NC Code</th>
              <th>Description / Defect</th>
              <th>Project</th>
              <th>Location</th>
              <th>Severity</th>
              <th>Raised Date</th>
              <th>Status</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody id="ncsTableBody">
            <tr><td colspan="8" class="muted table-empty-cell">Loading non-conformities...</td></tr>
          </tbody>
        </table>
      </div>
    </div>
  `);

  attachEvents(container);
  await loadNCsData(container);
}

function getSeverityBadge(severity) {
  const s = (severity || '').toLowerCase();
  if (s === 'critical') return html`<span class="badge badge-crit font-xs">Critical</span>`;
  if (s === 'major') return html`<span class="badge badge-major font-xs">Major</span>`;
  if (s === 'minor') return html`<span class="badge badge-minor font-xs">Minor</span>`;
  return html`<span class="badge badge-ofi font-xs">OFI</span>`;
}

function getStatusBadge(status) {
  const s = (status || '').toLowerCase();
  if (s === 'open') return html`<span class="badge badge-crit font-xs">Open</span>`;
  if (s === 'verified') return html`<span class="badge badge-minor font-xs">Verified</span>`;
  if (s === 'closed') return html`<span class="badge badge-mint font-xs">Closed</span>`;
  return html`<span class="badge badge-neutral font-xs">${status}</span>`;
}

async function loadNCsData(container) {
  try {
    const resp = await api.get('/api/ncs');
    allNCs = Array.isArray(resp) ? resp : (resp.ncs || []);
    renderTable(container);
  } catch (err) {
    const tbody = container.querySelector('#ncsTableBody');
    if (tbody) {
      render(tbody, html`
        <tr><td colspan="8" class="table-error-cell">Failed to load NCs. Please refresh.</td></tr>
      `);
    }
  }
}

function renderTable(container) {
  const tbody = container.querySelector('#ncsTableBody');
  if (!tbody) return;

  const filtered = allNCs.filter(nc => {
    if (selectedSeverity !== 'all' && (nc.severity || '').toLowerCase() !== selectedSeverity) return false;
    if (selectedStatus !== 'all' && (nc.status || '').toLowerCase() !== selectedStatus) return false;
    return true;
  });

  if (filtered.length === 0) {
    render(tbody, html`
      <tr>
        <td colspan="8" class="muted table-empty-cell">
          No non-conformities found matching the filter criteria.
        </td>
      </tr>
    `);
    return;
  }

  render(tbody, html`
    ${filtered.map(nc => html`
      <tr>
        <td><strong class="num">${nc.nc_code || nc.id}</strong></td>
        <td>
          <div class="fw-600">${nc.description || nc.title || 'Quality Defect'}</div>
          ${nc.checkpoint_id ? html`<div class="muted font-xs">Chk: ${nc.checkpoint_id}</div>` : ''}
        </td>
        <td>${nc.project_name || nc.project_id || '—'}</td>
        <td class="font-xs">${nc.location || nc.location_hierarchy || '—'}</td>
        <td>${getSeverityBadge(nc.severity)}</td>
        <td class="num font-xs">${formatDate(nc.raised_date || nc.created_at)}</td>
        <td>${getStatusBadge(nc.status)}</td>
        <td>
          <div class="flex-row-gap">
            ${(nc.status || '').toLowerCase() === 'open' ? html`
              <button type="button" class="btn btn-secondary btn-sm btn-nc-action" data-code="${nc.nc_code || nc.id}" data-action="verify">
                Verify
              </button>
              <button type="button" class="btn btn-ghost btn-sm btn-nc-action" data-code="${nc.nc_code || nc.id}" data-action="remind">
                Remind
              </button>
            ` : ''}

            ${(nc.status || '').toLowerCase() === 'verified' ? html`
              <button type="button" class="btn btn-primary btn-sm btn-nc-action" data-code="${nc.nc_code || nc.id}" data-action="close">
                Close
              </button>
              <button type="button" class="btn btn-ghost btn-sm btn-nc-action" data-code="${nc.nc_code || nc.id}" data-action="reopen">
                Reopen
              </button>
            ` : ''}

            ${(nc.status || '').toLowerCase() === 'closed' ? html`
              <button type="button" class="btn btn-ghost btn-sm btn-nc-action" data-code="${nc.nc_code || nc.id}" data-action="reopen">
                Reopen
              </button>
            ` : ''}
          </div>
        </td>
      </tr>
    `)}
  `);

  tbody.querySelectorAll('.btn-nc-action').forEach(btn => {
    btn.addEventListener('click', async () => {
      const code = btn.getAttribute('data-code');
      const action = btn.getAttribute('data-action');
      const note = window.prompt(`Enter optional note for '${action}' on ${code}:`) || '';

      btn.disabled = true;
      try {
        await api.post(`/api/ncs/${code}/action`, { action, note });
        showToast(`NC ${code} ${action} action recorded successfully!`, 'success');
        await loadNCsData(container);
      } catch (err) {
        btn.disabled = false;
      }
    });
  });
}

function attachEvents(container) {
  const sevSelect = container.querySelector('#ncSeverityFilter');
  if (sevSelect) {
    sevSelect.addEventListener('change', (e) => {
      selectedSeverity = e.target.value;
      renderTable(container);
    });
  }

  const statSelect = container.querySelector('#ncStatusFilter');
  if (statSelect) {
    statSelect.addEventListener('change', (e) => {
      selectedStatus = e.target.value;
      renderTable(container);
    });
  }

  const refreshBtn = container.querySelector('#btnRefreshNCs');
  if (refreshBtn) {
    refreshBtn.addEventListener('click', () => {
      loadNCsData(container);
    });
  }
}
