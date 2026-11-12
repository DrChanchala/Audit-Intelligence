"""
PyCray_SiteIQ — Progress Engine
Computes all four progress streams per the dual-mode architecture:
  1. Planned Progress      — derived from baseline dates vs today
  2. AI Automated Progress — from static camera AI observations (Mode A)
  3. Field Observed Progress — from field operator submissions, pre-PM (Mode B)
  4. PM Approved Progress  — PM-approved field observations (Mode B final)
"""
import sqlite3
from datetime import datetime, date
from database import get_db


def calculate_planned_progress(planned_start, planned_finish, today=None):
    """
    Returns planned % based on how far through the planned duration we are today.
    Returns 0 if not started, 100 if past finish.
    """
    if today is None:
        today = date.today()
    if not planned_start or not planned_finish:
        return 0.0
    try:
        ps = datetime.strptime(str(planned_start)[:10], "%Y-%m-%d").date()
        pf = datetime.strptime(str(planned_finish)[:10], "%Y-%m-%d").date()
    except Exception:
        return 0.0

    if today < ps:
        return 0.0
    if today >= pf:
        return 100.0
    total_days = (pf - ps).days
    if total_days <= 0:
        return 100.0
    elapsed = (today - ps).days
    return round(min((elapsed / total_days) * 100.0, 100.0), 2)


def calculate_activity_progress(planned_qty, accepted_qty, reported_qty=0.0):
    """
    Classic quantity-based physical progress.
    Returns (accepted_pct, reported_pct).
    """
    if planned_qty <= 0:
        return 0.0, 0.0
    acc_pct = (accepted_qty / planned_qty) * 100.0
    rep_pct = (reported_qty / planned_qty) * 100.0
    return round(acc_pct, 2), round(rep_pct, 2)


