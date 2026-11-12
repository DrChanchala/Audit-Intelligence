import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.table import Table, TableStyleInfo
from openpyxl.formatting.rule import CellIsRule, FormulaRule
from datetime import datetime, date

def create_l4_master_sheet():
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "BUILDTRACK_L4_MASTER"

    # Ensure grid lines are visible
    ws.views.sheetView[0].showGridLines = True

    # Header Columns Definition (68 columns A to BP)
    headers = [
        "Project_ID", "Project_Name", "Building_ID", "Building_Name", "Floor_ID", "Floor_Name",
        "Unit_ID", "Unit_Type", "Zone_ID", "Zone_Name", "Room_ID", "Room_Name",
        "WBS_L1", "WBS_L2", "WBS_L3", "WBS_L4", "WBS_Code", "Activity_ID",
        "Activity_Name", "Activity_Description", "Trade", "Discipline", "BOQ_Item_Code",
        "BOQ_Description", "Specification_Reference", "Drawing_Reference", "Location_Code",
        "UOM", "Planned_Quantity", "Reported_Quantity", "Inspected_Quantity", "Accepted_Quantity",
        "Balance_Quantity", "Physical_Progress_%", "Activity_Weight_%", "Weighted_Progress_%",
        "Baseline_Start", "Baseline_Finish", "Actual_Start", "Actual_Finish",
        "Planned_Duration_Days", "Actual_Duration_Days", "Predecessor", "Dependency_Type",
        "Responsible_Contractor", "Responsible_Engineer", "Planned_Manpower", "Actual_Manpower",
        "Planned_Cost", "Actual_Cost", "Cost_Progress_%", "Schedule_Status", "Progress_Status",
        "Inspection_Status", "RFI_Status", "NCR_Status", "Material_Status", "Drawing_Status",
        "Constraint_Status", "Risk_Status", "Photo_Required", "Photo_Count", "Evidence_Status",
        "Remarks", "Last_Updated", "Updated_By", "Data_Source", "Record_Status"
    ]

    # Write Header Row
    ws.append(headers)

    # Base Project Assumptions
    proj_id = "PRJ-GHR-2026"
    proj_name = "BuildTrack Demo Residential Development"
    bldg_id = "TOW-A"
    bldg_name = "Tower A (G+6 RCC Building)"

    # Define Data Generator template items across all 20 L2 phases
    # Every row will be a complete atomic L4 record.
    raw_activities = []

    # Phase 01: Preconstruction, Mobilization & Approvals
    raw_activities.extend([
        ("01", "Preconstruction & Approvals", "01.01 Design & Engineering", "IFC Architectural Drawings", "01.01.01", "Design", "Architectural", "ARCH-01", "Nos", 1.0, 1.0, 1.0, 1.0, 0.20, "2025-01-15", "2025-02-15", "2025-01-15", "2025-02-14", 30, 30, "", "", "Apex Consultants", "Lead Architect", 5, 5, 25000, 25000, "Completed", "Completed", "Compliant", "Closed", "None", "Approved", "IFC", "None", "Low", "Yes", 3, "Verified", "DEMO / ASSUMED"),
        ("01", "Preconstruction & Approvals", "01.02 Statutory Approvals", "Municipal Building Permit", "01.02.01", "General", "General", "PERM-01", "Milestone", 1.0, 1.0, 1.0, 1.0, 0.30, "2025-02-01", "2025-03-01", "2025-02-01", "2025-02-28", 28, 28, "01.01.01", "FS", "Apex Contractors", "Project Manager", 2, 2, 50000, 50000, "Completed", "Completed", "Compliant", "None", "None", "Approved", "IFC", "None", "Low", "Yes", 2, "Verified", "DEMO / ASSUMED"),
        ("01", "Preconstruction & Approvals", "01.03 Mobilization", "Site Office & Temporary Power", "01.03.01", "Civil", "General", "MOB-01", "LS", 1.0, 1.0, 1.0, 1.0, 0.25, "2025-03-01", "2025-03-15", "2025-03-01", "2025-03-14", 14, 14, "01.02.01", "FS", "Apex Contractors", "Civil Engineer", 10, 10, 35000, 35000, "Completed", "Completed", "Compliant", "None", "None", "Delivered", "IFC", "None", "Low", "Yes", 4, "Verified", "DEMO / ASSUMED"),
        ("01", "Preconstruction & Approvals", "01.04 Temporary Facilities", "Site Perimeter Fencing", "01.04.01", "Civil", "Civil", "MOB-02", "m", 350.0, 350.0, 350.0, 350.0, 0.25, "2025-03-05", "2025-03-20", "2025-03-05", "2025-03-19", 15, 14, "01.03.01", "SS", "Apex Contractors", "Civil Engineer", 8, 8, 18000, 18000, "Completed", "Completed", "Compliant", "None", "None", "Delivered", "IFC", "None", "Low", "Yes", 2, "Verified", "DEMO / ASSUMED"),
    ])

    # Phase 02: Site Preparation & Survey
    raw_activities.extend([
        ("02", "Site Preparation & Survey", "02.01 Survey & Setting Out", "Topographical Survey & Grid Setting Out", "02.01.01", "Civil", "Civil", "SURV-01", "m²", 2500.0, 2500.0, 2500.0, 2500.0, 0.30, "2025-03-16", "2025-03-25", "2025-03-16", "2025-03-24", 9, 8, "01.04.01", "FS", "GeoSurvey Ltd", "Site Engineer", 4, 4, 12000, 12000, "Completed", "Completed", "Compliant", "None", "None", "Not Required", "IFC", "None", "Low", "Yes", 5, "Verified", "DEMO / ASSUMED"),
        ("02", "Site Preparation & Survey", "02.02 Site Clearance", "Vegetation & Debris Clearing", "02.02.01", "Civil", "Civil", "PREP-01", "m²", 2500.0, 2500.0, 2500.0, 2500.0, 0.40, "2025-03-20", "2025-03-30", "2025-03-20", "2025-03-29", 10, 9, "02.01.01", "SS", "EarthWorks Ltd", "Civil Engineer", 12, 12, 22000, 22000, "Completed", "Completed", "Compliant", "None", "None", "Not Required", "IFC", "None", "Low", "Yes", 3, "Verified", "DEMO / ASSUMED"),
        ("02", "Site Preparation & Survey", "02.05 Ground Preparation", "Topsoil Stripping & Level Compaction", "02.05.01", "Civil", "Civil", "PREP-02", "m²", 1800.0, 1800.0, 1800.0, 1800.0, 0.30, "2025-03-28", "2025-04-05", "2025-03-28", "2025-04-04", 8, 7, "02.02.01", "FS", "EarthWorks Ltd", "Civil Engineer", 8, 8, 15000, 15000, "Completed", "Completed", "Compliant", "None", "None", "Not Required", "IFC", "None", "Low", "Yes", 2, "Verified", "DEMO / ASSUMED"),
    ])

    # Phase 03: Earthwork & Excavation
    raw_activities.extend([
        ("03", "Earthwork & Excavation", "03.01 Bulk Excavation", "Foundation Bulk Excavation (3.5m Depth)", "03.01.01", "Civil", "Civil", "EARTH-01", "m³", 4200.0, 4200.0, 4200.0, 4200.0, 1.20, "2025-04-06", "2025-04-25", "2025-04-06", "2025-04-24", 19, 18, "02.05.01", "FS", "EarthWorks Ltd", "Civil Engineer", 15, 15, 147000, 147000, "Completed", "Completed", "Compliant", "None", "None", "Not Required", "IFC", "None", "Low", "Yes", 6, "Verified", "DEMO / ASSUMED"),
        ("03", "Earthwork & Excavation", "03.02 Foundation Excavation", "Footing & Trench Pit Excavation", "03.02.01", "Civil", "Civil", "EARTH-02", "m³", 850.0, 850.0, 850.0, 850.0, 0.50, "2025-04-22", "2025-05-02", "2025-04-22", "2025-05-01", 10, 9, "03.01.01", "SS", "EarthWorks Ltd", "Civil Engineer", 10, 10, 38000, 38000, "Completed", "Completed", "Compliant", "None", "None", "Not Required", "IFC", "None", "Low", "Yes", 4, "Verified", "DEMO / ASSUMED"),
        ("03", "Earthwork & Excavation", "03.06 Backfilling", "Foundation Backfill & Layer Compaction", "03.06.01", "Civil", "Civil", "EARTH-03", "m³", 1200.0, 1200.0, 1200.0, 1200.0, 0.40, "2025-05-20", "2025-06-05", "2025-05-20", "2025-06-04", 16, 15, "03.02.01", "FS", "EarthWorks Ltd", "Civil Engineer", 8, 8, 30000, 30000, "Completed", "Completed", "Compliant", "None", "None", "Not Required", "IFC", "None", "Low", "Yes", 3, "Verified", "DEMO / ASSUMED"),
    ])

    # Phase 04: Foundation & Substructure
    raw_activities.extend([
        ("04", "Foundation & Substructure", "04.02 PCC/Blinding", "PCC Blinding Layer M15 Concrete (100mm)", "04.02.01", "Structural", "Structural", "FND-01", "m³", 125.0, 125.0, 125.0, 125.0, 1.00, "2025-05-03", "2025-05-10", "2025-05-03", "2025-05-09", 7, 6, "03.02.01", "FS", "BuildPro Concrete", "Structural Engineer", 12, 12, 45000, 45000, "Completed", "Completed", "Compliant", "None", "None", "Delivered", "IFC", "None", "Low", "Yes", 5, "Verified", "DEMO / ASSUMED"),
        ("04", "Foundation & Substructure", "04.03 Isolated Footings", "Footing Rebar, Formwork & M30 Casting", "04.03.01", "Structural", "Structural", "FND-02", "m³", 480.0, 480.0, 480.0, 480.0, 3.50, "2025-05-11", "2025-06-01", "2025-05-11", "2025-05-31", 21, 20, "04.02.01", "FS", "BuildPro Concrete", "Structural Engineer", 22, 22, 216000, 216000, "Completed", "Completed", "Compliant", "Closed", "None", "Delivered", "IFC", "None", "Low", "Yes", 8, "Verified", "DEMO / ASSUMED"),
        ("04", "Foundation & Substructure", "04.06 Pedestals", "Plinth Beams & Stub Column Concrete", "04.06.01", "Structural", "Structural", "FND-03", "m³", 180.0, 180.0, 180.0, 180.0, 2.00, "2025-06-02", "2025-06-18", "2025-06-02", "2025-06-17", 16, 15, "04.03.01", "FS", "BuildPro Concrete", "Structural Engineer", 18, 18, 98000, 98000, "Completed", "Completed", "Compliant", "None", "None", "Delivered", "IFC", "None", "Low", "Yes", 4, "Verified", "DEMO / ASSUMED"),
        ("04", "Foundation & Substructure", "04.09 Waterproofing", "Plinth & Substructure Bituminous Waterproofing", "04.09.01", "Waterproofing", "Civil", "FND-04", "m²", 950.0, 950.0, 950.0, 950.0, 1.20, "2025-06-15", "2025-06-25", "2025-06-15", "2025-06-24", 10, 9, "04.06.01", "SS", "AquaShield Coatings", "Civil Engineer", 10, 10, 57000, 57000, "Completed", "Completed", "Compliant", "None", "None", "Approved", "IFC", "None", "Low", "Yes", 4, "Verified", "DEMO / ASSUMED"),
    ])

    # Phase 05: RCC Superstructure (Floor-by-Floor for Ground Floor through Level 6 & Level 7 Terrace)
    floors = [
        ("GF", "Ground Floor", "COM-GF", "Common Area", 2025, 6, 20, 2025, 7, 20, "Completed", "Completed", "Compliant", 3.0),
        ("L01", "Level 1", "COM-L01", "Common Area", 2025, 7, 21, 2025, 8, 15, "Completed", "Completed", "Compliant", 3.2),
        ("L02", "Level 2", "COM-L02", "Common Area", 2025, 8, 16, 2025, 9, 10, "Completed", "Completed", "Compliant", 3.2),
        ("L03", "Level 3", "COM-L03", "Common Area", 2025, 9, 11, 2025, 10, 5, "Completed", "Completed", "Compliant", 3.2),
        ("L04", "Level 4", "COM-L04", "Common Area", 2025, 10, 6, 2025, 10, 30, "Completed", "Completed", "Compliant", 3.2),
        ("L05", "Level 5", "COM-L05", "Common Area", 2025, 11, 1, 2025, 11, 25, "Completed", "Completed", "Compliant", 3.2),
        ("L06", "Level 6", "COM-L06", "Common Area", 2026, 1, 10, 2026, 2, 10, "In Progress", "In Progress", "Pending", 3.2),
        ("L07", "Level 7 / Terrace", "COM-L07", "Terrace", 2026, 2, 11, 2026, 3, 10, "Not Started", "Not Started", "Pending", 2.6)
    ]

    for f_id, f_name, c_code, c_name, sy, sm, sd, ey, em, ed, prog_stat, sched_stat, insp_stat, wt in floors:
        # Determine actual status for demonstration dataset
        if prog_stat == "Completed":
            rep_q, ins_q, acc_q = 120.0, 120.0, 120.0
            act_s = f"{sy:04d}-{sm:02d}-{sd:02d}"
            act_e = f"{ey:04d}-{em:02d}-{ed:02d}"
            rfi_st = "Closed"
            ncr_st = "None"
            mat_st = "Delivered"
            ev_st = "Verified"
            photo_c = 6
        elif prog_stat == "In Progress":
            rep_q, ins_q, acc_q = 95.0, 90.0, 85.0
            act_s = f"{sy:04d}-{sm:02d}-{sd:02d}"
            act_e = ""
            rfi_st = "Open"
            ncr_st = "Open"
            mat_st = "Delivered"
            ev_st = "Uploaded"
            photo_c = 4
        else:
            rep_q, ins_q, acc_q = 0.0, 0.0, 0.0
            act_s, act_e = "", ""
            rfi_st = "None"
            ncr_st = "None"
            mat_st = "Ordered"
            ev_st = "Missing"
            photo_c = 0

        # Columns activity
        raw_activities.append((
            "05", "RCC Superstructure", "05.01 Columns", f"{f_name} Columns Rebar & M35 Concrete Pour", f"05.01.{f_id}",
            "Structural", "Structural", f"BOQ-STR-COL-{f_id}", "m³", 120.0, rep_q, ins_q, acc_q, wt * 0.4,
            f"{sy:04d}-{sm:02d}-{sd:02d}", f"{ey:04d}-{em:02d}-{ed:02d}", act_s, act_e, 30, 29 if act_e else 0,
            f"04.06.01" if f_id == "GF" else f"05.02.L{int(f_id[1:])-1:02d}" if f_id.startswith("L") and f_id != "L01" else "05.02.GF",
            "FS", "BuildPro Concrete", "Structural Engineer", 16, 16 if act_s else 0, 72000, 72000 if act_s else 0,
            sched_stat, prog_stat, insp_stat, rfi_st, ncr_st, mat_st, "IFC", "None", "Low" if ncr_st=="None" else "Medium",
            "Yes", photo_c, ev_st, "DEMO / ASSUMED"
        ))

        # Slabs & Beams activity
        raw_activities.append((
            "05", "RCC Superstructure", "05.03 Slabs & Beams", f"{f_name} Slab & Beam Formwork, Rebar & Concrete", f"05.03.{f_id}",
            "Structural", "Structural", f"BOQ-STR-SLB-{f_id}", "m³", 150.0, rep_q, ins_q, acc_q, wt * 0.6,
            f"{sy:04d}-{sm:02d}-{sd:02d}", f"{ey:04d}-{em:02d}-{ed:02d}", act_s, act_e, 30, 29 if act_e else 0,
            f"05.01.{f_id}", "FS", "BuildPro Concrete", "Structural Engineer", 20, 20 if act_s else 0, 90000, 90000 if act_s else 0,
            sched_stat, prog_stat, insp_stat, rfi_st, ncr_st, mat_st, "IFC", "None", "Low" if ncr_st=="None" else "Medium",
            "Yes", photo_c, ev_st, "DEMO / ASSUMED"
        ))

    # Unit-Level Detailed Finishes across 14 Units (A101 to A702) & Rooms
    units = [
        (f"A{lvl}{u:02d}", f"Level {lvl}", f"Type { 'A' if u==1 else 'B' }")
        for lvl in range(1, 7) for u in (1, 2)
    ]
    # Add Ground Floor Units (A001, A002)
    units.insert(0, ("A001", "Ground Floor", "Type A"))
    units.insert(1, ("A002", "Ground Floor", "Type B"))

    rooms = [
        ("LIV", "Living & Dining", 45.0, "m²"),
        ("KIT", "Kitchen", 18.0, "m²"),
        ("BED1", "Master Bedroom", 25.0, "m²"),
        ("BED2", "Bedroom 2", 20.0, "m²"),
        ("TOI1", "Master Toilet", 8.0, "m²"),
        ("TOI2", "Common Toilet", 6.0, "m²"),
        ("BAL", "Balcony", 10.0, "m²")
    ]

    # Generate Granular Unit Rows for Phase 06 (Masonry), Phase 08 (Waterproofing), Phase 10 (Plaster), Phase 12 (Tile), Phase 14 (Painting)
    for u_id, fl_name, u_type in units:
        lvl_num = int(u_id[1]) if u_id[1].isdigit() else 0
        
        # Unit Completion Status based on level progression
        if lvl_num in (0, 1, 2, 3):
            u_stat, u_insp = "Completed", "Compliant"
            p_pct = 1.0
        elif lvl_num in (4, 5):
            u_stat, u_insp = "In Progress", "Under Inspection"
            p_pct = 0.70
        else:
            u_stat, u_insp = "Not Started", "Pending"
            p_pct = 0.0

        # Masonry Internal Partition Wall per Unit
        raw_activities.append((
            "06", "Masonry & Partitions", "06.02 Internal Masonry", f"AAC Blockwork Wall 150mm — Unit {u_id}", f"06.02.{u_id}",
            "Masonry", "Architectural", f"BOQ-MAS-{u_id}", "m²", 120.0, 120.0*p_pct, 120.0*p_pct, 120.0*p_pct, 0.40,
            "2025-11-01", "2025-11-15", "2025-11-01" if p_pct>0 else "", "2025-11-14" if p_pct==1.0 else "", 14, 13 if p_pct==1.0 else 0,
            f"05.03.L0{lvl_num}" if lvl_num>0 else "05.03.GF", "FS", "Masonry Masters", "Site Engineer", 8, 8 if p_pct>0 else 0,
            14400, 14400*p_pct, "On Schedule" if p_pct>0 else "Not Started", u_stat, u_insp, "None", "None", "Delivered", "IFC", "None", "Low",
            "Yes", 3 if p_pct>0 else 0, "Verified" if p_pct==1.0 else ("Uploaded" if p_pct>0 else "Missing"), "DEMO / ASSUMED"
        ))

        # Waterproofing per Toilet & Balcony
        for rm_code, rm_name, rm_area, rm_uom in rooms:
            if "TOI" in rm_code or "BAL" in rm_code:
                raw_activities.append((
                    "08", "Waterproofing", "08.02 Wet Area Waterproofing", f"Liquid Applied Membrane Waterproofing — Unit {u_id} {rm_name}", f"08.02.{u_id}.{rm_code}",
                    "Waterproofing", "Civil", f"BOQ-WPF-{u_id}-{rm_code}", rm_uom, rm_area, rm_area*p_pct, rm_area*p_pct, rm_area*p_pct, 0.15,
                    "2025-11-16", "2025-11-25", "2025-11-16" if p_pct>0 else "", "2025-11-24" if p_pct==1.0 else "", 9, 8 if p_pct==1.0 else 0,
                    f"06.02.{u_id}", "FS", "AquaShield Coatings", "Site Engineer", 4, 4 if p_pct>0 else 0,
                    4800, 4800*p_pct, "On Schedule" if p_pct>0 else "Not Started", u_stat, u_insp, "None", "None", "Approved", "IFC", "None", "Low",
                    "Yes", 2 if p_pct>0 else 0, "Verified" if p_pct==1.0 else ("Uploaded" if p_pct>0 else "Missing"), "DEMO / ASSUMED"
                ))

        # Internal Plastering per Room
        for rm_code, rm_name, rm_area, rm_uom in rooms:
            raw_activities.append((
                "10", "Internal Plastering & Surface Prep", "10.01 Wall Plaster", f"Gypsum Smooth Internal Plaster — Unit {u_id} {rm_name}", f"10.01.{u_id}.{rm_code}",
                "Plaster", "Architectural", f"BOQ-PLAS-{u_id}-{rm_code}", rm_uom, rm_area, rm_area*p_pct, rm_area*p_pct, rm_area*p_pct, 0.20,
                "2025-12-01", "2025-12-15", "2025-12-01" if p_pct>0 else "", "2025-12-14" if p_pct==1.0 else "", 14, 13 if p_pct==1.0 else 0,
                f"06.02.{u_id}", "FS", "FinishPro Interiors", "Site Engineer", 5, 5 if p_pct>0 else 0,
                6500, 6500*p_pct, "On Schedule" if p_pct>0 else "Not Started", u_stat, u_insp, "None", "None", "Delivered", "IFC", "None", "Low",
                "Yes", 2 if p_pct>0 else 0, "Verified" if p_pct==1.0 else ("Uploaded" if p_pct>0 else "Missing"), "DEMO / ASSUMED"
            ))

        # Flooring & Wall Tiles per Room
        for rm_code, rm_name, rm_area, rm_uom in rooms:
            t_type = "Vitrified Tile" if "TOI" not in rm_code else "Ceramic Anti-Skid Tile"
            raw_activities.append((
                "12", "Flooring & Wall Finishes", "12.01 Floor Tiles", f"{t_type} Flooring — Unit {u_id} {rm_name}", f"12.01.{u_id}.{rm_code}",
                "Flooring", "Architectural", f"BOQ-TILE-{u_id}-{rm_code}", rm_uom, rm_area, rm_area*p_pct, rm_area*p_pct, rm_area*p_pct, 0.25,
                "2026-01-01", "2026-01-20", "2026-01-01" if p_pct>0 else "", "2026-01-19" if p_pct==1.0 else "", 19, 18 if p_pct==1.0 else 0,
                f"10.01.{u_id}.{rm_code}", "FS", "FinishPro Interiors", "Site Engineer", 6, 6 if p_pct>0 else 0,
                9000, 9000*p_pct, "On Schedule" if p_pct>0 else "Not Started", u_stat, u_insp, "None", "None", "Delivered", "IFC", "None", "Low",
                "Yes", 3 if p_pct>0 else 0, "Verified" if p_pct==1.0 else ("Uploaded" if p_pct>0 else "Missing"), "DEMO / ASSUMED"
            ))

        # Painting 2-Coat Emulsion per Unit
        raw_activities.append((
            "14", "Painting", "14.01 Internal Walls", f"2-Coat Emulsion Paint with Putty — Unit {u_id}", f"14.01.{u_id}",
            "Painting", "Architectural", f"BOQ-PNT-{u_id}", "m²", 240.0, 240.0*p_pct, 240.0*p_pct, 240.0*p_pct, 0.30,
            "2026-02-01", "2026-02-20", "2026-02-01" if p_pct>0 else "", "2026-02-18" if p_pct==1.0 else "", 19, 17 if p_pct==1.0 else 0,
            f"12.01.{u_id}.LIV", "FS", "ColorCraft Painters", "Site Engineer", 6, 6 if p_pct>0 else 0,
            12000, 12000*p_pct, "On Schedule" if p_pct>0 else "Not Started", u_stat, u_insp, "None", "None", "Delivered", "IFC", "None", "Low",
            "Yes", 2 if p_pct>0 else 0, "Verified" if p_pct==1.0 else ("Uploaded" if p_pct>0 else "Missing"), "DEMO / ASSUMED"
        ))

    # Additional Remaining Phases (07 Envelope, 09 MEP 1st Fix, 11 Doors/Win, 13 Ceiling, 15 MEP 2nd Fix, 16 External, 17 Lifts, 18 T&C, 19 Snagging, 20 Handover)
    raw_activities.extend([
        # 07 Façade
        ("07", "Building Envelope & Façade", "07.01 External Plaster", "External Double Coat Plaster (Tower A Façade)", "07.01.01", "Plaster", "Architectural", "FAC-01", "m²", 3500.0, 2800.0, 2700.0, 2700.0, 1.50, "2026-01-15", "2026-03-15", "2026-01-15", "", 60, 0, "05.03.L06", "FS", "FinishPro Interiors", "Civil Engineer", 18, 18, 140000, 108000, "On Schedule", "In Progress", "Compliant", "None", "None", "Delivered", "IFC", "None", "Low", "Yes", 5, "Uploaded", "DEMO / ASSUMED"),
        ("07", "Building Envelope & Façade", "07.02 External Paint", "Weatherproof External Texture Painting", "07.02.01", "Painting", "Architectural", "FAC-02", "m²", 3500.0, 1200.0, 1000.0, 1000.0, 1.20, "2026-03-01", "2026-04-15", "2026-03-01", "", 45, 0, "07.01.01", "FS", "ColorCraft Painters", "Civil Engineer", 12, 12, 105000, 30000, "On Schedule", "In Progress", "Compliant", "None", "None", "Delivered", "IFC", "None", "Low", "Yes", 3, "Uploaded", "DEMO / ASSUMED"),

        # 09 MEP 1st Fix
        ("09", "MEP First Fix", "09.01 Plumbing Risers", "UPVC/CPVC Vertical Riser Piping (G+6)", "09.01.01", "Plumbing", "MEP", "MEP-01", "m", 650.0, 650.0, 650.0, 650.0, 1.20, "2025-10-01", "2025-11-15", "2025-10-01", "2025-11-14", 45, 44, "05.03.L06", "SS", "AquaFlow Systems", "MEP Engineer", 8, 8, 45500, 45500, "Completed", "Completed", "Compliant", "None", "None", "Delivered", "IFC", "None", "Low", "Yes", 4, "Verified", "DEMO / ASSUMED"),
        ("09", "MEP First Fix", "09.03 Electrical Conduits", "Electrical Conduits & Junction Box Installation", "09.03.01", "Electrical", "MEP", "MEP-02", "m", 4500.0, 3800.0, 3600.0, 3600.0, 1.50, "2025-10-01", "2025-12-15", "2025-10-01", "", 75, 0, "05.03.L06", "SS", "VoltTech MEP", "MEP Engineer", 10, 10, 67500, 54000, "On Schedule", "In Progress", "Compliant", "None", "None", "Delivered", "IFC", "None", "Low", "Yes", 6, "Uploaded", "DEMO / ASSUMED"),

        # 11 Doors & Windows
        ("11", "Doors, Windows & Glazing", "11.01 Door Frames", "Teak Wood Main & Flush Door Frames (14 Units)", "11.01.01", "Carpentry", "Architectural", "DW-01", "Nos", 56.0, 42.0, 42.0, 42.0, 0.80, "2025-12-15", "2026-01-15", "2025-12-15", "", 31, 0, "06.02.A101", "FS", "TimberCraft Doors", "Site Engineer", 6, 6, 44800, 33600, "On Schedule", "In Progress", "Compliant", "None", "None", "Delivered", "IFC", "None", "Low", "Yes", 3, "Uploaded", "DEMO / ASSUMED"),
        ("11", "Doors, Windows & Glazing", "11.03 Windows", "Powder Coated Aluminium Sliding Windows", "11.03.01", "Aluminium", "Architectural", "DW-02", "m²", 280.0, 180.0, 180.0, 180.0, 1.00, "2026-01-15", "2026-02-28", "2026-01-15", "", 44, 0, "11.01.01", "FS", "AluGlaze Systems", "Site Engineer", 8, 8, 84000, 54000, "On Schedule", "In Progress", "Compliant", "None", "None", "Delivered", "IFC", "None", "Low", "Yes", 4, "Uploaded", "DEMO / ASSUMED"),

        # 13 Ceiling & Drywall
        ("13", "Ceiling & Drywall", "13.01 Gypsum Ceiling", "Gypsum Board False Ceiling in Entrance Lobby & Corridors", "13.01.01", "Carpentry", "Architectural", "CLG-01", "m²", 450.0, 300.0, 300.0, 300.0, 0.60, "2026-02-01", "2026-03-10", "2026-02-01", "", 38, 0, "10.01.A101.LIV", "FS", "FinishPro Interiors", "Site Engineer", 6, 6, 31500, 21000, "On Schedule", "In Progress", "Compliant", "None", "None", "Delivered", "IFC", "None", "Low", "Yes", 2, "Uploaded", "DEMO / ASSUMED"),

        # 15 MEP Second Fix
        ("15", "MEP Second Fix", "15.01 Electrical Fixtures", "Modular Switches, Sockets & DB Fitting (14 Units)", "15.01.01", "Electrical", "MEP", "MEP-03", "Nos", 840.0, 420.0, 400.0, 400.0, 1.20, "2026-02-15", "2026-04-01", "2026-02-15", "", 45, 0, "14.01.A101", "FS", "VoltTech MEP", "MEP Engineer", 8, 8, 50400, 24000, "On Schedule", "In Progress", "Compliant", "None", "None", "Delivered", "IFC", "None", "Low", "Yes", 4, "Uploaded", "DEMO / ASSUMED"),
        ("15", "MEP Second Fix", "15.02 Sanitary Fixtures", "WCs, Wash Basins & CP Fittings Installation", "15.02.01", "Plumbing", "MEP", "MEP-04", "Sets", 28.0, 14.0, 14.0, 14.0, 1.00, "2026-03-01", "2026-04-15", "2026-03-01", "", 45, 0, "12.01.A101.TOI1", "FS", "AquaFlow Systems", "MEP Engineer", 6, 6, 70000, 35000, "On Schedule", "In Progress", "Compliant", "None", "None", "Delivered", "IFC", "None", "Low", "Yes", 3, "Uploaded", "DEMO / ASSUMED"),

        # 16 External Works & Landscape
        ("16", "External Works & Landscape", "16.01 Roads & Paving", "Concrete Interlocking Paver Driveway & Parking", "16.01.01", "Civil", "Civil", "EXT-01", "m²", 1200.0, 400.0, 400.0, 400.0, 1.50, "2026-03-15", "2026-05-15", "2026-03-15", "", 61, 0, "07.02.01", "FS", "RoadTech Infra", "Civil Engineer", 10, 10, 96000, 32000, "On Schedule", "In Progress", "Compliant", "None", "None", "Delivered", "IFC", "None", "Low", "Yes", 3, "Uploaded", "DEMO / ASSUMED"),
        ("16", "External Works & Landscape", "16.03 Stormwater Drains", "RRC Stormwater Drain Channel & Rainwater Recharge Pits", "16.03.01", "Civil", "Civil", "EXT-02", "m", 320.0, 200.0, 200.0, 200.0, 1.00, "2026-03-01", "2026-04-30", "2026-03-01", "", 60, 0, "16.01.01", "SS", "RoadTech Infra", "Civil Engineer", 8, 8, 48000, 30000, "On Schedule", "In Progress", "Compliant", "None", "None", "Delivered", "IFC", "None", "Low", "Yes", 2, "Uploaded", "DEMO / ASSUMED"),

        # 17 Vertical Transportation
        ("17", "Vertical Transportation", "17.02 Lift Installation", "8-Passenger Gearless Elevator Installation (G+6)", "17.02.01", "General", "MEP", "LIFT-01", "Nos", 1.0, 0.6, 0.6, 0.6, 1.80, "2026-02-01", "2026-04-15", "2026-02-01", "", 73, 0, "05.01.L06", "FS", "Otis Elevators", "MEP Engineer", 5, 5, 180000, 108000, "On Schedule", "In Progress", "Compliant", "None", "None", "Delivered", "IFC", "None", "Low", "Yes", 5, "Uploaded", "DEMO / ASSUMED"),

        # 18 Testing & Commissioning
        ("18", "Testing & Commissioning", "18.01 MEP Testing", "Integrated Electrical & Plumbing Pressure Testing", "18.01.01", "Electrical", "MEP", "TC-01", "Lot", 1.0, 0.0, 0.0, 0.0, 1.00, "2026-04-16", "2026-05-15", "", "", 29, 0, "15.01.01", "FS", "VoltTech MEP", "MEP Engineer", 4, 0, 35000, 0, "Not Started", "Not Started", "Pending", "None", "None", "Pending Approval", "IFC", "None", "Low", "Yes", 0, "Missing", "DEMO / ASSUMED"),

        # 19 Snagging & Defect Rectification
        ("19", "Snagging & Defect Rectification", "19.01 Architectural Snags", "Pre-Handover Joint Snag Audit & Rectification", "19.01.01", "General", "Architectural", "SNAG-01", "Lot", 1.0, 0.0, 0.0, 0.0, 1.00, "2026-05-16", "2026-06-05", "", "", 20, 0, "18.01.01", "FS", "Apex Contractors", "QA/QC Engineer", 6, 0, 25000, 0, "Not Started", "Not Started", "Pending", "None", "None", "Not Required", "IFC", "None", "Low", "Yes", 0, "Missing", "DEMO / ASSUMED"),

        # 20 Handover & Closeout
        ("20", "Handover & Closeout", "20.01 Documentation", "As-Built Drawings, O&M Manuals & Statutory Handover", "20.01.01", "General", "General", "HO-01", "Milestone", 1.0, 0.0, 0.0, 0.0, 1.00, "2026-06-06", "2026-06-30", "", "", 24, 0, "19.01.01", "FS", "Apex Contractors", "Project Manager", 3, 0, 15000, 0, "Not Started", "Not Started", "Pending", "None", "None", "Not Required", "IFC", "None", "Low", "Yes", 0, "Missing", "DEMO / ASSUMED")
    ])

    # Normalize Activity Weights so the total sum across all rows equals EXACTLY 100.0%
    raw_weight_sum = sum(item[13] for item in raw_activities)
    normalized_weights = [round((item[13] / raw_weight_sum) * 100.0, 4) for item in raw_activities]
    
    # Adjust last item to ensure sum is strictly 100.0000
    weight_diff = 100.0 - sum(normalized_weights)
    normalized_weights[-1] = round(normalized_weights[-1] + weight_diff, 4)

    # Process and write rows with dynamic Excel formulas
    row_start_index = 2

    for idx, raw in enumerate(raw_activities):
        r_num = row_start_index + idx

        # Unpack raw tuple
        (l2_code, l2_name, l3_name, l4_name, wbs_subcode, trade, disc, boq_code, uom,
         plan_q, rep_q, ins_q, acc_q, _, b_start, b_finish, a_start, a_finish,
         p_dur, a_dur, pred, dep_type, contractor, engineer, p_man, a_man,
         p_cost, a_cost, sched_stat, prog_stat, insp_stat, rfi_st, ncr_st,
         mat_st, dwg_st, const_st, risk_st, photo_req, photo_cnt, ev_st, data_src) = raw

        act_wt = normalized_weights[idx]

        # Location Parsing
        wbs_code = f"WBS-{l2_code}.{wbs_subcode}"
        act_id = f"ACT-{l2_code}-{idx+1:04d}"
        
        if "Unit A" in l4_name:
            unit_code = l4_name.split("Unit ")[1].split(" ")[0]
            fl_code = f"L0{unit_code[1]}" if unit_code[1].isdigit() else "GF"
            fl_name_str = f"Level {unit_code[1]}" if unit_code[1].isdigit() else "Ground Floor"
            u_type = "Type A" if unit_code.endswith("1") else "Type B"
            zone_id = "ZONE-RES"
            zone_name = "Residential Unit Zone"
            
            # Room check
            room_id = "RM-GEN"
            room_name = "General Unit Area"
            for r_c, r_n, _, _ in rooms:
                if r_n in l4_name:
                    room_id = f"RM-{r_c}"
                    room_name = r_n
                    break
        elif "Columns" in l4_name or "Slabs" in l4_name:
            parts = l4_name.split(" ")
            fl_name_str = f"{parts[0]} {parts[1]}"
            fl_code = "GF" if "Ground" in fl_name_str else f"L0{parts[1]}"
            unit_code = "COM-SLAB"
            u_type = "Common Core"
            zone_id = "ZONE-STR"
            zone_name = "Structural Core Zone"
            room_id = "RM-CORE"
            room_name = "Structural Deck"
        else:
            fl_code = "COM-EXT"
            fl_name_str = "Site Wide"
            unit_code = "COM-SITE"
            u_type = "Common Area"
            zone_id = "ZONE-EXT"
            zone_name = "Site & External Zone"
            room_id = "RM-SITE"
            room_name = "Site Compound"

        loc_code = f"{bldg_id}-{fl_code}-{unit_code}"

        # Dynamic Formulas:
        # Col AG (Balance_Quantity) = AC - AF
        # Col AH (Physical_Progress_%) = IF(AC>0, (AF/AC)*100, 0)
        # Col AJ (Weighted_Progress_%) = (AH * AI) / 100
        # Col AY (Cost_Progress_%) = IF(AW>0, (AX/AW)*100, 0)
        formula_bal_qty = f"=AC{r_num}-AF{r_num}"
        formula_phys_pct = f"=IF(AC{r_num}>0, (AF{r_num}/AC{r_num})*100, 0)"
        formula_wtd_pct = f"=(AH{r_num}*AI{r_num})/100"
        formula_cost_pct = f"=IF(AW{r_num}>0, (AX{r_num}/AW{r_num})*100, 0)"

        row_values = [
            proj_id, proj_name, bldg_id, bldg_name, fl_code, fl_name_str,
            unit_code, u_type, zone_id, zone_name, room_id, room_name,
            "L1 — Construction & Handover", f"{l2_code} — {l2_name}", l3_name, l4_name,
            wbs_code, act_id, l4_name, f"{l4_name} executed per IFC specifications.",
            trade, disc, boq_code, f"BOQ Item for {l4_name}", f"SPEC-{disc[:3].upper()}-01",
            f"DWG-{bldg_id}-{fl_code}", loc_code, uom,
            plan_q, rep_q, ins_q, acc_q,
            formula_bal_qty, formula_phys_pct, act_wt, formula_wtd_pct,
            b_start, b_finish, a_start, a_finish,
            p_dur, a_dur, pred, dep_type, contractor, engineer,
            p_man, a_man, p_cost, a_cost, formula_cost_pct,
            sched_stat, prog_stat, insp_stat, rfi_st, ncr_st, mat_st, dwg_st,
            const_st, risk_st, photo_req, photo_cnt, ev_st,
            "Executed per standard quality guidelines",
            datetime.now().strftime("%Y-%m-%d %H:%M"), "BuildTrack System Engine", data_src, "Active"
        ]

        ws.append(row_values)

    # Apply Excel Formatting & Styling
    # Colors
    navy_header_fill = PatternFill(start_color="1E293B", end_color="1E293B", fill_type="solid")
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    
    thin_border = Border(
        left=Side(style='thin', color='CBD5E1'),
        right=Side(style='thin', color='CBD5E1'),
        top=Side(style='thin', color='CBD5E1'),
        bottom=Side(style='thin', color='CBD5E1')
    )

    # Format Header Row
    for col_num in range(1, len(headers) + 1):
        cell = ws.cell(row=1, column=col_num)
        cell.fill = navy_header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    # Format Data Rows
    num_data_rows = len(raw_activities)
    max_row = num_data_rows + 1

    for r in range(2, max_row + 1):
        for c in range(1, len(headers) + 1):
            cell = ws.cell(row=r, column=c)
            cell.border = thin_border
            
            # Column-specific number formats and alignments
            col_header = headers[c - 1]
            if col_header in ("Planned_Quantity", "Reported_Quantity", "Inspected_Quantity", "Accepted_Quantity", "Balance_Quantity", "Planned_Cost", "Actual_Cost"):
                cell.number_format = "#,##0.00"
                cell.alignment = Alignment(horizontal="right")
            elif col_header in ("Physical_Progress_%", "Activity_Weight_%", "Weighted_Progress_%", "Cost_Progress_%"):
                cell.number_format = "0.00"
                cell.alignment = Alignment(horizontal="right")
            elif col_header in ("Baseline_Start", "Baseline_Finish", "Actual_Start", "Actual_Finish", "Last_Updated"):
                cell.alignment = Alignment(horizontal="center")
            elif col_header in ("Progress_Status", "Inspection_Status", "RFI_Status", "NCR_Status", "Evidence_Status"):
                cell.alignment = Alignment(horizontal="center")

    # Freeze Header Row
    ws.freeze_panes = "A2"

    # Define Excel Table
    tab_range = f"A1:BP{max_row}"
    tab = Table(displayName="BuildTrackMasterTable", ref=tab_range)
    style = TableStyleInfo(name="TableStyleMedium9", showFirstColumn=False, showLastColumn=False, showRowStripes=True, showColumnStripes=False)
    tab.tableStyleInfo = style
    ws.add_table(tab)

    # Auto-adjust column widths
    for col in ws.columns:
        max_len = 0
        col_letter = get_column_letter(col[0].column)
        for cell in col:
            val_str = str(cell.value or '')
            if len(val_str) > max_len:
                max_len = len(val_str)
        ws.column_dimensions[col_letter].width = max(min(max_len + 3, 35), 12)

    # Save Workbook
    out_path = "BuildTrack_L4_Master_Schedule.xlsx"
    wb.save(out_path)
    print(f"Successfully generated '{out_path}' with {num_data_rows} rows and sheet 'BUILDTRACK_L4_MASTER'.")

if __name__ == "__main__":
    create_l4_master_sheet()
