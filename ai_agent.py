"""
PyCray_SiteIQ — Central AI Construction Project Agent
Powered by Google Gemini Multimodal AI (with heuristic rule fallback)
"""
import os
import json
import re
from datetime import datetime
from database import get_db
from progress_engine import compute_project_metrics

try:
    from dotenv import load_dotenv
    ENV_PATH = os.path.join(os.path.dirname(__file__), ".env")
    load_dotenv(ENV_PATH)
except ImportError:
    pass

try:
    from google import genai
    from google.genai import types
    HAS_GEMINI = True
except ImportError:
    HAS_GEMINI = False

def get_gemini_api_key():
    return os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")

class ProjectAIAgent:
    """
    Central AI Construction Project Assistant & Intelligence System.
    Answers natural language queries using Google Gemini with project database context.
    """

    @staticmethod
    def process_user_query(query: str, user_role: str = "Project Manager"):
        q = query.strip()
        metrics = compute_project_metrics()
        conn = get_db()
        cursor = conn.cursor()

        # Gather real-time project context from SQLite
        cursor.execute("SELECT COUNT(*) FROM rfis WHERE status = 'Open'")
        open_rfis = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM ncrs WHERE status = 'Open'")
        open_ncrs = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM safety_records WHERE status = 'Open'")
        open_safety = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM pm_reviews WHERE pm_status = 'PENDING'")
        pending_pm = cursor.fetchone()[0]

        cursor.execute("""
            SELECT a.activity_code, a.name, a.planned_finish, a.status, t.name as tower, a.floor_level
            FROM activities a
            LEFT JOIN towers t ON a.tower_id = t.id
            WHERE a.status IN ('In Progress', 'Not Started') AND a.planned_finish < DATE('now')
            LIMIT 5
        """)
        delayed = [dict(r) for r in cursor.fetchall()]

        cursor.execute("SELECT name, current_stock, reorder_level, uom FROM materials WHERE current_stock < reorder_level")
        shortages = [dict(r) for r in cursor.fetchall()]

        cursor.execute("SELECT ncr_number, location, description, severity, contractor FROM ncrs WHERE status = 'Open' LIMIT 3")
        recent_ncrs = [dict(r) for r in cursor.fetchall()]

        conn.close()

        # ── 1. REAL GOOGLE GEMINI ANSWERING ──────────────────────────────────
        api_key = get_gemini_api_key()
        if api_key and HAS_GEMINI:
            try:
                client = genai.Client(api_key=api_key)
                
                system_context = f"""
You are the PyCray_SiteIQ AI Construction Project Agent for 'Grand Horizon Residential Towers'.
You assist the project team ({user_role}) with real-time schedule, quality, safety, and progress intelligence.

LIVE PROJECT CONTEXT:
• 4-Way Progress:
  - Planned Baseline Target: {metrics['planned_progress']}%
  - Mode A (AI Automated from Cameras): {metrics['ai_automated_progress']}%
  - Mode B (Field Observed by Operators): {metrics['field_observed_progress']}%
  - Mode B (PM Approved Official): {metrics['pm_approved_progress']}%
  - AI vs PM Approved Variance: {metrics['variances'].get('ai_vs_pm', 0)}%
• Open Items:
  - Open RFIs: {open_rfis}
  - Open NCRs: {open_ncrs} (e.g. {json.dumps(recent_ncrs)})
  - Open Safety Hazards: {open_safety}
  - Pending PM Review Submissions: {pending_pm}
• Delayed Activities: {len(delayed)} activities behind baseline (e.g. {json.dumps(delayed)})
• Material Shortage Warnings: {len(shortages)} items below reorder level ({json.dumps(shortages)})

USER QUERY: "{q}"
USER ROLE: "{user_role}"

INSTRUCTIONS:
1. Answer authoritatively, factually, and concisely using GitHub-flavored Markdown.
2. If asked about Tower A, Level 12, or specific delays, reference the real metrics and activities above.
3. If the user asks about discrepancies, explain the variance between AI automated camera observations ({metrics['ai_automated_progress']}%) and PM approved progress ({metrics['pm_approved_progress']}%).
4. Keep the response crisp, professional, and directly actionable.
"""
                models_to_try = ['gemini-flash-latest', 'gemini-3.6-flash', 'gemini-3.1-flash-lite']
                resp_text = None
                for m in models_to_try:
                    try:
                        res = client.models.generate_content(
                            model=m,
                            contents=system_context
                        )
                        resp_text = res.text.strip()
                        break
                    except Exception:
                        continue

                if resp_text:
                    # Check for action trigger (e.g. create inspection)
                    action_type = None
                    payload = None
                    if "create inspection" in q.lower() or "request inspection" in q.lower():
                        action_type = "CREATE_INSPECTION"
                        payload = {
                            "activity_id": "ACT-TOWA-L12-SLAB",
                            "requested_by": user_role,
                            "target": "Tower A Level 12 Slab Reinforcement"
                        }

                    return {
                        "response": resp_text,
                        "data_type": "gemini_live",
                        "model": "Google Gemini",
                        "action_type": action_type,
                        "payload": payload
                    }

            except Exception as e:
                print(f"[Gemini Query Error]: {e}. Using fallback.")

        # ── 2. HEURISTIC FALLBACK IF GEMINI IS OFFLINE ────────────────────────
        q_lower = q.lower()
        if "tower a" in q_lower and ("complete" in q_lower or "progress" in q_lower):
            tower_a = next((t for t in metrics['towers'] if 'Tower A' in t['tower_name']), None)
            pct = tower_a['pm_pct'] if tower_a else 68.4
            return {
                "response": f"Tower A is currently **{pct}%** complete based on official PM-approved progress (AI observed: **{metrics['ai_automated_progress']}%**).",
                "data_type": "kpi"
            }
        elif "discrepancy" in q_lower or "variance" in q_lower:
            ai_diff = metrics['variances'].get('ai_vs_pm', 0)
            return {
                "response": (
                    f"**Current Progress Discrepancy Analysis:**\n\n"
                    f"• **Mode A (AI Automated Cameras)**: **{metrics['ai_automated_progress']}%**\n"
                    f"• **Mode B (PM Approved Verified)**: **{metrics['pm_approved_progress']}%**\n"
                    f"• **Variance**: **{'+' if ai_diff > 0 else ''}{ai_diff}%**\n\n"
                    f"The primary discrepancy is on **Tower A Level 12 Slab** where AI detected formwork/rebar completion before PM sign-off."
                ),
                "data_type": "discrepancy"
            }
        elif "delayed" in q_lower or "behind schedule" in q_lower:
            count = len(delayed)
            resp_lines = [f"There are currently **{count} activities** behind the approved baseline schedule:\n"]
            for act in delayed:
                resp_lines.append(f"- **[{act['activity_code']}] {act['name']}** ({act['tower']} L{act['floor_level']}) - Due: {act['planned_finish']}")
            return {
                "response": "\n".join(resp_lines),
                "data_type": "list"
            }
        elif "ncr" in q_lower:
            return {
                "response": f"There are currently **{open_ncrs} Open Non-Conformance Reports (NCRs)** requiring corrective action.",
                "data_type": "table"
            }
        elif "pm review" in q_lower or "queue" in q_lower:
            return {
                "response": f"There are **{pending_pm} field photo submissions** pending review in the Project Manager queue.",
                "data_type": "kpi"
            }
        else:
            return {
                "response": (
                    f"**Executive Project Summary:**\n\n"
                    f"• **Planned Baseline Target**: {metrics['planned_progress']}%\n"
                    f"• **Mode A (AI Automated)**: {metrics['ai_automated_progress']}%\n"
                    f"• **Mode B (Field Observed)**: {metrics['field_observed_progress']}%\n"
                    f"• **Mode B (PM Approved)**: {metrics['pm_approved_progress']}%\n"
                    f"• **Open Issues**: {open_rfis} RFIs | {open_ncrs} NCRs | {pending_pm} Pending PM Reviews\n\n"
                    "You can ask me questions such as *'What is the discrepancy between AI and PM progress?'*, *'Show open items in PM Review queue'*, or *'Why is Tower A Level 12 delayed?'*."
                ),
                "data_type": "general_summary"
            }

    @staticmethod
    def get_early_warnings():
        return [
            {
                "category": "Schedule Risk",
                "severity": "High",
                "title": "Superstructure Slab Cycle Slippage",
                "description": "Tower A Level 12 slab casting is trending behind baseline schedule due to inspection queue bottleneck.",
                "action": "Expedite QA/QC rebar clearance inspection."
            },
            {
                "category": "Procurement Risk",
                "severity": "High",
                "title": "Concrete & Rebar Shortage Risk",
                "description": "Ready-mix concrete inventory for tomorrow's Level 12 slab pour is at 110 m³, below the 150 m³ requirement.",
                "action": "Trigger urgent delivery requisition to UltraTech Batching Plant."
            },
            {
                "category": "Quality Risk",
                "severity": "Medium",
                "title": "Repeated Concrete Honeycombing NCRs",
                "description": "NCR flagged for concrete honeycomb compaction in Tower A Level 12 post-pour.",
                "action": "Issue supervisor mandatory vibrator compaction checklist."
            },
            {
                "category": "Safety Risk",
                "severity": "Medium",
                "title": "AI Camera Flagged Perimeter PPE Violations",
                "description": "Camera CAM-T01-12 flagged workers operating near slab edge without fall arrest harness tie-off.",
                "action": "Safety Officer tool-box talk intervention required at Level 12."
            },
            {
                "category": "Progress Discrepancy Risk",
                "severity": "Medium",
                "title": "Reported vs AI Estimated Variance",
                "description": "Contractor reported 85% completion for Tower A L12 Blockwork, while Camera AI detected ~70% visual progress.",
                "action": "Site engineer field verification recommended."
            }
        ]

    @staticmethod
    def generate_daily_report():
        metrics = compute_project_metrics()
        warnings = ProjectAIAgent.get_early_warnings()
        today_str = datetime.now().strftime("%B %d, %Y")

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM ncrs WHERE status = 'Open'")
        open_ncrs = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM rfis WHERE status = 'Open'")
        open_rfis = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM pm_reviews WHERE pm_status = 'PENDING'")
        pending_pm = cursor.fetchone()[0]
        conn.close()

        report = {
            "date": today_str,
            "title": f"Daily AI Construction Project Intelligence Report — {today_str}",
            "overall_physical_progress": f"{metrics['pm_approved_progress']}%",
            "reported_progress": f"{metrics['field_observed_progress']}%",
            "planned_target": f"{metrics['planned_progress']}%",
            "ai_automated_progress": f"{metrics['ai_automated_progress']}%",
            "schedule_variance": f"{metrics['variances'].get('pm_vs_planned', -0.98)}%",
            "today_highlights": [
                f"Mode A AI Automated Progress continuously tracking at {metrics['ai_automated_progress']}%.",
                f"Mode B Official PM-Approved Progress recorded at {metrics['pm_approved_progress']}%.",
                f"{pending_pm} field submission(s) currently awaiting Project Manager review.",
                f"Fixed site cameras completed autonomous scans across Tower A and Tower B."
            ],
            "quality_and_safety": {
                "open_ncrs": open_ncrs,
                "open_rfis": open_rfis,
                "pending_pm_reviews": pending_pm,
                "ai_safety_flags": 2
            },
            "procurement_status": {
                "critical_materials": ["M35 Grade Concrete", "16mm TMT Steel Rebar"],
                "shortage_alerts": 1
            },
            "recommended_actions": [
                {"role": "Project Manager", "action": "Review pending field photo submissions in PM Review Queue.", "priority": "High"},
                {"role": "QA/QC Engineer", "action": "Perform rebar inspection on Tower A Level 12 Slab.", "priority": "High"},
                {"role": "Safety Officer", "action": "Verify edge fall-protection harnesses on Tower A Level 12.", "priority": "Medium"}
            ],
            "early_warnings": warnings
        }

        return report
