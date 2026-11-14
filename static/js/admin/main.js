/**
 * Organization Admin Console controller.
 * Manages KPI summary, project directory & creation, and team member provisioning.
 */
import { api } from '../shared/api.js';
import { html, render } from '../shared/html.js';
import { formatDate, formatNumber, todayISO } from '../shared/format.js';
import { showToast, openModal, closeModal, setupModalDismiss } from '../shared/ui.js';

let allUsers = [];

function getStatusBadge(status) {
  const norm = (status || '').toLowerCase();
  switch (norm) {
    case 'live':
      return html`<span class="badge badge-mint">Live</span>`;
    case 'hold':
    case 'on_hold':
      return html`<span class="badge badge-major">On Hold</span>`;
    case 'upcoming':
      return html`<span class="badge badge-minor">Upcoming</span>`;
    case 'completed':
      return html`<span class="badge badge-ofi">Completed</span>`;
    default:
      return html`<span class="badge badge-neutral">${status || 'Unknown'}</span>`;
  }
}

function getRoleBadge(role) {
  const norm = (role || '').toLowerCase();
  switch (norm) {
    case 'admin':
      return html`<span class="badge badge-crit">Admin</span>`;
    case 'qc_lead':
      return html`<span class="badge badge-minor">QC Lead</span>`;
    case 'engineer':
      return html`<span class="badge badge-mint">Engineer</span>`;
    default:
      return html`<span class="badge badge-neutral">${role || 'User'}</span>`;
  }
}

async function loadOverview() {
  try {
    const data = await api.get('/api/admin/overview');
    const elProjects = document.getElementById('kpiProjects');
    const elProjectsSub = document.getElementById('kpiProjectsSub');
    const elUsers = document.getElementById('kpiUsers');
    const elUsersSub = document.getElementById('kpiUsersSub');
    const elAllocations = document.getElementById('kpiAllocations');
    const elAllocationsSub = document.getElementById('kpiAllocationsSub');
    const elOpenNCs = document.getElementById('kpiOpenNCs');

    if (elProjects) elProjects.textContent = formatNumber(data.projects || 0);
    if (elProjectsSub) elProjectsSub.textContent = `${data.live_projects || 0} active / live`;

    const totalUsers = (data.admins || 0) + (data.qc_leads || 0) + (data.engineers || 0);
    if (elUsers) elUsers.textContent = formatNumber(totalUsers);
    if (elUsersSub) elUsersSub.textContent = `${data.engineers || 0} Eng, ${data.qc_leads || 0} QC, ${data.admins || 0} Admin`;

    if (elAllocations) elAllocations.textContent = formatNumber(data.active_inspections || 0);
    if (elAllocationsSub) elAllocationsSub.textContent = 'Active / In Progress';

    if (elOpenNCs) elOpenNCs.textContent = formatNumber(data.open_ncs || 0);
  } catch (err) {
    console.error('Failed to load admin overview:', err);
  }
}

async function loadProjects() {
  const tbody = document.getElementById('projectsTableBody');
  const countEl = document.getElementById('projectsCount');
  try {
    const list = await api.get('/api/projects');
    const projects = Array.isArray(list) ? list : (list.projects || []);

    if (countEl) countEl.textContent = String(projects.length);

    if (projects.length === 0) {
      render(tbody, html`
        <tr>
          <td colspan="6" class="muted table-empty-cell">
            No projects found in this organization. Click "+ New Project" above to create one.
          </td>
        </tr>
      `);
      return;
    }

    render(tbody, html`
      ${projects.map(p => html`
        <tr>
          <td>
            <strong>${p.name}</strong>
            <div class="muted font-xs">${p.code || p.id}</div>
          </td>
          <td>${p.type || p.building_type || 'General'}</td>
          <td>${p.loc || p.location || '—'}</td>
          <td>${getStatusBadge(p.status)}</td>
          <td>
            <div class="num font-sm">
              ${formatDate(p.start_date)} → ${formatDate(p.end_date)}
            </div>
          </td>
          <td class="muted num font-sm">${p.geo || '—'}</td>
        </tr>
      `)}
    `);
  } catch (err) {
    render(tbody, html`
      <tr>
        <td colspan="6" class="table-error-cell">
          Failed to load projects. Please refresh.
        </td>
      </tr>
    `);
  }
}

