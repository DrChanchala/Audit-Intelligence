/**
 * QC Lead Console — 3-Step Allocation Wizard Controller.
 * Step 1: Project, Engineer, Location hierarchy, Dates, Priority, Instructions.
 * Step 2: Checkpoint Selection via reusable Checklist Browser.
 * Step 3: Review, Confirm & Activate, or Save Draft.
 * Includes inline server validation error rendering.
 */
import { api } from '../shared/api.js';
import { html, render } from '../shared/html.js';
import { todayISO, formatDate } from '../shared/format.js';
import { showToast } from '../shared/ui.js';
import { createChecklistBrowser } from './checklist.js';

let projectsList = [];
let engineersList = [];
let checklistComponent = null;
let onAllocationSuccess = null;

let wizardData = {
  project_id: '',
  engineer_id: '',
  title: '',
  tower_block: '',
  floor_level: '',
  zone_area: '',
  grid_ref: '',
  element_id: '',
  planned_date: '',
  due_date: '',
  due_time: '18:00',
  priority: 'High',
  instructions: '',
  checkpoint_ids: [],
  allow_duplicate: false,
};

let currentStep = 1;

export async function initAllocateWizard(container, onSuccess) {
  onAllocationSuccess = onSuccess;
  currentStep = 1;
  wizardData.planned_date = todayISO();
  const d = new Date();
  d.setDate(d.getDate() + 2);
  wizardData.due_date = d.toISOString().split('T')[0];

  try {
    const [pResp, eResp] = await Promise.all([
      api.get('/api/projects'),
      api.get('/api/engineers'),
    ]);
    projectsList = Array.isArray(pResp) ? pResp : (pResp.projects || []);
    engineersList = eResp.engineers || [];
    renderWizard(container);
  } catch (err) {
    console.error('Failed to load projects/engineers for wizard:', err);
  }
}

