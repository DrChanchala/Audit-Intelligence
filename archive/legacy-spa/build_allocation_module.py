# Build unified allocation_module.js for SiteIQ
import os

top_code = '''/**
 * SiteIQ / Audit Intelligence — Unified Inspection Creation & Change Engineer Module
 * Full implementation of 4-step Create Inspection wizard, Change Engineer engine,
 * and Inspection Engineer Workspace synchronization.
 */

// Master Checklist cache
let MASTER_STAGES = [];
let ALLOCATIONS_CACHE = {};

// Authoritative Inspection Engineer Directory with Stable Identifiers
const ENGINEER_ROSTER = [
  { id: 'EMP-1004', name: 'Anjali Rao', role: 'QC Inspection Engineer', spec: 'Finishes & Waterproofing' },
  { id: 'EMP-1002', name: 'Rohit Kale', role: 'Senior QC Engineer', spec: 'RCC & Structural' },
  { id: 'EMP-1003', name: 'Vikram Singh', role: 'QC Inspection Engineer', spec: 'Steel & Telecom' },
  { id: 'EMP-1005', name: 'Meera Iyer', role: 'Senior Façade & MEP Engineer', spec: 'Façade & MEP' },
  { id: 'EMP-1006', name: 'Arjun Mehta', role: 'QC Inspection Engineer', spec: 'Industrial & PEB' }
];

// ============================================================================
// UNIFIED CREATE INSPECTION WORKFLOW (4 STEPS)
// ============================================================================

const CREATE_INSP_WIZARD = {
  step: 1, // 1: Details & Location, 2: Select Checklist, 3: Assign Engineer, 4: Review & Confirm
  projectId: 'psv',
  inspectionId: '',
  title: 'RCC Structural & Quality Inspection',
  activityType: 'RCC Structural Works',
  inspectionType: 'Stage Quality Inspection',
  location: {
    tower: 'Tower 3',
    floor: 'Floor 8',
    zone: 'Zone B · Sunken Slab',
    grid: 'Grids B4–B8',
    element: 'Column C7 / Beam B12',
    instructions: 'Verify rebar lap length, cover blocks, and formwork alignment.'
  },
  plannedDate: '2026-11-04',
  dueDate: '2026-11-07',
  dueTime: '18:00',
  priority: 'High',
  selectedCheckpoints: new Set(['CHK-01-01-001', 'CHK-01-01-002']),
  expandedStages: new Set(['STG-01', 'STG-02', 'STG-03']),
  expandedSubgroups: new Set(['SUB-01-01', 'SUB-02-01', 'SUB-03-01']),
  searchQuery: '',
  priorityFilter: 'all',
  buildingTypeFilter: 'all',
  engineerId: 'EMP-1004',
  engineer: 'Anjali Rao',
  isSubmitting: false,
  isDraft: false
};

// Aliases for backward compatibility
const ALLOC_WIZARD = CREATE_INSP_WIZARD;

// ----------------- DATA LOADING -----------------

async function loadMasterChecklist() {
  try {
    const res = await fetch('/api/master-checklist');
    const data = await res.json();
    if (data.status === 'success' && data.stages) {
      MASTER_STAGES = data.stages;
      console.log(`Loaded ${MASTER_STAGES.length} master stages into client memory.`);
    }
  } catch (err) {
    console.warn("Could not load master checklist from API, retrying:", err);
  }
}

if (typeof window !== 'undefined') {
  loadMasterChecklist();
  window.addEventListener('DOMContentLoaded', loadMasterChecklist);
}

// ----------------- WIZARD NAVIGATION & OPENING -----------------

async function openCreateInspectionWizard(projectId, existingCode = null) {
  const pid = projectId || (typeof S !== 'undefined' && S.ctx) || 'psv';
  CREATE_INSP_WIZARD.projectId = pid;
  CREATE_INSP_WIZARD.step = 1;
  CREATE_INSP_WIZARD.isSubmitting = false;
  CREATE_INSP_WIZARD.isDraft = false;

  const p = typeof byId === 'function' ? byId(pid) : null;
  if (p) {
    if (p.status === 'hold') {
      if (typeof toast === 'function') toast(`Project ${p.name} is on HOLD. Cannot create new inspections.`);
      return;
    }
    if (p.status === 'completed') {
      if (typeof toast === 'function') toast(`Project ${p.name} is COMPLETED. Inspection creation disabled.`);
      return;
    }
  }

  // Pre-load next unique sequential ID from backend
  try {
    const idRes = await fetch(`/api/inspections/next-id?project_id=${pid}`);
    if (idRes.ok) {
      const idData = await idRes.json();
      if (idData.next_id) {
        CREATE_INSP_WIZARD.inspectionId = idData.next_id;
      }
    }
  } catch (e) {
    CREATE_INSP_WIZARD.inspectionId = `INS-0012-${String(Math.floor(Math.random()*900)+100).padStart(4,'0')}`;
  }

  // If opening an existing draft
  if (existingCode) {
    CREATE_INSP_WIZARD.inspectionId = existingCode;
    const existing = ALLOCATIONS_CACHE[existingCode];
    if (existing) {
      if (existing.title) CREATE_INSP_WIZARD.title = existing.title;
      if (existing.priority) CREATE_INSP_WIZARD.priority = existing.priority;
      if (existing.planned_date) CREATE_INSP_WIZARD.plannedDate = existing.planned_date;
      if (existing.due_date) CREATE_INSP_WIZARD.dueDate = existing.due_date;
      if (existing.engineer_id) {
        CREATE_INSP_WIZARD.engineerId = existing.engineer_id;
        CREATE_INSP_WIZARD.engineer = existing.engineer_name;
      }
      if (existing.checkpoints) {
        CREATE_INSP_WIZARD.selectedCheckpoints = new Set(existing.checkpoints.map(c => c.checkpoint_id));
      }
    }
  } else {
    if (CREATE_INSP_WIZARD.selectedCheckpoints.size === 0) {
      CREATE_INSP_WIZARD.selectedCheckpoints.add('CHK-01-01-001');
      CREATE_INSP_WIZARD.selectedCheckpoints.add('CHK-01-01-002');
    }
  }

  if (!MASTER_STAGES.length) {
    await loadMasterChecklist();
  }

  if (typeof openSheet === 'function') {
    openSheet('createInspection');
  }
}

// Obsolete alias redirecting directly to unified Create Inspection
function openAllocateWizard(projectId) {
  openCreateInspectionWizard(projectId);
}

function setCreateStep(step) {
  if (step === 2) {
    readStep1FormValues();
  }
  if (step > 2 && CREATE_INSP_WIZARD.selectedCheckpoints.size === 0) {
    if (typeof toast === 'function') toast("Please select at least one inspection checkpoint.");
    return;
  }
  if (step === 4 && (!CREATE_INSP_WIZARD.engineerId || CREATE_INSP_WIZARD.engineerId === 'Unassigned')) {
    if (typeof toast === 'function') toast("Please select an Inspection Engineer before confirmation.");
    return;
  }
  CREATE_INSP_WIZARD.step = step;
  if (typeof drawSheet === 'function') drawSheet();
}

// ----------------- CHECKLIST SELECTION HANDLERS -----------------

function toggleStageExpand(stageId) {
  if (CREATE_INSP_WIZARD.expandedStages.has(stageId)) {
    CREATE_INSP_WIZARD.expandedStages.delete(stageId);
  } else {
    CREATE_INSP_WIZARD.expandedStages.add(stageId);
  }
  if (typeof drawSheet === 'function') drawSheet();
}

function toggleSubgroupExpand(subgroupId) {
  if (CREATE_INSP_WIZARD.expandedSubgroups.has(subgroupId)) {
    CREATE_INSP_WIZARD.expandedSubgroups.delete(subgroupId);
  } else {
    CREATE_INSP_WIZARD.expandedSubgroups.add(subgroupId);
  }
  if (typeof drawSheet === 'function') drawSheet();
}

function toggleCheckpointSelect(chkId) {
  if (CREATE_INSP_WIZARD.selectedCheckpoints.has(chkId)) {
    CREATE_INSP_WIZARD.selectedCheckpoints.delete(chkId);
  } else {
    CREATE_INSP_WIZARD.selectedCheckpoints.add(chkId);
  }
  if (typeof drawSheet === 'function') drawSheet();
}

function selectAllInSubgroup(subgroupId, select = true) {
  for (const stg of MASTER_STAGES) {
    for (const sub of (stg.subgroups || [])) {
      if (sub.subgroup_id === subgroupId) {
        for (const chk of (sub.checkpoints || [])) {
          if (select) CREATE_INSP_WIZARD.selectedCheckpoints.add(chk.checkpoint_id);
          else CREATE_INSP_WIZARD.selectedCheckpoints.delete(chk.checkpoint_id);
        }
      }
    }
  }
  if (typeof drawSheet === 'function') drawSheet();
}

function selectAllInStage(stageId, select = true) {
  for (const stg of MASTER_STAGES) {
    if (stg.stage_id === stageId) {
      for (const sub of (stg.subgroups || [])) {
        for (const chk of (sub.checkpoints || [])) {
          if (select) CREATE_INSP_WIZARD.selectedCheckpoints.add(chk.checkpoint_id);
          else CREATE_INSP_WIZARD.selectedCheckpoints.delete(chk.checkpoint_id);
        }
      }
    }
  }
  if (typeof drawSheet === 'function') drawSheet();
}

function clearAllSelectedCheckpoints() {
  CREATE_INSP_WIZARD.selectedCheckpoints.clear();
  if (typeof drawSheet === 'function') drawSheet();
}

function readStep1FormValues() {
  const getVal = id => {
    const el = document.getElementById(id);
    return el ? el.value.trim() : '';
  };

  const t = getVal('ci_title');
  if (t) CREATE_INSP_WIZARD.title = t;

  const act = getVal('ci_activity');
  if (act) CREATE_INSP_WIZARD.activityType = act;

  const itype = getVal('ci_type');
  if (itype) CREATE_INSP_WIZARD.inspectionType = itype;

  const tower = getVal('ci_tower');
  const floor = getVal('ci_floor');
  const zone = getVal('ci_zone');
  const grid = getVal('ci_grid');
  const element = getVal('ci_element');
  const instr = getVal('ci_instructions');

  if (tower) CREATE_INSP_WIZARD.location.tower = tower;
  if (floor) CREATE_INSP_WIZARD.location.floor = floor;
  if (zone) CREATE_INSP_WIZARD.location.zone = zone;
  if (grid) CREATE_INSP_WIZARD.location.grid = grid;
  if (element) CREATE_INSP_WIZARD.location.element = element;
  if (instr) CREATE_INSP_WIZARD.location.instructions = instr;

  const pd = getVal('ci_pdate');
  if (pd) CREATE_INSP_WIZARD.plannedDate = pd;

  const dd = getVal('ci_ddate');
  if (dd) CREATE_INSP_WIZARD.dueDate = dd;

  const pri = getVal('ci_priority');
  if (pri) CREATE_INSP_WIZARD.priority = pri;
}

// ----------------- SUBMISSION & DRAFT SAVING -----------------

async function saveInspectionAsDraft() {
  if (CREATE_INSP_WIZARD.isSubmitting) return;
  CREATE_INSP_WIZARD.isSubmitting = true;

  readStep1FormValues();

  const payload = {
    project_id: CREATE_INSP_WIZARD.projectId,
    inspection_id: CREATE_INSP_WIZARD.inspectionId,
    title: CREATE_INSP_WIZARD.title || 'Quality Inspection Draft',
    activity_type: CREATE_INSP_WIZARD.activityType,
    inspection_type: CREATE_INSP_WIZARD.inspectionType,
    tower_block: CREATE_INSP_WIZARD.location.tower,
    floor_level: CREATE_INSP_WIZARD.location.floor,
    zone_area: CREATE_INSP_WIZARD.location.zone,
    grid_ref: CREATE_INSP_WIZARD.location.grid,
    element_id: CREATE_INSP_WIZARD.location.element,
    instructions: CREATE_INSP_WIZARD.location.instructions,
    planned_date: CREATE_INSP_WIZARD.plannedDate,
    due_date: CREATE_INSP_WIZARD.dueDate,
    priority: CREATE_INSP_WIZARD.priority,
    engineer_id: CREATE_INSP_WIZARD.engineerId || null,
    engineer_name: CREATE_INSP_WIZARD.engineer || 'Unassigned',
    checkpoint_ids: Array.from(CREATE_INSP_WIZARD.selectedCheckpoints),
    status: 'Draft',
    allow_duplicate: true
  };

  try {
    const res = await fetch('/api/inspections/create', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    CREATE_INSP_WIZARD.isSubmitting = false;

    if (!res.ok) {
      if (typeof toast === 'function') toast(data.detail || "Error saving draft.");
      return;
    }

    if (typeof toast === 'function') {
      toast(`✓ Inspection ${payload.inspection_id} saved as Draft.`);
    }

    if (typeof syncFromBackend === 'function') {
      await syncFromBackend();
    }
    if (typeof closeSheet === 'function') closeSheet();
    if (typeof render === 'function') render(false);

  } catch (err) {
    CREATE_INSP_WIZARD.isSubmitting = false;
    console.error("Save draft error:", err);
    if (typeof toast === 'function') toast("Network error saving draft.");
  }
}

async function submitCreateInspection() {
  if (CREATE_INSP_WIZARD.isSubmitting) return;

  readStep1FormValues();

  if (CREATE_INSP_WIZARD.selectedCheckpoints.size === 0) {
    if (typeof toast === 'function') toast("Please select at least one inspection checkpoint.");
    return;
  }
  if (!CREATE_INSP_WIZARD.engineerId || CREATE_INSP_WIZARD.engineerId === 'Unassigned') {
    if (typeof toast === 'function') toast("Please assign an Inspection Engineer before activation.");
    return;
  }

  CREATE_INSP_WIZARD.isSubmitting = true;
  const btn = document.getElementById('ci_confirm_btn');
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = `<span class="spinner"></span> Creating & Allocating...`;
  }

  const payload = {
    project_id: CREATE_INSP_WIZARD.projectId,
    inspection_id: CREATE_INSP_WIZARD.inspectionId,
    title: CREATE_INSP_WIZARD.title || 'Quality Inspection',
    activity_type: CREATE_INSP_WIZARD.activityType,
    inspection_type: CREATE_INSP_WIZARD.inspectionType,
    tower_block: CREATE_INSP_WIZARD.location.tower,
    floor_level: CREATE_INSP_WIZARD.location.floor,
    zone_area: CREATE_INSP_WIZARD.location.zone,
    grid_ref: CREATE_INSP_WIZARD.location.grid,
    element_id: CREATE_INSP_WIZARD.location.element,
    instructions: CREATE_INSP_WIZARD.location.instructions,
    planned_date: CREATE_INSP_WIZARD.plannedDate,
    due_date: CREATE_INSP_WIZARD.dueDate,
    priority: CREATE_INSP_WIZARD.priority,
    engineer_id: CREATE_INSP_WIZARD.engineerId,
    engineer_name: CREATE_INSP_WIZARD.engineer,
    checkpoint_ids: Array.from(CREATE_INSP_WIZARD.selectedCheckpoints),
    status: 'Allocated',
    allow_duplicate: true
  };

  try {
    const res = await fetch('/api/inspections/create', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    CREATE_INSP_WIZARD.isSubmitting = false;

    if (!res.ok) {
      if (btn) {
        btn.disabled = false;
        btn.innerHTML = `✓ Confirm & Create Inspection`;
      }
      if (typeof toast === 'function') toast(data.detail || "Error creating inspection.");
      return;
    }

    const alloc = data.allocation;
    const allocId = alloc.allocation_id || payload.inspection_id;

    if (typeof toast === 'function') {
      toast(`✓ Inspection ${allocId} successfully created and assigned to ${alloc.engineer_name}!`);
    }

    if (typeof syncFromBackend === 'function') {
      await syncFromBackend();
    }
    if (typeof closeSheet === 'function') closeSheet();

    if (typeof S !== 'undefined') {
      S.ctx = CREATE_INSP_WIZARD.projectId;
      S.pIns = 'Create';
      S.stack = [{ v: 'project', id: CREATE_INSP_WIZARD.projectId, tab: 'inspections' }];
      if (typeof render === 'function') render(false);
    }

  } catch (err) {
    CREATE_INSP_WIZARD.isSubmitting = false;
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = `✓ Confirm & Create Inspection`;
    }
    console.error("Create inspection error:", err);
    if (typeof toast === 'function') toast("Network error creating inspection.");
  }
}

// ----------------- RENDER 4-STEP WIZARD DRAWER -----------------

function renderCreateInspectionSheet() {
  const step = CREATE_INSP_WIZARD.step;
  const p = typeof byId === 'function' ? byId(CREATE_INSP_WIZARD.projectId) : { name: 'Purvanchal Skyline Vista', code: 'PRJ-0012' };

  const stepLabels = ['1. Details', '2. Checklist', '3. Engineer', '4. Confirm'];
  const stepIndicatorHtml = `
    <div style="display:flex; justify-content:space-between; margin-bottom:16px; border-bottom:1px solid var(--line); padding-bottom:10px">
      ${stepLabels.map((l, i) => {
        const sNum = i + 1;
        const isActive = sNum === step;
        const isDone = sNum < step;
        return `
          <button type="button" onclick="setCreateStep(${sNum})" style="border:none; background:none; cursor:pointer; display:flex; align-items:center; gap:5px; font-size:12px; font-weight:${isActive ? '800' : '600'}; color:${isActive ? 'var(--mint)' : isDone ? 'var(--mint-ink)' : 'var(--ink-3)'}">
            <span style="width:20px; height:20px; border-radius:50%; display:grid; place-items:center; font-size:11px; font-weight:800; ${isActive ? 'background:var(--mint); color:var(--on-mint)' : isDone ? 'background:var(--mint-soft); color:var(--mint-ink)' : 'background:var(--surface-2); color:var(--ink-3)'}">
              ${isDone ? '✓' : sNum}
            </span>
            <span>${l}</span>
          </button>
        `;
      }).join('')}
    </div>
  `;

  let bodyHtml = '';
  let footerHtml = '';

  if (step === 1) {
    bodyHtml = renderCreateStep1(p);
    footerHtml = `
      <div style="display:flex; justify-content:space-between; gap:10px; width:100%">
        <button class="btn ghost" type="button" onclick="saveInspectionAsDraft()" style="flex:1; font-weight:700">
          💾 Save as Draft
        </button>
        <button class="btn primary" type="button" onclick="setCreateStep(2)" style="flex:1.2; font-weight:700; background:var(--mint); color:var(--on-mint)">
          Next: Select Checklist →
        </button>
      </div>
    `;
  } else if (step === 2) {
    bodyHtml = renderCreateStep2(p);
    footerHtml = `
      <div style="display:flex; justify-content:space-between; gap:8px; width:100%">
        <button class="btn ghost" type="button" onclick="setCreateStep(1)" style="flex:0 0 auto">
          ← Back
        </button>
        <button class="btn ghost" type="button" onclick="saveInspectionAsDraft()" style="flex:1; font-weight:700">
          💾 Save Draft
        </button>
        <button class="btn primary" type="button" onclick="setCreateStep(3)" style="flex:1.2; font-weight:700; background:var(--mint); color:var(--on-mint)">
          Next: Assign Engineer →
        </button>
      </div>
    `;
  } else if (step === 3) {
    bodyHtml = renderCreateStep3(p);
    footerHtml = `
      <div style="display:flex; justify-content:space-between; gap:8px; width:100%">
        <button class="btn ghost" type="button" onclick="setCreateStep(2)" style="flex:0 0 auto">
          ← Back
        </button>
        <button class="btn ghost" type="button" onclick="saveInspectionAsDraft()" style="flex:1; font-weight:700">
          💾 Save Draft
        </button>
        <button class="btn primary" type="button" onclick="setCreateStep(4)" style="flex:1.2; font-weight:700; background:var(--mint); color:var(--on-mint)">
          Next: Review & Confirm →
        </button>
      </div>
    `;
  } else {
    bodyHtml = renderCreateStep4(p);
    footerHtml = `
      <div style="display:flex; justify-content:space-between; gap:8px; width:100%">
        <button class="btn ghost" type="button" onclick="setCreateStep(3)" style="flex:0 0 auto">
          ← Back
        </button>
        <button class="btn ghost" type="button" onclick="saveInspectionAsDraft()" style="flex:1; font-weight:700">
          💾 Save Draft
        </button>
        <button id="ci_confirm_btn" class="btn primary" type="button" onclick="submitCreateInspection()" style="flex:1.5; font-weight:800; background:linear-gradient(135deg, var(--mint), #38BDF8); color:#0B2A21">
          ✓ Confirm & Create Inspection
        </button>
      </div>
    `;
  }

  if (typeof setSheet === 'function') {
    setSheet(
      p.name || 'Quality Inspection',
      `+ Create Inspection · ${CREATE_INSP_WIZARD.inspectionId || 'New'}`,
      `${stepIndicatorHtml}${bodyHtml}`,
      footerHtml
    );
  }
}

// ----------------- STEP 1: CREATE INSPECTION DETAILS -----------------

function renderCreateStep1(p) {
  const w = CREATE_INSP_WIZARD;
  const projectsList = typeof P !== 'undefined' ? P : [];

  return `
    <div style="display:flex; flex-direction:column; gap:14px; font-size:13px">
      <!-- Generated ID Badge -->
      <div style="background:var(--surface-2); border:1px solid var(--line); border-left:4px solid var(--mint); border-radius:8px; padding:10px 12px; display:flex; justify-content:space-between; align-items:center">
        <div>
          <div style="font-size:10.5px; font-weight:800; text-transform:uppercase; color:var(--mint-ink); letter-spacing:0.06em">Unique Inspection Identifier</div>
          <div class="code" style="font-size:15px; font-weight:800; color:var(--mint)">${w.inspectionId || 'Generating...'}</div>
        </div>
        <span class="pill" style="background:var(--mint-soft); color:var(--mint-ink); font-size:11px; font-weight:700">Auto-Generated ID</span>
      </div>

      <!-- Project Selection -->
      <div>
        <label style="display:block; font-weight:700; margin-bottom:4px">Target Project *</label>
        <select id="ci_project" onchange="CREATE_INSP_WIZARD.projectId = this.value; openCreateInspectionWizard(this.value);" style="width:100%; padding:8px 10px; border-radius:8px; border:1px solid var(--line); background:var(--surface); font-size:13px">
          ${projectsList.map(proj => `
            <option value="${proj.id}" ${proj.id === w.projectId ? 'selected' : ''}>${proj.name} (${proj.code})</option>
          `).join('')}
        </select>
      </div>

      <!-- Construction Activity & Inspection Type -->
      <div style="display:grid; grid-template-columns:1fr 1fr; gap:10px">
        <div>
          <label style="display:block; font-weight:700; margin-bottom:4px">Construction Activity *</label>
          <select id="ci_activity" style="width:100%; padding:8px 10px; border-radius:8px; border:1px solid var(--line); background:var(--surface); font-size:12.5px">
            <option value="RCC Structural Works" ${w.activityType === 'RCC Structural Works' ? 'selected' : ''}>RCC Structural Works</option>
            <option value="Site Preparation & Survey" ${w.activityType === 'Site Preparation & Survey' ? 'selected' : ''}>Site Preparation & Survey</option>
            <option value="Foundation & Substructure" ${w.activityType === 'Foundation & Substructure' ? 'selected' : ''}>Foundation & Substructure</option>
            <option value="Waterproofing" ${w.activityType === 'Waterproofing' ? 'selected' : ''}>Waterproofing</option>
            <option value="Masonry & Shell Works" ${w.activityType === 'Masonry & Shell Works' ? 'selected' : ''}>Masonry & Shell Works</option>
            <option value="Finishes & Flooring" ${w.activityType === 'Finishes & Flooring' ? 'selected' : ''}>Finishes & Flooring</option>
            <option value="MEP Services" ${w.activityType === 'MEP Services' ? 'selected' : ''}>MEP Services</option>
          </select>
        </div>
        <div>
          <label style="display:block; font-weight:700; margin-bottom:4px">Inspection Type *</label>
          <select id="ci_type" style="width:100%; padding:8px 10px; border-radius:8px; border:1px solid var(--line); background:var(--surface); font-size:12.5px">
            <option value="Stage Quality Inspection">Stage Quality Inspection</option>
            <option value="Pre-Pour Hold Point">Pre-Pour Hold Point</option>
            <option value="Material Verification">Material Verification</option>
            <option value="Pre-Handover Snagging">Pre-Handover Snagging</option>
          </select>
        </div>
      </div>

      <!-- Inspection Title -->
      <div>
        <label style="display:block; font-weight:700; margin-bottom:4px">Inspection Title *</label>
        <input type="text" id="ci_title" value="${esc(w.title)}" placeholder="e.g. RCC Beam & Slab Quality Inspection" style="width:100%; padding:8px 10px; border-radius:8px; border:1px solid var(--line); background:var(--surface); font-size:13px">
      </div>

      <!-- Location Hierarchy -->
      <div style="background:var(--surface-2); border-radius:10px; padding:12px; display:flex; flex-direction:column; gap:10px">
        <div style="font-weight:700; font-size:12px; text-transform:uppercase; color:var(--ink-2)">Exact Site Location Scope</div>
        <div style="display:grid; grid-template-columns:1fr 1fr; gap:8px">
          <div>
            <label style="font-size:11.5px; color:var(--ink-3)">Tower / Block *</label>
            <input type="text" id="ci_tower" value="${esc(w.location.tower)}" placeholder="Tower 3" style="width:100%; padding:6px 8px; border-radius:6px; border:1px solid var(--line); background:var(--surface); font-size:12.5px">
          </div>
          <div>
            <label style="font-size:11.5px; color:var(--ink-3)">Floor Level *</label>
            <input type="text" id="ci_floor" value="${esc(w.location.floor)}" placeholder="Floor 8" style="width:100%; padding:6px 8px; border-radius:6px; border:1px solid var(--line); background:var(--surface); font-size:12.5px">
          </div>
        </div>
        <div style="display:grid; grid-template-columns:1fr 1fr; gap:8px">
          <div>
            <label style="font-size:11.5px; color:var(--ink-3)">Zone / Area *</label>
            <input type="text" id="ci_zone" value="${esc(w.location.zone)}" placeholder="Zone B · Sunken Slab" style="width:100%; padding:6px 8px; border-radius:6px; border:1px solid var(--line); background:var(--surface); font-size:12.5px">
          </div>
          <div>
            <label style="font-size:11.5px; color:var(--ink-3)">Grid / Element</label>
            <input type="text" id="ci_grid" value="${esc(w.location.grid)}" placeholder="Grids B4–B8 · Column C7" style="width:100%; padding:6px 8px; border-radius:6px; border:1px solid var(--line); background:var(--surface); font-size:12.5px">
          </div>
        </div>
        <div>
          <label style="font-size:11.5px; color:var(--ink-3)">Special Engineer Instructions</label>
          <input type="text" id="ci_instructions" value="${esc(w.location.instructions)}" placeholder="Instructions for field engineer..." style="width:100%; padding:6px 8px; border-radius:6px; border:1px solid var(--line); background:var(--surface); font-size:12.5px">
        </div>
      </div>

      <!-- Schedule & Priority -->
      <div style="display:grid; grid-template-columns:1fr 1fr 1fr; gap:8px">
        <div>
          <label style="display:block; font-weight:700; font-size:12px; margin-bottom:4px">Planned Date *</label>
          <input type="date" id="ci_pdate" value="${w.plannedDate}" style="width:100%; padding:6px 8px; border-radius:6px; border:1px solid var(--line); background:var(--surface); font-size:12.5px">
        </div>
        <div>
          <label style="display:block; font-weight:700; font-size:12px; margin-bottom:4px">Due Date *</label>
          <input type="date" id="ci_ddate" value="${w.dueDate}" style="width:100%; padding:6px 8px; border-radius:6px; border:1px solid var(--line); background:var(--surface); font-size:12.5px">
        </div>
        <div>
          <label style="display:block; font-weight:700; font-size:12px; margin-bottom:4px">Priority *</label>
          <select id="ci_priority" style="width:100%; padding:7px 8px; border-radius:6px; border:1px solid var(--line); background:var(--surface); font-size:12.5px; font-weight:700">
            <option value="High" ${w.priority === 'High' ? 'selected' : ''}>High</option>
            <option value="Medium" ${w.priority === 'Medium' ? 'selected' : ''}>Medium</option>
            <option value="Low" ${w.priority === 'Low' ? 'selected' : ''}>Low</option>
          </select>
        </div>
      </div>
    </div>
  `;
}

// ----------------- STEP 2: SELECT CHECKLIST -----------------

function renderCreateStep2(p) {
  const w = CREATE_INSP_WIZARD;
  const stages = MASTER_STAGES || [];

  const stageItemsHtml = stages.map(stg => {
    const isExpanded = w.expandedStages.has(stg.stage_id);
    let chkCount = 0;
    (stg.subgroups || []).forEach(sub => chkCount += (sub.checkpoints || []).length);

    let selectedInStage = 0;
    (stg.subgroups || []).forEach(sub => {
      (sub.checkpoints || []).forEach(chk => {
        if (w.selectedCheckpoints.has(chk.checkpoint_id)) selectedInStage++;
      });
    });

    const isAllSelected = chkCount > 0 && selectedInStage === chkCount;

    const subgroupsHtml = (stg.subgroups || []).map(sub => {
      const isSubExpanded = w.expandedSubgroups.has(sub.subgroup_id);
      const subChkCount = (sub.checkpoints || []).length;
      let selectedInSub = 0;
      (sub.checkpoints || []).forEach(chk => {
        if (w.selectedCheckpoints.has(chk.checkpoint_id)) selectedInSub++;
      });
      const isSubAll = subChkCount > 0 && selectedInSub === subChkCount;

      const checkpointsHtml = (sub.checkpoints || []).map(chk => {
        const isChecked = w.selectedCheckpoints.has(chk.checkpoint_id);
        const priColor = chk.priority === 'H' ? 'var(--crit)' : chk.priority === 'M' ? 'var(--major)' : 'var(--mint-ink)';
        return `
          <div style="display:flex; align-items:flex-start; gap:8px; padding:6px 0; border-bottom:1px dashed var(--line); font-size:12px">
            <input type="checkbox" id="chk_${chk.checkpoint_id}" ${isChecked ? 'checked' : ''} onchange="toggleCheckpointSelect('${chk.checkpoint_id}')" style="margin-top:2px">
            <label for="chk_${chk.checkpoint_id}" style="flex:1; cursor:pointer; line-height:1.35">
              <span style="font-weight:700; color:${priColor}; margin-right:4px">[${chk.priority}]</span>
              <span class="code" style="font-size:10.5px; color:var(--ink-3); margin-right:4px">${chk.checkpoint_id}</span>
              <span>${esc(chk.checkpoint_description)}</span>
            </label>
          </div>
        `;
      }).join('');

      return `
        <div style="border:1px solid var(--line); border-radius:8px; padding:8px 10px; margin-bottom:8px; background:var(--surface)">
          <div style="display:flex; justify-content:space-between; align-items:center">
            <div style="display:flex; align-items:center; gap:6px; cursor:pointer" onclick="toggleSubgroupExpand('${sub.subgroup_id}')">
              <span>${isSubExpanded ? '▾' : '▸'}</span>
              <span style="font-weight:700; font-size:12.5px">${esc(sub.subgroup_name)}</span>
              <span class="muted" style="font-size:11px">(${selectedInSub}/${subChkCount})</span>
            </div>
            <button type="button" class="btn ghost" onclick="selectAllInSubgroup('${sub.subgroup_id}', ${!isSubAll})" style="height:24px; padding:0 8px; font-size:11px">
              ${isSubAll ? 'Deselect All' : 'Select All'}
            </button>
          </div>
          ${isSubExpanded ? `<div style="margin-top:8px; padding-left:14px">${checkpointsHtml}</div>` : ''}
        </div>
      `;
    }).join('');

    return `
      <div style="border:1px solid var(--line); border-radius:10px; margin-bottom:10px; overflow:hidden; background:var(--surface)">
        <div style="background:var(--surface-2); padding:10px 12px; display:flex; justify-content:space-between; align-items:center">
          <div style="display:flex; align-items:center; gap:8px; cursor:pointer" onclick="toggleStageExpand('${stg.stage_id}')">
            <span>${isExpanded ? '▾' : '▸'}</span>
            <span style="font-weight:800; font-size:13px; color:var(--ink)">${esc(stg.stage_name)}</span>
            <span class="pill" style="font-size:10.5px; font-weight:700; background:var(--mint-soft); color:var(--mint-ink)">
              ${selectedInStage}/${chkCount}
            </span>
          </div>
          <button type="button" class="btn ghost" onclick="selectAllInStage('${stg.stage_id}', ${!isAllSelected})" style="height:26px; padding:0 10px; font-size:11.5px">
            ${isAllSelected ? 'Deselect Stage' : 'Select Stage'}
          </button>
        </div>
        ${isExpanded ? `<div style="padding:10px 12px">${subgroupsHtml}</div>` : ''}
      </div>
    `;
  }).join('');

  return `
    <div style="display:flex; flex-direction:column; gap:12px">
      <!-- Scope Preview Pill Bar -->
      <div style="display:flex; justify-content:space-between; align-items:center; background:var(--surface-2); padding:8px 12px; border-radius:8px; border:1px solid var(--line)">
        <div style="font-size:12.5px; font-weight:700">
          Selected Scope: <span style="color:var(--mint); font-weight:800">${w.selectedCheckpoints.size} Checkpoints</span>
        </div>
        ${w.selectedCheckpoints.size > 0 ? `
          <button type="button" class="btn ghost" onclick="clearAllSelectedCheckpoints()" style="height:24px; padding:0 8px; font-size:11px; color:var(--crit)">
            Clear Selection
          </button>
        ` : ''}
      </div>

      <!-- Checklist Tree -->
      <div style="max-height:50vh; overflow-y:auto; padding-right:4px">
        ${stageItemsHtml}
      </div>
    </div>
  `;
}

// ----------------- STEP 3: ASSIGN INSPECTION ENGINEER -----------------

function renderCreateStep3(p) {
  const w = CREATE_INSP_WIZARD;
  const roster = ENGINEER_ROSTER || [];

  const engineerCardsHtml = roster.map(eng => {
    const isSelected = eng.id === w.engineerId;
    const activeLoad = (typeof P !== 'undefined' ? P : []).reduce((acc, proj) => {
      return acc + (proj.ins || []).filter(i => i.eng === eng.name && ['Allocated', 'In progress'].includes(i.status)).length;
    }, 0);

    return `
      <div onclick="CREATE_INSP_WIZARD.engineerId = '${eng.id}'; CREATE_INSP_WIZARD.engineer = '${eng.name}'; if(typeof drawSheet === 'function') drawSheet();" style="border:1.5px solid ${isSelected ? 'var(--mint)' : 'var(--line)'}; background:${isSelected ? 'color-mix(in srgb, var(--mint) 8%, var(--surface))' : 'var(--surface)'}; border-radius:10px; padding:12px; cursor:pointer; display:flex; justify-content:space-between; align-items:center; transition:border-color .15s">
        <div style="display:flex; align-items:center; gap:10px">
          <div style="width:36px; height:36px; border-radius:50%; background:${isSelected ? 'var(--mint)' : 'var(--surface-2)'}; color:${isSelected ? 'var(--on-mint)' : 'var(--ink)'}; display:grid; place-items:center; font-weight:800; font-size:13px">
            ${eng.name.split(' ').map(n=>n[0]).join('')}
          </div>
          <div>
            <div style="font-weight:700; font-size:13.5px; color:var(--ink)">
              ${eng.name} <span class="code" style="font-size:11px; color:var(--mint)">${eng.id}</span>
            </div>
            <div class="muted" style="font-size:12px">${eng.role} · ${eng.spec}</div>
          </div>
        </div>
        <div style="text-align:right">
          <span class="pill" style="font-size:11px; font-weight:700; background:${activeLoad >= 3 ? 'var(--major-soft)' : 'var(--mint-soft)'}; color:${activeLoad >= 3 ? 'var(--major)' : 'var(--mint-ink)'}">
            ${activeLoad} Active Task${activeLoad === 1 ? '' : 's'}
          </span>
          <div style="font-size:11px; margin-top:3px; color:${isSelected ? 'var(--mint)' : 'transparent'}; font-weight:800">
            ✓ SELECTED
          </div>
        </div>
      </div>
    `;
  }).join('');

  return `
    <div style="display:flex; flex-direction:column; gap:12px">
      <div style="background:var(--surface-2); border-radius:8px; padding:10px 12px; font-size:12.5px; border-left:4px solid var(--mint)">
        <strong>Notice:</strong> Engineer assignment is mandatory before activating the inspection, but optional when saving a draft.
      </div>

      <div style="font-weight:700; font-size:13px; color:var(--ink-2)">Select from Authoritative Engineer Directory:</div>

      <div style="display:flex; flex-direction:column; gap:8px">
        ${engineerCardsHtml}
      </div>
    </div>
  `;
}

// ----------------- STEP 4: REVIEW & CONFIRM -----------------

function renderCreateStep4(p) {
  const w = CREATE_INSP_WIZARD;
  const eng = ENGINEER_ROSTER.find(e => e.id === w.engineerId) || { name: w.engineer || 'Unassigned', id: w.engineerId || 'N/A', spec: 'General' };

  return `
    <div style="display:flex; flex-direction:column; gap:12px; font-size:13px">
      <!-- Inspection Profile Overview -->
      <section style="background:var(--surface-2); border:1px solid var(--line); border-radius:10px; padding:14px; display:flex; flex-direction:column; gap:8px">
        <div style="display:flex; justify-content:space-between; align-items:center">
          <span class="code" style="font-size:14px; font-weight:800; color:var(--mint)">${w.inspectionId}</span>
          <span class="pill" style="font-size:11px; font-weight:800; background:var(--mint-soft); color:var(--mint-ink)">Ready to Create</span>
        </div>
        <div style="font-size:16px; font-weight:700">${esc(w.title)}</div>
        <div class="muted" style="font-size:12.5px">${w.activityType} · ${w.inspectionType}</div>
      </section>

      <!-- Key Parameters Grid -->
      <dl class="facts" style="grid-template-columns:1fr 1fr; background:var(--surface); border:1px solid var(--line); border-radius:10px; padding:12px; margin:0">
        <div><dt>Project</dt><dd><strong>${p.name}</strong> (${p.code})</dd></div>
        <div><dt>Assigned Engineer</dt><dd><strong style="color:var(--mint)">${eng.name}</strong> (${eng.id})</dd></div>
        <div><dt>Location</dt><dd>${w.location.tower} · ${w.location.floor} · ${w.location.zone}</dd></div>
        <div><dt>Schedule</dt><dd>Planned ${w.plannedDate} · Due ${w.dueDate}</dd></div>
        <div><dt>Priority</dt><dd><span style="font-weight:800; color:${w.priority === 'High' ? 'var(--crit)' : 'var(--mint-ink)'}">${w.priority}</span></dd></div>
        <div><dt>Checkpoints</dt><dd><strong>${w.selectedCheckpoints.size} Items Selected</strong></dd></div>
      </dl>

      <!-- Action Confirmation Note -->
      <div style="background:color-mix(in srgb, var(--mint) 10%, var(--surface)); border:1px solid var(--mint); border-radius:8px; padding:10px 12px; font-size:12px">
        <strong>Persistence Guarantee:</strong> On confirmation, this inspection will be saved permanently under ID <strong>${w.inspectionId}</strong> and immediately synced with ${eng.name}'s Field Workspace.
      </div>
    </div>
  `;
}

// ----------------- CHANGE INSPECTION ENGINEER WORKFLOW -----------------

let CHANGE_ENG_TARGET = null;

function openChangeEngineerModal(inspectionId) {
  CHANGE_ENG_TARGET = inspectionId;
  if (typeof openSheet === 'function') {
    openSheet(`changeEngineer:${inspectionId}`);
  }
}

function renderChangeEngineerSheet(inspectionId) {
  const code = inspectionId || CHANGE_ENG_TARGET;
  const alloc = ALLOCATIONS_CACHE[code];
  const ins = (typeof find === 'function' ? find('ins', code) : null)?.x || alloc || { code, title: 'Quality Inspection', eng: 'Unassigned', due: '2026-11-06', status: 'Allocated' };

  const currentEng = ins.eng || (alloc && alloc.engineer_name) || 'Unassigned';
  const currentStatus = ins.status || (alloc && alloc.status) || 'Allocated';

  const engineerOptionsHtml = ENGINEER_ROSTER.map(eng => {
    const isCurrent = eng.name === currentEng;
    return `
      <option value="${eng.id}" ${isCurrent ? 'disabled' : ''}>
        ${eng.name} (${eng.id}) · ${eng.spec} ${isCurrent ? '· (CURRENT)' : ''}
      </option>
    `;
  }).join('');

  const bodyHtml = `
    <div style="display:flex; flex-direction:column; gap:14px; font-size:13px">
      <!-- Target Inspection Summary -->
      <div style="background:var(--surface-2); border-radius:10px; padding:12px; border:1px solid var(--line)">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px">
          <span class="code" style="font-size:13px; font-weight:800; color:var(--mint)">${code}</span>
          <span class="stt info">${currentStatus}</span>
        </div>
        <div style="font-weight:700; font-size:14px">${esc(ins.title)}</div>
        <div class="muted" style="font-size:12px; margin-top:2px">Currently assigned to: <strong>${esc(currentEng)}</strong></div>
      </div>

      <!-- Select New Engineer -->
      <div>
        <label style="display:block; font-weight:700; margin-bottom:4px">Select New Inspection Engineer *</label>
        <select id="ce_new_eng" style="width:100%; padding:8px 10px; border-radius:8px; border:1px solid var(--line); background:var(--surface); font-size:13px">
          <option value="">-- Choose Engineer from Directory --</option>
          ${engineerOptionsHtml}
        </select>
      </div>

      <!-- New Due Date (Optional) -->
      <div>
        <label style="display:block; font-weight:700; margin-bottom:4px">Adjust Due Date (Optional)</label>
        <input type="date" id="ce_due_date" value="${ins.due || '2026-11-06'}" style="width:100%; padding:7px 10px; border-radius:8px; border:1px solid var(--line); background:var(--surface); font-size:12.5px">
      </div>

      <!-- Reassignment Reason (MANDATORY) -->
      <div>
        <label style="display:block; font-weight:700; margin-bottom:4px; color:var(--ink)">
          Reassignment Reason <span style="color:var(--crit); font-weight:800">* Mandatory</span>
        </label>
        <textarea id="ce_reason" rows="3" placeholder="State reason for engineer change (e.g. Workload reallocation, civil specialization required, engineer on leave)..." style="width:100%; padding:8px 10px; border-radius:8px; border:1px solid var(--line); background:var(--surface); font-size:12.5px; font-family:inherit"></textarea>
      </div>

      <div style="background:var(--surface-2); border-radius:8px; padding:10px; font-size:12px; color:var(--ink-2)">
        <strong>Integrity Protection:</strong> Changing the engineer preserves the unique inspection ID (<strong>${code}</strong>), all existing checklist findings, photographs, defect observations, and full audit logs.
      </div>
    </div>
  `;

  const footerHtml = `
    <div style="display:flex; justify-content:space-between; gap:10px; width:100%">
      <button class="btn ghost" type="button" onclick="closeSheet()" style="flex:1">
        Cancel
      </button>
      <button id="ce_submit_btn" class="btn primary" type="button" onclick="submitChangeEngineer('${code}')" style="flex:1.5; font-weight:800; background:var(--mint); color:var(--on-mint)">
        Confirm Change Engineer
      </button>
    </div>
  `;

  if (typeof setSheet === 'function') {
    setSheet(
      'Inspection Management',
      `Change Engineer · ${code}`,
      bodyHtml,
      footerHtml
    );
  }
}

async function submitChangeEngineer(code) {
  const engSelect = document.getElementById('ce_new_eng');
  const reasonInp = document.getElementById('ce_reason');
  const dueInp = document.getElementById('ce_due_date');

  const newEngId = engSelect ? engSelect.value : '';
  const reason = reasonInp ? reasonInp.value.trim() : '';
  const newDueDate = dueInp ? dueInp.value : '';

  if (!newEngId) {
    if (typeof toast === 'function') toast("Please select a new Inspection Engineer.");
    return;
  }
  if (!reason) {
    if (typeof toast === 'function') toast("A reason for reassignment is mandatory.");
    if (reasonInp) reasonInp.focus();
    return;
  }

  const btn = document.getElementById('ce_submit_btn');
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = `<span class="spinner"></span> Reassigning...`;
  }

  try {
    const res = await fetch(`/api/inspections/${code}/change-engineer`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        new_engineer: newEngId,
        reason: reason,
        new_due_date: newDueDate,
        actor_name: 'Priya Deshmukh (QC Lead)'
      })
    });
    const data = await res.json();

    if (!res.ok) {
      if (btn) {
        btn.disabled = false;
        btn.innerHTML = `Confirm Change Engineer`;
      }
      if (typeof toast === 'function') toast(data.detail || "Error reassigning engineer.");
      return;
    }

    if (typeof toast === 'function') {
      toast(`✓ Inspection ${code} successfully reassigned to ${data.new_engineer}!`);
    }

    if (typeof syncFromBackend === 'function') {
      await syncFromBackend();
    }
    if (typeof closeSheet === 'function') closeSheet();
    if (typeof render === 'function') render(false);

  } catch (err) {
    console.error("Change engineer error:", err);
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = `Confirm Change Engineer`;
    }
    if (typeof toast === 'function') toast("Network error reassigning engineer.");
  }
}

// Global exports
if (typeof window !== 'undefined') {
  window.CREATE_INSP_WIZARD = CREATE_INSP_WIZARD;
  window.openCreateInspectionWizard = openCreateInspectionWizard;
  window.openAllocateWizard = openCreateInspectionWizard; // redirect old alias
  window.setCreateStep = setCreateStep;
  window.saveInspectionAsDraft = saveInspectionAsDraft;
  window.submitCreateInspection = submitCreateInspection;
  window.renderCreateInspectionSheet = renderCreateInspectionSheet;
  window.openChangeEngineerModal = openChangeEngineerModal;
  window.renderChangeEngineerSheet = renderChangeEngineerSheet;
  window.submitChangeEngineer = submitChangeEngineer;
}
'''

with open('static/js/allocation_module.js', 'r', encoding='utf-8') as f:
    orig_lines = f.readlines()

# Line 850 is where openAllocationDetail begins
bottom_code = "".join(orig_lines[850:])

full_code = top_code + "\n" + bottom_code

with open('static/js/allocation_module.js', 'w', encoding='utf-8') as f:
    f.write(full_code)

print("allocation_module.js successfully updated. Total lines:", len(full_code.splitlines()))
