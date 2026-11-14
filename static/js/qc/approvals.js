/**
 * QC Lead Console — Pending Approvals Queue Controller.
 * Lists all inspections submitted by field engineers waiting for QC Lead review,
 * with one-click Approve / Return actions.
 */
import { api } from '../shared/api.js';
import { html, render } from '../shared/html.js';
import { formatDate } from '../shared/format.js';
import { showToast } from '../shared/ui.js';
import { openInspectionDrawer } from './dossier.js';

let approvalsList = [];

export async function initApprovals(container, onActionCompleted) {
  render(container, html`
    <div class="card">
      <div class="card-header">
        <h2 class="card-title">Pending Inspection Approvals Queue</h2>
        <button type="button" class="btn btn-secondary btn-sm" id="btnRefreshApprovals">
          ↻ Refresh
        </button>
      </div>
      <div class="table-wrap">
        <table class="data-table" id="approvalsTable">
          <thead>
            <tr>
              <th>Allocation ID</th>
              <th>Inspection Title</th>
              <th>Project</th>
              <th>Submitted By (Engineer)</th>
              <th>Due Date</th>
              <th>Status</th>
              <th>Review Actions</th>
            </tr>
          </thead>
          <tbody id="approvalsTableBody">
            <tr><td colspan="7" class="muted table-empty-cell">Loading approvals queue...</td></tr>
          </tbody>
        </table>
      </div>
    </div>
  `);

  const refreshBtn = container.querySelector('#btnRefreshApprovals');
  if (refreshBtn) {
    refreshBtn.addEventListener('click', () => loadApprovals(container, onActionCompleted));
  }

  await loadApprovals(container, onActionCompleted);
}

async function loadApprovals(container, onActionCompleted) {
  const tbody = container.querySelector('#approvalsTableBody');
  try {
    const resp = await api.get('/api/allocations?status=Pending%20review');
    approvalsList = Array.isArray(resp) ? resp : (resp.allocations || []);

    if (approvalsList.length === 0) {
      render(tbody, html`
        <tr>
          <td colspan="7" class="muted table-empty-cell">
            🎉 All caught up! No inspections currently pending review.
          </td>
        </tr>
      `);
      return;
    }

    render(tbody, html`
      ${approvalsList.map(a => html`
        <tr>
          <td><strong class="num">${a.allocation_id}</strong></td>
          <td>
            <div class="fw-600">${a.title || 'Field Quality Inspection'}</div>
            <div class="muted font-xs">${a.checkpoint_count || 0} checkpoints</div>
          </td>
          <td>${a.project_name || a.project_id}</td>
          <td>${a.engineer_name || a.engineer_id || '—'}</td>
          <td class="num font-xs">${formatDate(a.due_date)}</td>
          <td><span class="badge badge-major font-xs">Pending Review</span></td>
          <td>
            <div class="flex-row-gap">
              <button type="button" class="btn btn-secondary btn-sm btn-inspect-sheet" data-id="${a.allocation_id}">
                Inspect
              </button>
              <button type="button" class="btn btn-danger btn-sm btn-quick-return" data-id="${a.allocation_id}">
                Return
              </button>
              <button type="button" class="btn btn-primary btn-sm btn-quick-approve" data-id="${a.allocation_id}">
                Approve
              </button>
            </div>
          </td>
        </tr>
      `)}
    `);

    // Attach row events
    tbody.querySelectorAll('.btn-inspect-sheet').forEach(btn => {
      btn.addEventListener('click', () => {
        const id = btn.getAttribute('data-id');
        if (id) openInspectionDrawer(id);
      });
    });

    tbody.querySelectorAll('.btn-quick-approve').forEach(btn => {
      btn.addEventListener('click', async () => {
        const id = btn.getAttribute('data-id');
        if (!confirm(`Approve inspection ${id} and issue quality report?`)) return;

        btn.disabled = true;
        try {
          await api.post(`/api/allocations/${id}/review`, {
            decision: 'approve',
            comments: 'Approved by QC Lead.',
          });
          showToast(`Inspection ${id} approved!`, 'success');
          await loadApprovals(container, onActionCompleted);
          if (onActionCompleted) onActionCompleted();
        } catch (err) {
          btn.disabled = false;
        }
      });
    });

    tbody.querySelectorAll('.btn-quick-return').forEach(btn => {
      btn.addEventListener('click', async () => {
        const id = btn.getAttribute('data-id');
        const comments = window.prompt(`Enter rework comments for returning inspection ${id}:`);
        if (comments === null) return;
        if (!comments.trim()) {
          showToast('Comments are required to return an inspection.', 'error');
          return;
        }

        btn.disabled = true;
        try {
          await api.post(`/api/allocations/${id}/review`, {
            decision: 'return',
            comments: comments.trim(),
          });
          showToast(`Inspection ${id} returned for rework.`, 'info');
          await loadApprovals(container, onActionCompleted);
          if (onActionCompleted) onActionCompleted();
        } catch (err) {
          btn.disabled = false;
        }
      });
    });

  } catch (err) {
    render(tbody, html`
      <tr>
        <td colspan="7" class="table-error-cell">
          Failed to load approvals queue. Please refresh.
        </td>
      </tr>
    `);
  }
}
