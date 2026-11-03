"""
tests/test_visibility_and_pacing.py

Comprehensive Test Suite for Milestone 2: Profile Visibility & Recruiter Engagement Scaling (100K Impressions)
Validates Features 7 through 11:
- Feature 7: Unified 100K Impression Pacing Speedometer & Multi-Sink Telemetry (JSON, Excel, SQLite)
- Feature 8: MLOps Persona Keyword & Token Alignment & Fact Matrix Fidelity
- Feature 9: LinkedIn Search Appearance Metrics Extraction (Offline HTML Fixtures & Telemetry)
- Feature 10: Recency Bumping (2h Cooldown, Micro-bumps, 11-Facet Resdex Sync, SEO Saturation Score)
- Feature 11: Recruiter Outreach Automation & Rate Limits (<=8/day limit, <=300 chars, 30-80ms typing delay)

100% offline, deterministic, zero external network requests.
"""

import os
import json
import sqlite3
import tempfile
import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

from naukari_pro.modules.profile_performance import (
    BenchmarkPacing,
    compute_benchmark_pacing,
    compute_unified_pacing,
    Unified100KSpeedometer,
    get_unified_speedometer,
    TARGET_MLOPS_KEYWORDS,
    TARGET_DE_KEYWORDS,
    generate_keyword_diff_report,
    log_performance_snapshot,
)
from naukari_pro.modules.linkedin_optimizer import (
    LINKEDIN_100K_BLUEPRINT,
    LINKEDIN_100K_MLOPS_BLUEPRINT,
    get_100k_blueprint,
    LinkedInProfileAuditor,
    calculate_seo_saturation_score,
    extract_linkedin_search_appearances,
    LinkedInAnalyticsCollector,
)
from naukari_pro.modules.profile_updater import (
    COOLDOWN_SECONDS,
    MLOPS_HEADLINE_TEMPLATE,
    MLOPS_KEY_SKILLS,
    MLOPS_IT_SKILLS,
    check_cooldown,
    micro_bump_headline,
    sync_11_facets,
    ProfileUpdater,
)
from naukari_pro.modules.recruiter_outreach import (
    RecruiterTemplateGenerator,
    RecruiterOutreachCRM,
    generate_mlops_connection_note,
    generate_mlops_inmail,
    CANDIDATE_FACTS,
)
from naukari_pro.modules.linkedin_outreach import (
    LinkedInOutreachSender,
)
from naukari_pro.modules.goal_5calls import Goal5CallsEngine
from naukari_pro.config import load_config
from scripts.mutator import BlacklistValidator


# ==============================================================================
# FEATURE 7: UNIFIED 100K IMPRESSION PACING SPEEDOMETER & MULTI-SINK TELEMETRY
# ==============================================================================