function renderWizard(container) {
  render(container, html`
    <div class="card">
      <div class="card-header">
        <h2 class="card-title">Allocate Inspection & Checkpoints</h2>
        <span class="muted font-xs">Step ${currentStep} of 3</span>
      </div>
      <div class="card-body">
        <!-- Wizard Stepper Indicator -->
        <div class="wizard-stepper">
          <div class="wizard-step-node ${currentStep === 1 ? 'active' : ''} ${currentStep > 1 ? 'completed' : ''}">
            <div class="step-num">1</div>
            <span>Parameters & Location</span>
          </div>
          <div class="step-divider"></div>
          <div class="wizard-step-node ${currentStep === 2 ? 'active' : ''} ${currentStep > 2 ? 'completed' : ''}">
            <div class="step-num">2</div>
            <span>Checklist Selection</span>
          </div>
          <div class="step-divider"></div>
          <div class="wizard-step-node ${currentStep === 3 ? 'active' : ''}">
            <div class="step-num">3</div>
            <span>Review & Confirm</span>
          </div>
        </div>

        <!-- Inline Server Error Banner -->
        <div id="wizardServerError" class="d-none alert-crit mb-lg"></div>

        <!-- Step 1: Parameters -->
        <div id="step1Container" class="${currentStep !== 1 ? 'd-none' : ''}">
          <div class="form-row">
            <div class="form-group">
              <label class="form-label" for="wizProject">Target Project *</label>
              <select id="wizProject" class="form-select" required>
                <option value="">Select Project...</option>
                ${projectsList.map(p => html`
                  <option value="${p.id}" ${p.id === wizardData.project_id ? 'selected' : ''}>
                    ${p.name} (${p.code || p.id}) - ${p.status}
                  </option>
                `)}
              </select>
            </div>
            <div class="form-group">
              <label class="form-label" for="wizEngineer">Assign Inspection Engineer *</label>
              <select id="wizEngineer" class="form-select" required>
                <option value="">Select Engineer...</option>
                ${engineersList.map(e => html`
                  <option value="${e.id}" ${e.id === wizardData.engineer_id ? 'selected' : ''}>
                    ${e.name} (${e.specialty || e.role})
                  </option>
                `)}
              </select>
            </div>
          </div>

          <div class="form-group">
            <label class="form-label" for="wizTitle">Inspection Title / Scope</label>
            <input type="text" id="wizTitle" class="form-control" placeholder="e.g. Tower B Floor 4 Slab Reinforcement & Embeds" value="${wizardData.title}">
          </div>

          <div class="section-subheading">
            Work Area & Location Hierarchy
          </div>

          <div class="form-row">
            <div class="form-group">
              <label class="form-label" for="wizTower">Tower / Block *</label>
              <input type="text" id="wizTower" class="form-control" placeholder="e.g. Tower B" value="${wizardData.tower_block}">
            </div>
            <div class="form-group">
              <label class="form-label" for="wizFloor">Floor / Level *</label>
              <input type="text" id="wizFloor" class="form-control" placeholder="e.g. Level 4" value="${wizardData.floor_level}">
            </div>
          </div>

          <div class="form-row">
            <div class="form-group">
              <label class="form-label" for="wizZone">Zone / Area</label>
              <input type="text" id="wizZone" class="form-control" placeholder="e.g. Zone 2 / East Wing" value="${wizardData.zone_area}">
            </div>
            <div class="form-group">
              <label class="form-label" for="wizGrid">Grid Reference</label>
              <input type="text" id="wizGrid" class="form-control" placeholder="e.g. Grid C3-D5" value="${wizardData.grid_ref}">
            </div>
          </div>

          <div class="form-group">
            <label class="form-label" for="wizElement">Element / Component ID</label>
            <input type="text" id="wizElement" class="form-control" placeholder="e.g. SLAB-402, COL-B4" value="${wizardData.element_id}">
          </div>

          <div class="section-subheading">
            Schedule & Execution Parameters
          </div>

          <div class="form-row">
            <div class="form-group">
              <label class="form-label" for="wizPlannedDate">Planned Execution Date *</label>
              <input type="date" id="wizPlannedDate" class="form-control" value="${wizardData.planned_date}">
            </div>
            <div class="form-group">
              <label class="form-label" for="wizDueDate">Due Date *</label>
              <input type="date" id="wizDueDate" class="form-control" value="${wizardData.due_date}">
            </div>
          </div>

          <div class="form-row">
            <div class="form-group">
              <label class="form-label" for="wizDueTime">Due Time</label>
              <input type="time" id="wizDueTime" class="form-control" value="${wizardData.due_time}">
            </div>
            <div class="form-group">
              <label class="form-label" for="wizPriority">Audit Priority *</label>
              <select id="wizPriority" class="form-select">
                <option value="High" ${wizardData.priority === 'High' ? 'selected' : ''}>High Priority (Critical Milestones)</option>
                <option value="Medium" ${wizardData.priority === 'Medium' ? 'selected' : ''}>Medium Priority</option>
                <option value="Low" ${wizardData.priority === 'Low' ? 'selected' : ''}>Low Priority</option>
              </select>
            </div>
          </div>

          <div class="form-group">
            <label class="form-label" for="wizInstructions">Special Instructions / Engineer Notes</label>
            <textarea id="wizInstructions" class="form-textarea" placeholder="Specify mandatory holds, testing witness requirements, or tolerance checks...">${wizardData.instructions}</textarea>
          </div>

          <div class="flex-end mt-xl">
            <button type="button" class="btn btn-primary" id="btnStep1Next">
              Next: Select Checkpoints →
            </button>
          </div>
        </div>

        <!-- Step 2: Checkpoint Selection -->
        <div id="step2Container" class="${currentStep !== 2 ? 'd-none' : ''}">
          <div class="mb-md">
            <p class="muted font-sm">
              Filter the master checklist and tick the checkpoints required for this field inspection.
            </p>
          </div>

          <div id="checklistBrowserMount"></div>

          <div class="flex-between mt-xl">
            <button type="button" class="btn btn-secondary" id="btnStep2Back">
              ← Back: Parameters
            </button>
            <button type="button" class="btn btn-primary" id="btnStep2Next">
              Next: Review & Confirm →
            </button>
          </div>
        </div>

        <!-- Step 3: Review & Confirm -->
        <div id="step3Container" class="${currentStep !== 3 ? 'd-none' : ''}">
          <div class="mb-xl">
            <h3 class="card-title-sub mb-md">Review Inspection Parameters</h3>
            <div class="card p-md mb-lg">
              <div class="review-grid">
                <div>
                  <span class="muted">Project:</span>
                  <strong id="revProject">—</strong>
                </div>
                <div>
                  <span class="muted">Engineer:</span>
                  <strong id="revEngineer">—</strong>
                </div>
                <div>
                  <span class="muted">Location:</span>
                  <strong id="revLocation">—</strong>
                </div>
                <div>
                  <span class="muted">Priority:</span>
                  <span id="revPriority">—</span>
                </div>
                <div>
                  <span class="muted">Planned / Due:</span>
                  <strong id="revDates" class="num">—</strong>
                </div>
                <div>
                  <span class="muted">Checkpoints:</span>
                  <strong id="revCount" class="text-mint font-sm">—</strong>
                </div>
              </div>
            </div>

            <div class="form-group mt-lg">
              <label class="flex-row-gap cursor-pointer font-sm">
                <input type="checkbox" id="wizAllowDuplicate" ${wizardData.allow_duplicate ? 'checked' : ''}>
                <span>Allow duplicate allocation in same location if overlapping</span>
              </label>
            </div>
          </div>

          <div class="flex-between mt-xl">
            <button type="button" class="btn btn-secondary" id="btnStep3Back">
              ← Back: Checkpoints
            </button>
            <div class="flex-gap">
              <button type="button" class="btn btn-secondary" id="btnSaveDraft">
                Save as Draft
              </button>
              <button type="button" class="btn btn-primary" id="btnConfirmAllocate">
                Confirm & Allocate Now
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  `);

  attachStepEvents(container);
}

