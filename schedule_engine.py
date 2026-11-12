"""
PyCray_SiteIQ — Schedule Engine
Parses and validates L4 Excel/CSV schedule uploads.
On confirmation, writes activities, stages, towers and schedule_baselines to the DB.
"""
import os
import re
import uuid
import json
from datetime import datetime, date

try:
    import openpyxl
    HAS_OPENPYXL = True
except ImportError:
    HAS_OPENPYXL = False

from database import get_db
from progress_engine import calculate_planned_progress

# ── Column name aliases ────────────────────────────────────────────────────
# Maps flexible column header names → canonical field names
COLUMN_ALIASES = {
    'activity_code':    ['activity_code', 'activity_id', 'activity id', 'act_id', 'act_code', 'wbs_code', 'code'],
    'activity_name':    ['activity_name', 'act_name', 'name', 'activity description', 'description'],
    'wbs_code':         ['wbs_code', 'wbs code', 'wbs'],
    'l1':               ['l1', 'level 1', 'l1_name', 'wbs_l1_name', 'stage'],
    'l2':               ['l2', 'level 2', 'l2_name', 'wbs_l2_name', 'substage'],
    'l3':               ['l3', 'level 3', 'l3_name', 'wbs_l3_name'],
    'l4':               ['l4', 'level 4', 'l4_name', 'wbs_l4_name'],
    'trade':            ['trade', 'trade_type'],
    'discipline':       ['discipline'],
    'boq_item':         ['boq_item', 'boq_item_code', 'boq item', 'boq'],
    'boq_description':  ['boq_description', 'boq description', 'activity_description'],
    'building':         ['building', 'building_name', 'tower', 'block'],
    'floor':            ['floor', 'floor_name', 'floor_level', 'level'],
    'zone':             ['zone', 'zone_name'],
    'unit':             ['unit', 'unit_name', 'unit_id'],
    'room':             ['room', 'room_name', 'room_element'],
    'planned_qty':      ['planned_qty', 'planned_quantity', 'planned quantity', 'quantity', 'qty'],
    'uom':              ['uom', 'unit of measure', 'unit_of_measure', 'unit'],
    'weight':           ['weight', 'weightage', 'activity_weight', 'activity weight', 'activity_weight_%', 'activity weight %', 'activity_weight_pct'],
    'planned_start':    ['planned_start', 'start', 'baseline_start', 'baseline start'],
    'planned_finish':   ['planned_finish', 'finish', 'baseline_finish', 'baseline finish'],
    'planned_duration': ['planned_duration', 'planned_duration_days', 'duration', 'dur'],
    'predecessor':      ['predecessor', 'predecessors'],
    'dependency_type':  ['dependency_type', 'dep type', 'type'],
    'contractor':       ['contractor', 'responsible_contractor', 'subcontractor'],
    'responsible_engineer': ['responsible_engineer', 'responsible engineer', 'engineer'],
    'unit_cost':        ['unit_cost', 'rate', 'unit rate', 'planned_cost'],
}

REQUIRED_FIELDS = ['activity_code', 'activity_name', 'planned_qty', 'uom', 'weight']


def _clean_str(s):
    """Strip all non-alphanumeric characters for fuzzy resilient header matching."""
    return re.sub(r'[^a-zA-Z0-9]', '', str(s or '').lower())


def _find_col(headers, aliases):
    """Return first header index matching any alias using normalized clean strings."""
    clean_headers = [_clean_str(h) for h in headers]
    for alias in aliases:
        target = _clean_str(alias)
        for i, ch in enumerate(clean_headers):
            if ch == target:
                return i
    return None


def _parse_date(val):
    if not val:
        return None
    if isinstance(val, (date, datetime)):
        return str(val)[:10]
    s = str(val).strip()
    for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y', '%m/%d/%Y', '%Y/%m/%d'):
        try:
            return datetime.strptime(s, fmt).strftime('%Y-%m-%d')
        except ValueError:
            continue
    return None


def _parse_float(val, default=0.0):
    if val is None:
        return default
    try:
        s = str(val).strip().replace(',', '').replace('%', '')
        return float(s)
    except (TypeError, ValueError):
        return default


