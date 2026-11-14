/**
 * QC Lead Console — Main Application Controller.
 * Manages tab switching, deep linking via URL hashes, and coordinates modules.
 */
import { api } from '../shared/api.js';
import { setupModalDismiss } from '../shared/ui.js';
import { initOverview } from './overview.js';
import { initInspections } from './inspections.js';
import { initAllocateWizard } from './allocate.js';
import { createChecklistBrowser } from './checklist.js';
import { initNCs } from './ncs.js';
import { initApprovals } from './approvals.js';
import { initSideSheet } from './dossier.js';

let activeTab = 'overview';

document.addEventListener('DOMContentLoaded', () => {
  setupModalDismiss();

  // Initialize side sheet drawer actions listener
  initSideSheet(() => {
    // Refresh current view when an action occurs
    switchTab(activeTab);
  });

  // Sign out button
  const signOutBtn = document.getElementById('signOutBtn');
  if (signOutBtn) {
    signOutBtn.addEventListener('click', async () => {
      try {
        await api.post('/api/auth/logout');
      } catch (_) {}
      window.location.href = '/login';
    });
  }

  // Setup tab buttons
  const tabButtons = document.querySelectorAll('.qc-tab-btn');
  tabButtons.forEach(btn => {
    btn.addEventListener('click', () => {
      const targetTab = btn.getAttribute('data-tab');
      if (targetTab) {
        window.location.hash = targetTab;
      }
    });
  });

  // Listen for hash changes
  window.addEventListener('hashchange', () => {
    const hash = window.location.hash.replace('#/', '').replace('#', '');
    switchTab(hash || 'overview');
  });

  // Initial tab resolution
  const initialHash = window.location.hash.replace('#/', '').replace('#', '');
  switchTab(initialHash || 'overview');
});

export function switchTab(tabName) {
  const validTabs = ['overview', 'inspections', 'allocate', 'checklist', 'ncs', 'approvals'];
  if (!validTabs.includes(tabName)) tabName = 'overview';
  activeTab = tabName;

  // Update tab navigation UI
  document.querySelectorAll('.qc-tab-btn').forEach(btn => {
    const isTarget = btn.getAttribute('data-tab') === tabName;
    btn.classList.toggle('active', isTarget);
    btn.setAttribute('aria-selected', isTarget ? 'true' : 'false');
  });

  // Hide all tab panels
  document.querySelectorAll('.qc-tab-panel').forEach(panel => {
    panel.classList.add('d-none');
  });

  // Show active panel
  const activePanel = document.getElementById(`panel-${tabName}`);
  if (activePanel) {
    activePanel.classList.remove('d-none');
  }

  // Mount respective module
  mountTabModule(tabName);
}

function mountTabModule(tabName) {
  const panel = document.getElementById(`panel-${tabName}`);
  if (!panel) return;

  switch (tabName) {
    case 'overview':
      initOverview(panel, (selectedProjectId) => {
        // Project card clicked: switch to inspections filtered by that project
        window.location.hash = 'inspections';
        setTimeout(() => {
          initInspections(document.getElementById('panel-inspections'), selectedProjectId);
        }, 50);
      });
      break;

    case 'inspections':
      initInspections(panel);
      break;

    case 'allocate':
      initAllocateWizard(panel, (newAllocId) => {
        // Switch to inspections tab and highlight new allocation
        window.location.hash = 'inspections';
      });
      break;

    case 'checklist':
      createChecklistBrowser(panel, { selectable: false });
      break;

    case 'ncs':
      initNCs(panel);
      break;

    case 'approvals':
      initApprovals(panel, () => {
        // When approved / returned, reload overview and inspections
      });
      break;
  }
}
