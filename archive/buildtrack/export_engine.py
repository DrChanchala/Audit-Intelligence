import os
import io
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from database import get_db
from progress_engine import compute_project_metrics

def generate_excel_report(report_type="progress"):
    """
    Generates a beautifully styled Excel report workbook for BuildTrack.
    Returns bytes of the Excel file.
    """
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "BuildTrack Executive Report"

    # Styling colors
    navy_header = PatternFill(start_color="1E293B", end_color="1E293B", fill_type="solid")
    accent_blue = PatternFill(start_color="2563EB", end_color="2563EB", fill_type="solid")
    light_gray = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")
    white_bold = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    dark_bold = Font(name="Calibri", size=12, bold=True, color="0F172A")
    title_font = Font(name="Calibri", size=16, bold=True, color="1E293B")
    
    thin_border = Border(
        left=Side(style='thin', color='E2E8F0'),
        right=Side(style='thin', color='E2E8F0'),
        top=Side(style='thin', color='E2E8F0'),
        bottom=Side(style='thin', color='E2E8F0')
    )

    # Title Block
    ws.merge_cells("A1:G1")
    ws["A1"] = "PYCRAY_SITEIQ — DUAL-MODE AI CONSTRUCTION PROGRESS REPORT"
    ws["A1"].font = title_font
    ws["A1"].alignment = Alignment(horizontal="left", vertical="center")

    ws["A2"] = "Project: Grand Horizon Residential Towers | L4 Baseline Rev 1.0"
    ws["A2"].font = Font(size=10, italic=True, color="64748B")

    conn = get_db()
    cursor = conn.cursor()

    if report_type == "progress":
        metrics = compute_project_metrics()
        
        # Summary Table
        ws["A4"] = "KPI Metric"
        ws["B4"] = "Percentage / Value"
        for col in ["A4", "B4"]:
            ws[col].fill = navy_header
            ws[col].font = white_bold
            
        summary_rows = [
            ("Planned Target Progress (L4 Baseline)", f"{metrics['planned_progress']}%"),
            ("Mode A: AI Automated Progress (Static Cameras)", f"{metrics['ai_automated_progress']}%"),
            ("Mode B: Field Observed Progress (Site Operator)", f"{metrics['field_observed_progress']}%"),
            ("Mode B: PM Approved Progress (Verified Official)", f"{metrics['pm_approved_progress']}%"),
            ("AI vs PM Approved Variance", f"{metrics['variances'].get('ai_vs_pm', 0)}%"),
            ("Financial Progress (Earned Value)", f"{metrics['financial_progress']}%")
        ]
        
        row_idx = 5
        for kpi, val in summary_rows:
            ws.cell(row=row_idx, column=1, value=kpi).border = thin_border
            cell_v = ws.cell(row=row_idx, column=2, value=val)
            cell_v.border = thin_border
            cell_v.alignment = Alignment(horizontal="right")
            row_idx += 1

        # Activity Breakdown Header
        row_idx += 2
        headers = ["Activity Code", "Activity Name", "Tower / Location", "Planned Qty", "Reported Qty", "Accepted Qty", "UOM", "Physical %", "Status"]
        for col_idx, h in enumerate(headers, 1):
            c = ws.cell(row=row_idx, column=col_idx, value=h)
            c.fill = accent_blue
            c.font = white_bold
            c.alignment = Alignment(horizontal="center")

        cursor.execute("""
            SELECT a.activity_code, a.name, t.name as tower, a.floor_level, a.planned_qty, a.reported_qty, a.accepted_qty, a.uom, a.status
            FROM activities a
            LEFT JOIN towers t ON a.tower_id = t.id
            ORDER BY a.tower_id, a.floor_level
        """)
        activities = cursor.fetchall()
        
        for act in activities:
            row_idx += 1
            pl = float(act['planned_qty'] or 0.0)
            acc = float(act['accepted_qty'] or 0.0)
            pct = round((acc / pl * 100.0), 1) if pl > 0 else 0.0
            loc = f"{act['tower']} L{act['floor_level']}" if act['tower'] else "Site General"
            
            ws.cell(row=row_idx, column=1, value=act['activity_code']).border = thin_border
            ws.cell(row=row_idx, column=2, value=act['name']).border = thin_border
            ws.cell(row=row_idx, column=3, value=loc).border = thin_border
            ws.cell(row=row_idx, column=4, value=act['planned_qty']).border = thin_border
            ws.cell(row=row_idx, column=5, value=act['reported_qty']).border = thin_border
            ws.cell(row=row_idx, column=6, value=act['accepted_qty']).border = thin_border
            ws.cell(row=row_idx, column=7, value=act['uom']).border = thin_border
            ws.cell(row=row_idx, column=8, value=f"{pct}%").border = thin_border
            ws.cell(row=row_idx, column=9, value=act['status']).border = thin_border

    elif report_type == "ncr":
        headers = ["NCR Number", "Location", "Description", "Severity", "Contractor", "Due Date", "Status"]
        row_idx = 4
        for col_idx, h in enumerate(headers, 1):
            c = ws.cell(row=row_idx, column=col_idx, value=h)
            c.fill = navy_header
            c.font = white_bold
            
        cursor.execute("SELECT * FROM ncrs")
        ncrs = cursor.fetchall()
        for n in ncrs:
            row_idx += 1
            ws.cell(row=row_idx, column=1, value=n['ncr_number']).border = thin_border
            ws.cell(row=row_idx, column=2, value=n['location']).border = thin_border
            ws.cell(row=row_idx, column=3, value=n['description']).border = thin_border
            ws.cell(row=row_idx, column=4, value=n['severity']).border = thin_border
            ws.cell(row=row_idx, column=5, value=n['contractor']).border = thin_border
            ws.cell(row=row_idx, column=6, value=n['due_date']).border = thin_border
            ws.cell(row=row_idx, column=7, value=n['status']).border = thin_border

    conn.close()

    # Adjust column widths
    for col in ws.columns:
        max_len = max(len(str(cell.value or '')) for cell in col)
        col_letter = openpyxl.utils.get_column_letter(col[0].column)
        ws.column_dimensions[col_letter].width = max(max_len + 3, 12)

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return output.getvalue()
