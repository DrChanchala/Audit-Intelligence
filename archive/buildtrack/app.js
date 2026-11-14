// PyCray_SiteIQ — Dual-Mode Enterprise AI Construction Progress Engine
// White & Blue Theme with Black Text (Aptos)

document.addEventListener("DOMContentLoaded", () => {
    window.app = new PyCraySiteIQApp();
    window.app.init();
});

class PyCraySiteIQApp {
    constructor() {
        this.state = {
            currentRole: "Project Manager",
            currentView: "dashboard",
            dashboardData: null,
            comparisonData: [],
            activities: [],
            stages: [],
            cameras: [],
            rfis: [],
            ncrs: [],
            safety: [],
            materials: [],
            pmReviews: [],
            currentBaseline: null,
            uploadedBaselineId: null,
            fieldPhotoFile: null,
            aiChatHistory: [
                {
                    sender: "ai",
                    text: "Hello! I am your **PyCray_SiteIQ Dual-Mode AI Project Agent**. I monitor both **Mode A (Static Camera Automated Progress)** and **Mode B (Human-Verified PM Approved Progress)** against the L4 Master Baseline Schedule. How can I assist you today?"
                }
            ]
        };
        this.sCurveChart = null;
    }

    async init() {
        this.setupNavigation();
        this.setupRoleSwitcher();
        this.setupEventListeners();
        await this.loadDashboardData();
        await this.loadActivities();
        await this.loadBaselineStatus();
        await this.loadCameras();
        await this.loadTimeLapse();
        await this.loadAuxiliaryData();
        await this.loadPMReviews('PENDING');
        await this.checkModelStatus();
        this.populateFieldActivitySelect();
    }

    // ── NAVIGATION ────────────────────────────────────────────────────────────
    setupNavigation() {
        document.querySelectorAll("[data-nav]").forEach(el => {
            el.addEventListener("click", (e) => {
                e.preventDefault();
                const targetView = el.getAttribute("data-nav");
                this.switchView(targetView);
            });
        });
    }

    switchView(viewName) {
        this.state.currentView = viewName;
        document.querySelectorAll(".view-section").forEach(sec => sec.classList.add("hidden"));

        const targetSec = document.getElementById(`view-${viewName}`);
        if (targetSec) {
            targetSec.classList.remove("hidden");
        }

        document.querySelectorAll("[data-nav]").forEach(el => {
            if (el.getAttribute("data-nav") === viewName) {
                el.classList.add("bg-blue-600", "text-white");
                el.classList.remove("text-black", "hover:bg-blue-50");
            } else {
                el.classList.remove("bg-blue-600", "text-white");
                el.classList.add("text-black", "hover:bg-blue-50");
            }
        });

        // Trigger view-specific loads
        if (viewName === "dashboard") {
            this.loadDashboardData();
        } else if (viewName === "ai-progress") {
            this.loadAIProgress();
        } else if (viewName === "pm-reviews") {
            this.loadPMReviews('PENDING');
        } else if (viewName === "pm-progress") {
            this.loadPMApprovedProgress();
        } else if (viewName === "completion") {
            this.renderFloorHeatmap();
        } else if (viewName === "field-capture") {
            this.populateFieldActivitySelect();
        }
    }

    // ── ROLE PERMISSIONS ──────────────────────────────────────────────────────
    setupRoleSwitcher() {
        const roleSelector = document.getElementById("role-switcher");
        if (roleSelector) {
            roleSelector.addEventListener("change", (e) => {
                this.state.currentRole = e.target.value;
                this.showToast(`Active role switched to: ${this.state.currentRole}`);
            });
        }
    }

    // ── 1. DASHBOARD & 4-WAY PROGRESS (Spec §20, §41, §42) ────────────────────
    async loadDashboardData() {
        try {
            const res = await fetch("/api/dashboard");
            const data = await res.json();
            this.state.dashboardData = data;
            this.renderDashboardUI();
            this.loadDiscrepancies();
        } catch (err) {
            console.error("Error loading dashboard data:", err);
        }
    }

    renderDashboardUI() {
        if (!this.state.dashboardData) return;
        const { metrics, kpis } = this.state.dashboardData;

        // 4 Hero KPI Cards
        document.getElementById("kpi-planned-progress").innerText = `${metrics.planned_progress}%`;
        document.getElementById("kpi-ai-progress").innerText = `${metrics.ai_automated_progress}%`;
        document.getElementById("kpi-field-progress").innerText = `${metrics.field_observed_progress}%`;
        document.getElementById("kpi-pm-progress").innerText = `${metrics.pm_approved_progress}%`;

        // Update nav badge
        const badge = document.getElementById("nav-pending-pm-badge");
        if (badge) {
            badge.innerText = kpis.pending_pm_reviews;
        }

        // 10 Stages Table with 4-Stream Breakdowns
        const stageTbody = document.getElementById("stage-progress-tbody");
        if (stageTbody) {
            stageTbody.innerHTML = metrics.stages.map(s => {
                const aiDiff = (s.ai_pct - s.pm_pct).toFixed(1);
                const varianceSign = aiDiff > 0 ? `+${aiDiff}%` : `${aiDiff}%`;
                return `
                    <tr class="hover:bg-blue-50/60 transition">
                        <td class="py-3 px-4 font-bold text-black">${s.stage_name}</td>
                        <td class="py-3 px-4 text-center font-mono font-bold text-black">${s.weightage}%</td>
                        <td class="py-3 px-4 text-center font-mono text-black">${s.planned_pct}%</td>
                        <td class="py-3 px-4 text-center font-mono font-bold text-blue-800">${s.ai_pct}%</td>
                        <td class="py-3 px-4 text-center font-mono text-black">${s.reported_progress_pct}%</td>
                        <td class="py-3 px-4 text-center font-mono font-bold text-black">${s.pm_pct}%</td>
                        <td class="py-3 px-4 text-center font-mono font-bold text-black">
                            <span class="px-2 py-0.5 rounded border ${Math.abs(aiDiff) > 5.0 ? 'bg-blue-100 border-blue-400' : 'bg-white border-blue-200'}">
                                ${varianceSign}
                            </span>
                        </td>
                    </tr>
                `;
            }).join("");
        }

        this.renderSCurve();
    }