class TestFeature7Unified100KSpeedometer:
    """Validates multi-platform aggregation, run-rate calculations, and multi-sink logging."""

    def test_compute_benchmark_pacing_basic(self):
        """Verify baseline 30-day 100K benchmark calculations (3,333.33 / day)."""
        # Exactly on benchmark: 10 days, 33,333 impressions
        pacing = compute_benchmark_pacing(
            current_appearances=33333,
            elapsed_days=10,
            target_appearances=100000,
            target_days=30,
        )
        assert pacing.target_total == 100000
        assert pacing.daily_target == pytest.approx(3333.33, rel=1e-3)
        assert pacing.actual_daily_pace == pytest.approx(3333.3, rel=1e-3)
        assert pacing.projected_30d_volume == pytest.approx(99999, abs=2)
        assert pacing.status == "ON_TRACK"
        assert pacing.attainment_pct == pytest.approx(33.33, rel=1e-2)
        assert pacing.daily_shortfall >= 0

    def test_compute_benchmark_pacing_ahead_and_deficit_status(self):
        """Verify status classifications: AHEAD (>+5%) and DEFICIT (<-5%)."""
        # Ahead: 10 days, 45,000 impressions (4,500/day vs 3,333.33/day)
        ahead = compute_benchmark_pacing(
            current_appearances=45000,
            elapsed_days=10,
            target_appearances=100000,
            target_days=30,
        )
        assert ahead.status == "AHEAD"
        assert ahead.deficit == 0.0
        assert ahead.projected_30d_volume == 135000

        # Deficit: 10 days, 20,000 impressions (2,000/day vs 3,333.33/day)
        behind = compute_benchmark_pacing(
            current_appearances=20000,
            elapsed_days=10,
            target_appearances=100000,
            target_days=30,
        )
        assert behind.status == "DEFICIT"
        assert behind.deficit > 0.0
        assert behind.projected_30d_volume == 60000
        assert behind.attainment_pct == 20.0

    def test_compute_benchmark_pacing_multiplatform_aggregation(self):
        """Verify aggregation across Naukri searches, LinkedIn searches, and LinkedIn impressions."""
        pacing = compute_benchmark_pacing(
            current_appearances=0,  # fallback if passed 0
            naukri_searches=15000,
            linkedin_searches=10000,
            linkedin_impressions=15000,
            elapsed_days=10,
            target_appearances=100000,
        )
        assert pacing.total_impressions == 40000
        assert pacing.naukri_searches == 15000
        assert pacing.linkedin_searches == 10000
        assert pacing.linkedin_impressions == 15000
        assert pacing.actual_daily_pace == 4000.0
        assert pacing.status == "AHEAD"
        assert pacing.platform_breakdown["naukri_searches"] == 15000
        assert pacing.platform_breakdown["linkedin_searches"] == 10000
        assert pacing.platform_breakdown["linkedin_impressions"] == 15000

    def test_unified_speedometer_class(self):
        """Verify Unified100KSpeedometer state management and report generation."""
        speedo = Unified100KSpeedometer(target_total=100000, target_days=30)
        speedo.add_naukri_metrics(search_appearances=12000, profile_views=400)
        speedo.add_linkedin_metrics(search_appearances=8000, impressions=15000)

        pacing = speedo.compute_current_pacing(elapsed_days=10)
        assert pacing.total_impressions == 35000
        assert pacing.status == "AHEAD"
        assert pacing.attainment_pct == 35.0

        report = speedo.generate_speedometer_report(elapsed_days=10)
        assert "UNIFIED 100K IMPRESSION PACING SPEEDOMETER" in report
        assert "AHEAD" in report
        assert "Naukri Searches:" in report
        assert "LinkedIn Searches:" in report
        assert "35.0%" in report

    def test_multi_sink_logging(self, tmp_path):
        """Verify telemetry snapshot logs to JSON, Excel, and SQLite without data corruption."""
        json_path = str(tmp_path / "test_history.json")
        excel_path = str(tmp_path / "test_tracker.xlsx")
        db_path = str(tmp_path / "test_applied.db")

        # Initialize SQLite DB schema
        conn = sqlite3.connect(db_path)
        conn.execute("""
            CREATE TABLE profile_performance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                searches_7d INTEGER,
                views_7d INTEGER,
                calls_today INTEGER,
                total_impressions INTEGER,
                daily_pace REAL,
                pacing_status TEXT,
                notes TEXT
            )
        """)
        conn.commit()
        conn.close()

        # Log snapshot
        success = log_performance_snapshot(
            searches=2500,
            views=80,
            calls_today=3,
            notes="Milestone 2 multi-sink test",
            json_path=json_path,
            excel_path=excel_path,
            db_path=db_path,
            naukri_searches=1500,
            linkedin_searches=1000,
            linkedin_impressions=2000,
            elapsed_days=2,
        )
        assert success is True

        # 1. Verify JSON Sink
        assert os.path.exists(json_path)
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert len(data) == 1
        entry = data[0]
        assert entry["searches_7d"] == 2500
        assert entry["views_7d"] == 80
        assert entry["total_impressions"] == 4500
        assert entry["pacing_status"] in ["AHEAD", "ON_TRACK", "DEFICIT"]

        # 2. Verify SQLite Sink
        conn = sqlite3.connect(db_path)
        row = conn.execute("SELECT total_impressions, pacing_status FROM profile_performance").fetchone()
        conn.close()
        assert row is not None
        assert row[0] == 4500
        assert row[1] in ["AHEAD", "ON_TRACK", "DEFICIT"]

        # 3. Verify Excel Sink
        import openpyxl
        wb = openpyxl.load_workbook(excel_path)
        assert "Recruiter_Performance_Log" in wb.sheetnames
        ws = wb["Recruiter_Performance_Log"]
        assert ws.max_row >= 2  # Header + at least 1 record


