/**
 * QC Lead Console — Inspection Side Sheet Drawer & AI Dossier Viewer.
 * Displays checkpoints, photo evidence, audit log, review comments,
 * and handles Approve / Return / Reassign / Generate Dossier actions.
 */
import { api } from '../shared/api.js';
import { html, render, raw } from '../shared/html.js';
import { formatDate, formatDateTime } from '../shared/format.js';
import { showToast, openModal, closeModal } from '../shared/ui.js';

let currentAllocation = null;
let currentEngineers = [];
let onActionCallback = null;

export function initSideSheet(onActionCompleted) {
  onActionCallback = onActionCompleted;
  loadEngineersList();

  const closeIcon = document.getElementById('closeDrawerIconBtn');
  if (closeIcon) closeIcon.addEventListener('click', closeInspectionDrawer);

  const backdrop = document.getElementById('inspectionDrawerBackdrop');
  if (backdrop) {
    backdrop.addEventListener('click', (e) => {
      if (e.target === backdrop) closeInspectionDrawer();
    });
  }
}

async function loadEngineersList() {
  try {
    const resp = await api.get('/api/engineers');
    currentEngineers = resp.engineers || [];
  } catch (_) {}
}

export async function openInspectionDrawer(allocationId) {
  const backdrop = document.getElementById('inspectionDrawerBackdrop');
  const bodyEl = document.getElementById('drawerBody');
  const footerEl = document.getElementById('drawerFooter');
  const titleEl = document.getElementById('drawerTitle');

  if (!backdrop) return;
  backdrop.classList.add('active');

  if (titleEl) titleEl.textContent = `Inspection ${allocationId}`;
  render(bodyEl, html`<div class="muted table-empty-cell">Loading inspection details...</div>`);
  render(footerEl, html``);

  try {
    const data = await api.get(`/api/allocations/${allocationId}`);
    currentAllocation = data.allocation || data;
    renderDrawerContent(currentAllocation);
  } catch (err) {
    render(bodyEl, html`
      <div class="table-error-cell">Failed to load inspection ${allocationId}.</div>
    `);
  }
}