def parse_schedule_excel(file_path: str, project_id: str = "PROJ-001") -> dict:
    """
    Parse an L4 Excel file.
    Returns a dict with:
      - activities: list of parsed activity dicts
      - errors:    list of {row, field, message}
      - warnings:  list of {row, field, message}
      - summary:   {total_rows, valid_rows, error_rows, total_weight, weight_valid}
    """
    if not HAS_OPENPYXL:
        return {"error": "openpyxl not installed. Run: pip install openpyxl"}

    if not os.path.exists(file_path):
        return {"error": f"File not found: {file_path}"}

    wb = openpyxl.load_workbook(file_path, data_only=True)
    ws = wb.active

    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        return {"error": "Excel file is empty."}

    # ── Map header row ─────────────────────────────────────────────────────
    header_row = [str(h).strip() if h is not None else '' for h in rows[0]]

    col_map = {}
    for field, aliases in COLUMN_ALIASES.items():
        idx = _find_col(header_row, aliases)
        if idx is not None:
            col_map[field] = idx

    # ── Validate required columns ─────────────────────────────────────────
    errors, warnings, activities = [], [], []
    seen_codes = set()
    total_weight = 0.0

    missing_cols = [f for f in REQUIRED_FIELDS if f not in col_map]
    if missing_cols:
        return {
            "error": f"Missing required columns: {', '.join(missing_cols)}",
            "activities": [], "errors": [], "warnings": [], "summary": {}
        }

    # ── Parse data rows ────────────────────────────────────────────────────
    for row_idx, row in enumerate(rows[1:], start=2):
        def cell(field, default=None):
            idx = col_map.get(field)
            if idx is None or idx >= len(row):
                return default
            v = row[idx]
            return v if v is not None else default

        code = str(cell('activity_code', '')).strip()
        name = str(cell('activity_name', '')).strip()

        if not code and not name:
            continue  # blank row — skip silently

        row_errors = []

        # ── Required field checks ─────────────────────────────────────────
        if not code:
            row_errors.append({'row': row_idx, 'field': 'activity_code', 'message': 'Activity code is missing'})
        elif code in seen_codes:
            row_errors.append({'row': row_idx, 'field': 'activity_code', 'message': f'Duplicate activity code: {code}'})
        else:
            seen_codes.add(code)

        if not name:
            row_errors.append({'row': row_idx, 'field': 'activity_name', 'message': 'Activity name is missing'})

        planned_qty = _parse_float(cell('planned_qty'))
        if planned_qty <= 0:
            row_errors.append({'row': row_idx, 'field': 'planned_qty', 'message': f'Invalid planned quantity: {cell("planned_qty")}'})

        uom = str(cell('uom', '')).strip()
        if not uom:
            row_errors.append({'row': row_idx, 'field': 'uom', 'message': 'UOM is missing'})

        weight = _parse_float(cell('weight'))
        if weight <= 0:
            row_errors.append({'row': row_idx, 'field': 'weight', 'message': f'Invalid or zero weight: {cell("weight")}'})

        # ── Date checks ───────────────────────────────────────────────────
        ps = _parse_date(cell('planned_start'))
        pf = _parse_date(cell('planned_finish'))
        if cell('planned_start') and not ps:
            warnings.append({'row': row_idx, 'field': 'planned_start', 'message': f'Could not parse start date: {cell("planned_start")}'})
        if cell('planned_finish') and not pf:
            warnings.append({'row': row_idx, 'field': 'planned_finish', 'message': f'Could not parse finish date: {cell("planned_finish")}'})
        if ps and pf and ps > pf:
            row_errors.append({'row': row_idx, 'field': 'planned_finish', 'message': 'Finish date is before start date'})

        errors.extend(row_errors)

        # Floor extraction from string e.g. "Level 12", "L12", "12"
        floor_val = 0
        floor_raw = str(cell('floor', '0')).strip()
        floor_match = re.search(r'\d+', floor_raw)
        if floor_match:
            floor_val = int(floor_match.group())

        activity = {
            'id': f"ACT-{code.replace(' ', '-').replace('_', '-')}",
            'activity_code': code,
            'name': name,
            'description': str(cell('boq_description', name)),
            'project_id': project_id,
            'wbs_code': str(cell('wbs_code', '')).strip(),
            'l1': str(cell('l1', '')).strip(),
            'l2': str(cell('l2', '')).strip(),
            'l3': str(cell('l3', '')).strip(),
            'l4': str(cell('l4', '')).strip(),
            'trade': str(cell('trade', '')).strip(),
            'discipline': str(cell('discipline', '')).strip(),
            'boq_item': str(cell('boq_item', '')).strip(),
            'boq_description': str(cell('boq_description', '')).strip(),
            'building': str(cell('building', '')).strip(),
            'floor_level': floor_val,
            'zone': str(cell('zone', '')).strip(),
            'unit': str(cell('unit', '')).strip(),
            'room': str(cell('room', '')).strip(),
            'planned_qty': planned_qty,
            'uom': uom,
            'weightage': weight,
            'planned_start': ps,
            'planned_finish': pf,
            'planned_duration': int(_parse_float(cell('planned_duration', 0))),
            'predecessor': str(cell('predecessor', '')).strip(),
            'dependency_type': str(cell('dependency_type', 'FS')).strip(),
            'contractor': str(cell('contractor', '')).strip(),
            'responsible_engineer': str(cell('responsible_engineer', '')).strip(),
            'unit_cost': _parse_float(cell('unit_cost', 0.0)),
            'has_errors': len(row_errors) > 0
        }
        total_weight += weight
        activities.append(activity)

    # ── Weight sum check ──────────────────────────────────────────────────
    if activities and abs(total_weight - 100.0) > 0.5:
        warnings.append({
            'row': 'ALL', 'field': 'weight',
            'message': f'Total activity weights sum to {total_weight:.4f}% (expected 100.0%)'
        })

    valid_count = sum(1 for a in activities if not a['has_errors'])

    return {
        'activities': activities,
        'errors': errors,
        'warnings': warnings,
        'summary': {
            'total_rows': len(activities),
            'valid_rows': valid_count,
            'error_rows': len(activities) - valid_count,
            'total_weight': round(total_weight, 4),
            'weight_valid': abs(total_weight - 100.0) <= 0.5
        }
    }