# ==============================================================================
# FEATURE 8: MLOPS PERSONA KEYWORD & TOKEN ALIGNMENT & FACT MATRIX FIDELITY
# ==============================================================================

class TestFeature8MLOpsPersonaAlignment:
    """Validates MLOps keyword clouds, diff reporting, and strict Fact Matrix adherence."""

    def test_target_mlops_keywords_coverage(self):
        """Verify presence of all mandatory MLOps production infrastructure keywords."""
        mandatory = [
            "Kubernetes", "Docker", "Helm", "CI/CD", "GitHub Actions", "Terraform",
            "Prometheus", "Grafana", "Triton Inference Server", "vLLM", "MLflow",
            "Kafka", "Python", "Linux", "FastAPI", "EKS", "AWS", "Redis", "StatefulSets"
        ]
        kw_lower = [k.lower() for k in TARGET_MLOPS_KEYWORDS]
        for kw in mandatory:
            assert kw.lower() in kw_lower, f"Missing critical MLOps keyword: {kw}"

    def test_target_de_keywords_backwards_compatibility(self):
        """Verify TARGET_DE_KEYWORDS is preserved for legacy tests."""
        assert len(TARGET_DE_KEYWORDS) >= 15
        assert "Azure Databricks" in TARGET_DE_KEYWORDS
        assert "PySpark" in TARGET_DE_KEYWORDS
        assert "Delta Lake" in TARGET_DE_KEYWORDS

    def test_generate_keyword_diff_report_personas(self):
        """Verify diff report distinguishes MLOps vs DE keywords."""
        # Candidate skills matching MLOps
        current_skills = ["Kubernetes", "Docker", "Terraform", "Python", "Prometheus"]
        report_mlops = generate_keyword_diff_report(current_skills, persona="mlops")
        assert report_mlops["persona"] == "mlops"
        assert "MLflow" in report_mlops["missing_keywords"]
        assert "Kubernetes" in report_mlops["matched_keywords"]

        # DE report
        report_de = generate_keyword_diff_report(current_skills, persona="de")
        assert report_de["persona"] == "de"
        assert "Azure Databricks" in report_de["missing_keywords"]

    def test_fact_matrix_profile_ground_truth(self):
        """Verify strict fidelity to 01_FACT_MATRIX.md across blueprint and outreach facts."""
        assert CANDIDATE_FACTS["name"] == "Lavkush Kumar"
        assert CANDIDATE_FACTS["total_yoe"] == "2.5 YOE"
        assert CANDIDATE_FACTS["notice_period"] == "15 Days or less"
        assert CANDIDATE_FACTS["current_role"] == "DevOps Engineer"
        assert CANDIDATE_FACTS["current_company"] == "CGI India"

        # Check blueprint employment history
        emp = LINKEDIN_100K_MLOPS_BLUEPRINT["employment_history"]
        assert len(emp) == 4
        assert emp[0]["company"] == "CGI India"
        assert emp[0]["title"] == "DevOps Engineer"
        assert emp[1]["company"] == "Himachal Futuristic Communications (HFCL)"
        assert emp[1]["title"] == "Engineer 1 - DevOps / Platform Engineering"
        assert emp[2]["company"] == "CGI India"
        assert emp[2]["title"] == "Security Analyst Apprentice"
        assert emp[3]["company"] == "Stipe Solutions"
        assert emp[3]["title"] == "Full Stack Developer Intern"

    def test_blacklist_validator_enforcement_on_mlops_content(self):
        """Ensure BlacklistValidator strictly forbids claims violating reality calibration."""
        # 1. Prohibit Triton at HFCL (only at CGI India or personal projects)
        with pytest.raises(ValueError, match="Blacklisted claim"):
            BlacklistValidator.enforce(
                field="experience",
                val="Engineered Triton Inference Server clusters at HFCL for 50-node clusters"
            )

        # 2. Prohibit inflating YOE >= 3.0
        with pytest.raises(ValueError, match="Blacklisted claim"):
            BlacklistValidator.enforce(
                field="headline",
                val="Senior MLOps Architect with 4+ YOE in Kubernetes and LLMs"
            )

        # 3. Prohibit extending notice > 15 days
        with pytest.raises(ValueError, match="Blacklisted claim"):
            BlacklistValidator.enforce(
                field="notice_period",
                val="30 Days Notice"
            )

    def test_config_json_mlops_persona_structure(self):
        """Verify config.json includes mlops_persona without breaking existing keys."""
        cfg = load_config()
        assert "headline_template" in cfg  # legacy preserved
        assert "mlops_persona" in cfg
        mlops_cfg = cfg["mlops_persona"]
        assert mlops_cfg["target_title"] == "MLOps Engineer"
        assert "Kubernetes" in mlops_cfg["keywords"]
        assert "Docker" in mlops_cfg["keywords"]
        assert len(mlops_cfg["it_skills"]) >= 10


