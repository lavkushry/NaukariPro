"""
Unit & Integration Tests for 5-Calls/Day Recruiter Outreach & Goal Pacing Engine
Validates:
- 5 message templates generation
- Strict <= 300 character limit on Connection Request Notes
- Recruiter Outreach CRM (JSON & Excel Recruiter_Outreach_Log sync)
- Funnel pacing calculations, conversion rates & diagnostic matrix
- 3-Block execution orchestrator
- CLI command dispatching & dry-run isolation
100% offline, deterministic, zero network calls.
"""

import os
import json
import pytest
import openpyxl
from datetime import datetime
from unittest.mock import MagicMock, patch

from naukari_pro.modules.recruiter_outreach import (
    RecruiterTemplateGenerator,
    RecruiterOutreachCRM,
    VALID_STATUSES,
    TOP_GCC_TARGETS,
    CANDIDATE_FACTS
)
from naukari_pro.modules.goal_5calls import (
    Goal5CallsEngine,
    DAILY_TARGETS,
    DIAGNOSTIC_RULES
)
from naukari_pro.cli import handle_goal_5calls, main


# ==============================================================================
# SECTION 1: TEMPLATE GENERATION & CHARACTER CONSTRAINTS
# ==============================================================================

def test_template_generator_initialization():
    gen = RecruiterTemplateGenerator()
    assert gen.name == "Lavkush Kumar"
    assert "2.5 YOE" in gen.yoe
    assert gen.phone == "+91-9122036484"
    assert gen.email == "lavkushry@gmail.com"


@pytest.mark.parametrize("recruiter_name,company,stack", [
    ("Priya Sharma", "Walmart Global Tech", "Azure Databricks, PySpark & Delta Lake"),
    ("Rajesh Kumar", "Microsoft India Development Center", "Databricks & Delta Lake"),
    ("Sneha", "Amazon Web Services (AWS)", "Distributed PySpark & Kafka"),
    ("Christopher Nolan-Smith-Montgomery", "A Very Long Enterprise Corporation Private Limited", "Databricks, PySpark, Delta Lake, ADF, Kafka, SQL, ADLS Gen2, Terraform"),
    ("", "", "Databricks")
])
def test_connection_note_strict_300_character_limit(recruiter_name, company, stack):
    """
    CRITICAL CONSTRAINT: LinkedIn connection notes must be strictly <= 300 characters.
    Must never exceed 300 chars even with long names or long company names.
    """
    gen = RecruiterTemplateGenerator()
    note = gen.generate_connection_note(recruiter_name, company, stack)
    assert len(note) <= 300, f"Connection note exceeded 300 chars: {len(note)} chars ('{note}')"
    assert "Lavkush" in note
    assert "2.5 YOE" in note
    assert "15-day notice" in note.lower() or "15 days" in note.lower()


def test_direct_inmail_template_content():
    """Verify Direct InMail includes 2.5 YOE, 2M+ events, 15-day notice, and contact details."""
    gen = RecruiterTemplateGenerator()
    inmail = gen.generate_direct_inmail("Anjali Roy", "JPMorgan Chase")
    assert "subject" in inmail and "body" in inmail
    subj = inmail["subject"]
    body = inmail["body"]

    assert "Azure Data Engineer" in subj
    assert "15-Day Notice" in subj
    assert "Lavkush Kumar" in subj

    assert "Hi Anjali," in body
    assert "JPMorgan Chase" in body
    assert "2M+ events/day" in body
    assert "35%" in body
    assert "+91-9122036484" in body
    assert "lavkushry@gmail.com" in body
    assert "linkedin.com/in/lavkushry" in body
    assert "₹20–25 LPA" in body


def test_tech_lead_pitch_content():
    """Verify Tech Lead Outreach highlights Lakehouse scaling, Delta ACID, and DataOps."""
    gen = RecruiterTemplateGenerator()
    pitch = gen.generate_tech_lead_pitch("Amit Verma", "PNC Bank GCC")
    assert "subject" in pitch and "body" in pitch
    subj = pitch["subject"]
    body = pitch["body"]

    assert "Architecture & Lakehouse Scaling" in subj
    assert "Hi Amit," in body
    assert "PNC Bank GCC" in body
    assert "Lakehouse Scaling" in body
    assert "Delta Lake ACID transactions" in body
    assert "Query & Pipeline Optimization" in body
    assert "35%" in body
    assert "Terraform" in body