function renderTeamTable(users) {
  const tbody = document.getElementById('teamTableBody');
  const countEl = document.getElementById('teamCount');
  if (countEl) countEl.textContent = String(users.length);

  if (users.length === 0) {
    render(tbody, html`
      <tr>
        <td colspan="8" class="muted table-empty-cell">
          No team members found. Click "+ Provision Member" above to add team members.
        </td>
      </tr>
    `);
    return;
  }

  render(tbody, html`
    ${users.map(u => html`
      <tr>
        <td><strong>${u.full_name || u.name}</strong></td>
        <td><a href="mailto:${u.email}">${u.email}</a></td>
        <td>${getRoleBadge(u.role)}</td>
        <td class="num">${u.employee_id || '—'}</td>
        <td>${u.specialization || u.specialty || 'General'}</td>
        <td class="num">${u.phone || '—'}</td>
        <td>
          <span class="badge ${u.status === 'active' ? 'badge-mint' : 'badge-neutral'}">
            ${u.status || 'active'}
          </span>
        </td>
        <td class="muted num font-sm">${formatDate(u.created_at)}</td>
      </tr>
    `)}
  `);
}

async function loadTeam() {
  const tbody = document.getElementById('teamTableBody');
  try {
    const resp = await api.get('/api/auth/users');
    allUsers = resp.users || [];
    filterAndRenderTeam();
  } catch (err) {
    render(tbody, html`
      <tr>
        <td colspan="8" class="table-error-cell">
          Failed to load team members. Please refresh.
        </td>
      </tr>
    `);
  }
}

function filterAndRenderTeam() {
  const select = document.getElementById('roleFilterSelect');
  const role = select ? select.value : 'all';
  const filtered = role === 'all'
    ? allUsers
    : allUsers.filter(u => (u.role || '').toLowerCase() === role);
  renderTeamTable(filtered);
}

