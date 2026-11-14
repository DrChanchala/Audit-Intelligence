/**
 * Reusable Checklist Browser Component.
 * Used in both Allocate Wizard (Step 2) and the dedicated Checklist tab.
 */
import { api } from '../shared/api.js';
import { html, render } from '../shared/html.js';

export function createChecklistBrowser(container, options = {}) {
  const isSelectable = Boolean(options.selectable);
  let selected = new Set(options.selectedIds || []);
  const onSelectionChange = options.onSelectionChange || (() => {});

  let currentStages = [];
  let filterBuildingType = 'all';
  let filterPriority = 'all';
  let searchQuery = '';
  let debounceTimer = null;

  function getPriorityBadge(priority) {
    const p = (priority || '').toUpperCase();
    if (p === 'H') return html`<span class="badge badge-crit font-xs">High</span>`;
    if (p === 'M') return html`<span class="badge badge-major font-xs">Medium</span>`;
    if (p === 'L') return html`<span class="badge badge-minor font-xs">Low</span>`;
    return html`<span class="badge badge-neutral font-xs">${priority}</span>`;
  }

  function renderBrowser() {
    render(container, html`
      <div class="checklist-browser-wrap">
        <div class="filter-row mb-md">
          <select id="chkBuildingTypeSelect" class="form-select select-compact">
            <option value="all" ${filterBuildingType === 'all' ? 'selected' : ''}>All Building Types</option>
            <option value="residential" ${filterBuildingType === 'residential' ? 'selected' : ''}>Residential</option>
            <option value="commercial" ${filterBuildingType === 'commercial' ? 'selected' : ''}>Commercial</option>
            <option value="industrial" ${filterBuildingType === 'industrial' ? 'selected' : ''}>Industrial</option>
            <option value="infrastructure" ${filterBuildingType === 'infrastructure' ? 'selected' : ''}>Infrastructure</option>
          </select>

          <select id="chkPrioritySelect" class="form-select select-compact">
            <option value="all" ${filterPriority === 'all' ? 'selected' : ''}>All Priorities</option>
            <option value="H" ${filterPriority === 'H' ? 'selected' : ''}>High Priority (H)</option>
            <option value="M" ${filterPriority === 'M' ? 'selected' : ''}>Medium Priority (M)</option>
            <option value="L" ${filterPriority === 'L' ? 'selected' : ''}>Low Priority (L)</option>
          </select>

          <input
            type="search"
            id="chkSearchInput"
            class="form-control select-compact"
            placeholder="Search checkpoints..."
            value="${searchQuery}"
          >

          ${isSelectable ? html`
            <div class="muted font-sm ml-auto">
              <strong class="text-mint font-sm" id="selectedCounter">${selected.size}</strong> checkpoints selected
            </div>
          ` : ''}
        </div>

        <div class="checklist-tree" id="checklistTreeContainer">
          ${currentStages.length === 0 ? html`
            <div class="muted table-empty-cell">Loading master checklist...</div>
          ` : currentStages.map(st => html`
            <div class="stage-block" data-stage-id="${st.stage_id}">
              <div class="stage-title-bar">
                <span>${st.stage_name} <span class="muted font-xs">(${st.stage_id})</span></span>
                <span class="badge badge-neutral font-xs">${st.total_checkpoints} checkpoints</span>
              </div>
              <div class="stage-subgroups">
                ${(st.subgroups || []).map(sub => html`
                  <div class="subgroup-block" data-subgroup-id="${sub.subgroup_id}">
                    <div class="subgroup-title-bar">
                      <span>${sub.subgroup_name} <span class="muted font-xs">(${sub.checkpoint_count})</span></span>
                      ${isSelectable ? html`
                        <button type="button" class="btn btn-ghost btn-sm text-mint subgroup-select-all" data-sub-id="${sub.subgroup_id}">
                          Select All
                        </button>
                      ` : ''}
                    </div>
                    <div class="subgroup-checkpoints">
                      ${(sub.checkpoints || []).map(chk => html`
                        <div class="checkpoint-row">
                          ${isSelectable ? html`
                            <input
                              type="checkbox"
                              class="chk-checkbox"
                              data-id="${chk.checkpoint_id}"
                              ${selected.has(chk.checkpoint_id) ? 'checked' : ''}
                            >
                          ` : ''}
                          <div class="w-full">
                            <div class="flex-between">
                              <span class="muted font-xs num">${chk.checkpoint_id}</span>
                              ${getPriorityBadge(chk.priority)}
                            </div>
                            <div class="mt-xs fw-600">
                              ${chk.checkpoint_description}
                            </div>
                            ${chk.standard_reference ? html`
                              <div class="muted font-xs mt-xs">
                                Ref: ${chk.standard_reference}
                              </div>
                            ` : ''}
                          </div>
                        </div>
                      `)}
                    </div>
                  </div>
                `)}
              </div>
            </div>
          `)}
        </div>
      </div>
    `);

    attachEvents();
  }

  function attachEvents() {
    const btSelect = container.querySelector('#chkBuildingTypeSelect');
    if (btSelect) {
      btSelect.addEventListener('change', (e) => {
        filterBuildingType = e.target.value;
        loadChecklist();
      });
    }

    const priSelect = container.querySelector('#chkPrioritySelect');
    if (priSelect) {
      priSelect.addEventListener('change', (e) => {
        filterPriority = e.target.value;
        loadChecklist();
      });
    }

    const searchInput = container.querySelector('#chkSearchInput');
    if (searchInput) {
      searchInput.addEventListener('input', (e) => {
        searchQuery = e.target.value;
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(() => {
          loadChecklist();
        }, 250);
      });
    }

    if (isSelectable) {
      container.querySelectorAll('.chk-checkbox').forEach(cb => {
        cb.addEventListener('change', (e) => {
          const id = e.target.getAttribute('data-id');
          if (e.target.checked) {
            selected.add(id);
          } else {
            selected.delete(id);
          }
          updateCounter();
          onSelectionChange(Array.from(selected));
        });
      });

      container.querySelectorAll('.subgroup-select-all').forEach(btn => {
        btn.addEventListener('click', (e) => {
          const subId = e.target.getAttribute('data-sub-id');
          const subBlock = container.querySelector(`.subgroup-block[data-subgroup-id="${subId}"]`);
          if (subBlock) {
            const checkboxes = subBlock.querySelectorAll('.chk-checkbox');
            const allChecked = Array.from(checkboxes).every(cb => cb.checked);
            checkboxes.forEach(cb => {
              cb.checked = !allChecked;
              const id = cb.getAttribute('data-id');
              if (!allChecked) selected.add(id);
              else selected.delete(id);
            });
            updateCounter();
            onSelectionChange(Array.from(selected));
          }
        });
      });
    }
  }

  function updateCounter() {
    const counter = container.querySelector('#selectedCounter');
    if (counter) counter.textContent = String(selected.size);
  }

  async function loadChecklist() {
    const params = new URLSearchParams();
    if (filterBuildingType && filterBuildingType !== 'all') params.set('building_type', filterBuildingType);
    if (filterPriority && filterPriority !== 'all') params.set('priority', filterPriority);
    if (searchQuery.trim()) params.set('q', searchQuery.trim());

    const qs = params.toString();
    const url = `/api/master-checklist${qs ? '?' + qs : ''}`;
    try {
      const resp = await api.get(url);
      currentStages = resp.stages || [];
      renderBrowser();
    } catch (err) {
      console.error('Failed to load checklist:', err);
    }
  }

  loadChecklist();

  return {
    getSelected: () => Array.from(selected),
    setSelected: (ids) => {
      selected = new Set(ids);
      renderBrowser();
    },
    refresh: () => loadChecklist(),
  };
}
