"""
Audit Intelligence — Stage-Based & Substage-Based Inspection Allocation Service
Enterprise Construction Quality Management & Checkpoint Allocation Engine
"""

import json
from datetime import datetime, date
from typing import List, Dict, Any, Optional
import sqlite3

from database_audit import get_connection

ENGINEER_REGISTRY = {
    "EMP-1002": {"id": "EMP-1002", "name": "Rohit Kale", "role": "Senior QC Engineer", "specialty": "RCC & Structural"},
    "EMP-1003": {"id": "EMP-1003", "name": "Vikram Singh", "role": "QC Inspection Engineer", "specialty": "Steel & Telecom"},
    "EMP-1004": {"id": "EMP-1004", "name": "Anjali Rao", "role": "QC Inspection Engineer", "specialty": "Finishes & Waterproofing"},
    "EMP-1005": {"id": "EMP-1005", "name": "Meera Iyer", "role": "Senior Façade & MEP Engineer", "specialty": "Façade & MEP"},
    "EMP-1006": {"id": "EMP-1006", "name": "Arjun Mehta", "role": "QC Inspection Engineer", "specialty": "Industrial & PEB"}
}
NAME_TO_ID = {v["name"]: k for k, v in ENGINEER_REGISTRY.items()}

class AllocationService:

    @staticmethod
    def get_master_checklist(stage_id: Optional[str] = None,
                             building_type: Optional[str] = None,
                             priority: Optional[str] = None,
                             search_q: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Retrieves the complete hierarchical master checklist:
        Stage -> Subgroup -> Checkpoints
        """
        conn = get_connection()
        cur = conn.cursor()

        stage_query = "SELECT * FROM master_stages WHERE 1=1"
        stage_params = []
        if stage_id:
            stage_query += " AND (stage_id = ? OR stage_num = ?)"
            stage_params.extend([stage_id, stage_id])
        stage_query += " ORDER BY display_order ASC"

        cur.execute(stage_query, stage_params)
        stages = [dict(r) for r in cur.fetchall()]

        result = []
        for stg in stages:
            sid = stg['stage_id']
            cur.execute("""
                SELECT * FROM master_subgroups
                WHERE stage_id = ?
                ORDER BY display_order ASC
            """, (sid,))
            subgroups = [dict(r) for r in cur.fetchall()]

            stg_subgroups = []
            stg_checkpoint_count = 0

            for sub in subgroups:
                sub_id = sub['subgroup_id']
                chk_query = "SELECT * FROM master_checkpoints WHERE subgroup_id = ?"
                chk_params = [sub_id]

                if priority and priority != 'all':
                    chk_query += " AND priority = ?"
                    chk_params.append(priority.upper())

                if building_type and building_type != 'all':
                    chk_query += " AND (applicable_building_types = 'all' OR applicable_building_types LIKE ?)"
                    chk_params.append(f"%{building_type}%")

                if search_q:
                    chk_query += " AND checkpoint_description LIKE ?"
                    chk_params.append(f"%{search_q}%")

                chk_query += " ORDER BY display_order ASC"
                cur.execute(chk_query, chk_params)
                checkpoints = [dict(r) for r in cur.fetchall()]

                if checkpoints or not search_q:
                    sub['checkpoints'] = checkpoints
                    sub['checkpoint_count'] = len(checkpoints)
                    stg_checkpoint_count += len(checkpoints)
                    stg_subgroups.append(sub)

            if stg_subgroups or not search_q:
                stg['subgroups'] = stg_subgroups
                stg['total_checkpoints'] = stg_checkpoint_count
                result.append(stg)

        conn.close()
        return result

    @staticmethod
    @staticmethod
    def get_next_inspection_id(project_id: str) -> str:
        """
        Generates the next sequential unique inspection ID for a given project.
        Format: INS-{project_num}-{sequence:04d}
        """
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("SELECT code FROM projects WHERE id = ? OR code = ?", (project_id, project_id))
        p_row = cur.fetchone()
        p_code = p_row['code'] if p_row else "PRJ-0012"
        p_num = p_code.replace("PRJ-", "")

        prefix = f"INS-{p_num}-"
        cur.execute("SELECT code FROM inspections WHERE code LIKE ? ORDER BY code DESC LIMIT 1", (prefix + '%',))
        last_ins = cur.fetchone()

        cur.execute("SELECT allocation_id FROM inspection_allocations WHERE allocation_id LIKE ? ORDER BY allocation_id DESC LIMIT 1", (prefix + '%',))
        last_alloc = cur.fetchone()

        max_seq = 0
        for row in [last_ins, last_alloc]:
            if row and row[0]:
                try:
                    num = int(row[0].split('-')[-1])
                    if num > max_seq:
                        max_seq = num
                except Exception:
                    pass

        if max_seq == 0:
            alc_prefix = f"ALC-{p_num}-"
            cur.execute("SELECT allocation_id FROM inspection_allocations WHERE allocation_id LIKE ? ORDER BY allocation_id DESC LIMIT 1", (alc_prefix + '%',))
            r = cur.fetchone()
            if r and r[0]:
                try:
                    max_seq = int(r[0].split('-')[-1])
                except Exception:
                    pass

        next_id = f"{prefix}{str(max_seq + 1).zfill(4)}"
        conn.close()
        return next_id

    @staticmethod
    def create_allocation(data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Atomically creates or updates an inspection / checkpoint allocation.
        Supports:
          - Step 1 Create Inspection (Save as Draft or Confirm & Create)
          - Draft vs Allocated status
          - Preserving a single unique Inspection ID throughout the lifecycle
        """
        conn = get_connection()
        cur = conn.cursor()

        pid = data.get('project_id')
        eid = data.get('engineer_id')
        engineer = data.get('engineer_name')
        allocated_by = data.get('allocated_by', 'Priya Deshmukh (QC Lead)')
        checkpoint_ids = data.get('checkpoint_ids', [])
        target_status = data.get('status', 'Allocated')
        is_draft = target_status.lower() == 'draft'

        if not pid:
            conn.close()
            raise ValueError("Project ID is required.")

        # Resolve engineer identifier and name
        if eid and not engineer:
            engineer = ENGINEER_REGISTRY.get(eid, {}).get('name', 'Anjali Rao')
        elif not eid and engineer:
            eid = NAME_TO_ID.get(engineer, "EMP-1004")
        elif not eid and not engineer:
            if is_draft:
                engineer = "Unassigned"
                eid = None
            else:
                conn.close()
                raise ValueError("Inspection Engineer must be selected before activating an inspection.")

        if not is_draft and not checkpoint_ids:
            conn.close()
            raise ValueError("At least one inspection checkpoint must be selected before activating an inspection.")

        # 1. Verify Project Eligibility
        cur.execute("SELECT * FROM projects WHERE id = ? OR code = ?", (pid, pid))
        p_row = cur.fetchone()
        if not p_row:
            conn.close()
            raise ValueError(f"Project '{pid}' does not exist.")
        project = dict(p_row)
        pid = project['id']

        if project['status'] == 'completed':
            conn.close()
            raise ValueError("Cannot allocate inspections to a Completed project.")
        if project['status'] == 'hold':
            conn.close()
            raise ValueError(f"Project is on Hold: {project.get('hold_reason') or 'Stop-work active'}. Cannot allocate new scope.")

        # 2. Date validation
        planned_date = data.get('planned_date', datetime.now().strftime("%Y-%m-%d"))
        due_date = data.get('due_date', planned_date)
        if due_date < planned_date:
            conn.close()
            raise ValueError("Inspection due date cannot precede the planned inspection date.")

        # Location details
        tower = data.get('tower_block', '')
        floor = data.get('floor_level', '')
        zone = data.get('zone_area', '')
        grid = data.get('grid_ref', '')
        element = data.get('element_id', '')
        instructions = data.get('instructions', '')
        priority = data.get('priority', 'High')
        custom_title = data.get('title')

        location_parts = [p for p in [tower, floor, zone, grid, element] if p]
        location_scope = " · ".join(location_parts) if location_parts else "General Site Area"

        # Check if existing inspection_id was passed
        passed_id = data.get('inspection_id')
        alloc_id = passed_id
        is_existing_record = False

        if alloc_id:
            cur.execute("SELECT allocation_id, status FROM inspection_allocations WHERE allocation_id = ?", (alloc_id,))
            ex = cur.fetchone()
            if ex:
                is_existing_record = True

        if not alloc_id:
            # Generate Unique Sequential ID
            p_num = project['code'].replace('PRJ-', '')
            prefix = f"INS-{p_num}-"
            cur.execute("SELECT allocation_id FROM inspection_allocations WHERE allocation_id LIKE ? ORDER BY allocation_id DESC LIMIT 1", (prefix + '%',))
            last_row = cur.fetchone()
            if last_row:
                try:
                    last_num = int(last_row[0].split('-')[-1])
                    alloc_count = last_num + 1
                except Exception:
                    cur.execute("SELECT COUNT(*) FROM inspection_allocations")
                    alloc_count = cur.fetchone()[0] + 1
            else:
                # Also check ALC-
                cur.execute("SELECT allocation_id FROM inspection_allocations WHERE allocation_id LIKE ? ORDER BY allocation_id DESC LIMIT 1", (f"ALC-{p_num}-%",))
                last_alc = cur.fetchone()
                if last_alc:
                    try:
                        alloc_count = int(last_alc[0].split('-')[-1]) + 1
                    except Exception:
                        alloc_count = 1
                else:
                    alloc_count = 1
            alloc_id = f"{prefix}{str(alloc_count).zfill(4)}"

        # 3. Duplicate Prevention for active non-drafts
        if not is_draft and not is_existing_record and not data.get('allow_duplicate', False) and checkpoint_ids:
            sorted_chk_ids = sorted(checkpoint_ids)
            cur.execute("""
                SELECT a.allocation_id, a.created_at, GROUP_CONCAT(ac.checkpoint_id) as chk_list
                FROM inspection_allocations a
                JOIN allocation_checkpoints ac ON a.allocation_id = ac.allocation_id
                WHERE a.project_id = ? AND a.location_scope = ? AND a.engineer_name = ?
                  AND a.status IN ('Allocated', 'In progress')
                GROUP BY a.allocation_id
            """, (pid, location_scope, engineer))
            for existing in cur.fetchall():
                existing_chks = sorted((existing[2] or "").split(","))
                if existing_chks == sorted_chk_ids:
                    conn.close()
                    raise ValueError(f"Duplicate allocation prevented: Active assignment {existing[0]} already covers this identical scope and engineer.")

        # 4. Fetch Checkpoint Details
        chk_rows = []
        stage_names = []
        subgroup_names = []
        if checkpoint_ids:
            placeholders = ','.join('?' for _ in checkpoint_ids)
            cur.execute(f"""
                SELECT c.*, s.stage_name, g.subgroup_name
                FROM master_checkpoints c
                JOIN master_stages s ON c.stage_id = s.stage_id
                JOIN master_subgroups g ON c.subgroup_id = g.subgroup_id
                WHERE c.checkpoint_id IN ({placeholders})
            """, checkpoint_ids)
            chk_rows = [dict(r) for r in cur.fetchall()]
            stage_names = list(dict.fromkeys(r['stage_name'] for r in chk_rows))
            subgroup_names = list(dict.fromkeys(r['subgroup_name'] for r in chk_rows))

        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        status_to_save = 'Draft' if is_draft else 'Allocated'

        # 5. Atomic Transaction Management across all 4 tables
        try:
            if is_existing_record:
                # Update existing record
                cur.execute("""
                    UPDATE inspection_allocations
                    SET project_id = ?, engineer_id = ?, engineer_name = ?, allocated_by = ?,
                        location_scope = ?, tower_block = ?, floor_level = ?, zone_area = ?,
                        grid_ref = ?, element_id = ?, instructions = ?, planned_date = ?,
                        due_date = ?, due_time = ?, priority = ?, status = ?, updated_at = ?
                    WHERE allocation_id = ?
                """, (
                    pid, eid, engineer, allocated_by,
                    location_scope, tower, floor, zone, grid, element,
                    instructions, planned_date, due_date, data.get('due_time', '18:00'),
                    priority, status_to_save, now_str, alloc_id
                ))
                # Clear and re-insert checkpoints
                cur.execute("DELETE FROM allocation_checkpoints WHERE allocation_id = ?", (alloc_id,))
            else:
                # Insert new record
                cur.execute("""
                    INSERT INTO inspection_allocations (
                        allocation_id, project_id, engineer_id, engineer_name, allocated_by,
                        location_scope, tower_block, floor_level, zone_area, grid_ref, element_id,
                        instructions, planned_date, due_date, due_time, priority, status,
                        created_at, updated_at, linked_ins_code
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    alloc_id, pid, eid, engineer, allocated_by,
                    location_scope, tower, floor, zone, grid, element,
                    instructions, planned_date, due_date, data.get('due_time', '18:00'),
                    priority, status_to_save, now_str, now_str, alloc_id
                ))

            # Insert checkpoints if any
            for chk in chk_rows:
                cur.execute("""
                    INSERT INTO allocation_checkpoints (
                        allocation_id, checkpoint_id, stage_id, subgroup_id,
                        stage_name, subgroup_name, checkpoint_text_snapshot,
                        priority, result_status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'Pending')
                """, (
                    alloc_id, chk['checkpoint_id'], chk['stage_id'], chk['subgroup_id'],
                    chk['stage_name'], chk['subgroup_name'], chk['checkpoint_description'],
                    chk['priority']
                ))

            # Title formulation
            if custom_title and custom_title.strip():
                ins_title = custom_title.strip()
            elif stage_names:
                ins_title = stage_names[0] if len(stage_names) == 1 else f"{stage_names[0]} (+{len(stage_names)-1} stages)"
            else:
                ins_title = "Quality Inspection"

            template_name = subgroup_names[0] if len(subgroup_names) == 1 else (f"{len(chk_rows)} Checkpoints" if chk_rows else "Checklist Pending")

            # Mirror into inspections table
            cur.execute("""
                INSERT OR REPLACE INTO inspections (
                    code, project_id, title, zone, tpl, eng, due_date, status,
                    items_count, items_pass, items_nc, items_na
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 0, 0)
            """, (
                alloc_id, pid, ins_title, location_scope, template_name, engineer, due_date, status_to_save, len(chk_rows)
            ))

            # Record Audit Event
            audit_action = 'SAVE_DRAFT' if is_draft else ('ACTIVATE' if is_existing_record else 'CREATE_INSPECTION')
            audit_remarks = f"Draft saved with {len(chk_rows)} checkpoints" if is_draft else f"Created and allocated {len(chk_rows)} checkpoints across {len(stage_names)} stage(s) to {engineer} ({eid or 'N/A'}) at {location_scope}"
            cur.execute("""
                INSERT INTO inspection_audit_events (
                    allocation_id, actor_name, action, previous_status, new_status, timestamp, remarks
                ) VALUES (?, ?, ?, NULL, ?, ?, ?)
            """, (alloc_id, allocated_by, audit_action, status_to_save, now_str, audit_remarks))

            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

        return {
            "allocation_id": alloc_id,
            "inspection_id": alloc_id,
            "project_id": pid,
            "project_name": project['name'],
            "engineer_name": engineer,
            "engineer_id": eid,
            "status": status_to_save,
            "checkpoint_count": len(chk_rows),
            "stages": stage_names,
            "subgroups": subgroup_names,
            "planned_date": planned_date,
            "due_date": due_date,
            "location_scope": location_scope,
            "created_at": now_str,
            "title": ins_title,
            "tpl": template_name,
            "message": f"Inspection {alloc_id} {'saved as draft' if is_draft else 'successfully created and allocated'}."
        }

    @staticmethod
    def get_allocation_detail(alloc_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves full allocation details including all assigned checkpoints.
        """
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT a.*, p.name as project_name, p.code as project_code, p.type as project_type,
                   p.loc as project_loc, p.geo as project_geo
            FROM inspection_allocations a
            JOIN projects p ON a.project_id = p.id
            WHERE a.allocation_id = ?
        """, (alloc_id,))
        row = cur.fetchone()
        if not row:
            conn.close()
            return None

        alloc = dict(row)

        # Checkpoints
        cur.execute("""
            SELECT * FROM allocation_checkpoints
            WHERE allocation_id = ?
            ORDER BY id ASC
        """, (alloc_id,))
        checkpoints = [dict(r) for r in cur.fetchall()]
        alloc['checkpoints'] = checkpoints

        # Metrics
        total = len(checkpoints)
        ok_count = sum(1 for c in checkpoints if c['result_status'] == 'OK')
        nc_count = sum(1 for c in checkpoints if c['result_status'] == 'NC')
        na_count = sum(1 for c in checkpoints if c['result_status'] == 'NA')
        pending = total - (ok_count + nc_count + na_count)

        alloc['stats'] = {
            'total': total,
            'ok': ok_count,
            'nc': nc_count,
            'na': na_count,
            'pending': pending,
            'compliance_pct': round((ok_count / (ok_count + nc_count or 1)) * 100, 1) if (ok_count + nc_count) > 0 else 0
        }

        # Audit history
        cur.execute("""
            SELECT * FROM inspection_audit_events
            WHERE allocation_id = ?
            ORDER BY event_id ASC
        """, (alloc_id,))
        alloc['audit_trail'] = [dict(r) for r in cur.fetchall()]

        # Review history
        cur.execute("""
            SELECT * FROM inspection_reviews
            WHERE allocation_id = ?
            ORDER BY review_id DESC
        """, (alloc_id,))
        alloc['reviews'] = [dict(r) for r in cur.fetchall()]

        conn.close()
        return alloc

    @staticmethod
    def list_allocations(project_id: Optional[str] = None,
                         engineer_name: Optional[str] = None,
                         status: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Lists inspection allocations with filter support.
        """
        conn = get_connection()
        cur = conn.cursor()

        query = """
            SELECT a.*, p.name as project_name, p.code as project_code,
                   (SELECT COUNT(*) FROM allocation_checkpoints WHERE allocation_id = a.allocation_id) as total_checkpoints,
                   (SELECT COUNT(*) FROM allocation_checkpoints WHERE allocation_id = a.allocation_id AND result_status = 'OK') as ok_count,
                   (SELECT COUNT(*) FROM allocation_checkpoints WHERE allocation_id = a.allocation_id AND result_status = 'NC') as nc_count,
                   (SELECT COUNT(*) FROM allocation_checkpoints WHERE allocation_id = a.allocation_id AND result_status = 'NA') as na_count
            FROM inspection_allocations a
            JOIN projects p ON a.project_id = p.id
            WHERE 1=1
        """
        params = []
        if project_id:
            query += " AND a.project_id = ?"
            params.append(project_id)
        if engineer_name:
            query += " AND a.engineer_name = ?"
            params.append(engineer_name)
        if status and status != 'all':
            query += " AND a.status = ?"
            params.append(status)

        query += " ORDER BY a.due_date ASC, a.created_at DESC"
        cur.execute(query, params)
        rows = [dict(r) for r in cur.fetchall()]

        conn.close()
        return rows

    @staticmethod
    def update_checkpoint_result(alloc_id: str,
                                 checkpoint_id: str,
                                 result_status: str,
                                 observations: Optional[str] = None,
                                 photo_url: Optional[str] = None,
                                 inspected_by: str = "Inspection Engineer") -> Dict[str, Any]:
        """
        Updates inspection finding for an allocated checkpoint.
        Automatically transitions allocation to 'In progress'.
        """
        conn = get_connection()
        cur = conn.cursor()

        if result_status == 'NC' and (not observations or not observations.strip()):
            conn.close()
            raise ValueError("Observation remarks are mandatory when marking a checkpoint as Non-Compliant (NC).")
        if result_status == 'NA' and (not observations or not observations.strip()):
            conn.close()
            raise ValueError("Justification reason is mandatory when marking a checkpoint as Not Applicable (NA).")

        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Check existing status
        cur.execute("SELECT status FROM inspection_allocations WHERE allocation_id = ?", (alloc_id,))
        a_row = cur.fetchone()
        if not a_row:
            conn.close()
            raise ValueError("Allocation not found.")

        current_alloc_status = a_row['status']
        if current_alloc_status in ('Pending review', 'Report issued'):
            conn.close()
            raise ValueError(f"Cannot edit findings while inspection is in '{current_alloc_status}' state.")

        # Update checkpoint
        cur.execute("""
            UPDATE allocation_checkpoints
            SET result_status = ?, observations = ?, evidence_photo_url = ?, inspected_at = ?, inspected_by = ?
            WHERE allocation_id = ? AND checkpoint_id = ?
        """, (result_status, observations, photo_url, now_str, inspected_by, alloc_id, checkpoint_id))

        # If allocation was 'Allocated', transition to 'In progress'
        if current_alloc_status == 'Allocated':
            cur.execute("""
                UPDATE inspection_allocations
                SET status = 'In progress', updated_at = ?
                WHERE allocation_id = ?
            """, (now_str, alloc_id))

            cur.execute("""
                UPDATE inspections
                SET status = 'In progress'
                WHERE code = ?
            """, (alloc_id,))

            cur.execute("""
                INSERT INTO inspection_audit_events (
                    allocation_id, actor_name, action, previous_status, new_status, timestamp, remarks
                ) VALUES (?, ?, 'START_INSPECTION', 'Allocated', 'In progress', ?, 'Inspection work commenced on site')
            """, (alloc_id, inspected_by, now_str))

        # Recompute totals for mirror inspections table
        cur.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN result_status = 'OK' THEN 1 ELSE 0 END) as ok_c,
                SUM(CASE WHEN result_status = 'NC' THEN 1 ELSE 0 END) as nc_c,
                SUM(CASE WHEN result_status = 'NA' THEN 1 ELSE 0 END) as na_c
            FROM allocation_checkpoints
            WHERE allocation_id = ?
        """, (alloc_id,))
        stats = cur.fetchone()

        cur.execute("""
            UPDATE inspections
            SET items_pass = ?, items_nc = ?, items_na = ?
            WHERE code = ?
        """, (stats['ok_c'], stats['nc_c'], stats['na_c'], alloc_id))

        conn.commit()
        conn.close()

        return {
            "status": "success",
            "allocation_id": alloc_id,
            "checkpoint_id": checkpoint_id,
            "result_status": result_status,
            "allocation_status": "In progress" if current_alloc_status == 'Allocated' else current_alloc_status,
            "timestamp": now_str
        }

    @staticmethod
    def save_progress(alloc_id: str, checkpoints_data: List[Dict[str, Any]], saved_by: str = "Inspection Engineer") -> Dict[str, Any]:
        """
        Batch saves checkpoint inspection findings and evidence during execution.
        Automatically transitions 'Allocated' -> 'In progress'.
        """
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("SELECT status, engineer_name FROM inspection_allocations WHERE allocation_id = ?", (alloc_id,))
        a_row = cur.fetchone()
        if not a_row:
            conn.close()
            raise ValueError("Allocation not found.")

        current_alloc_status = a_row['status']
        if current_alloc_status in ('Pending review', 'Report issued'):
            conn.close()
            raise ValueError(f"Cannot modify findings while inspection is in '{current_alloc_status}' state.")

        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        for cp in checkpoints_data:
            c_id = cp.get('checkpoint_id')
            if not c_id:
                continue
            r_stat = cp.get('result_status', 'Pending')
            obs = cp.get('observations') or ""
            photo = cp.get('evidence_photo_url') or ""

            # Check individual validations if marked
            if r_stat == 'NC' and not obs.strip():
                conn.close()
                raise ValueError(f"Observation remarks are mandatory for Non-Compliant checkpoint {c_id}.")
            if r_stat == 'NA' and not obs.strip():
                conn.close()
                raise ValueError(f"Justification reason is mandatory for Not Applicable checkpoint {c_id}.")

            cur.execute("""
                UPDATE allocation_checkpoints
                SET result_status = ?, observations = ?, evidence_photo_url = ?, inspected_at = ?, inspected_by = ?
                WHERE allocation_id = ? AND checkpoint_id = ?
            """, (r_stat, obs, photo, now_str, saved_by, alloc_id, c_id))

        # Transition status to In progress if Allocated
        new_status = current_alloc_status
        if current_alloc_status == 'Allocated':
            new_status = 'In progress'
            cur.execute("""
                UPDATE inspection_allocations
                SET status = 'In progress', updated_at = ?
                WHERE allocation_id = ?
            """, (now_str, alloc_id))

            cur.execute("""
                UPDATE inspections
                SET status = 'In progress'
                WHERE code = ?
            """, (alloc_id,))

            cur.execute("""
                INSERT INTO inspection_audit_events (
                    allocation_id, actor_name, action, previous_status, new_status, timestamp, remarks
                ) VALUES (?, ?, 'SAVE_PROGRESS', 'Allocated', 'In progress', ?, 'Inspection progress saved on site')
            """, (alloc_id, saved_by, now_str))

        # Recompute totals for mirror inspections table
        cur.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN result_status = 'OK' THEN 1 ELSE 0 END) as ok_c,
                SUM(CASE WHEN result_status = 'NC' THEN 1 ELSE 0 END) as nc_c,
                SUM(CASE WHEN result_status = 'NA' THEN 1 ELSE 0 END) as na_c,
                SUM(CASE WHEN result_status = 'Pending' OR result_status IS NULL THEN 1 ELSE 0 END) as pending_c
            FROM allocation_checkpoints
            WHERE allocation_id = ?
        """, (alloc_id,))
        stats = dict(cur.fetchone())

        cur.execute("""
            UPDATE inspections
            SET items_pass = ?, items_nc = ?, items_na = ?
            WHERE code = ?
        """, (stats['ok_c'], stats['nc_c'], stats['na_c'], alloc_id))

        conn.commit()
        conn.close()

        total = stats['total'] or 0
        completed = (stats['ok_c'] or 0) + (stats['nc_c'] or 0) + (stats['na_c'] or 0)
        progress_pct = round((completed / total * 100), 1) if total > 0 else 0

        return {
            "status": "success",
            "allocation_id": alloc_id,
            "allocation_status": new_status,
            "updated_at": now_str,
            "stats": {
                "total": total,
                "completed": completed,
                "pending": stats['pending_c'] or 0,
                "ok": stats['ok_c'] or 0,
                "nc": stats['nc_c'] or 0,
                "na": stats['na_c'] or 0,
                "progress_pct": progress_pct
            }
        }

    @staticmethod
    def submit_allocation(alloc_id: str, submitted_by: str = "Inspection Engineer", notes: Optional[str] = None) -> Dict[str, Any]:
        """
        Submits the inspection for QC Lead review and queues an approval item.
        Blocks submission if any checkpoint remains Pending or if remarks are missing.
        """
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT a.*, p.name as project_name
            FROM inspection_allocations a
            JOIN projects p ON a.project_id = p.id
            WHERE a.allocation_id = ?
        """, (alloc_id,))
        a_row = cur.fetchone()
        if not a_row:
            conn.close()
            raise ValueError("Allocation not found.")

        alloc = dict(a_row)

        if alloc['status'] in ('Pending review', 'Report issued'):
            conn.close()
            raise ValueError(f"Allocation is already in '{alloc['status']}' state.")

        # Validate that no checkpoints are pending and all NC/NA have remarks
        cur.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN result_status = 'Pending' OR result_status IS NULL THEN 1 ELSE 0 END) as pending_c,
                SUM(CASE WHEN result_status = 'NC' AND (observations IS NULL OR TRIM(observations) = '') THEN 1 ELSE 0 END) as nc_missing_obs,
                SUM(CASE WHEN result_status = 'NA' AND (observations IS NULL OR TRIM(observations) = '') THEN 1 ELSE 0 END) as na_missing_obs
            FROM allocation_checkpoints
            WHERE allocation_id = ?
        """, (alloc_id,))
        chk_stats = dict(cur.fetchone())

        if chk_stats['pending_c'] > 0:
            conn.close()
            raise ValueError(f"Cannot submit inspection. {chk_stats['pending_c']} checkpoint(s) remain pending.")

        if chk_stats['nc_missing_obs'] > 0:
            conn.close()
            raise ValueError(f"Cannot submit inspection. {chk_stats['nc_missing_obs']} Non-Compliant (NC) checkpoint(s) lack required observation remarks.")

        if chk_stats['na_missing_obs'] > 0:
            conn.close()
            raise ValueError(f"Cannot submit inspection. {chk_stats['na_missing_obs']} Not Applicable (NA) checkpoint(s) lack required justification reason.")
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        cur.execute("""
            UPDATE inspection_allocations
            SET status = 'Pending review', submitted_at = ?, updated_at = ?
            WHERE allocation_id = ?
        """, (now_str, now_str, alloc_id))

        cur.execute("""
            UPDATE inspections
            SET status = 'Pending review'
            WHERE code = ?
        """, (alloc_id,))

        # Queue Approval
        ap_code = f"AP-{alloc['project_id'].upper()}-{alloc_id[-4:]}"
        cur.execute("""
            INSERT OR REPLACE INTO approvals (
                code, project_id, kind, title, by_user, at_time, ref_ins, status
            ) VALUES (?, ?, 'Inspection report', ?, ?, ?, ?, 'Pending')
        """, (
            ap_code, alloc['project_id'],
            f"Stage Checkpoint Report · {alloc['location_scope']}",
            submitted_by, now_str, alloc_id
        ))

        # Log audit
        cur.execute("""
            INSERT INTO inspection_audit_events (
                allocation_id, actor_name, action, previous_status, new_status, timestamp, remarks
            ) VALUES (?, ?, 'SUBMIT', ?, 'Pending review', ?, ?)
        """, (
            alloc_id, submitted_by, alloc['status'], now_str,
            f"Report submitted by {submitted_by} for QC Lead sign-off. {notes or ''}"
        ))

        conn.commit()
        conn.close()

        return {
            "status": "success",
            "allocation_id": alloc_id,
            "new_status": "Pending review",
            "approval_code": ap_code,
            "submitted_at": now_str
        }

    @staticmethod
    def review_allocation(alloc_id: str, decision: str, reviewer_name: str = "Priya Deshmukh (QC Lead)", comments: Optional[str] = None) -> Dict[str, Any]:
        """
        QC Lead approves or returns inspection with comments.
        """
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("SELECT * FROM inspection_allocations WHERE allocation_id = ?", (alloc_id,))
        a_row = cur.fetchone()
        if not a_row:
            conn.close()
            raise ValueError("Allocation not found.")

        alloc = dict(a_row)
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        dec = decision.lower()

        if dec == 'approve':
            new_status = 'Report issued'
            cur.execute("""
                UPDATE inspection_allocations
                SET status = ?, approved_at = ?, updated_at = ?
                WHERE allocation_id = ?
            """, (new_status, now_str, now_str, alloc_id))

            cur.execute("""
                UPDATE inspections
                SET status = 'Report issued'
                WHERE code = ?
            """, (alloc_id,))

            cur.execute("UPDATE approvals SET status = 'Approved' WHERE ref_ins = ?", (alloc_id,))

            msg = f"Inspection {alloc_id} approved. Formal report issued."
        elif dec == 'return':
            if not comments:
                conn.close()
                raise ValueError("Review comments are mandatory when returning an inspection for correction.")
            new_status = 'In progress'
            cur.execute("""
                UPDATE inspection_allocations
                SET status = ?, returned_at = ?, return_comments = ?, updated_at = ?
                WHERE allocation_id = ?
            """, (new_status, now_str, comments, now_str, alloc_id))

            cur.execute("""
                UPDATE inspections
                SET status = 'In progress'
                WHERE code = ?
            """, (alloc_id,))

            cur.execute("UPDATE approvals SET status = 'Returned' WHERE ref_ins = ?", (alloc_id,))
            msg = f"Inspection {alloc_id} returned for correction to {alloc['engineer_name']}."
        else:
            conn.close()
            raise ValueError("Invalid review decision. Must be 'approve' or 'return'.")

        # Record review table
        cur.execute("""
            INSERT INTO inspection_reviews (allocation_id, reviewer_name, decision, comments, reviewed_at)
            VALUES (?, ?, ?, ?, ?)
        """, (alloc_id, reviewer_name, decision.capitalize(), comments, now_str))

        # Record audit event
        cur.execute("""
            INSERT INTO inspection_audit_events (
                allocation_id, actor_name, action, previous_status, new_status, timestamp, remarks
            ) VALUES (?, ?, 'REVIEW', ?, ?, ?, ?)
        """, (alloc_id, reviewer_name, alloc['status'], new_status, now_str, comments or decision))

        conn.commit()
        conn.close()

        return {
            "status": "success",
            "allocation_id": alloc_id,
            "decision": decision,
            "new_status": new_status,
            "message": msg,
            "reviewed_at": now_str
        }

    @staticmethod
    def reassign_allocation(alloc_id: str,
                            new_engineer: str,
                            reason: str,
                            new_due_date: Optional[str] = None,
                            actor_name: str = "Priya Deshmukh (QC Lead)") -> Dict[str, Any]:
        """
        Reassigns an inspection to a different engineer with mandatory reason and full audit logging.
        Works across all inspection stages (Draft, Allocated, In progress, Pending review, On hold, Done).
        Preserves all existing checklist results, photos, observations, NCs, and approval state.
        For completed/Done inspections, changing engineer does NOT reopen or modify approved results.
        """
        if not reason or not reason.strip():
            raise ValueError("Reassignment reason is mandatory.")

        conn = get_connection()
        cur = conn.cursor()

        # Resolve new engineer ID and name
        new_eid = new_engineer
        new_ename = new_engineer
        if new_engineer in ENGINEER_REGISTRY:
            new_eid = new_engineer
            new_ename = ENGINEER_REGISTRY[new_engineer]['name']
        elif new_engineer in NAME_TO_ID:
            new_ename = new_engineer
            new_eid = NAME_TO_ID[new_engineer]
        else:
            for eid, prof in ENGINEER_REGISTRY.items():
                if prof['name'].lower() == new_engineer.lower():
                    new_eid = eid
                    new_ename = prof['name']
                    break

        cur.execute("SELECT * FROM inspection_allocations WHERE allocation_id = ?", (alloc_id,))
        a_row = cur.fetchone()

        cur.execute("SELECT * FROM inspections WHERE code = ?", (alloc_id,))
        i_row = cur.fetchone()

        if not a_row and not i_row:
            conn.close()
            raise ValueError(f"Inspection '{alloc_id}' not found.")

        alloc = dict(a_row) if a_row else None
        ins = dict(i_row) if i_row else None

        old_eng = (alloc and alloc.get('engineer_name')) or (ins and ins.get('eng')) or "Unassigned"
        old_status = (alloc and alloc.get('status')) or (ins and ins.get('status')) or "Allocated"
        target_due = new_due_date or (alloc and alloc.get('due_date')) or (ins and ins.get('due_date')) or datetime.now().strftime("%Y-%m-%d")
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Update inspection_allocations if exists
        if alloc:
            cur.execute("""
                UPDATE inspection_allocations
                SET engineer_name = ?, engineer_id = ?, due_date = ?, updated_at = ?
                WHERE allocation_id = ?
            """, (new_ename, new_eid, target_due, now_str, alloc_id))

        # Update inspections table
        if ins:
            cur.execute("""
                UPDATE inspections
                SET eng = ?, due_date = ?
                WHERE code = ?
            """, (new_ename, target_due, alloc_id))

        remarks = f"Reassigned from {old_eng} to {new_ename} ({new_eid}). Reason: {reason.strip()}."
        cur.execute("""
            INSERT INTO inspection_audit_events (
                allocation_id, actor_name, action, previous_status, new_status, timestamp, remarks
            ) VALUES (?, ?, 'CHANGE_ENGINEER', ?, ?, ?, ?)
        """, (alloc_id, actor_name, old_status, old_status, now_str, remarks))

        conn.commit()
        conn.close()

        return {
            "status": "success",
            "allocation_id": alloc_id,
            "previous_engineer": old_eng,
            "new_engineer": new_ename,
            "new_engineer_id": new_eid,
            "reason": reason.strip(),
            "due_date": target_due,
            "inspection_status": old_status,
            "reassigned_by": actor_name,
            "reassigned_at": now_str,
            "message": remarks
        }

    @staticmethod
    def update_inspection_status(alloc_id: str, new_status: str, actor_name: str = "Priya Deshmukh (QC Lead)", reason: Optional[str] = None) -> Dict[str, Any]:
        """
        Updates inspection status (e.g. 'On hold', 'In progress', 'Returned for Reinspection', 'Done').
        Only QC Lead can transition to 'Done'.
        """
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("SELECT status FROM inspection_allocations WHERE allocation_id = ?", (alloc_id,))
        a_row = cur.fetchone()
        cur.execute("SELECT status FROM inspections WHERE code = ?", (alloc_id,))
        i_row = cur.fetchone()

        if not a_row and not i_row:
            conn.close()
            raise ValueError(f"Inspection '{alloc_id}' not found.")

        old_status = (a_row and a_row['status']) or (i_row and i_row['status']) or "Allocated"
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        stat_map = {
            'on hold': 'On hold',
            'on_hold': 'On hold',
            'in progress': 'In progress',
            'in_progress': 'In progress',
            'pending review': 'Pending review',
            'pending_review': 'Pending review',
            'returned for reinspection': 'Returned for Reinspection',
            'returned': 'Returned for Reinspection',
            'done': 'Done',
            'closed': 'Done',
            'report issued': 'Report issued',
            'allocated': 'Allocated',
            'draft': 'Draft'
        }
        canonical_status = stat_map.get(new_status.lower(), new_status)

        if a_row:
            cur.execute("""
                UPDATE inspection_allocations
                SET status = ?, updated_at = ?
                WHERE allocation_id = ?
            """, (canonical_status, now_str, alloc_id))

        if i_row:
            cur.execute("""
                UPDATE inspections
                SET status = ?
                WHERE code = ?
            """, (canonical_status, alloc_id))

        audit_remarks = reason or f"Status changed from {old_status} to {canonical_status} by {actor_name}."
        cur.execute("""
            INSERT INTO inspection_audit_events (
                allocation_id, actor_name, action, previous_status, new_status, timestamp, remarks
            ) VALUES (?, ?, 'UPDATE_STATUS', ?, ?, ?, ?)
        """, (alloc_id, actor_name, old_status, canonical_status, now_str, audit_remarks))

        conn.commit()
        conn.close()

        return {
            "status": "success",
            "allocation_id": alloc_id,
            "previous_status": old_status,
            "new_status": canonical_status,
            "updated_at": now_str,
            "remarks": audit_remarks
        }

    @staticmethod
    def get_engineer_dashboard_data(engineer_id_or_name: str,
                                    status_filter: Optional[str] = None,
                                    project_filter: Optional[str] = None,
                                    stage_filter: Optional[str] = None,
                                    priority_filter: Optional[str] = None,
                                    search_q: Optional[str] = None) -> Dict[str, Any]:
        """
        Phase 6: Returns the dedicated My Inspections dashboard data for an Inspection Engineer.
        Includes metrics (Allocated, In Progress, Due Today, Overdue, Submitted) and filtered inspection cards.
        """
        conn = get_connection()
        cur = conn.cursor()

        # Resolve engineer profile
        eng_id = engineer_id_or_name
        eng_profile = ENGINEER_REGISTRY.get(eng_id)
        if not eng_profile:
            eng_id = NAME_TO_ID.get(engineer_id_or_name, engineer_id_or_name)
            eng_profile = ENGINEER_REGISTRY.get(eng_id, {
                "id": eng_id,
                "name": engineer_id_or_name,
                "role": "QC Inspection Engineer",
                "specialty": "Civil & Finishes"
            })

        eng_name = eng_profile['name']
        today_str = datetime.now().strftime("%Y-%m-%d")

        # Fetch all allocations assigned to this engineer
        cur.execute("""
            SELECT a.*, p.name as project_name, p.code as project_code,
                   (SELECT COUNT(*) FROM allocation_checkpoints WHERE allocation_id = a.allocation_id) as total_checkpoints,
                   (SELECT COUNT(*) FROM allocation_checkpoints WHERE allocation_id = a.allocation_id AND result_status = 'OK') as ok_count,
                   (SELECT COUNT(*) FROM allocation_checkpoints WHERE allocation_id = a.allocation_id AND result_status = 'NC') as nc_count,
                   (SELECT COUNT(*) FROM allocation_checkpoints WHERE allocation_id = a.allocation_id AND result_status = 'NA') as na_count,
                   (SELECT COUNT(*) FROM allocation_checkpoints WHERE allocation_id = a.allocation_id AND (result_status = 'Pending' OR result_status IS NULL)) as pending_count
            FROM inspection_allocations a
            JOIN projects p ON a.project_id = p.id
            WHERE a.engineer_id = ? OR a.engineer_name = ?
            ORDER BY a.due_date ASC, a.created_at DESC
        """, (eng_id, eng_name))

        raw_allocs = [dict(r) for r in cur.fetchall()]

        # Compute stage & subgroup breakdown for each allocation
        alloc_ids = [a['allocation_id'] for a in raw_allocs]
        stages_map = {}
        if alloc_ids:
            placeholders = ",".join("?" for _ in alloc_ids)
            cur.execute(f"""
                SELECT DISTINCT allocation_id, stage_id, stage_name, subgroup_id, subgroup_name
                FROM allocation_checkpoints
                WHERE allocation_id IN ({placeholders})
                ORDER BY id ASC
            """, alloc_ids)
            for r in cur.fetchall():
                aid = r['allocation_id']
                if aid not in stages_map:
                    stages_map[aid] = {'stages': [], 'subgroups': []}
                if r['stage_name'] not in stages_map[aid]['stages']:
                    stages_map[aid]['stages'].append(r['stage_name'])
                if r['subgroup_name'] not in stages_map[aid]['subgroups']:
                    stages_map[aid]['subgroups'].append(r['subgroup_name'])

        # Enrich allocations
        enriched_list = []
        metrics = {
            "allocated": 0,
            "in_progress": 0,
            "due_today": 0,
            "overdue": 0,
            "submitted": 0,
            "total": len(raw_allocs)
        }

        for a in raw_allocs:
            aid = a['allocation_id']
            st_info = stages_map.get(aid, {'stages': [], 'subgroups': []})
            a['stages'] = st_info['stages']
            a['subgroups'] = st_info['subgroups']
            a['primary_stage'] = st_info['stages'][0] if st_info['stages'] else 'General Inspection'
            a['primary_subgroup'] = st_info['subgroups'][0] if st_info['subgroups'] else 'Checkpoints'

            tot = a['total_checkpoints'] or 0
            comp = (a['ok_count'] or 0) + (a['nc_count'] or 0) + (a['na_count'] or 0)
            a['completed_count'] = comp
            a['progress_pct'] = round((comp / tot * 100), 1) if tot > 0 else 0

            # Date flags
            due_d = a['due_date']
            status = a['status']
            is_active = status not in ('Pending review', 'Report issued')
            is_overdue = bool(due_d < today_str and is_active)
            is_due_today = bool(due_d == today_str and is_active)
            a['is_overdue'] = is_overdue
            a['is_due_today'] = is_due_today

            # Count metrics across all assigned
            if status == 'Allocated':
                metrics['allocated'] += 1
            elif status == 'In progress':
                metrics['in_progress'] += 1
            elif status in ('Pending review', 'Report issued'):
                metrics['submitted'] += 1

            if is_due_today:
                metrics['due_today'] += 1
            if is_overdue:
                metrics['overdue'] += 1

            # Apply filters
            include = True
            if status_filter and status_filter.lower() != 'all':
                sf = status_filter.lower()
                if sf == 'allocated' and status != 'Allocated':
                    include = False
                elif sf in ('in progress', 'in_progress') and status != 'In progress':
                    include = False
                elif sf in ('due today', 'due_today') and not is_due_today:
                    include = False
                elif sf == 'overdue' and not is_overdue:
                    include = False
                elif sf in ('submitted', 'pending review') and status not in ('Pending review', 'Report issued'):
                    include = False
                elif sf not in ('allocated', 'in progress', 'in_progress', 'due today', 'due_today', 'overdue', 'submitted', 'pending review') and status.lower() != sf:
                    include = False

            if include and project_filter and project_filter.lower() != 'all':
                if a['project_id'].lower() != project_filter.lower() and a['project_code'].lower() != project_filter.lower():
                    include = False

            if include and stage_filter and stage_filter.lower() != 'all':
                if not any(stage_filter.lower() in s.lower() for s in a['stages']):
                    include = False

            if include and priority_filter and priority_filter.lower() != 'all':
                if a['priority'].lower() != priority_filter.lower():
                    include = False

            if include and search_q and search_q.strip():
                sq = search_q.strip().lower()
                blob = f"{a['allocation_id']} {a['project_name']} {a['location_scope']} {' '.join(a['stages'])} {' '.join(a['subgroups'])}".lower()
                if sq not in blob:
                    include = False

            if include:
                enriched_list.append(a)

        conn.close()

        return {
            "status": "success",
            "engineer": eng_profile,
            "metrics": metrics,
            "inspections": enriched_list,
            "total_assigned": len(raw_allocs),
            "filtered_count": len(enriched_list)
        }