def test_48h_followup_urgency():
    """Verify 48-Hour Follow-Up is concise, high urgency, and reminds of 15-day notice."""
    gen = RecruiterTemplateGenerator()
    followup = gen.generate_48h_followup("Rohan Gupta", "Barclays")
    assert "subject" in followup and "body" in followup
    assert "Re:" in followup["subject"]
    body = followup["body"]
    assert "Hi Rohan," in body
    assert "Barclays" in body
    assert "active interview rounds" in body.lower()
    assert "15-day notice period" in body.lower()
    assert "+91-9122036484" in body


def test_application_followup():
    """Verify external portal application follow-up references portal and stack."""
    gen = RecruiterTemplateGenerator()
    app_f = gen.generate_application_followup("Vikram", "Adobe", req_id_or_portal="Greenhouse #9812")
    assert "subject" in app_f and "body" in app_f
    assert "Greenhouse #9812" in app_f["subject"]
    body = app_f["body"]
    assert "Greenhouse #9812" in body
    assert "Adobe" in body
    assert "2M+ events/day" in body


def test_template_dispatcher():
    """Verify generate_template dispatches correctly to all 5 template types."""
    gen = RecruiterTemplateGenerator()
    t1 = gen.generate_template("connect", "Sarah", "Google")
    assert len(t1["body"]) <= 300

    t2 = gen.generate_template("inmail", "Sarah", "Google")
    assert "2M+ events" in t2["body"]

    t3 = gen.generate_template("tech-lead", "Dave", "Google")
    assert "Architecture" in t3["subject"]

    t4 = gen.generate_template("48h", "Sarah", "Google")
    assert "active interview rounds" in t4["body"]

    t5 = gen.generate_template("app-followup", "Sarah", "Google", portal_or_req_id="Workday R-102")
    assert "Workday R-102" in t5["body"]


# ==============================================================================
# SECTION 2: RECRUITER OUTREACH CRM & EXCEL LOGGING
# ==============================================================================