def confirm_schedule_as_baseline(parsed_result: dict, baseline_id: str,
                                  confirmed_by: str = "Project Manager",
                                  project_id: str = "PROJ-001") -> dict:
    """
    Write confirmed schedule activities to the database.
    Updates stages, towers, activities, and marks schedule_baseline as CONFIRMED.
    """
    activities = [a for a in parsed_result['activities'] if not a['has_errors']]
    if not activities:
        return {"error": "No valid activities to import."}

    conn = get_db()
    cursor = conn.cursor()

    # ── Ensure stage rows exist ───────────────────────────────────────────
    stages_seen = {}
    stage_weights = {}

    # Check if stages already exist in database
    cursor.execute("SELECT id, name, stage_number FROM stages WHERE project_id = ?", (project_id,))
    existing_stages = {r['name'].strip().lower(): r['id'] for r in cursor.fetchall()}

    stage_num = 1
    for a in activities:
        stage_key = a.get('l1') or a.get('l2') or 'General Construction'
        stage_key_clean = stage_key.strip()
        sk_lower = stage_key_clean.lower()

        if sk_lower in existing_stages:
            stages_seen[stage_key_clean] = existing_stages[sk_lower]
        elif stage_key_clean not in stages_seen:
            sid = f"STG-{uuid.uuid4().hex[:6].upper()}"
            stages_seen[stage_key_clean] = sid
            cursor.execute("""
                INSERT INTO stages (id, project_id, stage_number, name, code, weightage)
                VALUES (?, ?, ?, ?, ?, 0.0)
            """, (sid, project_id, stage_num, stage_key_clean, f"STG-{stage_num:02d}"))
            stage_num += 1

        stage_id = stages_seen[stage_key_clean]
        stage_weights[stage_id] = stage_weights.get(stage_id, 0.0) + float(a['weightage'] or 0.0)

    # Update stages with their aggregated weights
    for sid, w in stage_weights.items():
        cursor.execute("UPDATE stages SET weightage = ? WHERE id = ?", (round(w, 2), sid))

    # ── Ensure tower rows exist ───────────────────────────────────────────
    cursor.execute("SELECT id, name FROM towers WHERE project_id = ?", (project_id,))
    existing_towers = {r['name'].strip().lower(): r['id'] for r in cursor.fetchall()}
    towers_seen = {}

    for a in activities:
        bldg = a.get('building', '').strip()
        if not bldg:
            continue
        bldg_lower = bldg.lower()
        if bldg_lower in existing_towers:
            towers_seen[bldg] = existing_towers[bldg_lower]
        elif any(k in bldg_lower for k in ['tower a', 'towa', 'block a']):
            towers_seen[bldg] = 'TOW-A'
        elif any(k in bldg_lower for k in ['tower b', 'towb', 'block b']):
            towers_seen[bldg] = 'TOW-B'
        elif bldg not in towers_seen:
            tid = f"TOW-{bldg[:3].upper()}"
            towers_seen[bldg] = tid
            cursor.execute("""
                INSERT OR IGNORE INTO towers (id, project_id, name, code, total_floors, weightage)
                VALUES (?, ?, ?, ?, 20, 50.0)
            """, (tid, project_id, bldg, bldg[:8]))

    # ── Clear existing activities for this project ────────────────────────
    cursor.execute("DELETE FROM activities WHERE project_id = ?", (project_id,))

    # ── Insert new activities with calculated planned progress ────────────
    today = date.today()
    for a in activities:
        stage_key = (a.get('l1') or a.get('l2') or 'General Construction').strip()
        stage_id  = stages_seen.get(stage_key)
        bldg      = a.get('building', '').strip()
        tower_id  = towers_seen.get(bldg) if bldg else None

        planned_pct = calculate_planned_progress(a['planned_start'], a['planned_finish'], today)

        cursor.execute("""
            INSERT INTO activities (
                id, activity_code, name, description, project_id, tower_id, floor_level, zone, unit, room,
                discipline, trade, boq_item, boq_description, stage_id, responsible_engineer, contractor,
                planned_qty, uom, weightage, planned_start, planned_finish, planned_duration,
                predecessor, dependency_type, unit_cost,
                reported_qty, accepted_qty, inspected_qty,
                planned_progress_pct, ai_automated_progress_pct, field_observed_progress_pct, pm_approved_progress_pct,
                status, inspection_status
            ) VALUES (
                ?,?,?,?,?,?,?,?,?,?,
                ?,?,?,?,?,?,?,
                ?,?,?,?,?,?,
                ?,?,?,
                0.0,0.0,0.0,
                ?,0.0,0.0,0.0,
                'Not Started','Not Requested'
            )
        """, (
            a['id'], a['activity_code'], a['name'], a['description'],
            project_id, tower_id, a['floor_level'], a['zone'], a['unit'], a['room'],
            a['discipline'], a['trade'], a['boq_item'], a['boq_description'],
            stage_id, a['responsible_engineer'], a['contractor'],
            a['planned_qty'], a['uom'], a['weightage'],
            a['planned_start'], a['planned_finish'], a['planned_duration'],
            a['predecessor'], a['dependency_type'], a['unit_cost'],
            planned_pct
        ))

    # ── Mark baseline as confirmed ────────────────────────────────────────
    cursor.execute("""
        UPDATE schedule_baselines SET status='CONFIRMED', confirmed_at=?, confirmed_by=?
        WHERE id=?
    """, (datetime.now().isoformat(), confirmed_by, baseline_id))

    conn.commit()
    conn.close()

    return {
        'message': f"Baseline confirmed. {len(activities)} activities imported into master WBS.",
        'baseline_id': baseline_id,
        'activities_imported': len(activities)
    }