def compute_project_metrics(project_id="PROJ-001"):
    """
    Computes all four weighted progress streams for the entire project,
    plus per-stage, per-tower, per-floor rollups for the dashboard.
    """
    conn = get_db()
    cursor = conn.cursor()
    today = date.today()

    # ── Load all activities ───────────────────────────────────────────────
    cursor.execute("""
        SELECT a.*, s.name as stage_name, s.weightage as stage_weightage, t.name as tower_name
        FROM activities a
        JOIN stages s ON a.stage_id = s.id
        LEFT JOIN towers t ON a.tower_id = t.id
        WHERE a.project_id = ?
    """, (project_id,))
    activities = cursor.fetchall()

    # ── Accumulators ─────────────────────────────────────────────────────
    total_weight = 0.0

    earned_planned      = 0.0  # Weighted planned progress
    earned_ai_auto      = 0.0  # Weighted AI automated progress
    earned_field_obs    = 0.0  # Weighted field observed progress
    earned_pm_approved  = 0.0  # Weighted PM approved progress
    earned_qa_accepted  = 0.0  # Legacy: QA/QC accepted (accepted_qty)

    total_planned_value = 0.0
    total_earned_value  = 0.0

    stage_metrics = {}
    tower_metrics = {}
    floor_metrics = {}

    for act in activities:
        weight           = float(act['weightage'] or 0.0)
        planned_qty      = float(act['planned_qty'] or 0.0)
        accepted_qty     = float(act['accepted_qty'] or 0.0)
        reported_qty     = float(act['reported_qty'] or 0.0)
        unit_cost        = float(act['unit_cost'] or 0.0)
        stage_id         = act['stage_id']
        stage_name       = act['stage_name']
        tower_id         = act['tower_id'] or 'General'
        tower_name       = act['tower_name'] or 'General Site'
        floor_level      = act['floor_level'] or 0

        # ── 4 progress streams ────────────────────────────────────────────
        planned_pct      = float(act['planned_progress_pct'] or
                                  calculate_planned_progress(act['planned_start'], act['planned_finish'], today))
        ai_auto_pct      = float(act['ai_automated_progress_pct'] or 0.0)
        field_obs_pct    = float(act['field_observed_progress_pct'] or 0.0)
        pm_appr_pct      = float(act['pm_approved_progress_pct'] or 0.0)
        acc_pct, rep_pct = calculate_activity_progress(planned_qty, accepted_qty, reported_qty)

        # ── Weighted contributions ────────────────────────────────────────
        earned_planned      += (planned_pct   / 100.0) * weight
        earned_ai_auto      += (ai_auto_pct   / 100.0) * weight
        earned_field_obs    += (field_obs_pct / 100.0) * weight
        earned_pm_approved  += (pm_appr_pct   / 100.0) * weight
        earned_qa_accepted  += (acc_pct       / 100.0) * weight
        total_weight        += weight

        # ── Financial ─────────────────────────────────────────────────────
        total_planned_value += planned_qty * unit_cost
        total_earned_value  += accepted_qty * unit_cost

        # ── Stage rollups ─────────────────────────────────────────────────
        if stage_id not in stage_metrics:
            stage_metrics[stage_id] = {
                'id': stage_id, 'name': stage_name,
                'weightage': float(act['stage_weightage'] or 0.0),
                'total_w': 0.0,
                'earned_planned': 0.0, 'earned_ai': 0.0,
                'earned_field': 0.0,  'earned_pm': 0.0, 'earned_qa': 0.0,
                'activities_count': 0, 'completed_count': 0
            }
        sm = stage_metrics[stage_id]
        sm['total_w']       += weight
        sm['earned_planned'] += (planned_pct   / 100.0) * weight
        sm['earned_ai']      += (ai_auto_pct   / 100.0) * weight
        sm['earned_field']   += (field_obs_pct / 100.0) * weight
        sm['earned_pm']      += (pm_appr_pct   / 100.0) * weight
        sm['earned_qa']      += (acc_pct       / 100.0) * weight
        sm['activities_count'] += 1
        if acc_pct >= 100.0:
            sm['completed_count'] += 1

        # ── Tower rollups ─────────────────────────────────────────────────
        if tower_id not in tower_metrics:
            tower_metrics[tower_id] = {
                'id': tower_id, 'name': tower_name,
                'total_w': 0.0, 'earned_planned': 0.0,
                'earned_ai': 0.0, 'earned_field': 0.0, 'earned_pm': 0.0
            }
        tm = tower_metrics[tower_id]
        tm['total_w']        += weight
        tm['earned_planned'] += (planned_pct   / 100.0) * weight
        tm['earned_ai']      += (ai_auto_pct   / 100.0) * weight
        tm['earned_field']   += (field_obs_pct / 100.0) * weight
        tm['earned_pm']      += (pm_appr_pct   / 100.0) * weight

        # ── Floor heatmap ─────────────────────────────────────────────────
        if tower_id != 'General':
            fk = f"{tower_id}_L{floor_level}"
            if fk not in floor_metrics:
                floor_metrics[fk] = {
                    'tower_id': tower_id, 'tower_name': tower_name,
                    'floor_level': floor_level,
                    'total_w': 0.0,
                    'earned_planned': 0.0, 'earned_ai': 0.0,
                    'earned_field': 0.0,  'earned_pm': 0.0, 'earned_qa': 0.0,
                    'activities_count': 0
                }
            fm = floor_metrics[fk]
            fm['total_w']        += weight
            fm['earned_planned'] += (planned_pct   / 100.0) * weight
            fm['earned_ai']      += (ai_auto_pct   / 100.0) * weight
            fm['earned_field']   += (field_obs_pct / 100.0) * weight
            fm['earned_pm']      += (pm_appr_pct   / 100.0) * weight
            fm['earned_qa']      += (acc_pct       / 100.0) * weight
            fm['activities_count'] += 1

    # ── PM pending reviews count ──────────────────────────────────────────
    cursor.execute("SELECT COUNT(*) FROM pm_reviews WHERE pm_status = 'PENDING'")
    pending_pm = cursor.fetchone()[0]

    conn.close()

    def pct(earned, total):
        return round(earned, 2) if total > 0 else 0.0

    # ── Stage list ────────────────────────────────────────────────────────
    stage_list = []
    for s_id, s in stage_metrics.items():
        tw = s['total_w'] or 1.0
        stage_list.append({
            'stage_id': s_id,
            'stage_name': s['name'],
            'weightage': s['weightage'],
            'earned_weight': round(s['earned_qa'], 2),
            'progress_pct': round((s['earned_qa'] / tw) * 100, 2),
            'reported_progress_pct': round((s['earned_field'] / tw) * 100, 2),
            'planned_pct': round((s['earned_planned'] / tw) * 100, 2),
            'ai_pct': round((s['earned_ai'] / tw) * 100, 2),
            'pm_pct': round((s['earned_pm'] / tw) * 100, 2),
            'activities_count': s['activities_count'],
            'completed_count': s['completed_count']
        })

    # ── Tower list ────────────────────────────────────────────────────────
    tower_list = []
    for t_id, t in tower_metrics.items():
        tw = t['total_w'] or 1.0
        tower_list.append({
            'tower_id': t_id, 'tower_name': t['name'],
            'planned_pct':  round((t['earned_planned'] / tw) * 100, 2),
            'ai_pct':       round((t['earned_ai']      / tw) * 100, 2),
            'field_pct':    round((t['earned_field']   / tw) * 100, 2),
            'pm_pct':       round((t['earned_pm']      / tw) * 100, 2),
            'total_weight': round(tw, 2)
        })

    # ── Floor heatmap ─────────────────────────────────────────────────────
    floor_heatmap = []
    for f_key, f in floor_metrics.items():
        tw = f['total_w'] or 1.0
        floor_heatmap.append({
            'tower_id':   f['tower_id'],
            'tower_name': f['tower_name'],
            'floor_level': f['floor_level'],
            'progress_pct': round((f['earned_qa'] / tw) * 100, 1),
            'ai_pct':       round((f['earned_ai'] / tw) * 100, 1),
            'pm_pct':       round((f['earned_pm'] / tw) * 100, 1),
            'activities_count': f['activities_count']
        })

    total_w = total_weight or 1.0
    financial_progress = round(
        (total_earned_value / total_planned_value * 100.0), 2
    ) if total_planned_value > 0 else 0.0

    return {
        # ── 4 primary streams ─────────────────────────────────────────────
        'planned_progress':       pct(earned_planned,     total_w),
        'ai_automated_progress':  pct(earned_ai_auto,     total_w),
        'field_observed_progress':pct(earned_field_obs,   total_w),
        'pm_approved_progress':   pct(earned_pm_approved, total_w),
        # ── Legacy / additional ──────────────────────────────────────────
        'physical_progress':      pct(earned_qa_accepted, total_w),
        'reported_progress':      pct(earned_field_obs,   total_w),
        'financial_progress':     financial_progress,
        'schedule_progress':      pct(earned_planned,     total_w),
        'planned_target_progress':pct(earned_planned,     total_w),
        'pending_pm_reviews':     pending_pm,
        # ── Rollups ───────────────────────────────────────────────────────
        'stages':       stage_list,
        'towers':       tower_list,
        'floor_heatmap':floor_heatmap,
        'variances': {
            'ai_vs_planned':      round(pct(earned_ai_auto, total_w)     - pct(earned_planned, total_w), 2),
            'pm_vs_planned':      round(pct(earned_pm_approved, total_w) - pct(earned_planned, total_w), 2),
            'field_vs_planned':   round(pct(earned_field_obs, total_w)   - pct(earned_planned, total_w), 2),
            'ai_vs_pm':           round(pct(earned_ai_auto, total_w)     - pct(earned_pm_approved, total_w), 2),
            'physical_vs_planned':round(pct(earned_qa_accepted, total_w) - pct(earned_planned, total_w), 2)
        }
    }


if __name__ == "__main__":
    from database import init_db
    init_db()
    import json
    print(json.dumps(compute_project_metrics(), indent=2))
