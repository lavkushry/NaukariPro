"""
naukariPro Recruiter Outreach Engine & CRM Tracker
Target: 5 Recruiter Calls Per Day for ₹25 LPA Azure Data Engineer Opportunities.
Operationalizes outreach template generation, CRM tracking in outreach_tracker.json,
and synchronization to Recruiter_Outreach_Log in Naukri_Live_Application_Tracker.xlsx.
"""

import os
import json
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any

try:
    import openpyxl
    import openpyxl.utils
    from openpyxl.styles import PatternFill, Font, Alignment
except ImportError:
    openpyxl = None
    PatternFill = None
    Font = None
    Alignment = None

from naukari_pro.config import BASE_DIR, WORKSPACE_DIR, TRACKER_PATH, load_config

DEFAULT_OUTREACH_JSON = os.path.join(WORKSPACE_DIR, "outreach_tracker.json")

VALID_STATUSES = [
    "CONTACTED",
    "CONNECTED",
    "PITCH_SENT",
    "CALL_SCHEDULED",
    "REJECTED"
]

VALID_PLATFORMS = ["LinkedIn", "Naukri", "Email", "Referral", "Careers Portal"]

VALID_MESSAGE_TYPES = [
    "Connection Request Note",
    "Direct InMail",
    "Tech Lead Outreach",
    "48-Hour Follow-Up",
    "Application Follow-Up"
]

CANDIDATE_FACTS = {
    "name": "Lavkush Kumar",
    "email": "lavkushry@gmail.com",
    "phone": "+91-9122036484",
    "linkedin": "linkedin.com/in/lavkushry",
    "github": "github.com/lavkushry",
    "experience_yoe": "2.5 YOE",
    "current_role": "Azure Data Engineer / DevOps Engineer",
    "current_company": "CGI India (PNC Bank GCC)",
    "previous_company": "HFCL Limited",
    "target_role": "Azure Data Engineer",
    "target_ctc": "₹20–25 LPA",
    "notice_period": "15 Days or less (Immediate Joiner)",
    "location": "Hyderabad / Bangalore (Open to Bengaluru, Hyderabad, Pune, Gurugram, Remote)",
    "core_stack": "Azure Databricks, PySpark, Delta Lake, ADF, Kafka, SQL, ADLS Gen2, Terraform",
    "key_metrics": "2M+ events/day Medallion Lakehouses, 35% ETL runtime reduction, 99.95% platform uptime"
}

TOP_GCC_TARGETS = [
    {"company": "Microsoft", "role": "Azure Data Engineer", "recruiter": "Kavita Rao", "title": "Data & AI Technical Recruiter"},
    {"company": "Walmart Global Tech", "role": "Azure Data Engineer", "recruiter": "Priya Sharma", "title": "Senior Data Engineering Recruiter"},
    {"company": "JPMorgan Chase", "role": "Data Engineer - VP/Associate", "recruiter": "Rohan Gupta", "title": "Corporate Technology Talent Acquisition"},
    {"company": "Amazon", "role": "Data Engineer II", "recruiter": "Ananya Sen", "title": "AWS / Retail Data Tech Recruiting"},
    {"company": "PNC Bank GCC", "role": "Senior Azure Data Engineer", "recruiter": "Amit Verma", "title": "GCC Campus & Lateral Talent Acquisition"},
    {"company": "Barclays", "role": "Data Platform Engineer", "recruiter": "Vikram Malhotra", "title": "Global Technology Recruiter - Data"},
    {"company": "HSBC Technology", "role": "Azure Data Engineer", "recruiter": "Sneha Kulkarni", "title": "Commercial & Data Tech Talent Sourcing"},
    {"company": "Lloyds Technology Centre", "role": "Cloud Data Engineer", "recruiter": "Arjun Nair", "title": "India Tech Hub Talent Partner"},
    {"company": "Salesforce", "role": "Data Engineer (Data Cloud)", "recruiter": "Neha Kapoor", "title": "Core Engineering Recruiting Lead"},
    {"company": "Adobe", "role": "Big Data / Platform Engineer", "recruiter": "Siddharth Joshi", "title": "Search & Data Platform Tech Sourcing"}
]


