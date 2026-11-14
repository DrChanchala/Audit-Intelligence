import uuid
import json
from datetime import datetime, timedelta
from database import get_db, init_db, reset_db

def seed_all_data():
    reset_db()
    conn = get_db()
    cursor = conn.cursor()

    # Clear existing data
    tables = [
        "projects", "towers", "stages", "substages", "activities",
        "progress_updates", "inspections", "rfis", "ncrs",
        "safety_records", "materials", "material_requisitions",
        "cameras", "camera_coverage", "ai_camera_observations",
        "field_visits", "field_photos", "image_validations",
        "ai_observations", "pm_reviews", "progress_snapshots",
        "schedule_baselines", "audit_logs"
    ]
    for table in tables:
        try:
            cursor.execute(f"DELETE FROM {table}")
        except Exception:
            pass

    print("Seeding PyCray_SiteIQ Dual-Mode data...")

    # 1. Project
    project_id = "PROJ-001"
    cursor.execute("""
        INSERT INTO projects (id, name, code, location, planned_start, planned_finish, contract_value, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        project_id,
        "Grand Horizon Residential Towers",
        "GHR-RES-2026",
        "Plot 42, Sector 15, Metro Boulevard",
        "2025-01-15",
        "2027-06-30",
        24500000.0,
        "In Progress"
    ))

    # 2. Towers
    towers = [
        ("TOW-A", project_id, "Tower A (20 Floors)", "TOW-A", 20, 50.0),
        ("TOW-B", project_id, "Tower B (15 Floors)", "TOW-B", 15, 50.0)
    ]
    cursor.executemany("""
        INSERT INTO towers (id, project_id, name, code, total_floors, weightage)
        VALUES (?, ?, ?, ?, ?, ?)
    """, towers)

    # 3. Default 10 Stages with baseline weightages totaling 100%
    stages_data = [
        ("STG-01", project_id, 1, "Pre-Construction & Mobilization", 2.0, "STG-01", "Approvals, site office, utilities & mobilization"),
        ("STG-02", project_id, 2, "Site Preparation & Earthwork", 5.0, "STG-02", "Site clearing, excavation, grading & backfilling"),
        ("STG-03", project_id, 3, "Foundation & Substructure", 12.0, "STG-03", "PCC, Footings, Raft, Piles, Basement & Ground Slab"),
        ("STG-04", project_id, 4, "Superstructure", 25.0, "STG-04", "Columns, Beams, Slabs, Staircases & Structural Walls"),
        ("STG-05", project_id, 5, "Masonry & Building Envelope", 10.0, "STG-05", "Blockwork, Plaster, Façade, Doors, Windows & Glazing"),
        ("STG-06", project_id, 6, "MEP Services", 12.0, "STG-06", "Electrical, Plumbing, HVAC & Fire Fighting systems"),
        ("STG-07", project_id, 7, "Internal Finishes", 15.0, "STG-07", "Flooring, Wall tiles, Painting, False ceiling & Fixtures"),
        ("STG-08", project_id, 8, "External Development", 6.0, "STG-08", "Internal roads, Stormwater, Rainwater harvesting & Landscape"),
        ("STG-09", project_id, 9, "Testing & Commissioning", 5.0, "STG-09", "Electrical, Plumbing, HVAC, Fire & Lift commissioning"),
        ("STG-10", project_id, 10, "Final Inspection & Handover", 8.0, "STG-10", "Snagging, As-built drawings, Statutory approvals & Handover")
    ]
    cursor.executemany("""
        INSERT INTO stages (id, project_id, stage_number, name, weightage, code, description)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, stages_data)

    # 4. Substages
    substages_data = [
        ("SUB-01-1", "STG-01", "Approvals & Permitting", "SUB-01-1", 0.5),
        ("SUB-01-2", "STG-01", "Site Office & Utilities", "SUB-01-2", 0.8),
        ("SUB-01-3", "STG-01", "Equipment & Labour Mobilization", "SUB-01-3", 0.7),
        ("SUB-02-1", "STG-02", "Site Clearing & Grading", "SUB-02-1", 1.5),
        ("SUB-02-2", "STG-02", "Foundation Excavation", "SUB-02-2", 2.0),
        ("SUB-02-3", "STG-02", "Backfilling & Compaction", "SUB-02-3", 1.5),
        ("SUB-03-1", "STG-03", "PCC & Footings", "SUB-03-1", 3.0),
        ("SUB-03-2", "STG-03", "Raft Foundation & Piling", "SUB-03-2", 5.0),
        ("SUB-03-3", "STG-03", "Basement Retaining Walls & Slab", "SUB-03-3", 4.0),
        ("SUB-04-1", "STG-04", "Columns & Structural Walls", "SUB-04-1", 8.0),
        ("SUB-04-2", "STG-04", "Beams & Slabs", "SUB-04-2", 14.0),
        ("SUB-04-3", "STG-04", "Staircases", "SUB-04-3", 3.0),
        ("SUB-05-1", "STG-05", "Internal & External Masonry", "SUB-05-1", 5.0),
        ("SUB-05-2", "STG-05", "Internal & External Plaster", "SUB-05-2", 3.0),
        ("SUB-05-3", "STG-05", "Façade & Windows", "SUB-05-3", 2.0),
        ("SUB-06-1", "STG-06", "Electrical Conduits & Wiring", "SUB-06-1", 3.5),
        ("SUB-06-2", "STG-06", "Plumbing & Drainage Piping", "SUB-06-2", 3.5),
        ("SUB-06-3", "STG-06", "HVAC Ducting & Piping", "SUB-06-3", 2.5),
        ("SUB-06-4", "STG-06", "Fire Fighting Systems", "SUB-06-4", 2.5),
        ("SUB-07-1", "STG-07", "Tile & Stone Flooring", "SUB-07-1", 6.0),
        ("SUB-07-2", "STG-07", "Internal & External Painting", "SUB-07-2", 4.0),
        ("SUB-07-3", "STG-07", "Doors, Windows & False Ceiling", "SUB-07-3", 5.0),
        ("SUB-08-1", "STG-08", "Internal Roads & Paving", "SUB-08-1", 2.0),
        ("SUB-08-2", "STG-08", "Stormwater & Rainwater Harvesting", "SUB-08-2", 2.0),
        ("SUB-08-3", "STG-08", "Landscape & Irrigation", "SUB-08-3", 2.0),
        ("SUB-09-1", "STG-09", "MEP Systems Testing", "SUB-09-1", 2.5),
        ("SUB-09-2", "STG-09", "Fire & Lift Commissioning", "SUB-09-2", 2.5),
        ("SUB-10-1", "STG-10", "Snagging & Rectification", "SUB-10-1", 4.0),
        ("SUB-10-2", "STG-10", "Statutory Approvals & Handover", "SUB-10-2", 4.0)
    ]
    cursor.executemany("""
        INSERT INTO substages (id, stage_id, name, code, weightage)
        VALUES (?, ?, ?, ?, ?)
    """, substages_data)

    # 5. Granular Activities (With 4 progress streams populated)
    # Schema columns: id, activity_code, name, description, project_id, tower_id, floor_level, zone, unit, room,
    # discipline, trade, boq_item, boq_description, stage_id, substage_id, responsible_role, responsible_engineer,
    # contractor, planned_qty, reported_qty, inspected_qty, accepted_qty, uom, unit_cost, weightage,
    # planned_start, planned_finish, planned_duration, predecessor, dependency_type, actual_start, actual_finish,
    # status, inspection_status, rfi_status, ncr_status, camera_ref, remarks,
    # planned_progress_pct, ai_automated_progress_pct, ai_automated_confidence, field_observed_progress_pct, pm_approved_progress_pct

    activities = []

    # Completed Stage 1 & 2
    activities.append((
        "ACT-STG1-01", "ACT-STG1-01", "Municipal Building Permit & Design Approval", "Obtain approvals",
        project_id, None, 0, "Site", None, None, "General", "Management", "BOQ-01-01", "Approvals",
        "STG-01", "SUB-01-1", "Project Manager", "Er. Robert Vance", "Apex Contractors",
        1.0, 1.0, 1.0, 1.0, "Milestone", 50000.0, 0.5,
        "2025-01-15", "2025-02-01", 17, "", "FS", "2025-01-15", "2025-01-30",
        "Completed", "Accepted", "None", "None", "CAM-SITE-01", "Permits approved",
        100.0, 100.0, 0.98, 100.0, 100.0
    ))
    activities.append((
        "ACT-STG1-02", "ACT-STG1-02", "Site Office & Temporary Power/Water Setup", "Site setup",
        project_id, None, 0, "Site", None, None, "General", "Civil", "BOQ-01-02", "Mobilization",
        "STG-01", "SUB-01-2", "Civil Engineer", "Er. Ankit Sharma", "Apex Contractors",
        1.0, 1.0, 1.0, 1.0, "LS", 120000.0, 0.8,
        "2025-02-01", "2025-02-20", 20, "ACT-STG1-01", "FS", "2025-02-01", "2025-02-18",
        "Completed", "Accepted", "None", "None", "CAM-SITE-01", "Utilities connected",
        100.0, 100.0, 0.96, 100.0, 100.0
    ))
    activities.append((
        "ACT-STG1-03", "ACT-STG1-03", "Heavy Machinery & Labour Mobilization", "Tower cranes & equipment",
        project_id, None, 0, "Site", None, None, "General", "Logistics", "BOQ-01-03", "Plant",
        "STG-01", "SUB-01-3", "Supervisor", "Er. Ankit Sharma", "Apex Contractors",
        1.0, 1.0, 1.0, 1.0, "LS", 80000.0, 0.7,
        "2025-02-15", "2025-03-01", 14, "ACT-STG1-02", "FS", "2025-02-15", "2025-02-28",
        "Completed", "Accepted", "None", "None", "CAM-SITE-01", "Cranes assembled",
        100.0, 100.0, 0.95, 100.0, 100.0
    ))

    # Stage 2 Excavation
    activities.append((
        "ACT-STG2-01", "ACT-STG2-01", "Site Clearing & Debris Removal", "Clear site surface",
        project_id, None, 0, "Site", None, None, "Civil", "Earthwork", "BOQ-02-01", "Clearing",
        "STG-02", "SUB-02-1", "Civil Engineer", "Er. Ankit Sharma", "EarthWorks Ltd",
        15000.0, 15000.0, 15000.0, 15000.0, "m²", 15.0, 1.5,
        "2025-03-01", "2025-03-20", 20, "ACT-STG1-03", "FS", "2025-03-01", "2025-03-18",
        "Completed", "Accepted", "None", "None", "CAM-SITE-01", "Cleared",
        100.0, 100.0, 0.99, 100.0, 100.0
    ))
    activities.append((
        "ACT-STG2-02", "ACT-STG2-02", "Foundation Deep Excavation", "Basement excavation",
        project_id, None, 0, "Basement", None, None, "Civil", "Earthwork", "BOQ-02-02", "Deep Excavation",
        "STG-02", "SUB-02-2", "Structural Engineer", "Er. David Chen", "EarthWorks Ltd",
        45000.0, 45000.0, 45000.0, 45000.0, "m³", 35.0, 2.0,
        "2025-03-20", "2025-04-30", 41, "ACT-STG2-01", "FS", "2025-03-20", "2025-04-28",
        "Completed", "Accepted", "None", "None", "CAM-SITE-02", "Excavated",
        100.0, 100.0, 0.97, 100.0, 100.0
    ))
    activities.append((
        "ACT-STG2-03", "ACT-STG2-03", "Backfilling & Soil Compaction", "Perimeter backfilling",
        project_id, None, 0, "Basement", None, None, "Civil", "Earthwork", "BOQ-02-03", "Backfill",
        "STG-02", "SUB-02-3", "Civil Engineer", "Er. Ankit Sharma", "EarthWorks Ltd",
        12000.0, 12000.0, 12000.0, 12000.0, "m³", 25.0, 1.5,
        "2025-05-01", "2025-05-20", 20, "ACT-STG2-02", "FS", "2025-05-01", "2025-05-19",
        "Completed", "Accepted", "None", "None", "CAM-SITE-02", "Compacted",
        100.0, 100.0, 0.95, 100.0, 100.0
    ))

    # Stage 3 Foundation
    activities.append((
        "ACT-STG3-01", "ACT-STG3-01", "PCC Bedding Layer Placement", "Plain Cement Concrete",
        project_id, "TOW-A", 0, "Basement", None, None, "Structural", "Concrete", "BOQ-03-01", "PCC",
        "STG-03", "SUB-03-1", "Civil Engineer", "Er. David Chen", "BuildPro Concrete",
        1200.0, 1200.0, 1200.0, 1200.0, "m³", 120.0, 3.0,
        "2025-05-21", "2025-06-10", 20, "ACT-STG2-03", "FS", "2025-05-21", "2025-06-08",
        "Completed", "Accepted", "None", "None", "CAM-T01-01", "Poured",
        100.0, 100.0, 0.98, 100.0, 100.0
    ))
    activities.append((
        "ACT-STG3-02", "ACT-STG3-02", "Raft Foundation Reinforcement & Concrete Casting", "Raft 2.5m thick",
        project_id, "TOW-A", 0, "Basement", None, None, "Structural", "Concrete", "BOQ-03-02", "Raft Slab",
        "STG-03", "SUB-03-2", "Structural Engineer", "Er. David Chen", "BuildPro Concrete",
        4500.0, 4500.0, 4500.0, 4500.0, "m³", 180.0, 5.0,
        "2025-06-11", "2025-07-25", 44, "ACT-STG3-01", "FS", "2025-06-11", "2025-07-24",
        "Completed", "Accepted", "None", "None", "CAM-T01-01", "Raft completed",
        100.0, 100.0, 0.98, 100.0, 100.0
    ))
    activities.append((
        "ACT-STG3-03", "ACT-STG3-03", "Basement Retaining Walls & Slab Concrete", "Retaining wall",
        project_id, "TOW-A", 0, "Basement", None, None, "Structural", "Concrete", "BOQ-03-03", "Retaining Wall",
        "STG-03", "SUB-03-3", "Civil Engineer", "Er. David Chen", "BuildPro Concrete",
        2800.0, 2800.0, 2800.0, 2800.0, "m³", 210.0, 4.0,
        "2025-07-26", "2025-09-10", 46, "ACT-STG3-02", "FS", "2025-07-26", "2025-09-08",
        "Completed", "Accepted", "None", "None", "CAM-T01-01", "Basement complete",
        100.0, 100.0, 0.97, 100.0, 100.0
    ))

    # Stage 4 Superstructure: Tower A Floors 1 to 11 (Completed)
    for lvl in range(1, 12):
        activities.append((
            f"ACT-TOWA-L{lvl}-COL", f"ACT-TOWA-L{lvl}-COL", f"Tower A Level {lvl} Column Reinforcement & Concrete",
            f"Columns L{lvl}", project_id, "TOW-A", lvl, "Core", None, None, "Structural", "Concrete",
            f"BOQ-04-C{lvl}", "Columns", "STG-04", "SUB-04-1", "Civil Engineer", "Er. David Chen", "BuildPro Concrete",
            120.0, 120.0, 120.0, 120.0, "m³", 250.0, 0.4,
            "2025-09-15", "2025-09-25", 10, "", "FS", "2025-09-15", "2025-09-24",
            "Completed", "Accepted", "None", "None", "CAM-T01-12", "Cast",
            100.0, 100.0, 0.96, 100.0, 100.0
        ))
        activities.append((
            f"ACT-TOWA-L{lvl}-SLAB", f"ACT-TOWA-L{lvl}-SLAB", f"Tower A Level {lvl} Slab Formwork, Rebar & Concrete",
            f"Slab L{lvl}", project_id, "TOW-A", lvl, "Core", None, None, "Structural", "Concrete",
            f"BOQ-04-S{lvl}", "Slab", "STG-04", "SUB-04-2", "Structural Engineer", "Er. David Chen", "BuildPro Concrete",
            150.0, 150.0, 150.0, 150.0, "m³", 240.0, 0.6,
            "2025-09-26", "2025-10-10", 14, f"ACT-TOWA-L{lvl}-COL", "FS", "2025-09-26", "2025-10-09",
            "Completed", "Accepted", "None", "None", "CAM-T01-12", "Cast",
            100.0, 100.0, 0.96, 100.0, 100.0
        ))

    # Stage 4 Active Floor: Tower A Level 12 (Core demo scenario showing 4-way variance!)
    # Planned = 100%, AI Automated = 76.0%, Field Observed = 75.0%, PM Approved = 72.0%
    activities.append((
        "ACT-TOWA-L12-COL", "ACT-TOWA-L12-COL", "Tower A Level 12 Column Reinforcement & Concrete",
        "Columns L12", project_id, "TOW-A", 12, "Core", None, None, "Structural", "Concrete",
        "BOQ-04-C12", "Columns", "STG-04", "SUB-04-1", "Civil Engineer", "Er. David Chen", "BuildPro Concrete",
        120.0, 120.0, 120.0, 120.0, "m³", 250.0, 0.4,
        "2026-09-01", "2026-09-10", 9, "", "FS", "2026-09-01", "2026-09-09",
        "Completed", "Accepted", "None", "None", "CAM-T01-12", "Cast",
        100.0, 100.0, 0.95, 100.0, 100.0
    ))
    activities.append((
        "ACT-TOWA-L12-SLAB", "ACT-TOWA-L12-SLAB", "Tower A Level 12 Slab Formwork, Rebar & Concrete",
        "Slab L12 active", project_id, "TOW-A", 12, "Core", "Unit 12B", "Balcony", "Structural", "Concrete",
        "BOQ-04-S12", "Slab", "STG-04", "SUB-04-2", "Structural Engineer", "Er. David Chen", "BuildPro Concrete",
        150.0, 120.0, 115.0, 115.0, "m³", 240.0, 1.5,
        "2026-09-11", "2026-09-20", 9, "ACT-TOWA-L12-COL", "FS", "2026-09-11", None,
        "In Progress", "Pending QA/QC", "RFI-TOWA-104", "NCR-TOWA-012", "CAM-T01-12", "Active deck",
        68.0, 76.0, 0.91, 75.0, 72.0
    ))

    # Tower A Floors 13-20 (Not Started)
    for lvl in range(13, 21):
        activities.append((
            f"ACT-TOWA-L{lvl}-SLAB", f"ACT-TOWA-L{lvl}-SLAB", f"Tower A Level {lvl} Slab Formwork, Rebar & Concrete",
            f"Slab L{lvl}", project_id, "TOW-A", lvl, "Core", None, None, "Structural", "Concrete",
            f"BOQ-04-S{lvl}", "Slab", "STG-04", "SUB-04-2", "Structural Engineer", "Er. David Chen", "BuildPro Concrete",
            150.0, 0.0, 0.0, 0.0, "m³", 240.0, 0.6,
            "2026-10-01", "2026-10-15", 14, "", "FS", None, None,
            "Not Started", "Not Requested", "None", "None", "CAM-T01-12", "Scheduled",
            0.0, 0.0, 0.0, 0.0, 0.0
        ))

    # Tower B Levels 1 to 10 (Stage 4 Completed)
    for lvl in range(1, 11):
        activities.append((
            f"ACT-TOWB-L{lvl}-SLAB", f"ACT-TOWB-L{lvl}-SLAB", f"Tower B Level {lvl} Slab Concrete",
            f"Slab L{lvl}", project_id, "TOW-B", lvl, "Core", None, None, "Structural", "Concrete",
            f"BOQ-B-S{lvl}", "Slab", "STG-04", "SUB-04-2", "Civil Engineer", "Er. David Chen", "BuildPro Concrete",
            140.0, 140.0, 140.0, 140.0, "m³", 240.0, 0.5,
            "2025-10-01", "2025-10-15", 14, "", "FS", "2025-10-01", "2025-10-14",
            "Completed", "Accepted", "None", "None", "CAM-T02-08", "Cast",
            100.0, 100.0, 0.97, 100.0, 100.0
        ))
    for lvl in range(11, 16):
        activities.append((
            f"ACT-TOWB-L{lvl}-SLAB", f"ACT-TOWB-L{lvl}-SLAB", f"Tower B Level {lvl} Slab Concrete",
            f"Slab L{lvl}", project_id, "TOW-B", lvl, "Core", None, None, "Structural", "Concrete",
            f"BOQ-B-S{lvl}", "Slab", "STG-04", "SUB-04-2", "Civil Engineer", "Er. David Chen", "BuildPro Concrete",
            140.0, 0.0, 0.0, 0.0, "m³", 240.0, 0.5,
            "2026-11-01", "2026-11-15", 14, "", "FS", None, None,
            "Not Started", "Not Requested", "None", "None", "CAM-T02-08", "Scheduled",
            0.0, 0.0, 0.0, 0.0, 0.0
        ))

    # Stage 5 Masonry (Active on Level 5 & Level 11)
    activities.append((
        "ACT-TOWA-L05-MAS", "ACT-L05-MAS-001", "Tower A Level 5 Internal Masonry & Partition Walls",
        "Blockwork L5", project_id, "TOW-A", 5, "Internal", "Unit 5B", "Living", "Architectural", "Masonry",
        "BOQ-05-01", "AAC Blockwork 150mm", "STG-05", "SUB-05-1", "Site Engineer", "Er. Priya Nair", "Masonry Masters",
        180.0, 135.0, 125.0, 120.0, "m²", 48.0, 2.5,
        "2026-09-10", "2026-09-20", 10, "", "FS", "2026-09-10", None,
        "In Progress", "Pending QA/QC", "None", "None", "CAM-T01-01", "Prompt example activity",
        70.0, 72.0, 0.88, 75.0, 69.0
    ))
    activities.append((
        "ACT-TOWA-L11-MAS", "ACT-TOWA-L11-MAS", "Tower A Level 11 External AAC Blockwork",
        "Blockwork L11", project_id, "TOW-A", 11, "Facade", None, None, "Architectural", "Masonry",
        "BOQ-05-02", "External Blockwork", "STG-05", "SUB-05-1", "Site Engineer", "Er. Priya Nair", "Masonry Masters",
        800.0, 600.0, 560.0, 560.0, "m²", 45.0, 2.5,
        "2026-08-15", "2026-09-05", 21, "", "FS", "2026-08-15", None,
        "In Progress", "Accepted", "None", "None", "CAM-T01-12", "70% accepted",
        100.0, 78.0, 0.90, 75.0, 70.0
    ))

    # Stage 6 MEP
    activities.append((
        "ACT-MEP-ELEC-01", "ACT-MEP-ELEC-01", "Tower A Electrical Conduits & Cable Trays (L1-L10)",
        "Wiring L1-L10", project_id, "TOW-A", 10, "Core", None, None, "Electrical", "MEP",
        "BOQ-06-01", "Conduits", "STG-06", "SUB-06-1", "MEP Engineer", "Er. Vikram Sen", "VoltTech MEP",
        3500.0, 2800.0, 2600.0, 2600.0, "m", 30.0, 3.5,
        "2026-07-01", "2026-09-30", 91, "", "FS", "2026-07-01", None,
        "In Progress", "Accepted", "None", "None", "CAM-T01-12", "Wiring in progress",
        85.0, 78.0, 0.86, 80.0, 74.0
    ))
    activities.append((
        "ACT-MEP-PLUMB-01", "ACT-MEP-PLUMB-01", "Tower A Water Supply & Drainage Vertical Riser Piping",
        "Riser piping", project_id, "TOW-A", 10, "Core", None, None, "Plumbing", "MEP",
        "BOQ-06-02", "Risers", "STG-06", "SUB-06-2", "MEP Engineer", "Er. Vikram Sen", "AquaFlow Systems",
        1800.0, 1400.0, 1350.0, 1350.0, "m", 50.0, 3.5,
        "2026-07-15", "2026-10-15", 92, "", "FS", "2026-07-15", None,
        "In Progress", "Accepted", "RFI-MEP-045", "None", "CAM-T01-12", "Risers installed",
        70.0, 74.0, 0.88, 77.0, 75.0
    ))

    # Stage 7 Finishes
    activities.append((
        "ACT-FIN-TILE-01", "ACT-FIN-TILE-01", "Tower A Vitrified Floor Tiling (Levels 1 to 6)",
        "Floor tiles", project_id, "TOW-A", 6, "Internal", None, None, "Finishes", "Architectural",
        "BOQ-07-01", "Vitrified Tile", "STG-07", "SUB-07-1", "Civil Engineer", "Er. Ankit Sharma", "FinishPro Interiors",
        4500.0, 2200.0, 2000.0, 2000.0, "m²", 65.0, 5.0,
        "2026-08-01", "2026-11-30", 121, "", "FS", "2026-08-01", None,
        "In Progress", "Accepted", "RFI-FIN-012", "None", "CAM-T01-12", "Flooring",
        45.0, 48.0, 0.84, 49.0, 44.0
    ))

    # Stage 8 External
    activities.append((
        "ACT-EXT-ROAD-01", "ACT-EXT-ROAD-01", "Internal Asphalt Roads & Paver Block Driveways",
        "Road paving", project_id, None, 0, "External", None, None, "Civil", "Infrastructure",
        "BOQ-08-01", "Asphalt Road", "STG-08", "SUB-08-1", "Civil Engineer", "Er. Ankit Sharma", "RoadTech Infra",
        2500.0, 800.0, 750.0, 750.0, "m²", 80.0, 2.0,
        "2026-08-01", "2026-12-15", 136, "", "FS", "2026-08-01", None,
        "In Progress", "Accepted", "None", "None", "CAM-SITE-01", "Sub-base laid",
        35.0, 32.0, 0.82, 32.0, 30.0
    ))
    activities.append((
        "ACT-EXT-STORM-01", "ACT-EXT-STORM-01", "Stormwater Drains & Rainwater Harvesting Recharges",
        "Drains", project_id, None, 0, "External", None, None, "Civil", "Infrastructure",
        "BOQ-08-02", "Storm Drain", "STG-08", "SUB-08-2", "Civil Engineer", "Er. Ankit Sharma", "RoadTech Infra",
        800.0, 500.0, 480.0, 480.0, "m", 110.0, 2.0,
        "2026-07-15", "2026-11-15", 123, "", "FS", "2026-07-15", None,
        "In Progress", "Accepted", "None", "None", "CAM-SITE-02", "Active",
        55.0, 62.0, 0.85, 62.0, 60.0
    ))

    # Stage 9 & 10 Not Started
    activities.append((
        "ACT-STG9-01", "ACT-STG9-01", "Integrated System Electrical & Lift Commissioning",
        "Commissioning", project_id, None, 0, "All", None, None, "MEP", "Testing",
        "BOQ-09-01", "Commissioning", "STG-09", "SUB-09-2", "MEP Engineer", "Er. Vikram Sen", "VoltTech MEP",
        1.0, 0.0, 0.0, 0.0, "Milestone", 100000.0, 5.0,
        "2027-02-01", "2027-04-15", 73, "", "FS", None, None,
        "Not Started", "Not Requested", "None", "None", "CAM-SITE-01", "Scheduled",
        0.0, 0.0, 0.0, 0.0, 0.0
    ))
    activities.append((
        "ACT-STG10-01", "ACT-STG10-01", "Final Snag Rectification & Client Handover",
        "Handover", project_id, None, 0, "All", None, None, "General", "Management",
        "BOQ-10-01", "Handover", "STG-10", "SUB-10-2", "Project Manager", "Er. Robert Vance", "Apex Contractors",
        1.0, 0.0, 0.0, 0.0, "Milestone", 50000.0, 8.0,
        "2027-04-16", "2027-06-30", 75, "ACT-STG9-01", "FS", None, None,
        "Not Started", "Not Requested", "None", "None", "CAM-SITE-01", "Scheduled",
        0.0, 0.0, 0.0, 0.0, 0.0
    ))

    cursor.executemany("""
        INSERT INTO activities (
            id, activity_code, name, description, project_id, tower_id, floor_level, zone, unit, room,
            discipline, trade, boq_item, boq_description, stage_id, substage_id, responsible_role, responsible_engineer,
            contractor, planned_qty, reported_qty, inspected_qty, accepted_qty, uom, unit_cost, weightage,
            planned_start, planned_finish, planned_duration, predecessor, dependency_type, actual_start, actual_finish,
            status, inspection_status, rfi_status, ncr_status, camera_ref, remarks,
            planned_progress_pct, ai_automated_progress_pct, ai_automated_confidence, field_observed_progress_pct, pm_approved_progress_pct
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, activities)

    # 6. Pre-populated Schedule Baseline
    cursor.execute("""
        INSERT INTO schedule_baselines (
            id, project_id, version, filename, uploaded_by, status,
            total_activities, total_weight, validation_errors, validation_warnings,
            validation_report, uploaded_at, confirmed_at, confirmed_by, notes
        ) VALUES (
            'BASE-REV-001', 'PROJ-001', 1, 'BuildTrack_L4_Master_Schedule.xlsx',
            'Project Manager', 'CONFIRMED', 311, 100.0, 0, 0,
            '{"summary": {"total_rows": 311, "valid_rows": 311, "error_rows": 0, "total_weight": 100.0, "weight_valid": true}}',
            '2026-09-01 10:00:00', '2026-09-01 10:15:00', 'Er. Robert Vance (PM)', 'Approved Baseline Rev 1.0'
        )
    """)

    # 7. Fixed Cameras with coverage
    cameras = [
        ("CAM-T01-12", "CAM-T01-12", "Tower A Level 12 North Façade", "TOW-A", 12, "North Façade", "North-West", "28.5355, 77.3910", "Levels 10-14", "Active", "https://images.unsplash.com/photo-1541888946425-d0fbb186a5b7?w=600", "2026-09-17 08:30:00"),
        ("CAM-T01-01", "CAM-T01-01", "Tower A Ground Level & Podiums", "TOW-A", 1, "Ground Lobby", "South", "28.5350, 77.3912", "Levels 1-5", "Active", "https://images.unsplash.com/photo-1503387762-592deb58ef4e?w=600", "2026-09-17 08:30:00"),
        ("CAM-T02-08", "CAM-T02-08", "Tower B Level 8 Slab Camera", "TOW-B", 8, "Core Deck", "East", "28.5360, 77.3905", "Levels 6-11", "Active", "https://images.unsplash.com/photo-1590486803833-1c5dc8ddd4c8?w=600", "2026-09-17 08:30:00"),
        ("CAM-SITE-01", "CAM-SITE-01", "Main Site Gate & Batching View", None, 0, "Perimeter Gate 1", "Pan-Tilt-Zoom", "28.5348, 77.3920", "Ground & Roads", "Active", "https://images.unsplash.com/photo-1581094794329-c8112a89af12?w=600", "2026-09-17 08:30:00")
    ]
    cursor.executemany("""
        INSERT INTO cameras (id, camera_code, location, tower_id, floor_level, zone, viewing_direction, gps_coordinates, coverage_floors, status, last_image_url, last_updated)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, cameras)

    # 8. Mode B: Pre-populated Field Visits, Field Photos, Validations & PM Reviews (Spec §17, §36, §37)
    # Submission 1: Pending PM Review (Tower A Level 5 Internal Masonry — matching prompt example!)
    photo_1 = "PHOTO-FLD-001"
    cursor.execute("""
        INSERT INTO field_photos (
            id, activity_id, tower_id, floor_level, zone, unit, file_path, file_name,
            captured_by, operator_quantity, operator_uom, operator_remarks,
            validation_status, ai_progress_percent, ai_confidence, pm_review_status, created_at
        ) VALUES (
            ?, 'ACT-TOWA-L05-MAS', 'TOW-A', 5, 'Zone 1', 'Unit 5B',
            'https://images.unsplash.com/photo-1503387762-592deb58ef4e?w=600', 'masonry_L5_unit5b.jpg',
            'Kunal Verma (Field Operator)', 125.0, 'm²', 'AAC blockwork completed in living room & corridor.',
            'VALID', 70.0, 0.91, 'PENDING_PM_REVIEW', '2026-09-17 07:45:00'
        )
    """, (photo_1,))

    cursor.execute("""
        INSERT INTO image_validations (
            id, photo_id, source_type, image_valid, construction_site_detected,
            wrong_object_detected, image_quality, context_relevant, activity_visible,
            validation_confidence, validation_status, raw_output
        ) VALUES (
            'VAL-001', ?, 'FIELD_OPERATOR', 1, 1, 0, 'HIGH', 1, 1, 0.96, 'VALID',
            '{"image_valid": true, "construction_site_detected": true, "context_relevant": true, "activity_visible": true}'
        )
    """, (photo_1,))

    cursor.execute("""
        INSERT INTO ai_observations (
            id, source_type, photo_id, activity_id, scheduled_status, ai_observed_status,
            ai_progress_percent, confidence, evidence_quality, quantity_measurable,
            schedule_variance, requires_human_intervention, output_json, observed_at
        ) VALUES (
            'OBS-001', 'FIELD_OPERATOR', ?, 'ACT-TOWA-L05-MAS', 'IN_PROGRESS', 'IN_PROGRESS',
            70.0, 0.91, 'HIGH', 1, 'ON_TRACK', 1,
            '{"source_type": "FIELD_OPERATOR", "ai_progress_percent": 70.0, "operator_quantity": 125.0, "operator_uom": "m2"}',
            '2026-09-17 07:46:00'
        )
    """, (photo_1,))

    cursor.execute("""
        INSERT INTO pm_reviews (
            id, photo_id, activity_id, field_operator,
            ai_progress_percent, ai_confidence, operator_quantity, operator_uom,
            pm_status, created_at
        ) VALUES (
            'REV-001', ?, 'ACT-TOWA-L05-MAS', 'Kunal Verma (Field Operator)',
            70.0, 0.91, 125.0, 'm²', 'PENDING', '2026-09-17 07:46:00'
        )
    """, (photo_1,))

    # Submission 2: Pending PM Review (Tower A Level 12 Slab)
    photo_2 = "PHOTO-FLD-002"
    cursor.execute("""
        INSERT INTO field_photos (
            id, activity_id, tower_id, floor_level, zone, unit, file_path, file_name,
            captured_by, operator_quantity, operator_uom, operator_remarks,
            validation_status, ai_progress_percent, ai_confidence, pm_review_status, created_at
        ) VALUES (
            ?, 'ACT-TOWA-L12-SLAB', 'TOW-A', 12, 'Core', 'Unit 12B',
            'https://images.unsplash.com/photo-1541888946425-d0fbb186a5b7?w=600', 'slab_L12_rebar.jpg',
            'Kunal Verma (Field Operator)', 118.0, 'm³', 'Top layer rebar mesh tying completed. Ready for inspection.',
            'VALID', 78.0, 0.93, 'PENDING_PM_REVIEW', '2026-09-17 08:15:00'
        )
    """, (photo_2,))

    cursor.execute("""
        INSERT INTO image_validations (
            id, photo_id, source_type, image_valid, construction_site_detected,
            wrong_object_detected, image_quality, context_relevant, activity_visible,
            validation_confidence, validation_status, raw_output
        ) VALUES (
            'VAL-002', ?, 'FIELD_OPERATOR', 1, 1, 0, 'HIGH', 1, 1, 0.95, 'VALID',
            '{"image_valid": true, "construction_site_detected": true, "context_relevant": true}'
        )
    """, (photo_2,))

    cursor.execute("""
        INSERT INTO pm_reviews (
            id, photo_id, activity_id, field_operator,
            ai_progress_percent, ai_confidence, operator_quantity, operator_uom,
            pm_status, created_at
        ) VALUES (
            'REV-002', ?, 'ACT-TOWA-L12-SLAB', 'Kunal Verma (Field Operator)',
            78.0, 0.93, 118.0, 'm³', 'PENDING', '2026-09-17 08:16:00'
        )
    """, (photo_2,))

    # Submission 3: Historical Approved PM Review (Tower A Level 11 AAC Blockwork)
    photo_3 = "PHOTO-FLD-003"
    cursor.execute("""
        INSERT INTO field_photos (
            id, activity_id, tower_id, floor_level, zone, unit, file_path, file_name,
            captured_by, operator_quantity, operator_uom, operator_remarks,
            validation_status, ai_progress_percent, ai_confidence, pm_review_status, created_at
        ) VALUES (
            ?, 'ACT-TOWA-L11-MAS', 'TOW-A', 11, 'Facade', NULL,
            'https://images.unsplash.com/photo-1590486803833-1c5dc8ddd4c8?w=600', 'blockwork_L11_exterior.jpg',
            'Kunal Verma (Field Operator)', 560.0, 'm²', 'External blockwork 70% completed.',
            'VALID', 75.0, 0.94, 'APPROVED', '2026-09-15 14:00:00'
        )
    """, (photo_3,))

    cursor.execute("""
        INSERT INTO pm_reviews (
            id, photo_id, activity_id, field_operator,
            ai_progress_percent, ai_confidence, operator_quantity, operator_uom,
            pm_status, pm_approved_quantity, pm_approved_progress_percent,
            pm_reviewer, pm_remarks, pm_action, reviewed_at, created_at
        ) VALUES (
            'REV-003', ?, 'ACT-TOWA-L11-MAS', 'Kunal Verma (Field Operator)',
            75.0, 0.94, 560.0, 'm²',
            'APPROVED', 560.0, 70.0,
            'Er. Robert Vance (PM)', 'Verified against site survey report. Approved.',
            'APPROVE', '2026-09-15 16:30:00', '2026-09-15 14:05:00'
        )
    """, (photo_3,))

    # 9. RFIs, NCRs, Safety, Materials
    rfis = [
        ("RFI-101", "RFI-TOWA-104", "Structural Column Rebar Lap Splice Detail Level 12", "Clarification needed on lap length for 25mm TMT bars in core columns.", "ACT-TOWA-L12-SLAB", "DWG-STR-TOWA-112", "Contractor", "Structural Engineer", "High", "Open", "Awaiting response from structural consultant", "2026-09-12 10:00:00", None),
        ("RFI-102", "RFI-MEP-045", "MEP Sleeve Location vs Slab Drop Level 10", "Discrepancy between plumbing riser drawing and structural beam depth.", "ACT-MEP-PLUMB-01", "DWG-MEP-PL-10", "MEP Engineer", "Architect", "Medium", "Open", "Under review by architectural team", "2026-09-14 14:30:00", None),
        ("RFI-103", "RFI-FIN-012", "Stone Flooring Sample Approval for Entrance Lobby", "Granite shade confirmation for Tower A entrance.", "ACT-FIN-TILE-01", "SPEC-FIN-02", "Site Engineer", "Project Owner", "Low", "Closed", "Approved Sample Option B (Jet Black Granite)", "2026-09-01 09:00:00", "2026-09-05 16:00:00")
    ]
    cursor.executemany("""
        INSERT INTO rfis (id, rfi_number, subject, description, activity_id, drawing_ref, raised_by, assigned_to, priority, status, response, created_at, closed_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, rfis)

    ncrs = [
        ("NCR-201", "NCR-TOWA-012", "ACT-TOWA-L12-SLAB", "Tower A Level 12 Slab", "Concrete honeycombing detected near grid intersection C-4 post-pour.", "High", "BuildPro Concrete", "Chipping of weak concrete, application of non-shrink structural epoxy grout.", "2026-09-20", "Open", "https://images.unsplash.com/photo-1541888946425-d0fbb186a5b7?w=400", "QA/QC Engineer", "2026-09-14 11:20:00", None),
        ("NCR-202", "NCR-TOWB-008", "ACT-TOWB-L10-SLAB", "Tower B Level 8 Columns", "Minor rebar cover displacement observed during column formwork inspection.", "Moderate", "BuildPro Concrete", "Re-aligned plastic spacers and secured rebar tying wire.", "2026-09-10", "Closed", "https://images.unsplash.com/photo-1503387762-592deb58ef4e?w=400", "QA/QC Engineer", "2026-09-08 15:10:00", "2026-09-11 10:00:00")
    ]
    cursor.executemany("""
        INSERT INTO ncrs (id, ncr_number, activity_id, location, description, severity, contractor, corrective_action, due_date, status, evidence_photo, created_by, created_at, closed_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, ncrs)

    safety = [
        ("SAF-301", "Observation", "TOW-A", 12, "North Perimeter", "Workers operating near edge without fall protection harness tied.", "High", 1, 0.94, "Open", "Enforce safety harness tie-off and verify edge net installation.", "Safety Officer", "AI Camera Scanner", "https://images.unsplash.com/photo-1581094794329-c8112a89af12?w=400", "2026-09-16 08:30:00"),
        ("SAF-302", "Incident", "TOW-B", 5, "Stairwell B", "Unsecured timber debris blocking emergency exit walkway.", "Moderate", 0, 0.0, "Closed", "Path cleared and warning signs posted.", "Supervisor", "Site Engineer", "https://images.unsplash.com/photo-1590486803833-1c5dc8ddd4c8?w=400", "2026-09-13 14:00:00")
    ]
    cursor.executemany("""
        INSERT INTO safety_records (id, record_type, tower_id, floor_level, zone, description, severity, is_ai_flagged, ai_confidence, status, corrective_action, assigned_to, created_by, photo_url, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, safety)

    materials = [
        ("MAT-01", "CONC-M35", "Ready-Mix Concrete M35 Grade", "Concrete", "m³", 110.0, 150.0, 120.0, "UltraTech Concrete Ltd"),
        ("MAT-02", "REINF-TMT-16", "High Yield TMT Steel Bars 16mm", "Steel", "MT", 45.0, 20.0, 850.0, "Tata Tiscon Steel"),
        ("MAT-03", "AAC-BLOCK-200", "AAC Lightweight Masonry Blocks 200mm", "Masonry", "m³", 350.0, 100.0, 65.0, "Magicrete Building Solutions"),
        ("MAT-04", "ELEC-CABLE-4C", "4-Core Armoured Copper Cable 35sqmm", "Electrical", "m", 1200.0, 300.0, 12.5, "Polycab Wires")
    ]
    cursor.executemany("""
        INSERT INTO materials (id, code, name, category, uom, current_stock, reorder_level, unit_price, supplier)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, materials)

    conn.commit()
    conn.close()
    print("PyCray_SiteIQ dual-mode seed data populated successfully!")

if __name__ == "__main__":
    seed_all_data()