# ==============================================================================
# FEATURE 9: LINKEDIN SEARCH APPEARANCE METRICS EXTRACTION
# ==============================================================================

class TestFeature9LinkedInSearchAppearanceExtraction:
    """Validates offline HTML fixture parsing for LinkedIn search appearances & analytics."""

    SAMPLE_LINKEDIN_ANALYTICS_HTML = """
    <div class="analytics-search-appearances-card">
        <h3 class="t-16 t-bold">Search appearances</h3>
        <p class="analytics-count-text">1,480</p>
        <span>search appearances this week</span>
        <div class="top-searcher-companies">
            <h4>Where your searchers work</h4>
            <ul class="companies-list">
                <li><span class="company-name">Microsoft</span> (12%)</li>
                <li><span class="company-name">Amazon</span> (9%)</li>
                <li><span class="company-name">CGI</span> (7%)</li>
                <li><span class="company-name">Walmart Global Tech</span> (5%)</li>
                <li><span class="company-name">Uber</span> (4%)</li>
            </ul>
        </div>
        <div class="top-searcher-titles">
            <h4>What your searchers do</h4>
            <ul class="titles-list">
                <li><span class="title-name">MLOps Engineer</span> (18%)</li>
                <li><span class="title-name">DevOps Engineer</span> (15%)</li>
                <li><span class="title-name">Platform Engineer</span> (11%)</li>
                <li><span class="title-name">Cloud Architect</span> (8%)</li>
            </ul>
        </div>
    </div>
    """

    def test_extract_search_appearances_from_raw_html(self):
        """Verify parsing offline HTML string returns accurate search appearance telemetry."""
        result = extract_linkedin_search_appearances(self.SAMPLE_LINKEDIN_ANALYTICS_HTML)
        assert result["search_appearances"] == 1480
        assert "Microsoft" in result["top_companies"]
        assert "Amazon" in result["top_companies"]
        assert "CGI" in result["top_companies"]
        assert "MLOps Engineer" in result["top_titles"]
        assert "DevOps Engineer" in result["top_titles"]
        assert result["extraction_timestamp"] != ""

    def test_extract_search_appearances_empty_or_malformed_html(self):
        """Verify graceful fallback on empty or malformed HTML."""
        empty_res = extract_linkedin_search_appearances("<html><body>No analytics here</body></html>")
        assert empty_res["search_appearances"] == 0
        assert empty_res["top_companies"] == []
        assert empty_res["top_titles"] == []

    def test_linkedin_analytics_collector_integration(self):
        """Verify LinkedInAnalyticsCollector collects data and updates unified speedometer."""
        collector = LinkedInAnalyticsCollector()
        telemetry = collector.parse_offline_html(self.SAMPLE_LINKEDIN_ANALYTICS_HTML)
        assert telemetry["search_appearances"] == 1480
        assert collector.last_telemetry["search_appearances"] == 1480

        speedo = Unified100KSpeedometer(target_total=100000, target_days=30)
        collector.update_speedometer(speedo, impressions=5000)
        pacing = speedo.compute_current_pacing(elapsed_days=5)

        assert pacing.linkedin_searches == 1480
        assert pacing.linkedin_impressions == 5000
        assert pacing.total_impressions == 6480