export function closeInspectionDrawer() {
  const backdrop = document.getElementById('inspectionDrawerBackdrop');
  if (backdrop) backdrop.classList.remove('active');
  currentAllocation = null;
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

function renderDrawerContent(alloc) {
  const bodyEl = document.getElementById('drawerBody');
  const footerEl = document.getElementById('drawerFooter');
  const titleEl = document.getElementById('drawerTitle');

  if (titleEl) {
    titleEl.textContent = `${alloc.allocation_id || alloc.inspection_id || 'Inspection'} — ${alloc.title || 'Quality Audit'}`;
  }

  const checkpoints = alloc.checkpoints || [];
  const photos = alloc.evidence_photos || alloc.photos || [];
  const auditLog = alloc.audit_trail || alloc.audit_events || [];
  const reviews = alloc.reviews || [];

  const isPendingReview = (alloc.status === 'Pending review');

  render(bodyEl, html`
    <div class="mb-xl">
      <div class="flex-between mb-sm">
        <span class="muted font-xs num">${alloc.allocation_id}</span>
        ${getStatusBadge(alloc.status)}
      </div>

      <h3 class="card-title-sub mb-xs">${alloc.title || 'Field Quality Inspection'}</h3>
      <div class="muted font-sm lh-base">
        Project: <strong>${alloc.project_name || alloc.project_id}</strong><br>
        Location: <strong>${alloc.location_hierarchy || [alloc.tower, alloc.floor, alloc.zone, alloc.grid, alloc.element].filter(Boolean).join(' • ') || 'Field Site'}</strong><br>
        Assigned Engineer: <strong>${alloc.engineer_name || alloc.engineer_id}</strong><br>
        Due Date: <span class="num">${formatDate(alloc.due_date)}</span> ${alloc.due_time ? html`at <span class="num">${alloc.due_time}</span>` : ''}
      </div>

      ${alloc.qc_return_comments ? html`
        <div class="alert-crit mt-md">
          <strong class="text-crit font-sm">QC Lead Return Comments:</strong>
          <div class="mt-xs font-sm">${alloc.qc_return_comments}</div>
        </div>
      ` : ''}
    </div>

    <!-- Checkpoints Section -->
    <div class="card mb-lg">
      <div class="card-header">
        <h4 class="card-title font-sm">Checkpoints (${checkpoints.length})</h4>
        <span class="muted font-xs">
          Pass: ${checkpoints.filter(c => c.result === 'OK').length} •
          NC: ${checkpoints.filter(c => c.result === 'NC').length} •
          NA: ${checkpoints.filter(c => c.result === 'NA').length}
        </span>
      </div>
      <div class="table-wrap">
        <table class="data-table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Description</th>
              <th>Result</th>
              <th>Remarks</th>
            </tr>
          </thead>
          <tbody>
            ${checkpoints.length === 0 ? html`
              <tr><td colspan="4" class="muted table-empty-cell">No checkpoints assigned.</td></tr>
            ` : checkpoints.map(c => html`
              <tr>
                <td class="num font-xs muted">${c.checkpoint_id}</td>
                <td>
                  <div>${c.checkpoint_description || c.description || c.checkpoint_id}</div>
                  ${c.stage_name ? html`<div class="muted font-xs">${c.stage_name} / ${c.subgroup_name}</div>` : ''}
                </td>
                <td>
                  ${c.result === 'OK' ? html`<span class="badge badge-mint font-xs">OK</span>` : ''}
                  ${c.result === 'NC' ? html`<span class="badge badge-crit font-xs">NC</span>` : ''}
                  ${c.result === 'NA' ? html`<span class="badge badge-neutral font-xs">NA</span>` : ''}
                  ${!c.result ? html`<span class="badge badge-neutral font-xs">Pending</span>` : ''}
                </td>
                <td class="font-xs">${c.remarks || c.observation || '—'}</td>
              </tr>
            `)}
          </tbody>
        </table>
      </div>
    </div>

    <!-- Evidence Photos -->
    <div class="card mb-lg">
      <div class="card-header">
        <h4 class="card-title font-sm">Photo Evidence (${photos.length})</h4>
      </div>
      <div class="card-body">
        ${photos.length === 0 ? html`
          <div class="muted font-xs text-center p-md">No evidence photos uploaded yet.</div>
        ` : html`
          <div class="photo-grid">
            ${photos.map(p => html`
              <div class="photo-thumb-wrap">
                <img
                  src="${p.photo_url || p.url || p}"
                  alt="Evidence for ${p.checkpoint_id || 'checkpoint'}"
                  class="photo-thumb"
                  loading="lazy"
                >
              </div>
            `)}
          </div>
        `}
      </div>
    </div>

    <!-- AI Quality Dossier Container -->
    <div class="card mb-lg">
      <div class="card-header">
        <h4 class="card-title font-sm">Quality Audit Dossier</h4>
        <button type="button" class="btn btn-secondary btn-sm" id="btnGenerateDossier">
          ⚡ Generate / Refresh AI Dossier
        </button>
      </div>
      <div class="card-body" id="dossierReportContainer">
        ${alloc.dossier_markdown || alloc.report_markdown ? html`
          <article class="dossier-article" id="renderedDossierArticle"></article>
        ` : html`
          <div class="muted font-xs text-center p-md">
            AI Dossier has not been generated yet. Click "Generate / Refresh AI Dossier" above.
          </div>
        `}
      </div>
    </div>

    <!-- Audit Event Log -->
    <div class="card">
      <div class="card-header">
        <h4 class="card-title font-sm">Audit Trail</h4>
      </div>
      <div class="table-wrap">
        <table class="data-table">
          <thead>
            <tr>
              <th>Timestamp</th>
              <th>Action</th>
              <th>Actor</th>
              <th>Notes</th>
            </tr>
          </thead>
          <tbody>
            ${auditLog.length === 0 ? html`
              <tr><td colspan="4" class="muted table-empty-cell">No audit events recorded.</td></tr>
            ` : auditLog.map(ev => html`
              <tr>
                <td class="num font-xs muted">${formatDateTime(ev.created_at || ev.timestamp)}</td>
                <td><strong>${ev.action || ev.event_type}</strong></td>
                <td class="font-xs">${ev.actor_name || ev.actor_id || 'System'}</td>
                <td class="font-xs">${ev.details || ev.note || '—'}</td>
              </tr>
            `)}
          </tbody>
        </table>
      </div>
    </div>
  `);

  // Render markdown if available
  if (alloc.dossier_markdown || alloc.report_markdown) {
    renderMarkdownDossier(alloc.dossier_markdown || alloc.report_markdown);
  }

  // Render Footer Actions
  render(footerEl, html`
    <button type="button" class="btn btn-secondary" id="btnDrawerClose">Close</button>
    <button type="button" class="btn btn-ghost" id="btnDrawerReassign">Reassign</button>

    ${isPendingReview ? html`
      <button type="button" class="btn btn-danger" id="btnDrawerReturn">Return for Reinspection</button>
      <button type="button" class="btn btn-primary" id="btnDrawerApprove">Approve Inspection</button>
    ` : ''}
  `);

  attachDrawerEvents(alloc);
}

function renderMarkdownDossier(markdownText) {
  const container = document.getElementById('renderedDossierArticle');
  if (!container || !markdownText) return;

  if (window.DOMPurify && window.marked) {
    const rawHtml = window.marked.parse(markdownText);
    const cleanHtml = window.DOMPurify.sanitize(rawHtml);
    render(container, raw(cleanHtml));
  } else {
    render(container, html`<pre class="pre-wrap">${markdownText}</pre>`);
  }
}

function attachDrawerEvents(alloc) {
  const closeBtn = document.getElementById('btnDrawerClose');
  if (closeBtn) closeBtn.addEventListener('click', closeInspectionDrawer);

  const genBtn = document.getElementById('btnGenerateDossier');
  if (genBtn) {
    genBtn.addEventListener('click', async () => {
      genBtn.disabled = true;
      genBtn.textContent = 'Generating AI Dossier...';
      try {
        const resp = await api.post(`/api/inspections/${alloc.allocation_id || alloc.id}/generate-report`, {});
        showToast('AI Quality Dossier generated successfully!', 'success');
        const reportMd = resp.report_markdown || resp.dossier || resp.report || 'Dossier generated.';
        alloc.dossier_markdown = reportMd;
        renderDrawerContent(alloc);
      } catch (err) {
        genBtn.disabled = false;
        genBtn.textContent = '⚡ Generate / Refresh AI Dossier';
      }
    });
  }

  const approveBtn = document.getElementById('btnDrawerApprove');
  if (approveBtn) {
    approveBtn.addEventListener('click', async () => {
      if (!confirm('Are you sure you want to approve this inspection and issue the quality report?')) return;
      approveBtn.disabled = true;
      approveBtn.textContent = 'Approving...';
      try {
        await api.post(`/api/allocations/${alloc.allocation_id || alloc.id}/review`, {
          decision: 'approve',
          comments: 'Approved by QC Lead.',
        });
        showToast('Inspection approved! Report issued.', 'success');
        closeInspectionDrawer();
        if (onActionCallback) onActionCallback();
      } catch (err) {
        approveBtn.disabled = false;
        approveBtn.textContent = 'Approve Inspection';
      }
    });
  }

  const returnBtn = document.getElementById('btnDrawerReturn');
  if (returnBtn) {
    returnBtn.addEventListener('click', () => {
      promptReturnInspection(alloc);
    });
  }

  const reassignBtn = document.getElementById('btnDrawerReassign');
  if (reassignBtn) {
    reassignBtn.addEventListener('click', () => {
      promptReassignInspection(alloc);
    });
  }
}

function promptReturnInspection(alloc) {
  const comments = window.prompt('Please enter the reason / required rework comments for returning this inspection:');
  if (comments === null) return;
  if (!comments.trim()) {
    showToast('Comments are strictly required to return an inspection.', 'error');
    return;
  }

  api.post(`/api/allocations/${alloc.allocation_id || alloc.id}/review`, {
    decision: 'return',
    comments: comments.trim(),
  }).then(() => {
    showToast('Inspection returned to field engineer for rework.', 'info');
    closeInspectionDrawer();
    if (onActionCallback) onActionCallback();
  }).catch(() => {});
}

function promptReassignInspection(alloc) {
  const reason = window.prompt('Please enter the reason for reassigning this inspection:');
  if (reason === null) return;
  if (!reason.trim()) {
    showToast('A reassign reason is strictly required.', 'error');
    return;
  }

  // Open Reassign Modal
  const modal = document.getElementById('reassignModal');
  const select = document.getElementById('reassignEngineerSelect');
  const allocIdSpan = document.getElementById('reassignAllocId');

  if (allocIdSpan) allocIdSpan.textContent = alloc.allocation_id || alloc.id;
  if (select) {
    render(select, html`
      ${currentEngineers.map(e => html`
        <option value="${e.id}" ${e.id === alloc.engineer_id ? 'selected' : ''}>
          ${e.name} (${e.specialty || e.role})
        </option>
      `)}
    `);
  }

  const submitReassign = async () => {
    const newEngId = select.value;
    try {
      await api.post(`/api/allocations/${alloc.allocation_id || alloc.id}/reassign`, {
        engineer_id: newEngId,
        reason: reason.trim(),
      });
      showToast('Inspection successfully reassigned.', 'success');
      closeModal('reassignModal');
      closeInspectionDrawer();
      if (onActionCallback) onActionCallback();
    } catch (err) {}
  };

  const confirmBtn = document.getElementById('confirmReassignBtn');
  if (confirmBtn) {
    confirmBtn.onclick = submitReassign;
  }

  openModal('reassignModal');
}