document.addEventListener('DOMContentLoaded', () => {
  setupModalDismiss();

  // Load Initial Data
  loadOverview();
  loadProjects();
  loadTeam();

  // Refresh Button
  const refreshBtn = document.getElementById('refreshDashboardBtn');
  if (refreshBtn) {
    refreshBtn.addEventListener('click', () => {
      loadOverview();
      loadProjects();
      loadTeam();
      showToast('Dashboard data refreshed', 'info');
    });
  }

  // Sign Out Button
  const signOutBtn = document.getElementById('signOutBtn');
  if (signOutBtn) {
    signOutBtn.addEventListener('click', async () => {
      try {
        await api.post('/api/auth/logout');
      } catch (_) {}
      window.location.href = '/login';
    });
  }

  // Tab Switching
  const tabBtnProjects = document.getElementById('tabBtnProjects');
  const tabBtnTeam = document.getElementById('tabBtnTeam');
  const tabProjects = document.getElementById('tabProjects');
  const tabTeam = document.getElementById('tabTeam');

  if (tabBtnProjects && tabBtnTeam && tabProjects && tabTeam) {
    tabBtnProjects.addEventListener('click', () => {
      tabBtnProjects.classList.add('active');
      tabBtnProjects.setAttribute('aria-selected', 'true');
      tabBtnTeam.classList.remove('active');
      tabBtnTeam.setAttribute('aria-selected', 'false');
      tabProjects.classList.remove('d-none');
      tabTeam.classList.add('d-none');
    });

    tabBtnTeam.addEventListener('click', () => {
      tabBtnTeam.classList.add('active');
      tabBtnTeam.setAttribute('aria-selected', 'true');
      tabBtnProjects.classList.remove('active');
      tabBtnProjects.setAttribute('aria-selected', 'false');
      tabTeam.classList.remove('d-none');
      tabProjects.classList.add('d-none');
    });
  }

  // Role Filter Select
  const roleFilterSelect = document.getElementById('roleFilterSelect');
  if (roleFilterSelect) {
    roleFilterSelect.addEventListener('change', filterAndRenderTeam);
  }

  // Open Create Project Modal
  const openCreateProjectModalBtn = document.getElementById('openCreateProjectModalBtn');
  if (openCreateProjectModalBtn) {
    openCreateProjectModalBtn.addEventListener('click', () => {
      const startInput = document.getElementById('projStartDate');
      const endInput = document.getElementById('projEndDate');
      if (startInput && !startInput.value) startInput.value = todayISO();
      if (endInput && !endInput.value) {
        const nextYear = new Date();
        nextYear.setFullYear(nextYear.getFullYear() + 1);
        endInput.value = nextYear.toISOString().split('T')[0];
      }
      openModal('createProjectModal');
    });
  }

  // Handle Create Project Form
  const createProjectForm = document.getElementById('createProjectForm');
  const saveProjectBtn = document.getElementById('saveProjectBtn');
  if (createProjectForm) {
    createProjectForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const name = document.getElementById('projName').value.trim();
      const code = document.getElementById('projCode').value.trim();
      const building_type = document.getElementById('projBuildingType').value;
      const location = document.getElementById('projLocation').value.trim();
      const status = document.getElementById('projStatus').value;
      const start_date = document.getElementById('projStartDate').value || todayISO();
      const end_date = document.getElementById('projEndDate').value || todayISO();
      const lat = document.getElementById('projLat').value.trim();
      const lng = document.getElementById('projLng').value.trim();
      const geo = (lat && lng) ? `${lat}, ${lng}` : undefined;

      if (!name || !code || !location) {
        showToast('Please fill in all required project fields.', 'error');
        return;
      }

      if (saveProjectBtn) {
        saveProjectBtn.disabled = true;
        saveProjectBtn.textContent = 'Saving...';
      }

      try {
        const payload = {
          name,
          code,
          type: building_type,
          loc: location,
          status,
          start_date,
          end_date,
          geo,
          progress: 0,
        };

        await api.post('/api/projects', payload);
        showToast(`Project '${name}' created successfully!`, 'success');
        closeModal('createProjectModal');
        createProjectForm.reset();
        loadProjects();
        loadOverview();
      } catch (err) {
        // Toast handled by api wrapper
      } finally {
        if (saveProjectBtn) {
          saveProjectBtn.disabled = false;
          saveProjectBtn.textContent = 'Create Project';
        }
      }
    });
  }

  // Open Provision User Modal
  const openProvisionUserModalBtn = document.getElementById('openProvisionUserModalBtn');
  if (openProvisionUserModalBtn) {
    openProvisionUserModalBtn.addEventListener('click', () => {
      openModal('provisionUserModal');
    });
  }

  // Handle Provision User Form
  const provisionUserForm = document.getElementById('provisionUserForm');
  const saveUserBtn = document.getElementById('saveUserBtn');
  if (provisionUserForm) {
    provisionUserForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const full_name = document.getElementById('userFullName').value.trim();
      const email = document.getElementById('userEmail').value.trim();
      const role = document.getElementById('userRole').value;
      const employee_id = document.getElementById('userEmpId').value.trim() || undefined;
      const specialization = document.getElementById('userSpec').value.trim() || undefined;
      const phone = document.getElementById('userPhone').value.trim() || undefined;
      const password = document.getElementById('userPassword').value;

      if (!full_name || !email || !password) {
        showToast('Please fill in all required user fields.', 'error');
        return;
      }

      if (password.length < 10) {
        showToast('Password must be at least 10 characters long.', 'error');
        return;
      }

      if (saveUserBtn) {
        saveUserBtn.disabled = true;
        saveUserBtn.textContent = 'Provisioning...';
      }

      try {
        const payload = {
          full_name,
          email,
          role,
          employee_id,
          specialization,
          phone,
          password,
        };

        await api.post('/api/auth/users', payload);
        showToast(`Member '${full_name}' provisioned successfully!`, 'success');
        closeModal('provisionUserModal');
        provisionUserForm.reset();
        loadTeam();
        loadOverview();
      } catch (err) {
        // Toast handled by api wrapper
      } finally {
        if (saveUserBtn) {
          saveUserBtn.disabled = false;
          saveUserBtn.textContent = 'Provision Member';
        }
      }
    });
  }
});