function showServerError(container, message) {
  const errBox = container.querySelector('#wizardServerError');
  if (errBox) {
    errBox.textContent = message;
    errBox.classList.remove('d-none');
    errBox.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }
}

function hideServerError(container) {
  const errBox = container.querySelector('#wizardServerError');
  if (errBox) {
    errBox.textContent = '';
    errBox.classList.add('d-none');
  }
}

function attachStepEvents(container) {
  // Step 1 Next
  const btnStep1Next = container.querySelector('#btnStep1Next');
  if (btnStep1Next) {
    btnStep1Next.addEventListener('click', () => {
      hideServerError(container);
      wizardData.project_id = container.querySelector('#wizProject').value;
      wizardData.engineer_id = container.querySelector('#wizEngineer').value;
      wizardData.title = container.querySelector('#wizTitle').value.trim();
      wizardData.tower_block = container.querySelector('#wizTower').value.trim();
      wizardData.floor_level = container.querySelector('#wizFloor').value.trim();
      wizardData.zone_area = container.querySelector('#wizZone').value.trim();
      wizardData.grid_ref = container.querySelector('#wizGrid').value.trim();
      wizardData.element_id = container.querySelector('#wizElement').value.trim();
      wizardData.planned_date = container.querySelector('#wizPlannedDate').value;
      wizardData.due_date = container.querySelector('#wizDueDate').value;
      wizardData.due_time = container.querySelector('#wizDueTime').value || '18:00';
      wizardData.priority = container.querySelector('#wizPriority').value;
      wizardData.instructions = container.querySelector('#wizInstructions').value.trim();

      if (!wizardData.project_id) {
        showServerError(container, 'Please select a target project.');
        return;
      }
      if (!wizardData.engineer_id) {
        showServerError(container, 'Please assign an inspection engineer.');
        return;
      }
      if (!wizardData.tower_block || !wizardData.floor_level) {
        showServerError(container, 'Tower / Block and Floor / Level are mandatory.');
        return;
      }
      if (wizardData.due_date && wizardData.planned_date && wizardData.due_date < wizardData.planned_date) {
        showServerError(container, 'Due date cannot be before planned execution date.');
        return;
      }

      currentStep = 2;
      renderWizard(container);

      // Mount checklist browser on step 2
      const mount = container.querySelector('#checklistBrowserMount');
      if (mount) {
        checklistComponent = createChecklistBrowser(mount, {
          selectable: true,
          selectedIds: wizardData.checkpoint_ids,
          onSelectionChange: (selectedIds) => {
            wizardData.checkpoint_ids = selectedIds;
          },
        });
      }
    });
  }

  // Step 2 Back & Next
  const btnStep2Back = container.querySelector('#btnStep2Back');
  if (btnStep2Back) {
    btnStep2Back.addEventListener('click', () => {
      currentStep = 1;
      renderWizard(container);
    });
  }

  const btnStep2Next = container.querySelector('#btnStep2Next');
  if (btnStep2Next) {
    btnStep2Next.addEventListener('click', () => {
      hideServerError(container);
      if (checklistComponent) {
        wizardData.checkpoint_ids = checklistComponent.getSelected();
      }
      if (wizardData.checkpoint_ids.length === 0) {
        showServerError(container, 'Please select at least 1 checkpoint to allocate.');
        return;
      }

      currentStep = 3;
      renderWizard(container);

      // Populate review values
      const p = projectsList.find(x => x.id === wizardData.project_id);
      const e = engineersList.find(x => x.id === wizardData.engineer_id);
      const revP = container.querySelector('#revProject');
      const revE = container.querySelector('#revEngineer');
      const revL = container.querySelector('#revLocation');
      const revPr = container.querySelector('#revPriority');
      const revD = container.querySelector('#revDates');
      const revC = container.querySelector('#revCount');

      if (revP) revP.textContent = p ? p.name : wizardData.project_id;
      if (revE) revE.textContent = e ? `${e.name} (${e.specialty || e.role})` : wizardData.engineer_id;
      if (revL) revL.textContent = [wizardData.tower_block, wizardData.floor_level, wizardData.zone_area, wizardData.grid_ref, wizardData.element_id].filter(Boolean).join(' • ');
      if (revPr) revPr.textContent = wizardData.priority;
      if (revD) revD.textContent = `${formatDate(wizardData.planned_date)} → ${formatDate(wizardData.due_date)}`;
      if (revC) revC.textContent = `${wizardData.checkpoint_ids.length} checkpoints`;
    });
  }

  // Step 3 Back
  const btnStep3Back = container.querySelector('#btnStep3Back');
  if (btnStep3Back) {
    btnStep3Back.addEventListener('click', () => {
      currentStep = 2;
      renderWizard(container);
      const mount = container.querySelector('#checklistBrowserMount');
      if (mount) {
        checklistComponent = createChecklistBrowser(mount, {
          selectable: true,
          selectedIds: wizardData.checkpoint_ids,
          onSelectionChange: (selectedIds) => {
            wizardData.checkpoint_ids = selectedIds;
          },
        });
      }
    });
  }

  // Step 3 Confirm Allocation
  const btnConfirmAllocate = container.querySelector('#btnConfirmAllocate');
  if (btnConfirmAllocate) {
    btnConfirmAllocate.addEventListener('click', () => submitAllocation(container, 'Allocated'));
  }

  // Step 3 Save Draft
  const btnSaveDraft = container.querySelector('#btnSaveDraft');
  if (btnSaveDraft) {
    btnSaveDraft.addEventListener('click', () => submitAllocation(container, 'Draft'));
  }
}

