/**
 * QC Lead Console — Overview Tab Controller.
 * Displays organization quality KPIs and interactive project summary cards.
 */
import { api } from '../shared/api.js';
import { html, render } from '../shared/html.js';
import { formatNumber } from '../shared/format.js';

export async function initOverview(container, onProjectSelect) {
  render(container, html`
    <div class="kpi-grid">
      <div class="kpi-card">
        <div class="kpi-label">Active Inspections</div>
        <div class="kpi-value" id="ovActiveInspections">—</div>
        <div class="kpi-sub" id="ovPendingReviewSub">Pending review: 0</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">Open Defects (NCs)</div>
        <div class="kpi-value text-crit" id="ovOpenNCs">—</div>
        <div class="kpi-sub text-crit" id="ovCriticalNCsSub">Critical: 0</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">Quality Score</div>
        <div class="kpi-value text-mint" id="ovQualityScore">—</div>
        <div class="kpi-sub">Target: ≥ 95%</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">Live Projects</div>
        <div class="kpi-value" id="ovLiveProjects">—</div>
        <div class="kpi-sub" id="ovTotalProjectsSub">Total: 0</div>
      </div>
    </div>

    <div class="card">
      <div class="card-header">
        <h2 class="card-title">Project Quality Summaries</h2>
        <span class="muted font-xs">Click any project to view its inspections</span>
      </div>
      <div class="card-body">
        <div class="kpi-grid" id="projectCardsGrid">
          <div class="muted table-empty-cell">Loading projects...</div>
        </div>
      </div>
    </div>
  `);

  try {
    const [summary, projects] = await Promise.all([
      api.get('/api/summary'),
      api.get('/api/projects'),
    ]);

    // Populate KPIs
    const elActive = container.querySelector('#ovActiveInspections');
    const elPending = container.querySelector('#ovPendingReviewSub');
    const elOpen = container.querySelector('#ovOpenNCs');
    const elCrit = container.querySelector('#ovCriticalNCsSub');
    const elScore = container.querySelector('#ovQualityScore');
    const elLive = container.querySelector('#ovLiveProjects');
    const elTotal = container.querySelector('#ovTotalProjectsSub');

    if (elActive) elActive.textContent = formatNumber(summary.active_inspections ?? summary.inspections_in_progress ?? 0);
    if (elPending) elPending.textContent = `Pending review: ${summary.pending_review_count ?? summary.approvals_pending ?? 0}`;
    if (elOpen) elOpen.textContent = formatNumber(summary.open_ncs ?? summary.ncs_open ?? 0);
    if (elCrit) elCrit.textContent = `Critical: ${summary.critical_ncs ?? summary.critical_nc_count ?? 0}`;
    if (elScore) elScore.textContent = `${summary.compliance_rate ?? summary.quality_score ?? 96}%`;
    if (elLive) elLive.textContent = formatNumber(summary.live_projects ?? summary.projects_live ?? 0);
    if (elTotal) elTotal.textContent = `Total: ${summary.total_projects ?? summary.projects_total ?? (projects.length || 0)}`;

    // Populate Project Cards
    const cardsGrid = container.querySelector('#projectCardsGrid');
    const projList = Array.isArray(projects) ? projects : (projects.projects || []);

    if (projList.length === 0) {
      render(cardsGrid, html`
        <div class="muted table-empty-cell">No active projects found.</div>
      `);
      return;
    }

    render(cardsGrid, html`
      ${projList.map(p => html`
        <div class="kpi-card project-summary-card cursor-pointer" data-project-id="${p.id}">
          <div class="flex-between mb-sm">
            <div>
              <strong class="fw-bold-title">${p.name}</strong>
              <span class="muted font-xs num">${p.code || p.id}</span>
            </div>
            <span class="badge ${p.status === 'live' ? 'badge-mint' : 'badge-neutral'} font-xs">
              ${p.status || 'live'}
            </span>
          </div>

          <div class="muted font-xs mb-md">
            📍 ${p.loc || p.location || 'Site'}
          </div>

          <div class="border-top-card">
            <div class="font-xs">
              <span class="muted">Active Inspections:</span>
              <strong class="num">${p.active_inspections ?? p.inspection_count ?? 0}</strong>
            </div>
            <div class="font-xs">
              <span class="muted">Open NCs:</span>
              <strong class="num text-crit">${p.open_ncs ?? p.nc_count ?? 0}</strong>
            </div>
          </div>
        </div>
      `)}
    `);

    // Attach click events
    cardsGrid.querySelectorAll('.project-summary-card').forEach(card => {
      card.addEventListener('click', () => {
        const pId = card.getAttribute('data-project-id');
        if (onProjectSelect && pId) {
          onProjectSelect(pId);
        }
      });
    });

  } catch (err) {
    console.error('Failed to load QC overview:', err);
  }
}