    renderSCurve() {
        const ctx = document.getElementById("s-curve-chart");
        if (!ctx) return;

        if (this.sCurveChart) {
            this.sCurveChart.destroy();
        }

        const labels = ["Jan 25", "Mar 25", "May 25", "Jul 25", "Sep 25", "Nov 25", "Jan 26", "Mar 26", "May 26", "Jul 26", "Sep 26 (Now)", "Nov 26", "Jan 27", "Mar 27"];
        
        // 4 separate progress curves
        const plannedCurve = [0, 7, 12, 18, 25, 33, 41, 50, 58, 62, 68, 77, 88, 100];
        const aiCurve      = [0, 7, 12, 18, 25, 33, 41, 49, 56, 61, 72.0, null, null, null];
        const fieldCurve   = [0, 7, 12, 18, 24, 32, 40, 48, 55, 60, 71.0, null, null, null];
        const pmCurve      = [0, 7, 12, 18, 24, 32, 40, 48, 54, 59, 69.0, null, null, null];

        this.sCurveChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: 'Planned Target (L4 Baseline)',
                        data: plannedCurve,
                        borderColor: '#60a5fa',
                        borderDash: [6, 4],
                        borderWidth: 2,
                        pointRadius: 2,
                        fill: false,
                        tension: 0.25
                    },
                    {
                        label: 'Mode A: AI Automated Progress',
                        data: aiCurve,
                        borderColor: '#1d4ed8',
                        backgroundColor: 'rgba(29, 78, 216, 0.05)',
                        borderWidth: 3,
                        pointRadius: 3,
                        fill: true,
                        tension: 0.25
                    },
                    {
                        label: 'Mode B: Field Observed Progress',
                        data: fieldCurve,
                        borderColor: '#3b82f6',
                        borderDash: [2, 2],
                        borderWidth: 2,
                        pointRadius: 2,
                        fill: false,
                        tension: 0.25
                    },
                    {
                        label: 'Mode B: PM Approved Progress',
                        data: pmCurve,
                        borderColor: '#000000',
                        borderWidth: 3,
                        pointRadius: 3,
                        fill: false,
                        tension: 0.25
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        labels: {
                            color: '#000000',
                            font: { family: 'Aptos, sans-serif', weight: 'bold', size: 11 }
                        }
                    }
                },
                scales: {
                    x: {
                        ticks: { color: '#000000', font: { family: 'Aptos, sans-serif', size: 10 } },
                        grid: { color: '#dbeafe' }
                    },
                    y: {
                        ticks: { color: '#000000', font: { family: 'Aptos, sans-serif', size: 10 } },
                        grid: { color: '#dbeafe' },
                        min: 0,
                        max: 100
                    }
                }
            }
        });
    }

    async loadDiscrepancies() {
        try {
            const res = await fetch("/api/discrepancies");
            const disc = await res.json();
            const container = document.getElementById("discrepancy-container");
            if (!container) return;

            if (!disc.length) {
                container.innerHTML = `<div class="p-3 bg-blue-50 text-black text-center rounded border border-blue-200">No active discrepancies above threshold.</div>`;
                return;
            }

            container.innerHTML = disc.map(d => `
                <div class="p-3 bg-white border border-blue-300 rounded-lg shadow-sm">
                    <div class="flex items-center justify-between font-bold text-black">
                        <span>${d.activity_code}</span>
                        <span class="text-blue-800 font-mono">Variance: ${d.ai_pm_variance > 0 ? '+' : ''}${d.ai_pm_variance}%</span>
                    </div>
                    <div class="text-[11px] font-bold text-black mt-0.5">${d.name}</div>
                    <div class="text-[10px] text-gray-700 mt-1 flex justify-between">
                        <span>Planned: <b>${d.planned_progress_pct}%</b></span>
                        <span>AI Auto: <b>${d.ai_automated_progress_pct}%</b></span>
                        <span>PM Appr: <b>${d.pm_approved_progress_pct}%</b></span>
                    </div>
                </div>
            `).join("");
        } catch (err) {
            console.error("Error loading discrepancies:", err);
        }
    }

    // ── 2. L4 SCHEDULE UPLOAD & BASELINE (Spec §3-§5) ─────────────────────────
    async loadBaselineStatus() {
        try {
            const res = await fetch("/api/schedule/baseline");
            const base = await res.json();
            this.state.currentBaseline = base;

            const verEl = document.getElementById("base-ver");
            const cntEl = document.getElementById("base-count");
            const wtEl  = document.getElementById("base-weight");

            if (base && base.status === "CONFIRMED") {
                if (verEl) verEl.innerText = `Rev ${base.version}.0 (${base.status})`;
                if (cntEl) cntEl.innerText = `${base.total_activities} Activities`;
                if (wtEl)  wtEl.innerText  = `${base.total_weight.toFixed(4)}%`;
            }
        } catch (err) {
            console.error("Error loading baseline status:", err);
        }
    }

    async uploadScheduleFile() {
        const fileInput = document.getElementById("schedule-file-input");
        if (!fileInput.files.length) {
            this.showToast("Please choose an Excel file (.xlsx) first!");
            return;
        }

        const file = fileInput.files[0];
        const formData = new FormData();
        formData.append("file", file);

        this.showToast("Parsing and validating L4 schedule...");
        try {
            const res = await fetch("/api/schedule/upload", {
                method: "POST",
                body: formData
            });
            const data = await res.json();

            if (!res.ok) {
                alert(`Upload failed: ${data.detail || 'Validation error'}`);
                return;
            }

            this.state.uploadedBaselineId = data.baseline_id;
            this.showToast(`L4 schedule parsed: ${data.summary.total_rows} rows evaluated.`);

            // Display Validation Summary
            document.getElementById("schedule-validation-panel").classList.remove("hidden");
            document.getElementById("val-total-rows").innerText = data.summary.total_rows;
            document.getElementById("val-valid-rows").innerText = data.summary.valid_rows;
            document.getElementById("val-errors").innerText = data.errors.length;
            document.getElementById("val-weight").innerText = `${data.summary.total_weight}%`;

            // Preview Table
            const tbody = document.getElementById("schedule-preview-tbody");
            if (tbody && data.preview_activities) {
                tbody.innerHTML = data.preview_activities.map(a => `
                    <tr class="hover:bg-blue-50/60">
                        <td class="py-2 px-3 font-mono font-bold text-black">${a.activity_code}</td>
                        <td class="py-2 px-3 font-bold text-black">${a.name}</td>
                        <td class="py-2 px-3 text-black">${a.building || 'Site'} L${a.floor_level}</td>
                        <td class="py-2 px-3 text-right font-mono text-black">${a.planned_qty}</td>
                        <td class="py-2 px-3 font-mono text-black">${a.uom}</td>
                        <td class="py-2 px-3 text-right font-mono font-bold text-black">${a.weightage}%</td>
                        <td class="py-2 px-3 text-black font-mono">${a.planned_start || '--'}</td>
                        <td class="py-2 px-3 text-black font-mono">${a.planned_finish || '--'}</td>
                    </tr>
                `).join("");
            }
        } catch (err) {
            console.error("Error uploading schedule:", err);
            alert("Upload failed. Please check network/file.");
        }
    }

    async confirmBaseline() {
        if (!this.state.uploadedBaselineId) {
            this.showToast("No uploaded baseline to confirm.");
            return;
        }

        try {
            const res = await fetch("/api/schedule/confirm", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    baseline_id: this.state.uploadedBaselineId,
                    confirmed_by: this.state.currentRole
                })
            });
            const data = await res.json();
            this.showToast(data.message || "Active L4 baseline confirmed!");
            await this.loadBaselineStatus();
            await this.loadActivities();
            await this.loadDashboardData();
        } catch (err) {
            console.error("Error confirming baseline:", err);
        }
    }

    // ── 3. MODE A: AI AUTOMATED PROGRESS STREAM (Spec §6-§11) ─────────────────
    async loadAIProgress() {
        try {
            const res = await fetch("/api/progress/comparison");
            const rows = await res.json();
            const tbody = document.getElementById("ai-progress-tbody");
            if (!tbody) return;

            tbody.innerHTML = rows.map(r => `
                <tr class="hover:bg-blue-50/60">
                    <td class="py-2.5 px-4 font-mono font-bold text-black">${r.activity_code}</td>
                    <td class="py-2.5 px-4 font-bold text-black">
                        <div>${r.name}</div>
                        <div class="text-[10px] text-gray-700">${r.stage_name || ''}</div>
                    </td>
                    <td class="py-2.5 px-4 text-black">${r.tower_name ? `${r.tower_name} L${r.floor_level}` : 'General Site'}</td>
                    <td class="py-2.5 px-4 text-center font-mono font-bold text-black">${r.planned_progress_pct}%</td>
                    <td class="py-2.5 px-4 text-center font-mono font-extrabold text-blue-800 bg-blue-50 border border-blue-200 rounded">
                        ${r.ai_automated_progress_pct}%
                    </td>
                    <td class="py-2.5 px-4 text-center font-mono text-black">
                        ${r.ai_automated_confidence ? `${(r.ai_automated_confidence * 100).toFixed(0)}%` : '--'}
                    </td>
                    <td class="py-2.5 px-4 text-center font-mono font-bold text-black">
                        ${(r.ai_automated_progress_pct - r.planned_progress_pct) >= 0 ? '+' : ''}${(r.ai_automated_progress_pct - r.planned_progress_pct).toFixed(1)}%
                    </td>
                    <td class="py-2.5 px-4 text-center font-bold text-black">
                        <span class="px-2 py-0.5 rounded border border-blue-300 bg-white">CAM-FIXED</span>
                    </td>
                </tr>
            `).join("");
        } catch (err) {
            console.error("Error loading AI progress:", err);
        }
    }

    // ── 4. MODE B: FIELD CAPTURE (Spec §12-§16, §34, §36) ─────────────────────
    populateFieldActivitySelect() {
        const select = document.getElementById("fld-activity-select");
        if (!select || !this.state.activities.length) return;

        select.innerHTML = this.state.activities.map(a => `
            <option value="${a.id}">
                ${a.activity_code} — ${a.name} (${a.tower_name || 'Site'} L${a.floor_level || 0})
            </option>
        `).join("");
    }

    onFieldPhotoPicked(event) {
        const file = event.target.files[0];
        if (!file) return;
        this.state.fieldPhotoFile = file;
        document.getElementById("fld-photo-name").innerText = file.name;

        const reader = new FileReader();
        reader.onload = (e) => {
            const preview = document.getElementById("fld-photo-preview");
            preview.src = e.target.result;
            document.getElementById("fld-photo-preview-container").classList.remove("hidden");
        };
        reader.readAsDataURL(file);
    }

    async submitFieldPhoto() {
        if (!this.state.fieldPhotoFile) {
            this.showToast("Please capture or choose a photograph first!");
            return;
        }

        const actId = document.getElementById("fld-activity-select").value;
        const towerId = document.getElementById("fld-tower").value;
        const floor = document.getElementById("fld-floor").value;
        const zone = document.getElementById("fld-zone").value;
        const qty = parseFloat(document.getElementById("fld-operator-qty").value) || 0.0;
        const remarks = document.getElementById("fld-operator-remarks").value;

        const formData = new FormData();
        formData.append("photo", this.state.fieldPhotoFile);
        formData.append("activity_id", actId);
        formData.append("tower_id", towerId);
        formData.append("floor_level", floor);
        formData.append("zone", zone);
        formData.append("operator_name", this.state.currentRole);
        formData.append("operator_quantity", qty);
        formData.append("operator_remarks", remarks);

        this.showToast("AI evaluating photograph against L4 schedule...");

        try {
            const res = await fetch("/api/field/photos", {
                method: "POST",
                body: formData
            });
            const data = await res.json();

            const resultBox = document.getElementById("field-validation-result-box");
            resultBox.classList.remove("hidden");

            if (data.status === "REJECTED_BY_AI") {
                resultBox.className = "p-4 rounded-xl border-2 border-black bg-white space-y-2";
                resultBox.innerHTML = `
                    <div class="font-bold text-black text-sm flex items-center gap-2">
                        <i class="fas fa-circle-xmark text-blue-800"></i> AI Image Validation: REJECTED
                    </div>
                    <div class="text-xs text-black font-semibold">${data.validation.rejection_reason}</div>
                    <div class="text-[11px] text-gray-700">Confidence: ${(data.validation.validation_confidence * 100).toFixed(0)}% • Action: <b>${data.validation.recommended_action}</b></div>
                `;
            } else {
                resultBox.className = "p-4 rounded-xl border-2 border-blue-400 bg-blue-50/50 space-y-2";
                resultBox.innerHTML = `
                    <div class="font-bold text-black text-sm flex items-center gap-2">
                        <i class="fas fa-circle-check text-blue-700"></i> AI Validation: VALID CONSTRUCTION EVIDENCE
                    </div>
                    <div class="grid grid-cols-3 gap-2 text-xs font-bold text-black pt-1">
                        <div class="p-2 bg-white border border-blue-200 rounded">Construction Scene: <b>DETECTED</b></div>
                        <div class="p-2 bg-white border border-blue-200 rounded">Context Relevant: <b>VERIFIED</b></div>
                        <div class="p-2 bg-white border border-blue-200 rounded">AI Visual Progress: <b>${data.ai_evaluation.ai_progress_percent}%</b></div>
                    </div>
                    <div class="text-xs font-bold text-blue-900 pt-2 flex items-center justify-between">
                        <span>Submitted to PM Review Queue (ID: ${data.pm_review_id})</span>
                        <button onclick="window.app.switchView('pm-reviews')" class="px-3 py-1 bg-blue-700 text-white rounded font-bold">View in PM Queue</button>
                    </div>
                `;
                this.showToast("Field observation successfully submitted to PM Review Queue!");
                await this.loadPMReviews('PENDING');
            }
        } catch (err) {
            console.error("Error submitting field photo:", err);
            alert("Submission error. Please check backend connection.");
        }
    }

    // ── 5. MODE B: PM REVIEW QUEUE (Spec §17-§18, §37) ────────────────────────
    async loadPMReviews(status = 'PENDING') {
        try {
            const res = await fetch(`/api/pm/reviews?status=${status}`);
            const reviews = await res.json();
            this.state.pmReviews = reviews;

            const badge = document.getElementById("nav-pending-pm-badge");
            if (badge && status === 'PENDING') {
                badge.innerText = reviews.length;
            }

            const container = document.getElementById("pm-reviews-container");
            if (!container) return;

            if (!reviews.length) {
                container.innerHTML = `<div class="p-8 bg-white text-black text-center font-bold border border-blue-200 rounded-xl">No ${status.toLowerCase()} review items found.</div>`;
                return;
            }

            container.innerHTML = reviews.map(r => `
                <div class="p-5 bg-white border-2 border-blue-200 rounded-xl shadow-sm space-y-4">
                    <div class="flex items-start justify-between pb-3 border-b border-blue-100">
                        <div>
                            <div class="text-xs font-bold text-black">${r.activity_code} — ${r.activity_name || ''}</div>
                            <div class="text-[11px] text-gray-700 font-bold">${r.tower_id || 'Site'} Level ${r.floor_level} (${r.zone}) • Submitted by ${r.field_operator}</div>
                        </div>
                        <span class="text-xs font-bold px-2.5 py-1 rounded border border-blue-300 bg-blue-50 text-black">
                            Status: ${r.pm_status}
                        </span>
                    </div>

                    <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
                        <!-- Evidence Photo Thumbnail -->
                        <div class="h-44 bg-blue-50 border border-blue-300 rounded-lg overflow-hidden">
                            <img src="${r.image_url}" class="w-full h-full object-cover" alt="Evidence">
                        </div>

                        <!-- L4 Baseline vs Field Observation Data -->
                        <div class="space-y-2 text-xs">
                            <div class="p-2.5 bg-blue-50/60 border border-blue-200 rounded">
                                <div class="text-gray-700 font-bold">L4 Planned Target:</div>
                                <div class="font-extrabold text-black font-mono text-sm">${r.planned_qty || 150} ${r.uom || 'm³'}</div>
                            </div>
                            <div class="p-2.5 bg-white border border-blue-300 rounded">
                                <div class="text-gray-700 font-bold">AI Visual Estimate (Spec §36):</div>
                                <div class="font-extrabold text-blue-800 font-mono text-sm">${r.ai_progress_percent}% (Confidence: ${(r.ai_confidence * 100).toFixed(0)}%)</div>
                            </div>
                            <div class="p-2.5 bg-white border border-blue-300 rounded">
                                <div class="text-gray-700 font-bold">Operator Measured Quantity:</div>
                                <div class="font-extrabold text-black font-mono text-sm">${r.operator_quantity} ${r.operator_uom}</div>
                            </div>
                        </div>

                        <!-- PM Decision Panel -->
                        <div class="flex flex-col justify-between p-3 bg-blue-50/40 border border-blue-200 rounded-lg text-xs">
                            <div>
                                <div class="font-bold text-black mb-1">Operator Notes:</div>
                                <div class="text-gray-800 italic">"${r.operator_remarks || 'Work completed per plan.'}"</div>
                            </div>
                            ${r.pm_status === 'PENDING' ? `
                                <div class="flex flex-col gap-2 pt-3">
                                    <button onclick="window.app.approvePMReview('${r.id}')"
                                            class="w-full py-2 bg-blue-700 hover:bg-blue-800 text-white font-bold rounded shadow-sm transition flex items-center justify-center gap-1.5">
                                        <i class="fas fa-check"></i> Approve Observation (${r.operator_quantity} ${r.operator_uom})
                                    </button>
                                    <button onclick="window.app.openPMModifyModal('${r.id}', ${r.operator_quantity})"
                                            class="w-full py-1.5 bg-white hover:bg-blue-50 text-black border border-blue-400 font-bold rounded transition">
                                        <i class="fas fa-pen-to-square"></i> Modify Quantity &amp; Approve
                                    </button>
                                    <button onclick="window.app.openPMRejectModal('${r.id}')"
                                            class="w-full py-1.5 bg-white hover:bg-gray-100 text-black border border-black font-bold rounded transition">
                                        <i class="fas fa-xmark"></i> Reject / Request Retake
                                    </button>
                                </div>
                            ` : `
                                <div class="p-2 bg-white border border-blue-300 rounded font-bold text-black">
                                    Approved by ${r.pm_reviewer || 'PM'}: <b>${r.pm_approved_quantity} ${r.operator_uom}</b> (${r.pm_approved_progress_percent}%)
                                </div>
                            `}
                        </div>
                    </div>
                </div>
            `).join("");
        } catch (err) {
            console.error("Error loading PM reviews:", err);
        }
    }

    async approvePMReview(reviewId) {
        try {
            const res = await fetch(`/api/pm/reviews/${reviewId}/approve`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ reviewer_name: this.state.currentRole })
            });
            const data = await res.json();
            this.showToast(`Approved! Official PM Progress recorded at ${data.pm_approved_progress_percent}%`);
            await this.loadPMReviews('PENDING');
            await this.loadDashboardData();
        } catch (err) {
            console.error("Error approving review:", err);
        }
    }

    openPMModifyModal(reviewId, currentQty) {
        document.getElementById("mod-review-id").value = reviewId;
        document.getElementById("mod-qty-input").value = currentQty;
        document.getElementById("pm-modify-modal").classList.remove("hidden");
    }

    async submitPMModify() {
        const reviewId = document.getElementById("mod-review-id").value;
        const modQty = parseFloat(document.getElementById("mod-qty-input").value);
        const reason = document.getElementById("mod-reason-input").value;

        try {
            const res = await fetch(`/api/pm/reviews/${reviewId}/modify`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    reviewer_name: this.state.currentRole,
                    modified_quantity: modQty,
                    override_reason: reason
                })
            });
            const data = await res.json();
            this.showToast(`Modified & Approved at ${data.pm_approved_quantity} (${data.pm_approved_progress_percent}%)`);
            document.getElementById("pm-modify-modal").classList.add("hidden");
            await this.loadPMReviews('PENDING');
            await this.loadDashboardData();
        } catch (err) {
            console.error("Error modifying review:", err);
        }
    }

    openPMRejectModal(reviewId) {
        document.getElementById("reject-review-id").value = reviewId;
        document.getElementById("pm-reject-modal").classList.remove("hidden");
    }

    async submitPMReject() {
        const reviewId = document.getElementById("reject-review-id").value;
        const action = document.getElementById("reject-action-select").value;
        const reason = document.getElementById("reject-reason-input").value;

        try {
            const res = await fetch(`/api/pm/reviews/${reviewId}/reject`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    reviewer_name: this.state.currentRole,
                    action: action,
                    reason: reason
                })
            });
            const data = await res.json();
            this.showToast(`Review rejected: ${data.action}`);
            document.getElementById("pm-reject-modal").classList.add("hidden");
            await this.loadPMReviews('PENDING');
            await this.loadDashboardData();
        } catch (err) {
            console.error("Error rejecting review:", err);
        }
    }

    // ── 6. MODE B: PM-APPROVED PROGRESS LIST (Spec §18) ───────────────────────
    async loadPMApprovedProgress() {
        try {
            const res = await fetch("/api/pm/reviews?status=APPROVED");
            const approved = await res.json();
            const tbody = document.getElementById("pm-progress-tbody");
            if (!tbody) return;

            if (!approved.length) {
                tbody.innerHTML = `<tr><td colspan="9" class="py-6 text-center text-black font-bold">No approved records yet. Approve items in PM Review Queue.</td></tr>`;
                return;
            }

            tbody.innerHTML = approved.map(r => `
                <tr class="hover:bg-blue-50/60">
                    <td class="py-3 px-4 font-bold text-black">${r.activity_code} — ${r.activity_name || ''}</td>
                    <td class="py-3 px-4 text-black">${r.tower_id || 'Site'} L${r.floor_level} (${r.zone})</td>
                    <td class="py-3 px-4 text-center font-mono text-black">${r.planned_qty || 150} ${r.uom || 'm³'}</td>
                    <td class="py-3 px-4 text-center font-mono text-blue-800">${r.ai_progress_percent}%</td>
                    <td class="py-3 px-4 text-center font-mono text-black">${r.operator_quantity} ${r.operator_uom}</td>
                    <td class="py-3 px-4 text-center font-mono font-bold text-black">${r.pm_approved_quantity} ${r.operator_uom}</td>
                    <td class="py-3 px-4 text-center font-mono font-extrabold text-black bg-blue-50 border border-blue-300 rounded">${r.pm_approved_progress_percent}%</td>
                    <td class="py-3 px-4 font-bold text-black">${r.pm_reviewer || 'PM'}</td>
                    <td class="py-3 px-4 font-mono text-[10px] text-gray-700">${r.reviewed_at ? r.reviewed_at.slice(0, 16).replace('T', ' ') : '--'}</td>
                </tr>
            `).join("");
        } catch (err) {
            console.error("Error loading PM approved progress:", err);
        }
    }

    // ── 7. WBS ACTIVITIES LIST ────────────────────────────────────────────────
    async loadActivities() {
        try {
            const res = await fetch("/api/activities");
            this.state.activities = await res.json();
            this.renderActivitiesTable();
            this.populateFieldActivitySelect();
        } catch (err) {
            console.error("Error loading activities:", err);
        }
    }

    renderActivitiesTable() {
        const tbody = document.getElementById("activities-tbody");
        if (!tbody) return;

        tbody.innerHTML = this.state.activities.map(a => `
            <tr class="hover:bg-blue-50/60 transition">
                <td class="py-3 px-4 font-mono text-xs font-bold text-blue-800">${a.activity_code}</td>
                <td class="py-3 px-4 text-sm font-bold text-black">
                    <div>${a.name}</div>
                    <div class="text-xs text-gray-600 font-normal">${a.stage_name || ''}</div>
                </td>
                <td class="py-3 px-4 text-xs font-semibold text-black">
                    ${a.tower_name ? `${a.tower_name} L${a.floor_level}` : 'General Site'}
                </td>
                <td class="py-3 px-4 text-xs font-mono text-right text-black font-bold">
                    ${a.planned_qty} ${a.uom}
                </td>
                <td class="py-3 px-4 text-xs font-mono text-right text-black">
                    ${a.reported_qty} ${a.uom}
                </td>
                <td class="py-3 px-4 text-xs font-mono text-right font-bold text-black">
                    ${a.accepted_qty} ${a.uom}
                </td>
                <td class="py-3 px-4 text-xs font-mono text-center font-bold text-black">
                    ${a.weightage}%
                </td>
                <td class="py-3 px-4 text-center">
                    <span class="px-2 py-0.5 rounded text-xs font-bold border border-blue-300 bg-blue-50 text-black">
                        ${a.status}
                    </span>
                </td>
                <td class="py-3 px-4 text-center space-x-1">
                    <button onclick="window.app.openReportModal('${a.id}')" class="px-2.5 py-1 bg-white hover:bg-blue-50 text-black border border-blue-300 text-xs font-bold rounded transition">
                        Report
                    </button>
                    <button onclick="window.app.openInspectModal('${a.id}')" class="px-2.5 py-1 bg-blue-700 hover:bg-blue-800 text-white text-xs font-bold rounded transition">
                        QA Clearance
                    </button>
                </td>
            </tr>
        `).join("");
    }

    // ── 8. FLOOR HEATMAP ──────────────────────────────────────────────────────
    renderFloorHeatmap() {
        const heatmapContainer = document.getElementById("floor-heatmap-container");
        if (!heatmapContainer || !this.state.dashboardData) return;

        const heatmapData = this.state.dashboardData.metrics.floor_heatmap;
        let html = '<div class="grid grid-cols-1 md:grid-cols-2 gap-6">';

        ["TOW-A", "TOW-B"].forEach(towerId => {
            const towerName = towerId === "TOW-A" ? "Tower A (20 Levels)" : "Tower B (15 Levels)";
            const maxLvl = towerId === "TOW-A" ? 20 : 15;

            html += `
                <div class="glass-card p-4 rounded-xl border border-blue-200">
                    <h3 class="font-bold text-sm text-black mb-3 flex items-center justify-between">
                        <span><i class="fas fa-building text-blue-700 mr-2"></i> ${towerName}</span>
                        <span class="text-xs bg-blue-50 text-black font-bold px-2 py-0.5 rounded border border-blue-300">Floor Matrix</span>
                    </h3>
                    <div class="space-y-1">
            `;

            for (let lvl = maxLvl; lvl >= 1; lvl--) {
                const floorCell = heatmapData.find(f => f.tower_id === towerId && f.floor_level === lvl) || { progress_pct: 0, ai_pct: 0, pm_pct: 0 };
                const pct = floorCell.progress_pct || 0;
                const aiPct = floorCell.ai_pct || 0;
                const pmPct = floorCell.pm_pct || 0;

                let colorClass = "level-0-20";
                if (pct > 20 && pct <= 50) colorClass = "level-21-50";
                else if (pct > 50 && pct <= 75) colorClass = "level-51-75";
                else if (pct > 75 && pct < 100) colorClass = "level-76-99";
                else if (pct >= 100) colorClass = "level-100";

                html += `
                    <div class="heatmap-cell ${colorClass} p-1.5 rounded border flex items-center justify-between text-xs font-bold text-black">
                        <span class="w-16 font-mono text-black">Level ${lvl}</span>
                        <div class="flex-1 mx-3 bg-white rounded-full h-2 overflow-hidden border border-blue-200">
                            <div class="h-2 bg-blue-600 rounded-full" style="width: ${pct}%"></div>
                        </div>
                        <span class="w-24 text-right font-mono text-[11px] text-black">AI:${aiPct}% | PM:${pmPct}%</span>
                    </div>
                `;
            }

            html += `</div></div>`;
        });

        html += '</div>';
        heatmapContainer.innerHTML = html;
    }

    // ── 9. FIXED CAMERAS & MODE A SCAN ────────────────────────────────────────
    async loadCameras() {
        try {
            const res = await fetch("/api/cameras");
            this.state.cameras = await res.json();
            this.renderCamerasGrid();
        } catch (err) {
            console.error("Error loading cameras:", err);
        }
    }

    renderCamerasGrid() {
        const grid = document.getElementById("cameras-grid");
        if (!grid) return;

        grid.innerHTML = this.state.cameras.map(c => `
            <div class="glass-card rounded-xl overflow-hidden border border-blue-200 group">
                <div class="relative h-44 bg-blue-50 overflow-hidden">
                    <img src="${c.last_image_url}" class="w-full h-full object-cover group-hover:scale-105 transition duration-500" alt="${c.camera_code}">
                    <div class="absolute inset-0 camera-frame-overlay p-3 flex flex-col justify-between">
                        <div class="flex items-center justify-between">
                            <span class="bg-blue-700 text-white text-[10px] font-bold px-2 py-0.5 rounded flex items-center gap-1">
                                <span class="w-2 h-2 rounded-full bg-white animate-pulse"></span> LIVE
                            </span>
                            <span class="bg-white text-black text-xs font-mono font-bold px-2 py-0.5 rounded border border-blue-300">
                                ${c.camera_code}
                            </span>
                        </div>
                        <div class="text-xs text-black font-bold">
                            <div>${c.location}</div>
                            <div class="text-gray-700 text-[10px] font-mono">Coverage: ${c.coverage_floors || 'Core'}</div>
                        </div>
                    </div>
                </div>
                <div class="p-3 bg-white border-t border-blue-200 flex items-center justify-between text-xs">
                    <span class="text-gray-700 font-bold">Mode A: Active</span>
                    <button onclick="window.app.runCameraAI('${c.id}')"
                            class="px-3 py-1 bg-blue-700 hover:bg-blue-800 text-white font-bold rounded transition flex items-center gap-1.5 shadow-sm">
                        <i class="fas fa-brain text-xs"></i> AI Automated Scan
                    </button>
                </div>
            </div>
        `).join("");
    }

    async runCameraAI(cameraId) {
        try {
            this.showToast("Mode A: Running automated AI delta scan on camera feed...");
            const res = await fetch(`/api/cameras/${cameraId}/analyze`);
            const analysis = await res.json();

            const modal = document.getElementById("cv-analysis-modal");
            document.getElementById("cv-cam-code").innerText = analysis.camera_code;
            document.getElementById("cv-detected-element").innerText = `${analysis.activity_code} — ${analysis.activity_name}`;
            document.getElementById("cv-prev-progress").innerText = `${analysis.previous_estimated_progress}%`;
            document.getElementById("cv-curr-progress").innerText = `${analysis.ai_progress_percent}%`;
            document.getElementById("cv-delta").innerText = `+${analysis.delta_change}%`;
            document.getElementById("cv-confidence").innerText = `${(analysis.confidence * 100).toFixed(0)}%`;

            const flagsContainer = document.getElementById("cv-safety-flags");
            flagsContainer.innerHTML = analysis.safety_flags.map(f => `
                <li class="flex items-center gap-2">
                    <i class="fas fa-shield text-blue-700"></i> ${f}
                </li>
            `).join("");

            modal.classList.remove("hidden");

            // Refresh dashboard so Mode A automated progress is updated instantly
            await this.loadDashboardData();
        } catch (err) {
            console.error("Error analyzing camera:", err);
        }
    }

    // ── 10. TIME-LAPSE ────────────────────────────────────────────────────────
    async loadTimeLapse() {
        try {
            const res = await fetch("/api/timelapse?tower_id=TOW-A&floor_level=12");
            const data = await res.json();
            document.getElementById("timelapse-location").innerText = data.location;
            document.getElementById("timelapse-ai-summary").innerText = data.ai_time_lapse_summary;

            const container = document.getElementById("timelapse-frames-container");
            if (!container) return;

            container.innerHTML = data.timeline.map(frame => `
                <div class="glass-card rounded-lg overflow-hidden border border-blue-200">
                    <div class="h-28 bg-blue-50 relative">
                        <img src="${frame.image_url}" class="w-full h-full object-cover">
                        <div class="absolute bottom-1 left-1 bg-white text-black text-[10px] px-1.5 py-0.5 rounded font-mono font-bold border border-blue-300">
                            Est: ${frame.estimated_progress}%
                        </div>
                    </div>
                    <div class="p-2 text-xs">
                        <div class="font-bold text-black">${frame.day_label}</div>
                        <div class="text-[10px] text-gray-700 font-mono">${frame.date}</div>
                    </div>
                </div>
            `).join("");
        } catch (err) {
            console.error("Error loading time lapse:", err);
        }
    }

    // ── 11. AUXILIARY DATA (RFIs, NCRs, Safety, Materials) ────────────────────
    async loadAuxiliaryData() {
        try {
            const [rfis, ncrs, safety, materials] = await Promise.all([
                fetch("/api/rfis").then(r => r.json()),
                fetch("/api/ncrs").then(r => r.json()),
                fetch("/api/safety").then(r => r.json()),
                fetch("/api/materials").then(r => r.json())
            ]);

            this.state.rfis = rfis;
            this.state.ncrs = ncrs;
            this.state.safety = safety;
            this.state.materials = materials;

            this.renderRFIs();
            this.renderNCRs();
            this.renderSafety();
            this.renderMaterials();
        } catch (err) {
            console.error("Error loading auxiliary data:", err);
        }
    }

    renderRFIs() {
        const tbody = document.getElementById("rfis-tbody");
        if (!tbody) return;
        tbody.innerHTML = this.state.rfis.map(r => `
            <tr class="hover:bg-blue-50/60">
                <td class="py-3 px-4 font-mono font-bold text-blue-800">${r.rfi_number}</td>
                <td class="py-3 px-4 font-bold text-black">${r.subject}</td>
                <td class="py-3 px-4 text-black font-semibold">${r.raised_by} → ${r.assigned_to}</td>
                <td class="py-3 px-4 font-bold text-black">${r.priority}</td>
                <td class="py-3 px-4"><span class="px-2 py-0.5 rounded border border-blue-300 bg-blue-50 font-bold text-black">${r.status}</span></td>
            </tr>
        `).join("");
    }

    renderNCRs() {
        const tbody = document.getElementById("ncrs-tbody");
        if (!tbody) return;
        tbody.innerHTML = this.state.ncrs.map(n => `
            <tr class="hover:bg-blue-50/60">
                <td class="py-3 px-4 font-mono font-bold text-black">${n.ncr_number}</td>
                <td class="py-3 px-4 font-bold text-black">${n.location}</td>
                <td class="py-3 px-4 text-black">${n.description}</td>
                <td class="py-3 px-4 font-bold text-black">${n.severity}</td>
                <td class="py-3 px-4 text-black font-semibold">${n.contractor}</td>
                <td class="py-3 px-4"><span class="px-2 py-0.5 rounded border border-black bg-white font-bold text-black">${n.status}</span></td>
            </tr>
        `).join("");
    }

    renderSafety() {
        const tbody = document.getElementById("safety-tbody");
        if (!tbody) return;
        tbody.innerHTML = this.state.safety.map(s => `
            <tr class="hover:bg-blue-50/60">
                <td class="py-3 px-4 font-mono font-bold text-black">${s.id}</td>
                <td class="py-3 px-4 text-black font-semibold">${s.tower_id} L${s.floor_level} (${s.zone})</td>
                <td class="py-3 px-4 font-bold text-black">${s.description}</td>
                <td class="py-3 px-4">
                    ${s.is_ai_flagged ? `<span class="px-2 py-0.5 rounded border border-blue-400 bg-blue-100 font-bold text-black"><i class="fas fa-brain text-blue-700"></i> AI Flagged (${(s.ai_confidence * 100).toFixed(0)}%)</span>` : '<span class="font-semibold text-black">Manual</span>'}
                </td>
                <td class="py-3 px-4"><span class="px-2 py-0.5 rounded border border-blue-300 bg-blue-50 font-bold text-black">${s.status}</span></td>
            </tr>
        `).join("");
    }

    renderMaterials() {
        const tbody = document.getElementById("materials-tbody");
        if (!tbody) return;
        tbody.innerHTML = this.state.materials.map(m => `
            <tr class="hover:bg-blue-50/60">
                <td class="py-3 px-4 font-mono font-bold text-blue-800">${m.code}</td>
                <td class="py-3 px-4 font-bold text-black">${m.name}</td>
                <td class="py-3 px-4 text-right font-mono font-bold text-black">${m.current_stock} ${m.uom}</td>
                <td class="py-3 px-4 text-right font-mono text-black">${m.reorder_level} ${m.uom}</td>
                <td class="py-3 px-4 text-black font-semibold">${m.supplier}</td>
                <td class="py-3 px-4 text-center">
                    ${m.shortage_warning ? `<span class="px-2 py-0.5 rounded border border-blue-400 bg-blue-100 font-bold text-black animate-pulse">Shortage Warning</span>` : `<span class="px-2 py-0.5 rounded border border-blue-200 bg-white font-bold text-black">Sufficient</span>`}
                </td>
            </tr>
        `).join("");
    }

    // ── 12. QUANTITY REPORTING & QA/QC INSPECT MODALS ─────────────────────────
    openReportModal(activityId) {
        const act = this.state.activities.find(a => a.id === activityId);
        if (!act) return;
        document.getElementById("report-modal-act-id").value = act.id;
        document.getElementById("report-modal-title").innerText = `Report Progress: ${act.name}`;
        document.getElementById("report-modal-uom").innerText = act.uom;
        document.getElementById("report-modal-qty").value = act.reported_qty || 0;
        document.getElementById("report-modal").classList.remove("hidden");
    }

    async submitReportModal() {
        const actId = document.getElementById("report-modal-act-id").value;
        const reportedQty = parseFloat(document.getElementById("report-modal-qty").value);

        try {
            const res = await fetch(`/api/activities/${actId}/report`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    reported_qty: reportedQty,
                    submitted_by: this.state.currentRole,
                    role: this.state.currentRole
                })
            });
            const data = await res.json();
            this.showToast(data.message);
            document.getElementById("report-modal").classList.add("hidden");
            await this.loadActivities();
            await this.loadDashboardData();
        } catch (err) {
            console.error("Error submitting report:", err);
        }
    }

    openInspectModal(activityId) {
        const act = this.state.activities.find(a => a.id === activityId);
        if (!act) return;
        document.getElementById("inspect-modal-act-id").value = act.id;
        document.getElementById("inspect-modal-title").innerText = `QA/QC Inspection: ${act.name}`;
        document.getElementById("inspect-modal-planned").innerText = `${act.planned_qty} ${act.uom}`;
        document.getElementById("inspect-modal-reported").innerText = `${act.reported_qty} ${act.uom}`;
        document.getElementById("inspect-modal-accepted-qty").value = act.reported_qty || act.planned_qty;
        document.getElementById("inspect-modal").classList.remove("hidden");
    }

    async submitInspectModal() {
        const actId = document.getElementById("inspect-modal-act-id").value;
        const acceptedQty = parseFloat(document.getElementById("inspect-modal-accepted-qty").value);

        try {
            const res = await fetch(`/api/activities/${actId}/inspect`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    inspected_qty: acceptedQty,
                    accepted_qty: acceptedQty,
                    inspector: this.state.currentRole,
                    status: "Accepted"
                })
            });
            const data = await res.json();
            this.showToast(data.message);
            document.getElementById("inspect-modal").classList.add("hidden");
            await this.loadActivities();
            await this.loadDashboardData();
        } catch (err) {
            console.error("Error submitting inspection:", err);
        }
    }

    // ── 13. AI AGENT CONSOLE ──────────────────────────────────────────────────
    async sendAIQuery(presetQuery = null) {
        const inputEl = document.getElementById("ai-query-input");
        const query = presetQuery || inputEl.value.trim();
        if (!query) return;

        if (!presetQuery) inputEl.value = "";
        this.state.aiChatHistory.push({ sender: "user", text: query });
        this.renderAIChat();

        try {
            const res = await fetch("/api/ai/query", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ query: query, user_role: this.state.currentRole })
            });
            const responseData = await res.json();
            this.state.aiChatHistory.push({
                sender: "ai",
                text: responseData.response,
                action_type: responseData.action_type,
                payload: responseData.payload
            });
            this.renderAIChat();
        } catch (err) {
            console.error("Error with AI query:", err);
        }
    }

    renderAIChat() {
        const chatContainer = document.getElementById("ai-chat-messages");
        if (!chatContainer) return;

        chatContainer.innerHTML = this.state.aiChatHistory.map(msg => `
            <div class="flex gap-3 ${msg.sender === 'user' ? 'justify-end' : 'justify-start'}">
                ${msg.sender === 'ai' ? '<div class="w-8 h-8 rounded-full bg-blue-700 flex items-center justify-center text-white text-xs font-bold shrink-0"><i class="fas fa-robot"></i></div>' : ''}
                <div class="max-w-[80%] rounded-xl p-3 text-sm font-semibold ${msg.sender === 'user' ? 'bg-blue-700 text-white' : 'bg-white border border-blue-300 text-black shadow-sm'}">
                    <div>${this.formatMarkdown(msg.text)}</div>
                </div>
                ${msg.sender === 'user' ? '<div class="w-8 h-8 rounded-full bg-blue-100 border border-blue-300 flex items-center justify-center text-black text-xs font-bold shrink-0"><i class="fas fa-user"></i></div>' : ''}
            </div>
        `).join("");

        chatContainer.scrollTop = chatContainer.scrollHeight;
    }

    formatMarkdown(text) {
        if (!text) return "";
        return text
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/\n/g, '<br>');
    }

    async generateDailyReport() {
        try {
            const res = await fetch("/api/ai/daily-report");
            const report = await res.json();
            this.state.aiChatHistory.push({
                sender: "ai",
                text: `**${report.title}**\n\n` +
                      `• **Mode A (AI Automated Progress)**: ${this.state.dashboardData.metrics.ai_automated_progress}%\n` +
                      `• **Mode B (PM Approved Progress)**: ${this.state.dashboardData.metrics.pm_approved_progress}%\n` +
                      `• **Planned Target**: ${this.state.dashboardData.metrics.planned_progress}%\n` +
                      `• **Highlights**: ${report.today_highlights.join(" | ")}`
            });
            this.renderAIChat();
        } catch (err) {
            console.error("Error generating daily report:", err);
        }
    }

    async checkModelStatus() {
        try {
            const res = await fetch("/api/settings/model");
            const data = await res.json();
            const headerBtn = document.getElementById("header-gemini-status");
            const modalBadge = document.getElementById("gemini-modal-badge");
            if (headerBtn) {
                headerBtn.innerText = data.is_live ? "AI: Gemini Live" : "AI: Gemini (Config)";
            }
            if (modalBadge) {
                modalBadge.innerText = data.is_live ? "Active: " + data.model_name : "Status: Awaiting Key";
            }
        } catch (err) {
            console.error("Error checking model status:", err);
        }
    }

    openGeminiSettingsModal() {
        this.checkModelStatus();
        document.getElementById("gemini-settings-modal").classList.remove("hidden");
    }

    async saveGeminiKey() {
        const input = document.getElementById("gemini-api-key-input");
        const key = input.value.trim();
        if (!key) {
            alert("Please paste your Gemini API key.");
            return;
        }
        try {
            const res = await fetch("/api/settings/gemini-key", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ api_key: key })
            });
            const data = await res.json();
            if (res.ok) {
                document.getElementById("gemini-status-message").innerHTML = `<span class="text-blue-700">✓ ${data.message}</span>`;
                this.showToast("Google Gemini 2.5 Flash activated successfully!");
                this.checkModelStatus();
                setTimeout(() => {
                    document.getElementById("gemini-settings-modal").classList.add("hidden");
                }, 1500);
            } else {
                alert(data.detail || "Failed to save key");
            }
        } catch (err) {
            console.error("Error saving Gemini key:", err);
        }
    }

    setupEventListeners() {
        const aiInput = document.getElementById("ai-query-input");
        if (aiInput) {
            aiInput.addEventListener("keydown", (e) => {
                if (e.key === "Enter") this.sendAIQuery();
            });
        }
        const scheduleFileInput = document.getElementById("schedule-file-input");
        if (scheduleFileInput) {
            scheduleFileInput.addEventListener("change", (e) => {
                if (e.target.files.length) {
                    document.getElementById("schedule-selected-filename").innerText = `Selected: ${e.target.files[0].name}`;
                }
            });
        }
    }

    showToast(msg) {
        const toast = document.createElement("div");
        toast.className = "fixed bottom-5 right-5 bg-blue-700 text-white text-xs font-bold px-4 py-3 rounded-lg shadow-2xl z-50 flex items-center gap-2 border border-blue-400";
        toast.innerHTML = `<i class="fas fa-circle-info"></i> ${msg}`;
        document.body.appendChild(toast);
        setTimeout(() => toast.remove(), 3500);
    }

    openProductVideoModal() {
        const modal = document.getElementById("product-video-modal");
        const player = document.getElementById("promo-video-player");
        if (modal) {
            modal.classList.remove("hidden");
            if (player) {
                player.currentTime = 0;
                player.play().catch(e => console.log("Autoplay prevented:", e));
            }
        }
    }

    closeProductVideoModal() {
        const modal = document.getElementById("product-video-modal");
        const player = document.getElementById("promo-video-player");
        if (modal) {
            modal.classList.add("hidden");
            if (player) {
                player.pause();
            }
        }
    }
}
