/**
 * SiteIQ / Audit Intelligence — Unified Inspection Creation & Change Engineer Module
 * Full implementation of 4-step Create Inspection wizard, Change Engineer engine,
 * and Inspection Engineer Workspace synchronization.
 */

// Universal safe esc helper
const esc = typeof window !== 'undefined' && typeof window.esc === 'function' 
  ? window.esc 
  : s => String(s || '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));

// Master Checklist cache
let MASTER_STAGES = [];
let ALLOCATIONS_CACHE = {};

// Authoritative Inspection Engineer Directory with Stable Identifiers
let ENGINEER_ROSTER = [
  { id: 'EMP-1004', name: 'Anjali Rao', role: 'QC Inspection Engineer', spec: 'Finishes & Waterproofing' },
  { id: 'EMP-1002', name: 'Rohit Kale', role: 'Senior QC Engineer', spec: 'RCC & Structural' },
  { id: 'EMP-1003', name: 'Vikram Singh', role: 'QC Inspection Engineer', spec: 'Steel & Telecom' },
  { id: 'EMP-1005', name: 'Meera Iyer', role: 'Senior Façade & MEP Engineer', spec: 'Façade & MEP' },
  { id: 'EMP-1006', name: 'Arjun Mehta', role: 'QC Inspection Engineer', spec: 'Industrial & PEB' }
];

async function loadOrganizationEngineers() {
  try {
    const token = typeof localStorage !== 'undefined' ? localStorage.getItem('siteiq_jwt_token') : null;
    const headers = token ? { 'Authorization': `Bearer ${token}` } : {};
    const res = await fetch('/api/auth/users?role=engineer', { headers });
    if (res.ok) {
      const data = await res.json();
      if (data && data.users && data.users.length > 0) {
        ENGINEER_ROSTER = data.users.map(u => ({
          id: u.employee_id || u.id,
          name: u.full_name,
          role: 'QC Inspection Engineer',
          spec: u.specialization || 'General Civil'
        }));
      }
    }
  } catch(e) {
    console.warn('Using default engineer roster:', e);
  }
}
window.loadOrganizationEngineers = loadOrganizationEngineers;

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

  // Refresh dynamic engineer roster for the active organization
  loadOrganizationEngineers().catch(() => {});

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
      <div class="wizard-foot-actions">
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
      <div class="wizard-foot-actions">
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
      <div class="wizard-foot-actions">
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
      <div class="wizard-foot-actions">
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
    <div class="wizard-foot-actions">
      <button class="btn ghost" type="button" onclick="closeSheet()" style="flex:1">
        Cancel
      </button>
      <button id="ce_submit_btn" class="btn primary" type="button" onclick="submitChangeEngineer('${code}')" style="flex:1.5; font-weight:800; background:var(--mint); color:var(--on-mint)">
        Confirm Change Inspection Engineer
      </button>
    </div>
  `;

  if (typeof setSheet === 'function') {
    setSheet(
      'Inspection Management',
      `Change Inspection Engineer · ${code}`,
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
        btn.innerHTML = `Confirm Change Inspection Engineer`;
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
      btn.innerHTML = `Confirm Change Inspection Engineer`;
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

// ----------------- ALLOCATION DETAIL WORKSPACE (PHASE 5) -----------------

async function openAllocationDetail(allocId) {
  if (typeof openSheet === 'function') {
    openSheet('allocationDetail:' + allocId);
  }

  if (!ALLOCATIONS_CACHE[allocId]) {
    try {
      const res = await fetch(`/api/allocations/${allocId}`);
      if (res.ok) {
        const data = await res.json();
        if (data.status === 'success' && data.allocation) {
          ALLOCATIONS_CACHE[allocId] = data.allocation;
          if (typeof drawSheet === 'function' && typeof S !== 'undefined' && S.sheet === 'allocationDetail:' + allocId) {
            drawSheet();
          }
        }
      }
    } catch (e) {
      console.warn("Could not load allocation details for " + allocId, e);
    }
  }
}

function renderAllocationDetailSheet(allocId) {
  const alloc = ALLOCATIONS_CACHE[allocId];
  if (!alloc) {
    if (typeof setSheet === 'function') {
      setSheet('Inspection', 'Loading Checkpoints...', `<div style="text-align:center; padding:30px">Loading allocated checkpoints...</div>`);
    }
    openAllocationDetail(allocId);
    return;
  }

  const checkpointsHtml = (alloc.checkpoints || []).map(chk => {
    const isOK = chk.result_status === 'OK';
    const isNC = chk.result_status === 'NC';
    const isNA = chk.result_status === 'NA';
    const priColor = chk.priority === 'H' ? 'var(--crit)' : chk.priority === 'M' ? 'var(--major)' : 'var(--mint-ink)';

    return `
      <div style="border:1px solid var(--line); border-radius:10px; padding:10px; margin-bottom:8px; background:var(--surface)">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px">
          <div style="display:flex; gap:6px; align-items:center">
            <span style="font-size:10px; font-weight:800; color:${priColor}">[${chk.priority}]</span>
            <span class="code" style="font-size:11px">${chk.checkpoint_id}</span>
          </div>
          <span style="font-size:11px; color:var(--ink-3); font-weight:600">${chk.subgroup_name || ''}</span>
        </div>
        <div style="font-size:13px; font-weight:600; line-height:1.4; margin-bottom:8px">${chk.checkpoint_text_snapshot || chk.checkpoint_description}</div>
        
        <div style="display:flex; gap:6px; align-items:center; flex-wrap:wrap">
          <span class="pill" style="font-size:11px; font-weight:700; ${isOK ? 'background:var(--mint); color:#0B2A21' : isNC ? 'background:var(--crit); color:#fff' : 'background:var(--surface-2); color:var(--ink-2)'}">
            ${chk.result_status || 'Pending'}
          </span>
          <span style="font-size:11.5px; color:var(--ink-3)">Stage: ${chk.stage_name || ''}</span>
        </div>
        ${chk.observations ? `<div style="font-size:12px; color:var(--crit); margin-top:6px; background:var(--crit-soft); padding:4px 8px; border-radius:6px"><strong>Observation:</strong> ${chk.observations}</div>` : ''}
      </div>
    `;
  }).join('');

  const stats = alloc.stats || { total: alloc.checkpoints ? alloc.checkpoints.length : 0, ok: 0, nc: 0, na: 0, pending: alloc.checkpoints ? alloc.checkpoints.length : 0, compliance_pct: 0 };

  if (typeof setSheet === 'function') {
    setSheet(alloc.project_name || 'Project', `${alloc.allocation_id} · Allocated Scope`,
      `<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px">
         <span class="stt ${alloc.status === 'Report issued' ? 'good' : alloc.status === 'Pending review' ? 'info' : 'bad'}">${alloc.status}</span>
         <span style="font-size:12px; color:var(--ink-2)">Due ${alloc.due_date} · <strong>${alloc.engineer_name}</strong></span>
       </div>
       <div style="background:var(--surface-2); border-radius:10px; padding:10px 12px; margin-bottom:12px; font-size:12.5px">
         <div><strong>Location:</strong> ${alloc.location_scope}</div>
         <div><strong>Allocated By:</strong> ${alloc.allocated_by || 'Priya Deshmukh (QC Lead)'}</div>
         <div><strong>Schedule:</strong> Planned ${alloc.planned_date} · Due ${alloc.due_date}</div>
         <div><strong>Priority:</strong> ${alloc.priority}</div>
         ${alloc.instructions ? `<div style="margin-top:4px"><strong>Instructions:</strong> ${alloc.instructions}</div>` : ''}
       </div>
       <div style="margin-bottom:12px">
         <div style="display:flex; justify-content:space-between; font-size:12px; font-weight:700; margin-bottom:4px">
           <span>Allocated Checkpoints (${alloc.checkpoints ? alloc.checkpoints.length : 0} items)</span>
           <span class="stt info">${alloc.status}</span>
         </div>
       </div>
       <div style="max-height:48vh; overflow-y:auto; padding-right:4px">
         ${checkpointsHtml}
       </div>`,
      `<button class="btn ghost" type="button" onclick="closeSheet()" style="width:100%">Close Drawer</button>`
    );
  }
}

// ============================================================================
// PHASE 6: INSPECTION ENGINEER WORKSPACE
// Enterprise Execution Engine, Hierarchical Checklist, Multi-Photo Evidence,
// Status Transitions (Allocated -> In Progress -> Pending Review)
// ============================================================================

const ENGINEER_WORKSPACE = {
  activeEngineerId: 'EMP-1004',
  activeEngineerName: 'Anjali Rao',
  filterStatus: 'all',
  filterProject: 'all',
  filterStage: 'all',
  filterPriority: 'all',
  searchQuery: '',
  dashboardData: null,
  activeInspectionId: null,
  activeInspectionData: null,
  localExecutionState: {}, // checkpointId -> { result_status, observations, photos: [] }
  isSaving: false,
  isSubmitting: false
};

// ----------------- DATA FETCHING -----------------

async function fetchEngineerDashboardData(engineerId) {
  const engId = engineerId || ENGINEER_WORKSPACE.activeEngineerId;
  const params = new URLSearchParams();
  if (ENGINEER_WORKSPACE.filterStatus && ENGINEER_WORKSPACE.filterStatus !== 'all') {
    params.set('status', ENGINEER_WORKSPACE.filterStatus);
  }
  if (ENGINEER_WORKSPACE.filterProject && ENGINEER_WORKSPACE.filterProject !== 'all') {
    params.set('project_id', ENGINEER_WORKSPACE.filterProject);
  }
  if (ENGINEER_WORKSPACE.filterStage && ENGINEER_WORKSPACE.filterStage !== 'all') {
    params.set('stage', ENGINEER_WORKSPACE.filterStage);
  }
  if (ENGINEER_WORKSPACE.filterPriority && ENGINEER_WORKSPACE.filterPriority !== 'all') {
    params.set('priority', ENGINEER_WORKSPACE.filterPriority);
  }
  if (ENGINEER_WORKSPACE.searchQuery && ENGINEER_WORKSPACE.searchQuery.trim()) {
    params.set('search', ENGINEER_WORKSPACE.searchQuery.trim());
  }

  try {
    const token = typeof localStorage !== 'undefined' ? localStorage.getItem('siteiq_jwt_token') : null;
    const headers = token ? { 'Authorization': `Bearer ${token}` } : {};
    const res = await fetch(`/api/engineer/${engId}/dashboard?${params.toString()}`, { headers });
    if (res.ok) {
      const data = await res.json();
      if (data.status === 'success') {
        ENGINEER_WORKSPACE.dashboardData = data;
        if (data.engineer && data.engineer.name) {
          ENGINEER_WORKSPACE.activeEngineerName = data.engineer.name;
        }
        return data;
      }
    }
  } catch (err) {
    console.warn("Error fetching engineer dashboard:", err);
  }
  return null;
}

async function fetchInspectionExecutionData(allocId) {
  try {
    const res = await fetch(`/api/allocations/${allocId}`);
    if (res.ok) {
      const data = await res.json();
      if (data.status === 'success' && data.allocation) {
        ENGINEER_WORKSPACE.activeInspectionData = data.allocation;
        // Initialize local execution state for each checkpoint
        ENGINEER_WORKSPACE.localExecutionState = {};
        (data.allocation.checkpoints || []).forEach(cp => {
          let photos = [];
          if (cp.evidence_photo_url) {
            try {
              if (cp.evidence_photo_url.startsWith('[')) {
                photos = JSON.parse(cp.evidence_photo_url);
              } else {
                photos = cp.evidence_photo_url.split(',').map(u => u.trim()).filter(Boolean);
              }
            } catch(e) {
              photos = [cp.evidence_photo_url];
            }
          }
          const obs = cp.observations || '';
          let sev = 'Major', trade = 'Civil Structure Agency', tDate = '', pureObs = obs;
          const sevM = obs.match(/\[Severity:\s*([^\]]+)\]/i);
          if (sevM) { sev = sevM[1].trim(); pureObs = pureObs.replace(sevM[0], '').trim(); }
          const tradeM = obs.match(/\[Trade:\s*([^\]]+)\]/i);
          if (tradeM) { trade = tradeM[1].trim(); pureObs = pureObs.replace(tradeM[0], '').trim(); }
          const dateM = obs.match(/\[Target Date:\s*([^\]]+)\]/i);
          if (dateM) { tDate = dateM[1].trim(); pureObs = pureObs.replace(dateM[0], '').trim(); }

          ENGINEER_WORKSPACE.localExecutionState[cp.checkpoint_id] = {
            checkpoint_id: cp.checkpoint_id,
            result_status: cp.result_status || 'Pending',
            observations: pureObs,
            nc_severity: sev,
            nc_trade: trade,
            nc_target_date: tDate,
            photos: Array.isArray(photos) ? photos : [photos]
          };
        });
        return data.allocation;
      }
    }
  } catch (err) {
    console.warn("Error fetching inspection execution data:", err);
  }
  return null;
}

// ----------------- CONTROLS & ROUTING -----------------

function switchActiveEngineer(engineerId) {
  ENGINEER_WORKSPACE.activeEngineerId = engineerId;
  const match = ENGINEER_ROSTER.find(e => e.id === engineerId);
  if (match) ENGINEER_WORKSPACE.activeEngineerName = match.name;
  
  if (typeof cur === 'function' && cur().v === 'engineer_dashboard') {
    fetchEngineerDashboardData(engineerId).then(() => {
      if (typeof render === 'function') render(false);
    });
  } else if (typeof push === 'function') {
    push('engineer_dashboard');
  }
}

function setEngineerStatusFilter(status) {
  ENGINEER_WORKSPACE.filterStatus = status;
  fetchEngineerDashboardData().then(() => {
    if (typeof render === 'function') render(false);
  });
}

function setEngineerProjectFilter(projectId) {
  ENGINEER_WORKSPACE.filterProject = projectId;
  fetchEngineerDashboardData().then(() => {
    if (typeof render === 'function') render(false);
  });
}

function setEngineerStageFilter(stageName) {
  ENGINEER_WORKSPACE.filterStage = stageName;
  fetchEngineerDashboardData().then(() => {
    if (typeof render === 'function') render(false);
  });
}

function setEngineerPriorityFilter(pri) {
  ENGINEER_WORKSPACE.filterPriority = pri;
  fetchEngineerDashboardData().then(() => {
    if (typeof render === 'function') render(false);
  });
}

function handleEngineerSearchInput(query) {
  ENGINEER_WORKSPACE.searchQuery = query;
  fetchEngineerDashboardData().then(() => {
    if (typeof render === 'function') render(false);
  });
}

function returnToEngineerDashboard() {
  if (typeof back === 'function' && typeof S !== 'undefined' && S.stack && S.stack.length > 1) {
    back();
  } else {
    if (typeof S !== 'undefined') S.stack = [{ v: 'engineer_dashboard' }];
    if (typeof render === 'function') render();
    window.scrollTo(0, 0);
  }
}
window.returnToEngineerDashboard = returnToEngineerDashboard;

function openInspectionExecution(allocId) {
  ENGINEER_WORKSPACE.activeInspectionId = allocId;
  if (typeof push === 'function') {
    push(`inspection_execution:${allocId}`);
  }
}

// ----------------- VIEW 1: MY INSPECTIONS DASHBOARD -----------------

function renderEngineerWorkspaceView() {
  const d = ENGINEER_WORKSPACE.dashboardData;
  const activeEng = ENGINEER_ROSTER.find(e => e.id === ENGINEER_WORKSPACE.activeEngineerId) || {
    id: ENGINEER_WORKSPACE.activeEngineerId,
    name: ENGINEER_WORKSPACE.activeEngineerName || 'Anjali Rao',
    role: 'QC Inspection Engineer',
    spec: 'Finishes & Waterproofing'
  };

  if (!d) {
    if (!ENGINEER_WORKSPACE.isFetching) {
      ENGINEER_WORKSPACE.isFetching = true;
      fetchEngineerDashboardData().then(res => {
        ENGINEER_WORKSPACE.isFetching = false;
        if (!res) {
          ENGINEER_WORKSPACE.dashboardData = {
            status: 'success',
            engineer: { id: ENGINEER_WORKSPACE.activeEngineerId, name: ENGINEER_WORKSPACE.activeEngineerName || activeEng.name },
            metrics: { allocated: 0, in_progress: 0, due_today: 0, overdue: 0, submitted: 0, total: 0 },
            inspections: []
          };
        }
        if (typeof render === 'function') render(false);
      }).catch(() => {
        ENGINEER_WORKSPACE.isFetching = false;
        ENGINEER_WORKSPACE.dashboardData = {
          status: 'success',
          engineer: { id: ENGINEER_WORKSPACE.activeEngineerId, name: ENGINEER_WORKSPACE.activeEngineerName || activeEng.name },
          metrics: { allocated: 0, in_progress: 0, due_today: 0, overdue: 0, submitted: 0, total: 0 },
          inspections: []
        };
        if (typeof render === 'function') render(false);
      });
    }
    return `
      <div style="padding:48px 16px; text-align:center">
        <div style="font-size:18px; font-weight:700; color:var(--mint)">Loading Inspection Engineer Workspace...</div>
        <div class="muted" style="margin-top:6px">Connecting to SiteIQ quality database</div>
      </div>
    `;
  }

  const m = d.metrics || { allocated: 0, in_progress: 0, due_today: 0, overdue: 0, submitted: 0, total: 0 };
  const inspections = d.inspections || [];
  const currFilter = ENGINEER_WORKSPACE.filterStatus || 'all';

  // Roster Options for Switcher
  const engineerOptionsHtml = ENGINEER_ROSTER.map(e => `
    <option value="${e.id}" ${e.id === ENGINEER_WORKSPACE.activeEngineerId ? 'selected' : ''}>
      ${e.name} (${e.id}) · ${e.role}
    </option>
  `).join('');

  // Project Filter Options
  const projectsList = typeof P !== 'undefined' ? P : [];
  const projectOptionsHtml = `
    <option value="all" ${ENGINEER_WORKSPACE.filterProject === 'all' ? 'selected' : ''}>All Projects</option>
    ${projectsList.map(p => `
      <option value="${p.id}" ${ENGINEER_WORKSPACE.filterProject === p.id ? 'selected' : ''}>${p.name} (${p.code})</option>
    `).join('')}
  `;

  // Summary Metrics Cards (Allocated, In Progress, Due Today, Overdue, Submitted)
  const metricCardsHtml = `
    <section class="sum sum-engineer" aria-label="Inspection Metrics">
      <button class="sum-btn ${currFilter === 'allocated' ? 'hot' : ''}" type="button" onclick="setEngineerStatusFilter('allocated')" style="border-color:${currFilter === 'allocated' ? 'var(--mint)' : 'var(--line)'}; background:var(--surface)">
        <span class="v num" style="color:var(--ink)">${m.allocated}</span>
        <span class="l">Allocated</span>
      </button>
      <button class="sum-btn ${currFilter === 'in_progress' ? 'hot' : ''}" type="button" onclick="setEngineerStatusFilter('in_progress')" style="border-color:${currFilter === 'in_progress' ? 'var(--mint)' : 'var(--line)'}; background:var(--surface)">
        <span class="v num" style="color:var(--mint)">${m.in_progress}</span>
        <span class="l">In Progress</span>
      </button>
      <button class="sum-btn ${currFilter === 'due_today' ? 'hot' : ''}" type="button" onclick="setEngineerStatusFilter('due_today')" style="border-color:${currFilter === 'due_today' ? 'var(--mint)' : 'var(--line)'}; background:var(--surface)">
        <span class="v num" style="color:var(--major)">${m.due_today}</span>
        <span class="l">Due Today</span>
      </button>
      <button class="sum-btn crit ${currFilter === 'overdue' ? 'hot' : ''}" type="button" onclick="setEngineerStatusFilter('overdue')" style="border-color:${currFilter === 'overdue' ? 'var(--crit)' : 'var(--line)'}; background:var(--surface)">
        <span class="v num">${m.overdue}</span>
        <span class="l">Overdue</span>
      </button>
      <button class="sum-btn ${currFilter === 'submitted' ? 'hot' : ''}" type="button" onclick="setEngineerStatusFilter('submitted')" style="border-color:${currFilter === 'submitted' ? 'var(--mint)' : 'var(--line)'}; background:var(--surface)">
        <span class="v num" style="color:#4FB892">${m.submitted}</span>
        <span class="l">Submitted</span>
      </button>
    </section>
  `;

  // Inspection Cards List
  let inspectionCardsHtml = '';
  if (inspections.length === 0) {
    inspectionCardsHtml = `
      <div style="background:var(--surface); border:1px dashed var(--line); border-radius:14px; padding:36px 20px; text-align:center">
        <div style="font-size:15px; font-weight:700">No inspections match the current filters</div>
        <p class="muted" style="margin-top:4px">Assigned to ${activeEng.name} · ${activeEng.id}</p>
        <button class="btn ghost" type="button" onclick="setEngineerStatusFilter('all'); setEngineerProjectFilter('all');" style="margin-top:10px">
          Clear All Filters
        </button>
      </div>
    `;
  } else {
    inspectionCardsHtml = inspections.map(a => {
      const isOverdue = a.is_overdue;
      const isDueToday = a.is_due_today;
      const statusClass = a.status === 'Report issued' ? 'good' : a.status === 'Pending review' ? 'info' : a.status === 'In progress' ? 'info' : '';
      const priColor = a.priority === 'High' ? 'var(--crit)' : a.priority === 'Medium' ? 'var(--major)' : 'var(--mint-ink)';
      const priBg = a.priority === 'High' ? 'var(--crit-soft)' : a.priority === 'Medium' ? 'var(--major-soft)' : 'var(--mint-soft)';

      const dateLabel = isOverdue
        ? `<span class="late" style="font-weight:700">Due ${a.due_date} · Overdue</span>`
        : isDueToday
        ? `<span class="late" style="color:var(--major); font-weight:700">Due Today (${a.due_date})</span>`
        : `Planned ${a.planned_date || '—'} · Due ${a.due_date || '—'}`;

      const stagesDisplay = a.stages && a.stages.length ? a.stages.join(' · ') : a.primary_stage;
      const subgroupsDisplay = a.subgroups && a.subgroups.length ? a.subgroups.join(' · ') : a.primary_subgroup;

      return `
        <article class="card" style="position:relative; display:flex; flex-direction:column; gap:12px; background:var(--surface); border:1px solid var(--line); border-radius:14px; padding:16px; transition:border-color .15s">
          <div style="display:flex; justify-content:space-between; align-items:flex-start; gap:8px">
            <div>
              <div style="display:flex; gap:6px; align-items:center; flex-wrap:wrap; margin-bottom:4px">
                <span class="code" style="font-weight:800; color:var(--mint); font-size:13px">${a.allocation_id}</span>
                <span style="font-size:11px; font-weight:700; background:${priBg}; color:${priColor}; padding:1px 6px; border-radius:4px; text-transform:uppercase">${a.priority} Priority</span>
                <span class="stt ${statusClass}">${a.status}</span>
              </div>
              <h3 style="font-size:16px; font-weight:700; margin:0; line-height:1.25">
                ${a.project_name} <span class="muted" style="font-size:13px; font-weight:400">(${a.project_code})</span>
              </h3>
            </div>
            <span class="pill" style="font-size:11.5px; font-weight:700; background:var(--mint-soft); color:var(--mint-ink); flex-shrink:0">
              ${a.total_checkpoints} Checkpoint${a.total_checkpoints === 1 ? '' : 's'}
            </span>
          </div>

          <div style="background:var(--surface-2); border-radius:8px; padding:10px 12px; font-size:12.5px; display:flex; flex-direction:column; gap:4px">
            <div><strong>Stage:</strong> <span style="color:var(--mint-ink); font-weight:600">${stagesDisplay}</span></div>
            <div><strong>Subgroup:</strong> ${subgroupsDisplay}</div>
            <div><strong>Location:</strong> ${a.location_scope}</div>
            <div style="margin-top:2px; font-size:12px; color:var(--ink-2)">${dateLabel}</div>
          </div>

          <div style="display:flex; flex-direction:column; gap:6px">
            <div style="display:flex; justify-content:space-between; font-size:12px; font-weight:600">
              <span>Progress: ${a.completed_count || 0}/${a.total_checkpoints} completed</span>
              <span class="num">${a.progress_pct || 0}%</span>
            </div>
            <div class="prog" style="margin:0"><div class="bar"><i style="width:${a.progress_pct || 0}%"></i></div></div>
          </div>

          <div style="display:flex; justify-content:space-between; align-items:center; margin-top:auto; pt:6px">
            <div style="display:flex; gap:6px; font-size:11px; font-weight:700">
              <span style="color:var(--mint)">${a.ok_count || 0} OK</span>
              <span style="color:var(--crit)">${a.nc_count || 0} NC</span>
              <span style="color:var(--ink-3)">${a.na_count || 0} NA</span>
              <span style="color:var(--ink-2)">${a.pending_count || 0} Pending</span>
            </div>
            <button class="btn primary" type="button" onclick="openInspectionExecution('${a.allocation_id}')" style="height:34px; padding:0 14px; font-size:12.5px; font-weight:700; background:var(--mint); color:var(--on-mint)">
              Open Inspection →
            </button>
          </div>
        </article>
      `;
    }).join('');
  }

  return `
    <section class="hello" style="display:flex; justify-content:space-between; align-items:flex-start; flex-wrap:wrap; gap:12px; border-bottom:1px solid var(--line); padding-bottom:16px">
      <div>
        <div class="eyebrow" style="display:flex; align-items:center; gap:6px">
          <span>Inspection Engineer Workspace</span>
          <span style="background:var(--mint-soft); color:var(--mint-ink); font-size:10.5px; font-weight:800; padding:1px 6px; border-radius:4px">FIELD MODE</span>
        </div>
        <h1 style="font-size:26px; font-weight:400; margin-top:4px">
          My Assigned Inspections · <span style="font-weight:700; color:var(--mint)">${activeEng.name}</span>
        </h1>
        <p class="muted" style="font-size:13px">
          ${activeEng.id} · ${activeEng.role} (${activeEng.spec})
        </p>
      </div>

      <div style="display:flex; align-items:center; gap:8px">
        <span class="pill" style="background:var(--mint-soft); color:var(--mint-ink); font-size:11px; font-weight:700">
          🔒 Authenticated Engineer Session
        </span>
      </div>
    </section>

    ${metricCardsHtml}

    <section class="proj-tools" style="display:flex; gap:10px; align-items:center; justify-content:space-between; flex-wrap:wrap">
      <label class="search" style="flex:1; min-width:240px; margin:0">
        <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>
        <input type="search" placeholder="Search by ID, project, stage, location..." value="${esc(ENGINEER_WORKSPACE.searchQuery)}" oninput="handleEngineerSearchInput(this.value)">
      </label>

      <div style="display:flex; gap:8px; align-items:center; flex-wrap:wrap">
        <select onchange="setEngineerProjectFilter(this.value)" style="padding:7px 10px; border-radius:8px; border:1px solid var(--line); background:var(--surface); font-size:12px; font-weight:600">
          ${projectOptionsHtml}
        </select>

        <select onchange="setEngineerPriorityFilter(this.value)" style="padding:7px 10px; border-radius:8px; border:1px solid var(--line); background:var(--surface); font-size:12px; font-weight:600">
          <option value="all" ${ENGINEER_WORKSPACE.filterPriority === 'all' ? 'selected' : ''}>All Priorities</option>
          <option value="High" ${ENGINEER_WORKSPACE.filterPriority === 'High' ? 'selected' : ''}>High</option>
          <option value="Medium" ${ENGINEER_WORKSPACE.filterPriority === 'Medium' ? 'selected' : ''}>Medium</option>
          <option value="Low" ${ENGINEER_WORKSPACE.filterPriority === 'Low' ? 'selected' : ''}>Low</option>
        </select>

        <div class="chips" style="margin:0">
          ${['all', 'Allocated', 'In progress', 'Due today', 'Overdue', 'Submitted'].map(st => {
            const val = st.toLowerCase().replace(' ', '_');
            const isActive = currFilter === val || (val === 'in_progress' && currFilter === 'in_progress') || (val === 'due_today' && currFilter === 'due_today') || currFilter === st.toLowerCase();
            return `
              <button class="chip" type="button" aria-pressed="${isActive}" onclick="setEngineerStatusFilter('${val}')">
                ${st}
              </button>
            `;
          }).join('')}
        </div>
      </div>
    </section>

    <section>
      <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px">
        <h2 style="font-size:18px; font-weight:700; margin:0">Allocated Inspection Tasks (${inspections.length})</h2>
        <span class="muted" style="font-size:12px">Synchronized with SiteIQ Quality Lead Engine</span>
      </div>
      <div class="cards cards-responsive">
        ${inspectionCardsHtml}
      </div>
    </section>
  `;
}

// ----------------- VIEW 2: INSPECTION EXECUTION VIEW -----------------

function renderInspectionExecutionView(allocId) {
  const targetId = allocId || ENGINEER_WORKSPACE.activeInspectionId;
  const alloc = ENGINEER_WORKSPACE.activeInspectionData;

  if (!alloc || alloc.allocation_id !== targetId) {
    fetchInspectionExecutionData(targetId).then(() => {
      if (typeof render === 'function') render(false);
    });
    return `
      <div style="padding:48px 16px; text-align:center">
        <div style="font-size:18px; font-weight:700; color:var(--mint)">Opening Inspection ${targetId}...</div>
        <div class="muted" style="margin-top:6px">Loading assigned checklist checkpoints</div>
      </div>
    `;
  }

  const isLocked = alloc.status === 'Pending review' || alloc.status === 'Report issued';
  const checkpoints = alloc.checkpoints || [];
  const localState = ENGINEER_WORKSPACE.localExecutionState || {};

  // Compute live progress from localExecutionState
  let okCount = 0, ncCount = 0, naCount = 0, pendingCount = 0;
  checkpoints.forEach(cp => {
    const st = localState[cp.checkpoint_id]?.result_status || cp.result_status || 'Pending';
    if (st === 'OK') okCount++;
    else if (st === 'NC') ncCount++;
    else if (st === 'NA') naCount++;
    else pendingCount++;
  });

  const totalCount = checkpoints.length;
  const completedCount = okCount + ncCount + naCount;
  const progressPct = totalCount > 0 ? Math.round((completedCount / totalCount) * 100) : 0;

  // Group checkpoints: Stage -> Subgroup -> Checkpoints
  // Important: Display only the checkpoints allocated by the QC Lead!
  const hierarchy = {};
  checkpoints.forEach(cp => {
    const sId = cp.stage_id || 'STG-01';
    const sName = cp.stage_name || 'Inspection Stage';
    const subId = cp.subgroup_id || 'SUB-01';
    const subName = cp.subgroup_name || 'Subgroup';

    if (!hierarchy[sId]) {
      hierarchy[sId] = { id: sId, name: sName, subgroups: {} };
    }
    if (!hierarchy[sId].subgroups[subId]) {
      hierarchy[sId].subgroups[subId] = { id: subId, name: subName, checkpoints: [] };
    }
    hierarchy[sId].subgroups[subId].checkpoints.push(cp);
  });

  // Render Checkpoints Hierarchical HTML
  const stagesHtml = Object.values(hierarchy).map(stage => {
    const subgroupsHtml = Object.values(stage.subgroups).map(sub => {
      const chkRowsHtml = sub.checkpoints.map((cp, idx) => {
        const state = localState[cp.checkpoint_id] || {
          checkpoint_id: cp.checkpoint_id,
          result_status: cp.result_status || 'Pending',
          observations: cp.observations || '',
          nc_severity: 'Major',
          nc_trade: 'Civil Structure Agency',
          nc_target_date: '',
          photos: []
        };
        const currRes = state.result_status;
        const photos = state.photos || [];

        const priBadge = cp.priority === 'H'
          ? `<span style="font-size:10.5px; font-weight:800; color:var(--crit); background:var(--crit-soft); padding:1px 6px; border-radius:4px">HIGH</span>`
          : cp.priority === 'M'
          ? `<span style="font-size:10.5px; font-weight:800; color:var(--major); background:var(--major-soft); padding:1px 6px; border-radius:4px">MED</span>`
          : `<span style="font-size:10.5px; font-weight:800; color:var(--mint-ink); background:var(--mint-soft); padding:1px 6px; border-radius:4px">LOW</span>`;

        // Photographs Gallery
        const photosGalleryHtml = photos.length ? `
          <div style="display:flex; gap:8px; flex-wrap:wrap; margin-top:8px">
            ${photos.map((pUrl, pIdx) => `
              <div style="position:relative; width:80px; height:80px; border-radius:8px; overflow:hidden; border:1px solid var(--line); background:#000">
                <img src="${pUrl}" alt="Evidence" style="width:100%; height:100%; object-fit:cover" onclick="window.open('${pUrl}','_blank')">
                ${!isLocked ? `
                  <button type="button" onclick="removeCheckpointEvidencePhoto('${cp.checkpoint_id}', '${pUrl}')" style="position:absolute; top:2px; right:2px; background:rgba(0,0,0,0.7); color:#fff; border:none; border-radius:50%; width:20px; height:20px; font-size:11px; cursor:pointer; display:grid; place-items:center">
                    ✕
                  </button>
                ` : ''}
              </div>
            `).join('')}
          </div>
        ` : '';

        return `
          <div id="card_${cp.checkpoint_id}" style="border:1px solid var(--line); border-radius:12px; padding:14px; margin-bottom:12px; background:var(--surface)">
            <div style="display:flex; justify-content:space-between; align-items:flex-start; gap:8px; margin-bottom:6px">
              <div style="display:flex; align-items:center; gap:6px; flex-wrap:wrap">
                <span class="code" style="font-size:11px; font-weight:800; color:var(--mint)">${cp.checkpoint_id}</span>
                ${priBadge}
              </div>
              <span class="pill" style="font-size:11px; font-weight:700; ${currRes === 'OK' ? 'background:var(--mint); color:#0B2A21' : currRes === 'NC' ? 'background:var(--crit); color:#fff' : currRes === 'NA' ? 'background:var(--ink-3); color:#fff' : 'background:var(--surface-2); color:var(--ink-2)'}">
                ${currRes || 'Pending'}
              </span>
            </div>

            <div style="font-size:13.5px; font-weight:600; line-height:1.45; margin-bottom:12px; color:var(--ink)">
              <strong>Checkpoint ${idx + 1}:</strong> ${esc(cp.checkpoint_text_snapshot || cp.checkpoint_description)}
            </div>

            <!-- Result Buttons [OK] [NC] [NA] -->
            <div style="display:flex; gap:8px; margin-bottom:10px; align-items:center; flex-wrap:wrap">
              <span style="font-size:12px; font-weight:700; color:var(--ink-2); margin-right:4px">Result:</span>
              <button type="button" class="btn chk-eval-btn" onclick="setCheckpointExecutionResult('${cp.checkpoint_id}', 'OK')" ${isLocked ? 'disabled' : ''} style="${currRes === 'OK' ? 'background:var(--mint); color:#0B2A21; border:1px solid var(--mint)' : 'background:var(--surface-2); color:var(--ink); border:1px solid var(--line)'}">
                ✓ OK
              </button>
              <button type="button" class="btn chk-eval-btn" onclick="setCheckpointExecutionResult('${cp.checkpoint_id}', 'NC')" ${isLocked ? 'disabled' : ''} style="${currRes === 'NC' ? 'background:var(--crit); color:#fff; border:1px solid var(--crit)' : 'background:var(--surface-2); color:var(--ink); border:1px solid var(--line)'}">
                ⚠ NC
              </button>
              <button type="button" class="btn chk-eval-btn" onclick="setCheckpointExecutionResult('${cp.checkpoint_id}', 'NA')" ${isLocked ? 'disabled' : ''} style="${currRes === 'NA' ? 'background:var(--ink-3); color:#fff; border:1px solid var(--ink-3)' : 'background:var(--surface-2); color:var(--ink); border:1px solid var(--line)'}">
                — NA
              </button>
            </div>

            <!-- Structured NC Details if NC -->
            ${currRes === 'NC' ? `
              <div style="background:var(--surface-2); border:1px solid rgba(239, 68, 68, 0.3); border-left:4px solid var(--crit); border-radius:8px; padding:10px 12px; margin-bottom:10px">
                <div style="font-size:11.5px; font-weight:800; color:var(--crit); text-transform:uppercase; letter-spacing:0.04em; margin-bottom:8px; display:flex; align-items:center; gap:5px">
                  <span>⚠</span> Non-Conformity Classification & Rectification Scope
                </div>
                <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(170px, 1fr)); gap:8px">
                  <div>
                    <label style="display:block; font-size:11px; font-weight:700; color:var(--ink-2); margin-bottom:3px">Defect Severity *</label>
                    <select ${isLocked ? 'disabled' : ''} onchange="updateCheckpointNCAttr('${cp.checkpoint_id}', 'nc_severity', this.value)" style="width:100%; height:32px; font-size:12px; border-radius:6px; border:1px solid var(--line); background:var(--surface); color:var(--ink); padding:0 8px">
                      <option value="Critical" ${(state.nc_severity || 'Major') === 'Critical' ? 'selected' : ''}>Critical (Hold Point / Safety)</option>
                      <option value="Major" ${(state.nc_severity || 'Major') === 'Major' ? 'selected' : ''}>Major (Non-Compliant Work)</option>
                      <option value="Minor" ${state.nc_severity === 'Minor' ? 'selected' : ''}>Minor (Surface / Cosmetic)</option>
                    </select>
                  </div>
                  <div>
                    <label style="display:block; font-size:11px; font-weight:700; color:var(--ink-2); margin-bottom:3px">Responsible Trade / Agency</label>
                    <select ${isLocked ? 'disabled' : ''} onchange="updateCheckpointNCAttr('${cp.checkpoint_id}', 'nc_trade', this.value)" style="width:100%; height:32px; font-size:12px; border-radius:6px; border:1px solid var(--line); background:var(--surface); color:var(--ink); padding:0 8px">
                      <option value="Civil Structure Agency" ${(state.nc_trade || '') === 'Civil Structure Agency' ? 'selected' : ''}>Civil Structure Agency</option>
                      <option value="Rebar & Steel Contractor" ${state.nc_trade === 'Rebar & Steel Contractor' ? 'selected' : ''}>Rebar & Steel Contractor</option>
                      <option value="Formwork & Shuttering Vendor" ${state.nc_trade === 'Formwork & Shuttering Vendor' ? 'selected' : ''}>Formwork & Shuttering Vendor</option>
                      <option value="Waterproofing Specialist" ${state.nc_trade === 'Waterproofing Specialist' ? 'selected' : ''}>Waterproofing Specialist</option>
                      <option value="MEP & Conduit Agency" ${state.nc_trade === 'MEP & Conduit Agency' ? 'selected' : ''}>MEP & Conduit Agency</option>
                      <option value="Façade & Cladding Agency" ${state.nc_trade === 'Façade & Cladding Agency' ? 'selected' : ''}>Façade & Cladding Agency</option>
                    </select>
                  </div>
                  <div>
                    <label style="display:block; font-size:11px; font-weight:700; color:var(--ink-2); margin-bottom:3px">Target Rectification Date</label>
                    <input type="date" ${isLocked ? 'disabled' : ''} value="${esc(state.nc_target_date || '')}" onchange="updateCheckpointNCAttr('${cp.checkpoint_id}', 'nc_target_date', this.value)" style="width:100%; height:32px; font-size:12px; border-radius:6px; border:1px solid var(--line); background:var(--surface); color:var(--ink); padding:0 8px">
                  </div>
                </div>
              </div>
            ` : ''}

            <!-- Observation / Remarks Input -->
            <div style="margin-bottom:10px">
              <label style="display:block; font-size:12px; font-weight:600; margin-bottom:4px; color:var(--ink-2)">
                Observation / Remarks
                ${currRes === 'NC' ? '<span style="color:var(--crit); font-weight:800; margin-left:4px">* Required for Non-Compliance (NC)</span>' : ''}
                ${currRes === 'NA' ? '<span style="color:var(--major); font-weight:800; margin-left:4px">* Justification reason required for Not Applicable (NA)</span>' : ''}
              </label>
              <textarea 
                rows="2" 
                placeholder="${currRes === 'NC' ? 'Describe defect, severity, and rectification required...' : currRes === 'NA' ? 'State engineering justification why this checkpoint is not applicable...' : 'Observation remarks (optional)...'}" 
                ${isLocked ? 'disabled' : ''}
                oninput="updateCheckpointObservationText('${cp.checkpoint_id}', this.value)"
                style="width:100%; border:1px solid ${currRes === 'NC' && !state.observations.trim() ? 'var(--crit)' : currRes === 'NA' && !state.observations.trim() ? 'var(--major)' : 'var(--line)'}; border-radius:8px; padding:8px 10px; font-size:12.5px; background:var(--surface); font-family:inherit"
              >${esc(state.observations)}</textarea>
            </div>

            <!-- Upload Photos / Evidence -->
            <div>
              <div style="display:flex; justify-content:space-between; align-items:center">
                <span style="font-size:12px; font-weight:600; color:var(--ink-2)">
                  Upload Photos / Supporting Evidence (${photos.length})
                </span>
                ${!isLocked ? `
                  <div style="display:flex; gap:6px">
                    <label class="btn ghost" style="height:28px; padding:0 10px; font-size:11.5px; cursor:pointer; display:inline-flex; align-items:center; gap:4px">
                      📷 Add Photo
                      <input type="file" accept="image/*" capture="environment" style="display:none" onchange="handleEvidenceFileUpload('${cp.checkpoint_id}', this)">
                    </label>
                    <button type="button" class="btn ghost" onclick="addDemoEvidencePhoto('${cp.checkpoint_id}')" style="height:28px; padding:0 8px; font-size:11px" title="Attach site inspection photo sample">
                      + Sample
                    </button>
                  </div>
                ` : ''}
              </div>
              ${photosGalleryHtml}
            </div>
          </div>
        `;
      }).join('');

      return `
        <div style="margin-bottom:18px">
          <div style="font-size:14px; font-weight:700; color:var(--ink); margin-bottom:8px; display:flex; align-items:center; gap:6px">
            <span style="width:4px; height:16px; background:var(--mint); border-radius:2px; display:inline-block"></span>
            Subgroup: ${sub.name}
            <span class="muted" style="font-size:12px; font-weight:400">(${sub.checkpoints.length} checkpoint${sub.checkpoints.length === 1 ? '' : 's'})</span>
          </div>
          ${chkRowsHtml}
        </div>
      `;
    }).join('');

    return `
      <section class="panel" style="background:var(--surface); border:1px solid var(--line); border-radius:14px; padding:16px; margin-bottom:16px">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:14px; padding-bottom:8px; border-bottom:1px solid var(--line)">
          <h2 style="font-size:16px; font-weight:800; color:var(--mint-ink); margin:0">
            ${stage.name}
          </h2>
          <span class="pill" style="font-size:11px; font-weight:700; background:var(--mint-soft); color:var(--mint-ink)">
            Stage Checkpoints
          </span>
        </div>
        ${subgroupsHtml}
      </section>
    `;
  }).join('');

  // Lock Banner if submitted
  const lockBannerHtml = isLocked ? `
    <div style="background:var(--surface-2); border:1px solid var(--line); border-left:4px solid var(--mint); border-radius:8px; padding:12px 16px; margin-bottom:14px; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px">
      <div>
        <div style="font-weight:700; font-size:13.5px; color:var(--mint-ink)">🔒 Inspection Submitted — Read-Only Mode</div>
        <div class="muted" style="font-size:12px">All findings and evidence are locked. Currently awaiting QC Lead sign-off.</div>
      </div>
      <span class="stt info">${alloc.status}</span>
    </div>
  ` : '';

  return `
    <div class="view-execution" style="display:flex; flex-direction:column; gap:16px">
      <!-- Top Navigation & Return -->
      <div style="display:flex; justify-content:space-between; align-items:center">
        <button class="btn ghost" type="button" onclick="returnToEngineerDashboard()" style="font-size:12.5px; font-weight:600">
          ← Back to My Inspections
        </button>
        <span class="code" style="font-size:12px; font-weight:700">${alloc.allocation_id}</span>
      </div>

      ${lockBannerHtml}

      <!-- Top Summary Card (Follows user specified layout) -->
      <section style="background:var(--surface); border:1px solid var(--line); border-radius:14px; padding:18px">
        <div style="display:flex; justify-content:space-between; align-items:flex-start; flex-wrap:wrap; gap:10px; margin-bottom:12px">
          <div>
            <div style="font-size:12px; font-weight:700; color:var(--mint-ink); text-transform:uppercase; letter-spacing:0.05em">Quality Inspection Execution</div>
            <h1 style="font-size:22px; font-weight:700; margin:2px 0 4px">Project: ${alloc.project_name}</h1>
            <div style="font-size:13.5px; color:var(--ink-2); display:flex; gap:8px; align-items:center; flex-wrap:wrap">
              <span><strong>Inspection:</strong> <span class="code" style="font-size:13px">${alloc.allocation_id}</span></span>
              <span>·</span>
              <span><strong>Location:</strong> ${alloc.location_scope}</span>
            </div>
          </div>
          <div style="display:flex; flex-direction:column; align-items:flex-end; gap:4px">
            <span class="stt ${alloc.status === 'Report issued' ? 'good' : alloc.status === 'Pending review' ? 'info' : 'bad'}" style="font-size:12px; padding:3px 10px">
              ${alloc.status}
            </span>
            <span style="font-size:11.5px; color:var(--ink-3)">Engineer: <strong>${alloc.engineer_name}</strong></span>
          </div>
        </div>

        <!-- Inspection Progress Bar -->
        <div style="background:var(--surface-2); border-radius:10px; padding:12px 14px">
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px">
            <span style="font-weight:700; font-size:13px">
              Inspection Progress: ${completedCount}/${totalCount} checkpoints completed — ${progressPct}%
            </span>
            <div style="display:flex; gap:6px; font-size:11px; font-weight:800">
              <span class="pill" style="background:var(--mint); color:#0B2A21">[OK: ${okCount}]</span>
              <span class="pill" style="background:var(--crit); color:#fff">[NC: ${ncCount}]</span>
              <span class="pill" style="background:var(--ink-3); color:#fff">[NA: ${naCount}]</span>
              <span class="pill" style="background:var(--surface); color:var(--ink-2); border:1px solid var(--line)">[Pending: ${pendingCount}]</span>
            </div>
          </div>
          <div class="prog" style="margin:0; height:8px"><div class="bar"><i style="width:${progressPct}%"></i></div></div>
        </div>
      </section>

      <!-- Checkpoint Hierarchy (Only Allocated Checkpoints) -->
      ${stagesHtml}

      <!-- Sticky Bottom Action Footer -->
      <div class="execution-sticky-bar">
        <div style="font-size:12.5px; color:var(--ink-2)">
          ${pendingCount > 0 ? `<span style="color:var(--major); font-weight:700">⚠ ${pendingCount} checkpoint(s) pending evaluation</span>` : `<span style="color:var(--mint); font-weight:700">✓ All checkpoints evaluated</span>`}
        </div>

        <div style="display:flex; gap:10px; align-items:center">
          ${!isLocked ? `
            <button class="btn ghost" type="button" onclick="saveInspectionProgress('${alloc.allocation_id}', false)" style="height:38px; font-weight:700; padding:0 16px">
              💾 Save Progress
            </button>
            <button class="btn primary" type="button" onclick="submitInspectionFromWorkspace('${alloc.allocation_id}')" style="height:38px; font-weight:700; padding:0 18px; background:var(--mint); color:var(--on-mint)">
              🚀 Submit Inspection
            </button>
          ` : `
            <button class="btn primary" type="button" onclick="returnToEngineerDashboard()" style="height:38px; font-weight:700; padding:0 18px">
              Back to My Inspections
            </button>
          `}
        </div>
      </div>
    </div>
  `;
}

// ----------------- INTERACTIVE EXECUTION HANDLERS -----------------

function setCheckpointExecutionResult(chkId, result) {
  if (!ENGINEER_WORKSPACE.localExecutionState[chkId]) {
    ENGINEER_WORKSPACE.localExecutionState[chkId] = { checkpoint_id: chkId, result_status: result, observations: '', photos: [] };
  } else {
    ENGINEER_WORKSPACE.localExecutionState[chkId].result_status = result;
  }
  if (typeof render === 'function') render(false);
}

function updateCheckpointObservationText(chkId, text) {
  if (!ENGINEER_WORKSPACE.localExecutionState[chkId]) {
    ENGINEER_WORKSPACE.localExecutionState[chkId] = { checkpoint_id: chkId, result_status: 'Pending', observations: text, photos: [] };
  } else {
    ENGINEER_WORKSPACE.localExecutionState[chkId].observations = text;
  }
}

function updateCheckpointNCAttr(chkId, attr, val) {
  if (!ENGINEER_WORKSPACE.localExecutionState[chkId]) {
    ENGINEER_WORKSPACE.localExecutionState[chkId] = { checkpoint_id: chkId, result_status: 'NC', observations: '', photos: [] };
  }
  ENGINEER_WORKSPACE.localExecutionState[chkId][attr] = val;
}

async function handleEvidenceFileUpload(chkId, inputEl) {
  const file = inputEl.files && inputEl.files[0];
  if (!file) return;

  const allocId = ENGINEER_WORKSPACE.activeInspectionId;
  const formData = new FormData();
  formData.append('file', file);

  if (typeof toast === 'function') toast("Uploading evidence photo...");

  try {
    const res = await fetch(`/api/allocations/${allocId}/upload-evidence`, {
      method: 'POST',
      body: formData
    });
    if (res.ok) {
      const data = await res.json();
      if (data.status === 'success' && data.url) {
        if (!ENGINEER_WORKSPACE.localExecutionState[chkId]) {
          ENGINEER_WORKSPACE.localExecutionState[chkId] = { checkpoint_id: chkId, result_status: 'Pending', observations: '', photos: [] };
        }
        ENGINEER_WORKSPACE.localExecutionState[chkId].photos.push(data.url);
        if (typeof toast === 'function') toast("Photo evidence attached.");
        if (typeof render === 'function') render(false);
      }
    }
  } catch(e) {
    console.warn("Evidence upload failed:", e);
    if (typeof toast === 'function') toast("Could not upload photo. Retrying locally.");
  }
}

function addDemoEvidencePhoto(chkId) {
  const samplePhotos = [
    '/static/uploads/evidence/site_rebar_check_sample.jpg',
    '/static/uploads/evidence/sunken_slab_waterproofing_sample.jpg',
    '/static/uploads/evidence/demarcation_benchmark_sample.jpg'
  ];
  const photo = samplePhotos[Math.floor(Math.random() * samplePhotos.length)];
  if (!ENGINEER_WORKSPACE.localExecutionState[chkId]) {
    ENGINEER_WORKSPACE.localExecutionState[chkId] = { checkpoint_id: chkId, result_status: 'Pending', observations: '', photos: [] };
  }
  ENGINEER_WORKSPACE.localExecutionState[chkId].photos.push(photo);
  if (typeof toast === 'function') toast("Sample inspection photo attached.");
  if (typeof render === 'function') render(false);
}

function removeCheckpointEvidencePhoto(chkId, photoUrl) {
  if (ENGINEER_WORKSPACE.localExecutionState[chkId]) {
    ENGINEER_WORKSPACE.localExecutionState[chkId].photos = ENGINEER_WORKSPACE.localExecutionState[chkId].photos.filter(p => p !== photoUrl);
    if (typeof render === 'function') render(false);
  }
}

// ----------------- SAVE PROGRESS & SUBMIT -----------------

async function saveInspectionProgress(allocId, isSubmitting = false) {
  if (ENGINEER_WORKSPACE.isSaving) return false;
  ENGINEER_WORKSPACE.isSaving = true;

  const payloadCheckpoints = Object.values(ENGINEER_WORKSPACE.localExecutionState).map(item => {
    let obs = (item.observations || '').trim();
    if (item.result_status === 'NC') {
      const meta = [];
      if (item.nc_severity) meta.push(`[Severity: ${item.nc_severity}]`);
      if (item.nc_trade) meta.push(`[Trade: ${item.nc_trade}]`);
      if (item.nc_target_date) meta.push(`[Target Date: ${item.nc_target_date}]`);
      if (meta.length > 0 && !obs.includes('[Severity:')) {
        obs = `${meta.join(' ')} ${obs}`.trim();
      }
    }
    return {
      checkpoint_id: item.checkpoint_id,
      result_status: item.result_status || 'Pending',
      observations: obs,
      evidence_photo_url: item.photos && item.photos.length ? JSON.stringify(item.photos) : ''
    };
  });

  try {
    const res = await fetch(`/api/allocations/${allocId}/save-progress`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        saved_by: ENGINEER_WORKSPACE.activeEngineerName,
        checkpoints: payloadCheckpoints
      })
    });

    const data = await res.json();
    ENGINEER_WORKSPACE.isSaving = false;

    if (!res.ok) {
      if (typeof toast === 'function') toast(data.detail || "Validation error saving progress.");
      return false;
    }

    if (data.status === 'success') {
      if (ENGINEER_WORKSPACE.activeInspectionData) {
        ENGINEER_WORKSPACE.activeInspectionData.status = data.allocation_status;
      }
      if (!isSubmitting && typeof toast === 'function') {
        toast(`Progress saved. Status: ${data.allocation_status}`);
      }
      return true;
    }
  } catch(e) {
    ENGINEER_WORKSPACE.isSaving = false;
    console.warn("Save progress error:", e);
    if (typeof toast === 'function') toast("Network error saving progress.");
    return false;
  }
  return false;
}

async function submitInspectionFromWorkspace(allocId) {
  if (ENGINEER_WORKSPACE.isSubmitting) return;

  const checkpoints = (ENGINEER_WORKSPACE.activeInspectionData && ENGINEER_WORKSPACE.activeInspectionData.checkpoints) || [];
  const localState = ENGINEER_WORKSPACE.localExecutionState || {};

  // 1. Check for Pending checkpoints
  const pending = checkpoints.filter(cp => {
    const st = localState[cp.checkpoint_id]?.result_status || cp.result_status || 'Pending';
    return st === 'Pending' || !st;
  });

  if (pending.length > 0) {
    if (typeof toast === 'function') {
      toast(`Cannot submit: ${pending.length} checkpoint(s) remain pending. Mark all as OK, NC, or NA.`);
    }
    const firstPending = document.getElementById(`card_${pending[0].checkpoint_id}`);
    if (firstPending) firstPending.scrollIntoView({ behavior: 'smooth', block: 'center' });
    return;
  }

  // 2. Check for missing NC observations
  const missingNC = checkpoints.filter(cp => {
    const st = localState[cp.checkpoint_id]?.result_status;
    const obs = localState[cp.checkpoint_id]?.observations || '';
    return st === 'NC' && !obs.trim();
  });

  if (missingNC.length > 0) {
    if (typeof toast === 'function') {
      toast(`Cannot submit: Observation remarks required for ${missingNC.length} NC checkpoint(s).`);
    }
    const firstNC = document.getElementById(`card_${missingNC[0].checkpoint_id}`);
    if (firstNC) firstNC.scrollIntoView({ behavior: 'smooth', block: 'center' });
    return;
  }

  // 3. Check for missing NA reasons
  const missingNA = checkpoints.filter(cp => {
    const st = localState[cp.checkpoint_id]?.result_status;
    const obs = localState[cp.checkpoint_id]?.observations || '';
    return st === 'NA' && !obs.trim();
  });

  if (missingNA.length > 0) {
    if (typeof toast === 'function') {
      toast(`Cannot submit: Justification reason required for ${missingNA.length} NA checkpoint(s).`);
    }
    const firstNA = document.getElementById(`card_${missingNA[0].checkpoint_id}`);
    if (firstNA) firstNA.scrollIntoView({ behavior: 'smooth', block: 'center' });
    return;
  }

  // Save latest findings first
  const saved = await saveInspectionProgress(allocId, true);
  if (!saved) return;

  ENGINEER_WORKSPACE.isSubmitting = true;
  if (typeof toast === 'function') toast("Submitting inspection for QC Lead review...");

  try {
    const res = await fetch(`/api/allocations/${allocId}/submit`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        submitted_by: ENGINEER_WORKSPACE.activeEngineerName,
        notes: "Field inspection completed. All checkpoints verified."
      })
    });

    const data = await res.json();
    ENGINEER_WORKSPACE.isSubmitting = false;

    if (!res.ok) {
      if (typeof toast === 'function') toast(data.detail || "Error submitting inspection.");
      return;
    }

    if (data.status === 'success') {
      if (ENGINEER_WORKSPACE.activeInspectionData) {
        ENGINEER_WORKSPACE.activeInspectionData.status = 'Pending review';
      }
      if (typeof toast === 'function') toast("Inspection successfully submitted for QC Lead sign-off!");
      
      // Reload detail to refresh cache and lock state
      await fetchInspectionExecutionData(allocId);
      if (typeof render === 'function') render(false);
    }
  } catch(e) {
    ENGINEER_WORKSPACE.isSubmitting = false;
    console.warn("Submit allocation error:", e);
    if (typeof toast === 'function') toast("Network error submitting inspection.");
  }
}

// Global exports
if (typeof window !== 'undefined') {
  window.ENGINEER_WORKSPACE = ENGINEER_WORKSPACE;
  window.switchActiveEngineer = switchActiveEngineer;
  window.setEngineerStatusFilter = setEngineerStatusFilter;
  window.setEngineerProjectFilter = setEngineerProjectFilter;
  window.setEngineerStageFilter = setEngineerStageFilter;
  window.setEngineerPriorityFilter = setEngineerPriorityFilter;
  window.handleEngineerSearchInput = handleEngineerSearchInput;
  window.openInspectionExecution = openInspectionExecution;
  window.renderEngineerWorkspaceView = renderEngineerWorkspaceView;
  window.renderInspectionExecutionView = renderInspectionExecutionView;
  window.setCheckpointExecutionResult = setCheckpointExecutionResult;
  window.updateCheckpointObservationText = updateCheckpointObservationText;
  window.updateCheckpointNCAttr = updateCheckpointNCAttr;
  window.handleEvidenceFileUpload = handleEvidenceFileUpload;
  window.addDemoEvidencePhoto = addDemoEvidencePhoto;
  window.removeCheckpointEvidencePhoto = removeCheckpointEvidencePhoto;
  window.saveInspectionProgress = saveInspectionProgress;
  window.submitInspectionFromWorkspace = submitInspectionFromWorkspace;
}