def test_crm_json_and_excel_synchronization(tmp_path):
    """
    Verify CRM persists leads to JSON and synchronizes with
    Recruiter_Outreach_Log sheet in Excel tracker.
    """
    json_file = str(tmp_path / "outreach_tracker.json")
    excel_file = str(tmp_path / "Tracker.xlsx")

    # Create dummy workbook
    wb = openpyxl.Workbook()
    wb.active.title = "Applications_Log"
    wb.save(excel_file)

    crm = RecruiterOutreachCRM(json_path=json_file, excel_path=excel_file)

    # 1. Log an outreach
    lead = crm.log_outreach(
        recruiter_name="Sunil Mehta",
        company="Microsoft",
        target_role="Azure Data Engineer",
        platform="LinkedIn",
        message_type="Direct InMail",
        status="CONTACTED",
        notes="First outreach note",
        message_content="Sample pitch"
    )

    assert lead["lead_id"].startswith("LEAD-")
    assert lead["status"] == "CONTACTED"
    assert os.path.exists(json_file)

    # Verify JSON content
    with open(json_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert len(data) == 1
    assert data[0]["recruiter_name"] == "Sunil Mehta"

    # Verify Excel Sheet content
    wb_read = openpyxl.load_workbook(excel_file, read_only=True)
    assert "Recruiter_Outreach_Log" in wb_read.sheetnames
    ws = wb_read["Recruiter_Outreach_Log"]
    rows = list(ws.iter_rows(values_only=True))
    assert len(rows) == 2  # header + 1 data row
    assert rows[0] == (
        "Date", "Recruiter Name", "Company", "Target Role",
        "Platform", "Message Type", "Status", "Notes"
    )
    assert rows[1][1] == "Sunil Mehta"
    assert rows[1][2] == "Microsoft"
    assert rows[1][6] == "CONTACTED"


def test_crm_update_status(tmp_path):
    """Verify lead status update updates both JSON and Excel."""
    json_file = str(tmp_path / "outreach_tracker.json")
    excel_file = str(tmp_path / "Tracker.xlsx")

    crm = RecruiterOutreachCRM(json_path=json_file, excel_path=excel_file)
    lead = crm.log_outreach("Ananya", "Walmart Global Tech", status="CONTACTED")

    # Update to CALL_SCHEDULED
    updated = crm.update_status("Walmart", "CALL_SCHEDULED", notes="Round 1 booked for Thursday")
    assert updated is not None
    assert updated["status"] == "CALL_SCHEDULED"
    assert "Round 1 booked for Thursday" in updated["notes"]

    # Verify invalid status throws ValueError
    with pytest.raises(ValueError):
        crm.update_status("Walmart", "INVALID_STATUS")

    # Verify Excel reflected update
    wb = openpyxl.load_workbook(excel_file, read_only=True)
    ws = wb["Recruiter_Outreach_Log"]
    rows = list(ws.iter_rows(values_only=True))
    assert rows[1][6] == "CALL_SCHEDULED"
    assert "Round 1 booked for Thursday" in rows[1][7]


def test_crm_batch_generate_gcc_outreach(tmp_path):
    """Verify batch generating GCC outreach logs 10 target companies."""
    json_file = str(tmp_path / "outreach_tracker.json")
    excel_file = str(tmp_path / "Tracker.xlsx")

    crm = RecruiterOutreachCRM(json_path=json_file, excel_path=excel_file)
    pitches = crm.batch_generate_gcc_outreach()

    assert len(pitches) == 10
    companies = [p["lead"]["company"] for p in pitches]
    assert "Microsoft" in companies
    assert "Walmart Global Tech" in companies
    assert "JPMorgan Chase" in companies
    assert "Amazon" in companies

    # Check that all generated connection notes strictly adhere to <= 300 chars
    for p in pitches:
        assert len(p["connection_note"]) <= 300

    summary = crm.get_summary()
    assert summary["total_leads"] == 10
    assert summary["today_outreaches"] == 10


# ==============================================================================
# SECTION 3: 5-CALLS/DAY PACING & FUNNEL DIAGNOSTICS
# ==============================================================================

def test_goal_pacing_and_diagnostics_calculation(tmp_path):
    """
    Verify funnel metrics computation, conversion ratios, and diagnostic matrix rules.
    """
    json_file = str(tmp_path / "outreach_tracker.json")
    excel_file = str(tmp_path / "Tracker.xlsx")

    # Set up workbook with mock application and performance rows
    wb = openpyxl.Workbook()
    ws_app = wb.active
    ws_app.title = "Applications_Log"
    ws_app.append(["Application Date", "Company Name", "Job Title", "Match Score (%)"])
    today_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    # Add 30 applications today
    for i in range(30):
        ws_app.append([today_str, f"Company_{i}", "Azure Data Engineer", "85%"])

    # Performance log: low contact views
    ws_perf = wb.create_sheet(title="Recruiter_Performance_Log")
    ws_perf.append(["Timestamp", "Search Appearances", "Profile Views", "Downloads", "Contact Views"])
    ws_perf.append([today_str, 250, 15, 2, 2])

    wb.save(excel_file)

    engine = Goal5CallsEngine(excel_path=excel_file, json_path=json_file)

    # 1. Add mock outreach leads
    engine.crm.log_outreach("Recruiter A", "Microsoft", status="CONNECTED")
    engine.crm.log_outreach("Recruiter B", "Walmart", status="CALL_SCHEDULED")
    engine.crm.log_outreach("Recruiter C", "Amazon", status="PITCH_SENT")

    metrics = engine.calculate_funnel_metrics()

    assert metrics["applications_today"] == 30
    assert metrics["applications_target"] == 35
    assert metrics["outreaches_today"] == 3
    assert metrics["calls_today"] == 1
    assert metrics["calls_target"] == 5
    assert metrics["search_appearances"] == 250
    assert metrics["contact_views"] == 2

    # Diagnostics verification
    diagnostics = engine.run_diagnostics(metrics)
    diag_ids = [d["id"] for d in diagnostics]

    # Should flag LOW_OUTREACH_VOLUME (3 < 10)
    assert "LOW_OUTREACH_VOLUME" in diag_ids
    # Should flag LOW_CONTACT_VIEWS (contact views 2 < 5 with searches 250)
    assert "LOW_CONTACT_VIEWS" in diag_ids
    # Should flag LOW_CALL_CONVERSION (1 < 5)
    assert "LOW_CALL_CONVERSION" in diag_ids


def test_goal_dashboard_string_format(tmp_path):
    """Verify format_dashboard outputs human-readable terminal dashboard with metrics."""
    json_file = str(tmp_path / "outreach_tracker.json")
    excel_file = str(tmp_path / "Tracker.xlsx")

    engine = Goal5CallsEngine(excel_path=excel_file, json_path=json_file)
    engine.crm.batch_generate_gcc_outreach()

    dashboard = engine.format_dashboard()
    assert "5-CALLS/DAY GOAL PACING & RECRUITER OUTREACH DASHBOARD" in dashboard
    assert "DAILY FUNNEL VELOCITY" in dashboard
    assert "Applications Sent:" in dashboard
    assert "Recruiter Outreaches:" in dashboard
    assert "Recruiter Calls Scheduled:" in dashboard
    assert "DAILY 3-BLOCK SCHEDULE:" in dashboard


# ==============================================================================
# SECTION 4: 3-BLOCK EXECUTION ORCHESTRATOR
# ==============================================================================

def test_daily_3_block_orchestrator(tmp_path):
    """Verify execution of Block 1, Block 2, and Block 3."""
    json_file = str(tmp_path / "outreach_tracker.json")
    excel_file = str(tmp_path / "Tracker.xlsx")

    engine = Goal5CallsEngine(excel_path=excel_file, json_path=json_file)

    # Block 1 (Morning)
    b1 = engine.run_block(block_number=1, dry_run=True)
    assert b1["status"] == "COMPLETED"
    assert len(b1["actions_executed"]) == 2
    assert "Resdex" in b1["actions_executed"][0]["action"]
    assert b1["actions_executed"][1]["target_count"] == 25

    # Block 2 (Afternoon)
    b2 = engine.run_block(block_number=2, dry_run=False)
    assert b2["status"] == "COMPLETED"
    assert b2["actions_executed"][0]["count"] == 10
    assert len(engine.crm.leads) == 10

    # Block 3 (Evening)
    b3 = engine.run_block(block_number=3, dry_run=False)
    assert b3["status"] == "COMPLETED"
    assert len(b3["actions_executed"]) == 3
    # Follow-ups executed
    assert b3["actions_executed"][1]["count"] == 5

    # Invalid block throws ValueError
    with pytest.raises(ValueError):
        engine.run_block(block_number=99)


# ==============================================================================
# SECTION 5: CLI DISPATCHING & INTEGRATION
# ==============================================================================

def test_cli_handle_goal_5calls_pacing(capsys):
    """Verify CLI --pacing option prints dashboard cleanly."""
    mock_args = MagicMock()
    mock_args.pacing = True
    mock_args.outreach = False
    mock_args.status = False
    mock_args.block = None
    mock_args.update_status = None
    mock_args.dry_run = True

    ret = handle_goal_5calls(args=mock_args)
    assert ret == 0
    captured = capsys.readouterr()
    assert "5-CALLS/DAY GOAL PACING" in captured.out


def test_cli_handle_goal_5calls_single_outreach(capsys):
    """Verify CLI single recruiter outreach generation in dry-run mode."""
    mock_args = MagicMock()
    mock_args.pacing = False
    mock_args.outreach = True
    mock_args.status = False
    mock_args.block = None
    mock_args.update_status = None
    mock_args.dry_run = True
    mock_args.company = "Microsoft"
    mock_args.recruiter = "Kavita Singh"
    mock_args.role = "Azure Data Engineer"
    mock_args.msg_type = "tech-lead"
    mock_args.notes = "UnitTest"

    ret = handle_goal_5calls(args=mock_args)
    assert ret == 0
    captured = capsys.readouterr()
    assert "RECRUITER OUTREACH TEMPLATES: MICROSOFT" in captured.out
    assert "Kavita Singh" in captured.out
    assert "LINKEDIN CONNECTION NOTE" in captured.out
    assert "Dry-run mode" in captured.out


def test_cli_handle_goal_5calls_block_execution(capsys):
    """Verify CLI --block 1 executes block 1 cleanly."""
    mock_args = MagicMock()
    mock_args.pacing = False
    mock_args.outreach = False
    mock_args.status = False
    mock_args.block = 1
    mock_args.update_status = None
    mock_args.dry_run = True

    ret = handle_goal_5calls(args=mock_args)
    assert ret == 0
    captured = capsys.readouterr()
    assert "DAILY BLOCK 1 EXECUTION SUMMARY" in captured.out
    assert "Resdex Profile Timestamp Refresh" in captured.out


def test_cli_handle_goal_5calls_status_view(capsys):
    """Verify CLI --status displays active CRM summary."""
    mock_args = MagicMock()
    mock_args.pacing = False
    mock_args.outreach = False
    mock_args.status = True
    mock_args.block = None
    mock_args.update_status = None
    mock_args.dry_run = True

    ret = handle_goal_5calls(args=mock_args)
    assert ret == 0
    captured = capsys.readouterr()
    assert "RECRUITER OUTREACH CRM & ACTIVE PIPELINE STATUS" in captured.out