class RecruiterTemplateGenerator:
    """
    Generates 5 battle-tested, high-converting recruiter message templates
    custom-tailored for 2.5 YOE Azure Data Engineer (₹20-25 LPA | 15-Day Notice).
    """

    ROLE_KEYWORDS = {
        "technical", "senior", "lead", "corporate", "commercial", "global",
        "india", "aws", "search", "core", "gcc", "talent", "recruiter",
        "recruiting", "acquisition", "hr", "hiring", "campus", "team",
        "partner", "sourcing", "executive", "head", "director", "manager",
        "staff", "associate", "vp", "avp", "tech", "technology", "engineering",
        "people", "specialist", "recruitment", "principal", "consultant"
    }

    PREFIX_TITLES = ["mr.", "mr", "ms.", "ms", "mrs.", "mrs", "dr.", "dr", "prof.", "prof"]

    def __init__(self, candidate: Optional[Dict[str, Any]] = None):
        cfg = load_config()
        self.candidate = candidate or cfg.get("candidate", CANDIDATE_FACTS)
        self.name = self.candidate.get("name", "Lavkush Kumar")
        self.first_name = self.name.split()[0] if self.name else "Lavkush"
        raw_phone = self.candidate.get("phone", "+91-9122036484")
        self.phone = raw_phone.replace(" ", "-") if raw_phone else "+91-9122036484"
        self.email = self.candidate.get("email", "lavkushry@gmail.com")
        self.linkedin = self.candidate.get("linkedin", "linkedin.com/in/lavkushry")
        self.notice = self.candidate.get("notice_period", "15 Days or less (Immediate Joiner)")
        self.yoe = str(self.candidate.get("total_experience_years", "2.5")) + " YOE"

    def _extract_first_name(self, full_or_first: str) -> Optional[str]:
        """
        Extracts personal first name if present. Returns None if the string represents
        a departmental title/role (e.g., 'Technical Talent Acquisition') or empty.
        """
        if not full_or_first or not full_or_first.strip():
            return None
        clean = full_or_first.strip()

        # If separated by parens, hyphen, pipe, comma, extract left portion
        for sep in ["(", " - ", " – ", " — ", "|", ","]:
            if sep in clean:
                left = clean.split(sep)[0].strip()
                if left:
                    clean = left

        # Strip prefixes like Mr., Ms., Dr., Prof.
        clean_lower = clean.lower()
        for prefix in self.PREFIX_TITLES:
            if clean_lower.startswith(prefix + " ") or clean_lower == prefix:
                clean = clean[len(prefix):].strip()
                break

        parts = [p for p in clean.split() if p]
        if not parts:
            return None

        first = parts[0]
        # If the extracted first word is a known role/department keyword, it's not a person's first name
        if first.lower() in self.ROLE_KEYWORDS:
            return None

        # Discard names containing digits
        if any(c.isdigit() for c in first):
            return None

        return first

    def _format_salutation(self, recruiter_name: str, company: str) -> str:
        """
        Produces a natural, polite recruiter salutation.
        If a personal first name is detected, produces 'Hi <Name>,'.
        If a team/role/department is detected, produces 'Hi <Company> Recruiting Team,'
        or 'Hi there,'.
        """
        comp_clean = company.strip() if company else ""
        first = self._extract_first_name(recruiter_name)
        if first:
            return f"Hi {first},"

        if comp_clean:
            if "team" in comp_clean.lower() or "tech" in comp_clean.lower():
                return f"Hi {comp_clean} Team,"
            return f"Hi {comp_clean} Recruiting Team,"
        return "Hi there,"

    def generate_connection_note(
        self,
        recruiter_name: str,
        company: str,
        tech_stack: str = "Databricks, PySpark & Delta Lake"
    ) -> str:
        """
        Template 1: LinkedIn Connection Request Note.
        CRITICAL CONSTRAINT: Hard limit <= 300 characters strictly.
        Guarantees sign-off '- Lavkush' is never sliced or truncated.
        """
        comp_clean = company.strip() if company else "your firm"
        first = self._extract_first_name(recruiter_name)

        if first:
            salutation = f"Hi {first},"
            lead_phrase = f"noticed you recruit for {comp_clean}'s Data team."
        else:
            if comp_clean and comp_clean != "your firm":
                salutation = f"Hi {comp_clean} Recruiting Team,"
                lead_phrase = "noticed your open Data platform roles."
            else:
                salutation = "Hi there,"
                lead_phrase = "noticed your open Data roles."

        closing = f" - {self.first_name}"

        # Tier 1: Base high-converting note
        note = (
            f"{salutation} {lead_phrase} "
            f"I'm an Azure Data Engineer ({self.yoe}) specializing in {tech_stack} "
            f"(2M+ events/day). On a 15-day notice period. Would love to connect regarding open roles!{closing}"
        )

        if len(note) <= 300:
            return note

        # Tier 2: Fallback trimmed version if company name or stack is too long
        note2 = (
            f"{salutation} noticed you hire Data Engineers for {comp_clean}. "
            f"I bring {self.yoe} in Azure Databricks, PySpark & Delta Lake (15-day notice). "
            f"Would love to connect regarding open opportunities!{closing}"
        )

        if len(note2) <= 300:
            return note2

        # Tier 3: Extreme safety truncation strictly guaranteeing <= 300 with intact closing
        fallback_stack = "Databricks & PySpark"
        prefix = f"{salutation} I'm an Azure Data Engineer ({self.yoe}) in {fallback_stack} (15-day notice). Connecting for roles at "
        suffix = f"!{closing}"
        budget = 300 - len(prefix) - len(suffix)
        if budget > 8:
            short_comp = comp_clean[:budget - 3].rstrip() + "..."
        elif budget > 0:
            short_comp = comp_clean[:budget]
        else:
            short_comp = ""
        safe_note = f"{prefix}{short_comp}{suffix}"
        return safe_note[:300]

    def generate_direct_inmail(
        self,
        recruiter_name: str,
        company: str,
        role: str = "Azure Data Engineer"
    ) -> Dict[str, str]:
        """
        Template 2: Direct InMail / First Message.
        Value pitch: 2.5 YOE, 2M+ events, 15-day notice, contact info.
        """
        salutation = self._format_salutation(recruiter_name, company)
        comp_clean = company.strip() if company else "your company"

        subject = f"{role} ({self.yoe} | Databricks, PySpark, Delta Lake) — 15-Day Notice | {self.name}"

        body = (
            f"{salutation}\n\n"
            f"Hope you're having a productive week.\n\n"
            f"I am reaching out regarding {role} opportunities at {comp_clean}. I bring {self.yoe} "
            f"specializing in Azure Databricks, PySpark, Delta Lake, and ADF across enterprise Medallion Lakehouses "
            f"at CGI (PNC Bank GCC) and HFCL.\n\n"
            f"Key Production Highlights:\n"
            f"• Medallion Lakehouse: Engineered ADF & PySpark pipelines processing 2M+ events/day into Bronze, Silver, "
            f"and Gold Delta tables with sub-second streaming ingestion.\n"
            f"• Performance & Latency: Optimized distributed Spark SQL transformations, slashing batch ETL execution "
            f"runtime by 35% while sustaining 99.95% platform availability.\n"
            f"• Infrastructure & DataOps: Automated Lakehouse provisioning & CI/CD quality validation gates using "
            f"Terraform, Docker, and Kubernetes.\n\n"
            f"Availability & Compensation:\n"
            f"• Notice Period: 15 Days or less (Immediate joiner)\n"
            f"• Target CTC: ₹20–25 LPA\n"
            f"• Location: Hyderabad / Bangalore (Open to Bengaluru, Hyderabad, Pune, Gurugram, Remote)\n\n"
            f"Direct Contact:\n"
            f"• Phone: {self.phone}\n"
            f"• Email: {self.email}\n"
            f"• LinkedIn: {self.linkedin}\n\n"
            f"Would you have 5 minutes for a brief introductory call this week?\n\n"
            f"Best regards,\n"
            f"{self.name}"
        )
        return {"subject": subject, "body": body}

    def generate_tech_lead_pitch(
        self,
        lead_name: str,
        company: str,
        role: str = "Azure Data Engineer"
    ) -> Dict[str, str]:
        """
        Template 3: Hiring Manager / Tech Lead Outreach.
        Lakehouse scaling pitch, Delta ACID, 15-day notice, engineering depth.
        """
        salutation = self._format_salutation(lead_name, company)
        comp_clean = company.strip() if company else "your engineering team"

        subject = f"{role} Architecture & Lakehouse Scaling | {self.name} (15-Day Notice)"

        body = (
            f"{salutation}\n\n"
            f"I have been following {comp_clean}'s engineering deliverables and wanted to reach out directly.\n\n"
            f"I am an Azure Data Engineer ({self.yoe}) building high-throughput Lakehouse data backbones "
            f"(Azure Databricks, PySpark, Delta Lake, ADF, Kafka) at CGI (PNC Bank GCC).\n\n"
            f"What I can immediately deliver for your data platform:\n"
            f"1. Lakehouse Scaling: Hands-on experience architecting Medallion Lakehouses processing 2M+ events/day "
            f"with Delta Lake ACID transactions, CDC ingestion, and schema enforcement.\n"
            f"2. Query & Pipeline Optimization: Deep PySpark & Spark SQL performance tuning (partition pruning, "
            f"liquid clustering, broadcast joins), reducing ETL execution latencies by 35%.\n"
            f"3. Reliable DataOps: Production Terraform IaC and automated validation gates (Great Expectations, CI/CD), "
            f"ensuring zero schema drift and high platform availability.\n\n"
            f"I am on a 15-day notice period and actively targeting ₹20–25 LPA Azure Data Engineering roles.\n\n"
            f"I would welcome a 10-minute technical chat to discuss your current data platform challenges and share "
            f"how my background aligns with {comp_clean}'s roadmap.\n\n"
            f"Best regards,\n"
            f"{self.name}\n"
            f"Phone: {self.phone} | Email: {self.email} | LinkedIn: {self.linkedin}"
        )
        return {"subject": subject, "body": body}

    def generate_48h_followup(
        self,
        recruiter_name: str,
        company: str,
        role: str = "Azure Data Engineer"
    ) -> Dict[str, str]:
        """
        Template 4: 48-Hour Follow-Up (Brief, high urgency).
        """
        salutation = self._format_salutation(recruiter_name, company)
        comp_clean = company.strip() if company else "your team"

        subject = f"Re: {role} Opportunities — 15-Day Notice | {self.name}"

        body = (
            f"{salutation}\n\n"
            f"Following up on my note from earlier this week regarding {role} roles at {comp_clean}.\n\n"
            f"I am currently in active interview rounds, but {comp_clean} is a top priority for me given "
            f"your data platform stack and engineering scope. As a quick reminder, I bring {self.yoe} in "
            f"Azure Databricks, PySpark, Delta Lake, and a confirmed 15-day notice period (immediate joiner).\n\n"
            f"Would you have 5 minutes for a quick sync today or tomorrow? You can reach me directly at {self.phone}.\n\n"
            f"Best,\n"
            f"{self.name}\n"
            f"{self.email} | {self.linkedin}"
        )
        return {"subject": subject, "body": body}

    def generate_application_followup(
        self,
        recruiter_name: str,
        company: str,
        role: str = "Azure Data Engineer",
        portal_or_req_id: Optional[str] = None,
        req_id_or_portal: Optional[str] = None
    ) -> Dict[str, str]:
        """
        Template 5: External Portal Application Follow-Up.
        Sent after applying on Greenhouse/Ashby/Workday/Naukri.
        """
        portal = portal_or_req_id or req_id_or_portal or "Careers Portal"
        salutation = self._format_salutation(recruiter_name, company)
        comp_clean = company.strip() if company else "your firm"

        subject = f"Applied: {role} ({portal}) — {self.name} (15-Day Notice)"

        body = (
            f"{salutation}\n\n"
            f"I recently submitted my application for the {role} position at {comp_clean} (via {portal}).\n\n"
            f"Given the direct alignment between your stack requirements and my {self.yoe} in Azure Databricks, "
            f"PySpark, Delta Lake, and ADF, I wanted to reach out personally to ensure my profile is on your radar.\n\n"
            f"Quick Snapshot:\n"
            f"• Stack: Azure Databricks, PySpark, Delta Lake, ADF, Kafka, SQL, Terraform\n"
            f"• Scale: 2M+ events/day Medallion Lakehouses, 35% ETL runtime cut, 99.95% uptime\n"
            f"• Availability: 15 Days or less (Immediate joiner)\n"
            f"• Target CTC: ₹20–25 LPA\n\n"
            f"I have attached my resume and would welcome the opportunity to discuss how I can hit the ground "
            f"running on {comp_clean}'s data engineering deliverables.\n\n"
            f"Direct Contact: {self.phone} | {self.email} | {self.linkedin}\n\n"
            f"Thanks for your time and consideration,\n"
            f"{self.name}"
        )
        return {"subject": subject, "body": body}

    def generate_template(
        self,
        template_type: str,
        recruiter_name: str,
        company: str,
        role: str = "Azure Data Engineer",
        **kwargs
    ) -> Dict[str, str]:
        """Unified template dispatcher."""
        t_lower = template_type.lower()
        if "connect" in t_lower or "note" in t_lower:
            note = self.generate_connection_note(
                recruiter_name, company, kwargs.get("tech_stack", "Databricks, PySpark & Delta Lake")
            )
            return {"subject": f"Connection Note for {company}", "body": note}
        elif "lead" in t_lower or "manager" in t_lower or "tech" in t_lower:
            return self.generate_tech_lead_pitch(recruiter_name, company, role)
        elif "48" in t_lower or "follow" in t_lower and "up" in t_lower and "app" not in t_lower:
            return self.generate_48h_followup(recruiter_name, company, role)
        elif "app" in t_lower or "portal" in t_lower:
            portal = (
                kwargs.get("portal")
                or kwargs.get("portal_or_req_id")
                or kwargs.get("req_id")
                or kwargs.get("req_id_or_portal")
                or "Careers Portal"
            )
            return self.generate_application_followup(recruiter_name, company, role, portal)
        else:
            return self.generate_direct_inmail(recruiter_name, company, role)


