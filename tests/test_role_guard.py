"""
Unit tests for Role Guard Module (naukari_pro/modules/role_guard.py).
Ensures non-data roles are NEVER applied to under any mode or condition.
"""

import pytest
from naukari_pro.modules.role_guard import is_strictly_data_or_cloud_role


class TestRoleGuard:
    @pytest.mark.parametrize("title, company", [
        ("German Language Processor / Associate HRO & German Mandatory", "Gratitude India"),
        ("Telecalling Executive", "Clickerscabin Studios Llp"),
        ("Mechanical Design Engineer BSc", "Soul Ai"),
        ("Electrical Design Engineer MSc", "Soul Ai"),
        ("Civil Engineer - Site Supervision", "L&T Construction"),
        ("SAP MDG Consultant", "Infosys"),
        ("Hiring For BCA, BSC, MCS, MCA, Be, B.tech, ME, and M.tech Freshers", "Nextgen Education Foundation"),
        ("Clinical Data Specialist", "IQVIA"),
        ("Coding and Robotics Educator", "K12 Techno Services"),
        ("Front End Developer", "Rakesh Infinivis"),
        ("Mis Analyst", "Talent Corner Hr Services"),
        ("Python Trainer & Developer ( Night Shift and Work From Home)", "Wonksknow Technologies"),
        ("Walk-in || Procurement Associate", "Conduent"),
        ("Customer Success Manager, APAC", "Linear"),
        ("Solution Engineer (Pre-Sales) - All Levels", "Salesforce"),
        ("Cashier", "Walmart Supercenter"),
        ("Bartender", "The Rusty Anchor Bar"),
        ("Dental Hygienist", "Apex Smile Clinic"),
        ("PHP 5.4 Webmaster", "Legacy Hosting LLC"),
        ("Marketing Intern (Totally Unrelated)", "Random Employer A"),
        ("Junior Receptionist", "Generic Corp"),
        ("Talent Acquisition Executive", "HR Corp"),
        ("Chartered Accountant", "Audit Firm"),
        ("Drilling Engineer MSc (Freelancer)", "Soul Ai"),
        ("Biology PhD Expert", "Soul Ai"),
        ("Product Manager II", "Linear"),
        ("Project Leader", "Confidential Employer"),
        ("Data Analyst", "Ecolab"),
        ("Business Analyst", "Fintech Corp"),
        ("2D CAD & Fabrication Drafter", "Glentec Engineering"),
        ("Manual QA Tester", "TestCo"),
        ("Operations Manager", "Delivery Corp"),
        ("Scrum Master", "Agile Services"),
        ("Guidewire Claim Developer 2-15 Yrs For Pan India", "Confidential Employer"),
        ("Dot Net Developer - Bangalore", "Veetechnologies"),
        ("Fullstack Developer", "Deloitte Shared Services India"),
        ("Java Developer", "Generic IT Services"),
    ])
    def test_non_data_roles_strictly_rejected(self, title, company):
        ok, reason = is_strictly_data_or_cloud_role(title, "", company=company)
        assert not ok, f"Expected '{title}' to be rejected, but got passed with reason: {reason}"
        assert "Rejected" in reason

    def test_forbidden_company_rejected_even_with_target_title(self):
        ok, reason = is_strictly_data_or_cloud_role("Azure Data Engineer", company="Soul Ai")
        assert not ok
        assert "Excluded non-target / gig annotator employer" in reason

    @pytest.mark.parametrize("title", [
        "Azure Data Engineer",
        "Lead Azure Data Engineer",
        "Data Engineer( Snowflake & Azure)",
        "Senior Azure Data Engineer",
        "Azure Databricks PySpark Engineer",
        "Data Platform Engineer",
        "Big Data Engineer",
        "ETL Developer - Spark / Azure",
        "Data Lakehouse Architect",
        "DevOps Engineer",
        "MLOps Engineer",
        "AI Infrastructure Engineer",
        "Site Reliability Engineer (Data Platform)",
        "Cloud Data Engineer",
    ])
    def test_target_roles_accepted(self, title):
        ok, reason = is_strictly_data_or_cloud_role(title, "")
        assert ok, f"Expected '{title}' to be accepted, but got: {reason}"

    def test_general_tech_title_with_data_jd_accepted(self):
        title = "Software Engineer - Backend"
        jd = "Building high-throughput data pipelines using Azure Databricks, PySpark, and Delta Lake."
        ok, reason = is_strictly_data_or_cloud_role(title, jd, score=70.0)
        assert ok, f"Expected tech role with data competencies to pass, got: {reason}"

    def test_general_tech_title_without_data_jd_rejected(self):
        title = "Software Engineer"
        jd = "Building React UI components with Tailwind CSS and Redux."
        ok, reason = is_strictly_data_or_cloud_role(title, jd, score=0.0)
        assert not ok, f"Expected generic non-data tech role to be rejected, got: {reason}"

    def test_empty_or_none_title_rejected(self):
        assert not is_strictly_data_or_cloud_role("")[0]
        assert not is_strictly_data_or_cloud_role(None)[0]