# ==============================================================================
# FEATURE 10: RECENCY BUMPING & OPTIMIZATION ROUTINES (SEO SATURATION SCORE)
# ==============================================================================

class TestFeature10RecencyBumpingAndOptimization:
    """Validates 2h cooldown, micro-toggling, 11-facet sync, and SEO saturation score."""

    def test_cooldown_throttle_enforcement(self):
        """Verify 2h (7200s) cooldown strictly throttles premature bumps."""
        now = datetime.now()
        # Case 1: First bump (None) -> allowed
        assert check_cooldown(None) is True

        # Case 2: Bumped 10 minutes ago -> denied
        recent = now - timedelta(minutes=10)
        assert check_cooldown(recent.isoformat()) is False

        # Case 3: Bumped 130 minutes ago (>7200s) -> allowed
        expired = now - timedelta(minutes=130)
        assert check_cooldown(expired.isoformat()) is True

    def test_micro_bump_headline_toggle(self):
        """Verify micro_bump_headline alternates trailing period cleanly."""
        base = "MLOps Engineer | 2.5 YOE | Kubernetes · Docker · Triton | 15 Days Notice"
        # First toggle: adds period
        bumped1 = micro_bump_headline(base)
        assert bumped1.endswith(".")
        assert bumped1.rstrip(".") == base

        # Second toggle: removes period
        bumped2 = micro_bump_headline(bumped1)
        assert not bumped2.endswith(".")
        assert bumped2 == base

    def test_sync_11_facets_contract(self):
        """Verify sync_11_facets checks all 11 Resdex facets."""
        profile_data = {
            "headline": MLOPS_HEADLINE_TEMPLATE,
            "summary": "MLOps Engineer with 2.5 YOE...",
            "key_skills": MLOPS_KEY_SKILLS,
            "it_skills": MLOPS_IT_SKILLS,
            "employment": LINKEDIN_100K_MLOPS_BLUEPRINT["employment_history"],
            "education": [{"degree": "B.Tech CSE", "institution": "MDU"}],
            "preferred_locations": ["Bengaluru", "Hyderabad", "Pune"],
            "notice_period": "15 Days or less",
            "current_ctc": 12,
            "target_role": "MLOps Engineer",
            "projects": [{"name": "AegisAgent", "tech": "Kubernetes, Triton"}]
        }
        res = sync_11_facets(profile_data)
        assert res["all_facets_synced"] is True
        assert len(res["synced_facets"]) == 11
        assert "key_skills" in res["synced_facets"]
        assert "it_skills" in res["synced_facets"]

    def test_calculate_seo_saturation_score(self):
        """Verify SEO saturation score generates a 0-100 scale score."""
        # Saturated MLOps profile
        text = (
            "MLOps Engineer Kubernetes Docker Helm CI/CD GitHub Actions Terraform "
            "Prometheus Grafana Triton Inference Server vLLM MLflow Kafka Python Linux "
            "FastAPI AWS EKS Redis PyTorch StatefulSets"
        )
        score = calculate_seo_saturation_score(text, persona="mlops")
        assert 70.0 <= score <= 100.0

        # Sparse text
        sparse_score = calculate_seo_saturation_score("Just some random text", persona="mlops")
        assert sparse_score < 30.0

    def test_linkedin_auditor_mlops_and_de_scores(self):
        """Verify LinkedInProfileAuditor calculates seo_score and saturation."""
        auditor = LinkedInProfileAuditor()

        # Audit MLOps blueprint
        mlops_audit = auditor.audit(LINKEDIN_100K_MLOPS_BLUEPRINT, persona="mlops")
        assert mlops_audit["seo_saturation_score"] >= 80.0
        assert mlops_audit["score"] >= 80.0
        assert mlops_audit["persona"] == "mlops"

        # Audit DE blueprint with DE persona
        de_audit = auditor.audit(LINKEDIN_100K_BLUEPRINT, persona="de")
        assert de_audit["score"] == 100.0
        assert de_audit["persona"] == "de"