class RecruiterOutreachCRM:
    """
    Recruiter Outreach CRM & Tracker.
    Stores leads in outreach_tracker.json and synchronizes with
    the Recruiter_Outreach_Log sheet in Naukri_Live_Application_Tracker.xlsx.
    """

    SHEET_NAME = "Recruiter_Outreach_Log"
    SHEET_HEADERS = [
        "Date",
        "Recruiter Name",
        "Company",
        "Target Role",
        "Platform",
        "Message Type",
        "Status",
        "Notes"
    ]

    def __init__(self, json_path: Optional[str] = None, excel_path: Optional[str] = None):
        self.json_path = json_path or DEFAULT_OUTREACH_JSON
        self.excel_path = excel_path or TRACKER_PATH
        self.generator = RecruiterTemplateGenerator()
        self.leads: List[Dict[str, Any]] = []
        self._load_json()

    def _load_json(self) -> None:
        if os.path.exists(self.json_path):
            try:
                with open(self.json_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.leads = data if isinstance(data, list) else data.get("leads", [])
            except Exception:
                self.leads = []
        else:
            self.leads = []

    def _save_json(self) -> None:
        try:
            parent = os.path.dirname(self.json_path)
            if parent and not os.path.exists(parent):
                os.makedirs(parent, exist_ok=True)
            with open(self.json_path, "w", encoding="utf-8") as f:
                json.dump(self.leads, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[!] Warning: Failed saving outreach json: {e}")

    def log_outreach(
        self,
        recruiter_name: str,
        company: str,
        target_role: str = "Azure Data Engineer",
        platform: str = "LinkedIn",
        message_type: str = "Connection Request Note",
        status: str = "CONTACTED",
        notes: str = "",
        message_content: str = "",
        lead_id: Optional[str] = None,
        date_str: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Logs a new recruiter outreach entry into JSON CRM and syncs to Excel.
        """
        status_norm = status.upper().strip()
        if status_norm not in VALID_STATUSES:
            status_norm = "CONTACTED"

        now = date_str or datetime.now().strftime("%Y-%m-%d %H:%M")

        # Check if already exists (same recruiter and company) or matching lead_id
        existing_idx = None
        for i, item in enumerate(self.leads):
            if (lead_id and item.get("lead_id") == lead_id) or (
                item.get("recruiter_name", "").lower() == recruiter_name.strip().lower()
                and item.get("company", "").lower() == company.strip().lower()
            ):
                existing_idx = i
                break

        lid = lead_id or (self.leads[existing_idx].get("lead_id") if existing_idx is not None else f"LEAD-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}")

        lead = {
            "lead_id": lid,
            "date": self.leads[existing_idx].get("date", now) if existing_idx is not None else now,
            "recruiter_name": recruiter_name.strip(),
            "company": company.strip(),
            "target_role": target_role.strip(),
            "platform": platform.strip(),
            "message_type": message_type.strip(),
            "status": status_norm,
            "notes": notes.strip(),
            "message_content": message_content.strip(),
            "updated_at": now
        }

        # Track timestamp when status is set to CALL_SCHEDULED
        if status_norm == "CALL_SCHEDULED":
            prev_call = self.leads[existing_idx].get("call_scheduled_at") if existing_idx is not None else None
            lead["call_scheduled_at"] = prev_call or now

        if existing_idx is not None:
            self.leads[existing_idx].update(lead)
            entry = self.leads[existing_idx]
        else:
            self.leads.append(lead)
            entry = lead

        self._save_json()
        self.sync_to_excel()
        return entry

    def update_status(
        self,
        identifier: str,
        new_status: str,
        notes: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Updates status and notes for a lead identified by lead_id, recruiter_name, or company.
        """
        status_norm = new_status.upper().strip()
        if status_norm not in VALID_STATUSES:
            raise ValueError(f"Invalid status '{new_status}'. Allowed: {VALID_STATUSES}")

        ident_clean = identifier.lower().strip()
        matched = None

        for lead in self.leads:
            if (
                lead.get("lead_id", "").lower() == ident_clean
                or lead.get("recruiter_name", "").lower() == ident_clean
                or ident_clean in lead.get("company", "").lower()
            ):
                lead["status"] = status_norm
                now = datetime.now().strftime("%Y-%m-%d %H:%M")
                lead["updated_at"] = now
                if status_norm == "CALL_SCHEDULED" and not lead.get("call_scheduled_at"):
                    lead["call_scheduled_at"] = now
                if notes:
                    prev_notes = lead.get("notes", "")
                    lead["notes"] = f"{prev_notes} | {notes}".strip(" |") if prev_notes else notes
                matched = lead
                break

        if matched:
            self._save_json()
            self.sync_to_excel()
        return matched

    def list_active_leads(self, filter_status: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Returns leads, optionally filtered by status (case-insensitive).
        """
        if not filter_status:
            return self.leads
        f_norm = filter_status.upper().strip()
        return [l for l in self.leads if l.get("status", "").upper() == f_norm]

    def get_summary(self) -> Dict[str, Any]:
        """
        Returns CRM status metrics summary.
        """
        total = len(self.leads)
        status_counts = {s: 0 for s in VALID_STATUSES}
        for l in self.leads:
            s = l.get("status", "CONTACTED").upper()
            if s in status_counts:
                status_counts[s] += 1
            else:
                status_counts[s] = status_counts.get(s, 0) + 1

        today_str = datetime.now().strftime("%Y-%m-%d")
        today_outreaches = sum(
            1 for l in self.leads if str(l.get("date", "")).startswith(today_str)
        )
        today_calls = sum(
            1 for l in self.leads
            if l.get("status") == "CALL_SCHEDULED"
            and (
                str(l.get("call_scheduled_at", "")).startswith(today_str)
                or (not l.get("call_scheduled_at") and (
                    str(l.get("updated_at", "")).startswith(today_str) or str(l.get("date", "")).startswith(today_str)
                ))
            )
        )

        return {
            "total_leads": total,
            "today_outreaches": today_outreaches,
            "today_calls_scheduled": today_calls,
            "by_status": status_counts
        }

    def sync_to_excel(self, excel_path: Optional[str] = None) -> bool:
        """
        Synchronizes all CRM leads into the dedicated Recruiter_Outreach_Log sheet
        in Naukri_Live_Application_Tracker.xlsx with executive styling.
        """
        if openpyxl is None:
            return False

        path = excel_path or self.excel_path
        try:
            if not os.path.exists(path):
                wb = openpyxl.Workbook()
                ws = wb.active
                ws.title = self.SHEET_NAME
                ws.append(self.SHEET_HEADERS)
            else:
                wb = openpyxl.load_workbook(path)
                if self.SHEET_NAME not in wb.sheetnames:
                    ws = wb.create_sheet(title=self.SHEET_NAME)
                    ws.append(self.SHEET_HEADERS)
                else:
                    ws = wb[self.SHEET_NAME]

            # Clear existing data rows while preserving headers
            max_r = ws.max_row
            if max_r > 1:
                ws.delete_rows(2, max_r - 1)

            # Style header row (Row 1)
            navy_fill = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")
            header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
            center_align = Alignment(horizontal="center", vertical="center", wrap_text=True)

            for col_idx in range(1, len(self.SHEET_HEADERS) + 1):
                cell = ws.cell(row=1, column=col_idx)
                cell.fill = navy_fill
                cell.font = header_font
                cell.alignment = center_align

            ws.row_dimensions[1].height = 28

            # Status fills
            scheduled_fill = PatternFill(start_color="D1FAE5", end_color="D1FAE5", fill_type="solid")
            scheduled_font = Font(name="Calibri", size=10, bold=True, color="065F46")
            connected_fill = PatternFill(start_color="DBEAFE", end_color="DBEAFE", fill_type="solid")
            connected_font = Font(name="Calibri", size=10, color="1E40AF")
            rejected_fill = PatternFill(start_color="FEE2E2", end_color="FEE2E2", fill_type="solid")
            rejected_font = Font(name="Calibri", size=10, color="991B1B")
            default_font = Font(name="Calibri", size=10)

            for l in self.leads:
                ws.append([
                    l.get("date", ""),
                    l.get("recruiter_name", ""),
                    l.get("company", ""),
                    l.get("target_role", "Azure Data Engineer"),
                    l.get("platform", "LinkedIn"),
                    l.get("message_type", "Connection Request Note"),
                    l.get("status", "CONTACTED"),
                    l.get("notes", "")
                ])
                curr_row = ws.max_row
                ws.row_dimensions[curr_row].height = 20
                st_val = l.get("status", "CONTACTED").upper()

                status_cell = ws.cell(row=curr_row, column=7)
                if st_val == "CALL_SCHEDULED":
                    status_cell.fill = scheduled_fill
                    status_cell.font = scheduled_font
                elif st_val in ["CONNECTED", "PITCH_SENT"]:
                    status_cell.fill = connected_fill
                    status_cell.font = connected_font
                elif st_val == "REJECTED":
                    status_cell.fill = rejected_fill
                    status_cell.font = rejected_font
                else:
                    status_cell.font = default_font

                for c_idx in range(1, 9):
                    c = ws.cell(row=curr_row, column=c_idx)
                    if c_idx not in [2, 3, 4, 8]:
                        c.alignment = Alignment(horizontal="center", vertical="center")
                    else:
                        c.alignment = Alignment(horizontal="left", vertical="center")

            # Auto-fit column widths
            col_widths = {
                1: 18,  # Date
                2: 24,  # Recruiter Name
                3: 25,  # Company
                4: 24,  # Target Role
                5: 14,  # Platform
                6: 24,  # Message Type
                7: 18,  # Status
                8: 45   # Notes
            }
            for col_idx, width in col_widths.items():
                col_letter = openpyxl.utils.get_column_letter(col_idx)
                ws.column_dimensions[col_letter].width = width

            wb.save(path)
            return True
        except Exception as e:
            print(f"[!] Warning: Failed syncing Recruiter_Outreach_Log in Excel: {e}")
            return False

    def batch_generate_gcc_outreach(self, target_list: Optional[List[Dict[str, str]]] = None) -> List[Dict[str, Any]]:
        """
        Generates 10 recruiter pitches for top target GCC companies and logs them.
        """
        targets = target_list or TOP_GCC_TARGETS
        generated = []
        for t in targets:
            comp = t.get("company", "Tech Company")
            rec = t.get("recruiter", "Recruiter")
            role = t.get("role", "Azure Data Engineer")

            # Alternating templates: direct inmail & tech lead pitch
            if any(k in comp.lower() for k in ["walmart", "jpmorgan", "amazon"]):
                pitch = self.generator.generate_tech_lead_pitch(rec, comp, role)
                msg_type = "Tech Lead Outreach"
            else:
                pitch = self.generator.generate_direct_inmail(rec, comp, role)
                msg_type = "Direct InMail"

            conn_note = self.generator.generate_connection_note(rec, comp)

            entry = self.log_outreach(
                recruiter_name=rec,
                company=comp,
                target_role=role,
                platform="LinkedIn",
                message_type=msg_type,
                status="CONTACTED",
                notes="Generated via 5-Calls/Day Autonomous GCC batch",
                message_content=pitch["body"]
            )
            generated.append({
                "lead": entry,
                "connection_note": conn_note,
                "inmail_subject": pitch["subject"],
                "inmail_body": pitch["body"]
            })
        return generated