async function submitAllocation(container, statusMode) {
  hideServerError(container);
  const allowDupCb = container.querySelector('#wizAllowDuplicate');
  const allow_duplicate = allowDupCb ? allowDupCb.checked : false;

  const payload = {
    project_id: wizardData.project_id,
    engineer_id: wizardData.engineer_id,
    title: wizardData.title || undefined,
    tower_block: wizardData.tower_block,
    floor_level: wizardData.floor_level,
    zone_area: wizardData.zone_area,
    grid_ref: wizardData.grid_ref,
    element_id: wizardData.element_id,
    planned_date: wizardData.planned_date,
    due_date: wizardData.due_date,
    due_time: wizardData.due_time,
    priority: wizardData.priority,
    instructions: wizardData.instructions,
    checkpoint_ids: wizardData.checkpoint_ids,
    allow_duplicate,
    status: statusMode,
  };

  const btnConfirm = container.querySelector('#btnConfirmAllocate');
  const btnDraft = container.querySelector('#btnSaveDraft');
  if (btnConfirm) btnConfirm.disabled = true;
  if (btnDraft) btnDraft.disabled = true;

  try {
    const resp = await api.post('/api/allocations', payload);
    const allocId = resp.allocation_id || resp.id || 'ALC';
    showToast(`Inspection ${allocId} successfully ${statusMode === 'Draft' ? 'saved as Draft' : 'allocated'}!`, 'success');
    if (onAllocationSuccess) onAllocationSuccess(allocId);
  } catch (err) {
    // Show server validation errors inline
    showServerError(container, err.message || 'Allocation rejected by server.');
  } finally {
    if (btnConfirm) btnConfirm.disabled = false;
    if (btnDraft) btnDraft.disabled = false;
  }
}