# ==============================================================================
# FEATURE 11: RECRUITER OUTREACH AUTOMATION & RATE LIMITS
# ==============================================================================

class TestFeature11RecruiterOutreachAutomation:
    """Validates daily outreach rate limits, strictly <=300 character notes, 30-80ms typing delay."""

    def test_daily_outreach_rate_limit(self, tmp_path):
        """Verify max 8 connection requests per day (default 5) with checkpoint circuit breaker."""
        json_path = str(tmp_path / "outreach.json")
        crm = RecruiterOutreachCRM(json_path=json_path)

        # Log 5 invitations
        for i in range(5):
            crm.log_outreach(
                recruiter_name=f"Recruiter_{i}",
                company="TechCorp",
                target_role="MLOps Engineer",
                platform="LinkedIn",
                message_type="Connection Request Note",
                status="CONTACTED"
            )

        assert crm.get_daily_outreach_count() == 5
        # Can still send if limit is 8
        assert crm.can_send_outreach(daily_limit=8) is True

        # Log up to 8
        for i in range(5, 8):
            crm.log_outreach(
                recruiter_name=f"Recruiter_{i}",
                company="TechCorp",
                target_role="MLOps Engineer",
                platform="LinkedIn",
                message_type="Connection Request Note",
                status="CONTACTED"
            )

        assert crm.get_daily_outreach_count() == 8
        # Circuit breaker trips at limit 8
        assert crm.can_send_outreach(daily_limit=8) is False

    def test_connection_note_character_limit_strictly_300(self):
        """Verify personalized connection notes never exceed 300 characters and keep intact sign-off."""
        names = ["Siddharth", "Aishwarya", "Christopher-Alexander", "Pooja", "Raghavendra"]
        companies = ["Microsoft India", "Amazon Web Services", "Walmart Global Tech", "Goldman Sachs"]

        for name in names:
            for comp in companies:
                note = generate_mlops_connection_note(name, comp)
                assert len(note) <= 300, f"Note exceeds 300 chars ({len(note)}): {note}"
                assert "- Lavkush" in note, f"Sign-off missing from note: {note}"
                assert "2.5 YOE" in note or "Kubernetes" in note or "MLOps" in note

    def test_mlops_inmail_template_grounding(self):
        """Verify MLOps InMail template is grounded in candidate's authentic experience."""
        inmail = generate_mlops_inmail("Ankit", "Microsoft")
        subject = inmail["subject"]
        body = inmail["body"]

        assert "MLOps" in subject or "DevOps" in subject
        assert "15-day notice" in subject.lower() or "15-day" in body.lower()
        assert "Lavkush Kumar" in body
        assert "50-node" in body or "Kubernetes" in body or "Ansible" in body
        assert "12 LPA" not in body  # don't broadcast salary unnecessarily in initial pitch
        assert "15 Days" in body or "15-day" in body

    def test_linkedin_outreach_typing_delay_range(self):
        """Verify keystroke simulation typing delay is within the 30-80ms window."""
        sender = LinkedInOutreachSender(headless=True)
        # Check typing delay generation
        delays = [sender._get_keystroke_delay() for _ in range(50)]
        for d in delays:
            assert 30 <= d <= 80, f"Typing delay {d}ms out of 30-80ms bounds"

    def test_goal_5calls_engine_mlops_batch(self, tmp_path):
        """Verify Goal5CallsEngine integrates with MLOps persona in block execution."""
        json_path = str(tmp_path / "goal_outreach.json")
        engine = Goal5CallsEngine(json_path=json_path, persona="mlops")
        assert engine.persona == "mlops"

        # Execute Block 2 (Afternoon Outreach)
        res = engine.execute_block(2)
        assert res["block"] == 2
        actions = res["actions_executed"]
        assert len(actions) > 0
        outreach_action = actions[0]
        assert outreach_action["count"] >= 5
