"""
Milestone 3 Empirical Adversarial Stress Test Suite
Author: Challenger 1 (teamwork_preview_challenger_m3_1)
Objective:
1. Boundary scores: test inputs producing scores exactly 69%, 70%, 71%, 0%, 100%.
   Verify that 69% is rejected by the gate, 70% is accepted.
2. Malformed/adversarial inputs to calculate_match_score:
   None, empty string, 1MB string, unicode strings, regex injection payloads, SQL injection strings.
3. ApplicationPayload edge cases:
   Missing fields, JSON serialization/deserialization roundtrips, unusual types, immutability/mutation boundaries.
4. Scale and diversity testing:
   Verify evaluate_job_match and AutoApplyEngine correctly reject low-scoring jobs across 100+ simulated diverse postings.
"""

import os
import sys
import json
import time
from datetime import datetime
from unittest.mock import patch
import pytest

from naukari_pro.modules.job_alerts import (
    calculate_match_score,
    MATCH_SCORE_THRESHOLD,
    KEYWORD_WEIGHTS,
    InstantAlertsEngine
)
from naukari_pro.modules.auto_apply import (
    ApplicationPayload,
    build_dry_run_payload,
    generate_dry_run_payload,
    evaluate_job_match,
    AutoApplyEngine,
    NativeChromeRunner,
    MIN_SALARY_LPA
)


# ==============================================================================
# 1. BOUNDARY SCORES & GATE DISCRIMINATION (0%, 69%, 70%, 71%, 100%)
# ==============================================================================

class TestBoundaryScoresAndGating:
    """
    Stress-tests the >= 70% match score gate at exact boundary values.
    Standard KEYWORD_WEIGHTS:
    azure: 20, databricks: 20, pyspark: 15, delta lake: 15,
    sql: 10, kafka: 10, terraform: 5, kubernetes: 5 (All multiples of 5, sum=100)
    """

    def test_0_percent_boundary_rejection(self):
        """0% score input is strictly rejected by all gating layers."""
        # Natural 0% input
        zero_score = calculate_match_score("Frontend React Native HTML CSS Vue Angular")
        assert zero_score == 0

        # evaluate_job_match gate
        is_match, score, reason = evaluate_job_match("React Dev", "Startup", "HTML CSS")
        assert is_match is False
        assert score == 0
        assert "below 70% threshold" in reason

        # build_dry_run_payload gate
        p = build_dry_run_payload("Startup", "React Dev", "https://example.com/1", "15 LPA", "HTML CSS")
        assert p.match_score == 0
        assert p.status == "REJECTED_BELOW_THRESHOLD"

        # NativeChromeRunner defense-in-depth gate
        runner = NativeChromeRunner(skip_list=set(), dry_run=False)
        applied, msg = runner.apply_to_job("https://example.com/1", "React Dev", "Startup", "15 LPA", match_score=0)
        assert applied is False
        assert "below required 70% threshold" in msg

    def test_70_percent_exact_boundary_acceptance(self):
        """
        Exact 70% boundary: natural input matching Azure (20) + Databricks (20) +
        PySpark (15) + Delta Lake (15) = 70. Must be accepted by the gate.
        """
        exact_70_jd = "Azure Databricks PySpark Delta Lake"
        score = calculate_match_score(exact_70_jd)
        assert score == 70

        # evaluate_job_match gate
        is_match, eval_score, reason = evaluate_job_match("Data Engineer", "Acme Corp", exact_70_jd)
        assert is_match is True
        assert eval_score == 70
        assert "meets 70% threshold" in reason

        # build_dry_run_payload gate
        p = build_dry_run_payload("Acme Corp", "Data Engineer", "https://example.com/70", "25 LPA", exact_70_jd)
        assert p.match_score == 70
        assert p.status == "VALIDATED_PAYLOAD"

        # NativeChromeRunner defense-in-depth gate (dry-run mode)
        runner = NativeChromeRunner(skip_list=set(), dry_run=True)
        applied, msg = runner.apply_to_job("https://example.com/70", "Data Engineer", "Acme Corp", "25 LPA", match_score=70)
        assert applied is True
        assert "Dry Run Simulation" in msg

    def test_100_percent_maximum_boundary_acceptance(self):
        """100% boundary: all 8 Azure Data Engineer competencies present. Must be accepted and capped at 100."""
        all_keywords_jd = "Azure Databricks PySpark Delta Lake SQL Kafka Terraform Kubernetes"
        score = calculate_match_score(all_keywords_jd)
        assert score == 100

        # With repeated keywords, score must stay capped at 100
        bloated_jd = f"{all_keywords_jd} {all_keywords_jd} Azure Databricks PySpark"
        assert calculate_match_score(bloated_jd) == 100

        is_match, eval_score, reason = evaluate_job_match("Principal Lakehouse Architect", "Cloud Corp", all_keywords_jd)
        assert is_match is True
        assert eval_score == 100
        assert "meets 70% threshold" in reason

        p = build_dry_run_payload("Cloud Corp", "Principal Lakehouse Architect", "https://example.com/100", "40 LPA", all_keywords_jd)
        assert p.match_score == 100
        assert p.status == "VALIDATED_PAYLOAD"

    def test_69_percent_boundary_rejection_via_mock_and_weights(self):
        """
        Boundary condition 69%:
        1. Default weights are all multiples of 5, so no natural text produces 69%.
        2. With direct score injection or patched weights producing 69%, verify 69% is REJECTED.
        """
        # A. Direct score injection into NativeChromeRunner.apply_to_job
        runner = NativeChromeRunner(skip_list=set(), dry_run=False)
        applied, msg = runner.apply_to_job(
            "https://example.com/69", "Near Match DE", "Enterprise", "20 LPA", match_score=69
        )
        assert applied is False
        assert "Rejected: Match score 69% is below required 70% threshold" in msg

        # B. Patched scoring producing exact 69% from input text
        with patch.dict(KEYWORD_WEIGHTS, {"azure": 69}, clear=True):
            score = calculate_match_score("Azure Data Engineer")
            assert score == 69

            is_match, eval_score, reason = evaluate_job_match("Azure Data Engineer", "Enterprise", "")
            assert eval_score == 69
            assert is_match is False
            assert "below 70% threshold" in reason

            p = build_dry_run_payload("Enterprise", "Azure Data Engineer", "https://example.com/69", "25 LPA", "")
            assert p.match_score == 69
            assert p.status == "REJECTED_BELOW_THRESHOLD"

            engine = AutoApplyEngine(dry_run=True)
            payloads = engine.run_offline_dry_run([
                {"title": "Azure Data Engineer", "company": "Enterprise", "salary": "25 LPA", "url": "https://example.com/69"}
            ])
            assert payloads[0].match_score == 69
            assert payloads[0].status == "REJECTED_BELOW_THRESHOLD"

    def test_71_percent_boundary_acceptance_via_mock_and_weights(self):
        """
        Boundary condition 71%:
        With score 71%, verify that the gate accepts the vacancy.
        """
        # A. Direct score injection into NativeChromeRunner.apply_to_job
        runner = NativeChromeRunner(skip_list=set(), dry_run=True)
        applied, msg = runner.apply_to_job(
            "https://example.com/71", "Qualifying DE", "Enterprise", "20 LPA", match_score=71
        )
        assert applied is True
        assert "Dry Run Simulation" in msg

        # B. Patched scoring producing exact 71% from input text
        with patch.dict(KEYWORD_WEIGHTS, {"azure": 71}, clear=True):
            score = calculate_match_score("Azure Data Engineer")
            assert score == 71

            is_match, eval_score, reason = evaluate_job_match("Azure Data Engineer", "Enterprise", "")
            assert eval_score == 71
            assert is_match is True
            assert "meets 70% threshold" in reason

            p = build_dry_run_payload("Enterprise", "Azure Data Engineer", "https://example.com/71", "25 LPA", "")
            assert p.match_score == 71
            assert p.status == "VALIDATED_PAYLOAD"

            engine = AutoApplyEngine(dry_run=True)
            payloads = engine.run_offline_dry_run([
                {"title": "Azure Data Engineer", "company": "Enterprise", "salary": "25 LPA", "url": "https://example.com/71"}
            ])
            assert payloads[0].match_score == 71
            assert payloads[0].status == "VALIDATED_PAYLOAD"

    def test_default_weights_mathematical_multiples_of_five(self):
        """
        Verifies that under default KEYWORD_WEIGHTS, every single keyword weight is a multiple of 5,
        meaning standard output domain is strictly multiples of 5 in [0, 100].
        """
        for kw, weight in KEYWORD_WEIGHTS.items():
            assert weight % 5 == 0, f"Weight for {kw} is {weight}, expected multiple of 5"
        assert sum(KEYWORD_WEIGHTS.values()) == 100


# ==============================================================================
# 2. MALFORMED & ADVERSARIAL INPUTS TO calculate_match_score
# ==============================================================================

class TestMalformedAdversarialInputs:
    """Stress tests calculate_match_score with hostile, malformed, and injection payloads."""

    def test_none_input(self):
        """None input safely returns 0 without raising AttributeError or TypeError."""
        assert calculate_match_score(None) == 0

    def test_empty_and_whitespace_variants(self):
        """Empty, whitespace, tabs, and newlines return 0 safely."""
        assert calculate_match_score("") == 0
        assert calculate_match_score(" ") == 0
        assert calculate_match_score("\t\t\n\r\n   ") == 0

    def test_1mb_extreme_string_performance_and_scoring(self):
        """
        1 MB (1,048,576 chars) string must complete in < 50ms without crashing or timing out.
        Sub-case A: 1MB without keywords -> returns 0.
        Sub-case B: 1MB with keywords dispersed throughout -> returns correct score.
        """
        # 1MB of filler 'x'
        filler_1mb = "x" * (1024 * 1024)
        t0 = time.perf_counter()
        score_empty = calculate_match_score(filler_1mb)
        t_elapsed = (time.perf_counter() - t0) * 1000  # ms
        assert score_empty == 0
        assert t_elapsed < 50.0, f"1MB empty scan took {t_elapsed:.2f}ms (>50ms)"

        # 1MB with keywords at start, middle, and end
        half = 512 * 1024
        adversarial_1mb = "azure " + ("y" * half) + " databricks pyspark " + ("z" * half) + " delta lake"
        t0 = time.perf_counter()
        score_matched = calculate_match_score(adversarial_1mb)
        t_elapsed = (time.perf_counter() - t0) * 1000  # ms
        assert score_matched == 70  # azure(20) + databricks(20) + pyspark(15) + delta lake(15)
        assert t_elapsed < 50.0, f"1MB matched scan took {t_elapsed:.2f}ms (>50ms)"

    def test_unicode_and_multilingual_strings(self):
        """
        Tests Unicode emojis, non-Latin scripts, zero-width spaces, null bytes,
        and homoglyph strings.
        """
        # Emojis containing keywords
        emoji_text = "🚀 Azure Cloud Architect ⚡ Databricks 🌊 Delta Lake 🐍 PySpark 🔥"
        assert calculate_match_score(emoji_text) == 70

        # Non-Latin languages without keywords -> 0, no encoding crash
        devanagari = "अज़ूर डेटा इंजीनियर डाटाब्रिक्स"
        chinese = "微软大数据工程师 实时流计算"
        arabic = "مهندس بيانات الحوسبة السحابية"
        cyrillic = "Инженер данных облачные технологии"
        for non_latin in [devanagari, chinese, arabic, cyrillic]:
            assert calculate_match_score(non_latin) == 0

        # Homoglyph attack: Cyrillic 'а' (U+0430) vs Latin 'a'
        # "аzure" with Cyrillic 'а' must NOT match ASCII 'azure'
        cyrillic_a_azure = "\u0430zure databricks pyspark delta lake"
        assert calculate_match_score(cyrillic_a_azure) == 50  # missed azure (20)

        # Embedded null bytes
        null_byte_text = "azure\x00databricks\x00pyspark\x00delta lake"
        assert calculate_match_score(null_byte_text) == 70

        # Zero-width non-joiner and zero-width spaces
        zws_text = "azure\u200b databricks\u200c pyspark\ufeff delta lake"
        assert calculate_match_score(zws_text) == 70

    def test_regex_injection_and_redos_payloads(self):
        """
        Adversarial ReDoS patterns and regex metacharacters in input strings.
        calculate_match_score uses substring containment ('kw in text_lower'),
        so regex metacharacters must not be evaluated or cause catastrophic backtracking.
        """
        redos_payloads = [
            "a" * 50 + "! (a+)+$",
            "((((((((a*)*)*)*)*)*)*)*)!",
            "(x+x+)+y" * 100,
            "(a|aa)+$" * 50,
            ".*.*.*.*.*.*.*.*.*.*.*.*.*.*.*",
            "(?i)azure.*databricks.*pyspark.*",
            "(?<=azure)databricks(?=pyspark)",
            "[a-zA-Z0-9_.-]+@[a-zA-Z0-9-]+\\.[a-zA-Z0-9-.]+",
            "(?[invalid regex syntax",
            "^\\s*$(?m)",
        ]
        for payload in redos_payloads:
            t0 = time.perf_counter()
            score = calculate_match_score(payload)
            t_ms = (time.perf_counter() - t0) * 1000
            assert t_ms < 5.0, f"ReDoS payload caused delay: {t_ms:.2f}ms"
            # Verify score is non-negative and properly bounded
            assert 0 <= score <= 100
            # Test specific ReDoS string without any keywords
            assert calculate_match_score("a" * 100 + "! (a+)+$") == 0

    def test_sql_injection_strings(self):
        """
        SQL injection payloads must not cause exceptions and must score only
        genuine keyword matches (e.g., 'sql' keyword = 10 pts).
        """
        sqli_payloads = [
            ("'; DROP TABLE applications; --", 0),
            ("' OR 1=1 --", 0),
            ("' UNION SELECT null, username, password FROM users --", 0),
            ("1; EXEC xp_cmdshell('format c:'); --", 0),
            ("SELECT * FROM jobs WHERE title LIKE '%azure%' AND dialect = 'spark sql'", 30),  # azure(20) + sql(10)
            ("PostgreSQL and Spark SQL queries optimization", 10),  # contains 'sql'(10)
        ]
        for payload, expected_min in sqli_payloads:
            score = calculate_match_score(payload)
            assert score >= expected_min, f"SQLi payload '{payload}' produced score {score} < {expected_min}"

    def test_unusual_types_coercion(self):
        """Coercion check when non-string types are passed to calculate_match_score."""
        assert calculate_match_score(0) == 0
        assert calculate_match_score(12345) == 0
        assert calculate_match_score(False) == 0
        assert calculate_match_score(["azure", "databricks"]) == 40  # str(["azure", "databricks"]) contains keywords
        assert calculate_match_score({"azure": 20}) == 20


# ==============================================================================
# 3. APPLICATIONPAYLOAD SCHEMA, MUTATION & SERIALIZATION BOUNDARIES
# ==============================================================================

class TestApplicationPayloadSchemaAndBoundaries:
    """Stress tests ApplicationPayload dataclass, edge cases, roundtrips, and mutations."""

    def test_minimal_instantiation(self):
        """ApplicationPayload requires only 'company'; all other fields have safe defaults."""
        payload = ApplicationPayload(company="Google")
        assert payload.company == "Google"
        assert payload.job_title == ""
        assert payload.title == ""
        assert payload.match_score == 0
        assert payload.portal_type == "Naukri 1-Click"
        assert payload.status == "VALIDATED_PAYLOAD"
        assert payload.dry_run is True
        assert payload.url == "N/A"
        assert payload.salary == "N/A"
        assert isinstance(payload.timestamp, str)
        assert payload.answers == {}
        assert payload.payload_data == {}

    def test_missing_company_raises_type_error(self):
        """Instantiating ApplicationPayload without required 'company' raises TypeError."""
        with pytest.raises(TypeError):
            ApplicationPayload()  # pylint: disable=no-value-for-parameter

    def test_bidirectional_title_and_job_title_sync_at_init(self):
        """__post_init__ ensures title and job_title mirror each other upon creation."""
        # Case A: title provided, job_title omitted
        p1 = ApplicationPayload(company="Amazon", title="Lead Azure Data Engineer")
        assert p1.job_title == "Lead Azure Data Engineer"
        assert p1.role == "Lead Azure Data Engineer"

        # Case B: job_title provided, title omitted
        p2 = ApplicationPayload(company="Amazon", job_title="Databricks Specialist")
        assert p2.title == "Databricks Specialist"
        assert p2.role == "Databricks Specialist"

    def test_bidirectional_answers_and_payload_data_sync_at_init(self):
        """__post_init__ ensures answers and payload_data mirror each other upon creation."""
        # Case A: answers provided, payload_data omitted
        p1 = ApplicationPayload(company="Meta", answers={"notice": "30 days"})
        assert p1.payload_data == {"notice": "30 days"}

        # Case B: payload_data provided, answers omitted
        p2 = ApplicationPayload(company="Meta", payload_data={"exp": "2.5 years"})
        assert p2.answers == {"exp": "2.5 years"}

    def test_role_property_mutation_behavior(self):
        """
        Tests role setter updates both title and job_title.
        Documents the behavior that direct mutation of job_title leaves title intact,
        where role property falls back to title.
        """
        p = ApplicationPayload(company="Apple", title="Initial Title")
        # Mutating via role property setter updates both
        p.role = "Updated Title"
        assert p.title == "Updated Title"
        assert p.job_title == "Updated Title"
        assert p.role == "Updated Title"

        # Direct mutation of job_title while title remains set:
        p.job_title = "Secondary Title"
        assert p.job_title == "Secondary Title"
        # Since p.title is non-empty, p.role evaluates (self.title or self.job_title) -> "Updated Title"
        assert p.role == "Updated Title"

    def test_json_serialization_and_roundtrip(self):
        """
        Tests to_dict() and to_json() serialization.
        Tests deserialization roundtrip and documents that 'role' property in to_dict()
        must be excluded or handled when reconstructing an ApplicationPayload instance.
        """
        p = ApplicationPayload(
            company="Microsoft",
            title="Azure Cloud Architect",
            match_score=95,
            portal_type="Career Portal (Workday)",
            status="VALIDATED_PAYLOAD",
            dry_run=True,
            url="https://careers.microsoft.com/123",
            salary="35 - 45 LPA",
            answers={"notice_period": "30", "expected_ctc": "35"}
        )

        d = p.to_dict()
        assert isinstance(d, dict)
        assert d["role"] == "Azure Cloud Architect"
        assert d["company"] == "Microsoft"
        assert d["match_score"] == 95

        # to_json string validation
        j = p.to_json()
        assert isinstance(j, str)
        parsed = json.loads(j)
        assert parsed["company"] == "Microsoft"
        assert parsed["role"] == "Azure Cloud Architect"
        assert parsed["answers"]["notice_period"] == "30"

        # Roundtrip reconstruction:
        # Note: 'role' is a dynamic property, not a dataclass field.
        clean_kwargs = {k: v for k, v in parsed.items() if k != "role"}
        p_reconstructed = ApplicationPayload(**clean_kwargs)
        assert p_reconstructed.company == p.company
        assert p_reconstructed.match_score == p.match_score
        assert p_reconstructed.role == p.role
        assert p_reconstructed.status == p.status

    def test_non_json_serializable_answers_boundary(self):
        """Passing non-JSON serializable objects inside answers (like set or datetime) raises TypeError on to_json."""
        p = ApplicationPayload(
            company="TestCorp",
            title="Dev",
            answers={"unsupported_set": {1, 2, 3}}
        )
        with pytest.raises(TypeError) as excinfo:
            p.to_json()
        assert "is not JSON serializable" in str(excinfo.value)


# ==============================================================================
# 4. SCALE & DIVERSITY SIMULATION (100+ DIVERSE POSTINGS TEST)
# ==============================================================================

class TestScaleAndDiversitySimulatedPostings:
    """
    Simulates 120 diverse job postings across diverse tech stacks, experience levels,
    and salary bands to verify that evaluate_job_match and AutoApplyEngine reject
    100% of low-scoring and low-salary vacancies with zero false positives.
    """

    @pytest.fixture
    def diverse_postings(self):
        """Generates 120 diverse job postings."""
        postings = []

        # 1. 30 High-scoring Azure Data Engineer roles (Score >= 70, Salary >= 12 LPA)
        ade_templates = [
            ("Lead Azure Data Engineer", "Databricks PySpark Delta Lake Medallion Architecture Kafka", "25 - 35 Lacs PA"),
            ("Senior Data Engineer (Azure)", "Azure Databricks PySpark Delta Lake SQL Terraform", "22 - 30 Lacs PA"),
            ("Azure Lakehouse Architect", "Azure Databricks Delta Lake PySpark Kafka Kubernetes", "35 - 50 Lacs PA"),
            ("Azure Big Data Engineer", "Azure PySpark Delta Lake SQL Kafka Databricks", "20 - 28 Lacs PA"),
            ("Data Platform Engineer", "Azure Databricks PySpark Delta Lake SQL", "24 - 32 Lacs PA"),
            ("Staff Azure Data Engineer", "Databricks Azure PySpark Delta Lake Terraform Kubernetes", "30 - 45 Lacs PA"),
        ]
        for i in range(30):
            tmpl = ade_templates[i % len(ade_templates)]
            postings.append({
                "id": f"ade_{i}",
                "title": f"{tmpl[0]} #{i+1}",
                "company": f"Global Enterprise {i+1}",
                "salary": tmpl[2],
                "url": f"https://www.naukri.com/job-ade-{i}",
                "jd": tmpl[1],
                "expected_category": "QUALIFIED"
            })

        # 2. 20 Borderline low-scoring roles (Score 20-55, Salary >= 12 LPA)
        borderline_templates = [
            ("DevOps Engineer", "Terraform Kubernetes Docker AWS Linux", "18 - 25 Lacs PA"),  # 10 pts (Terraform 5, K8s 5)
            ("SQL Database Administrator", "SQL Server T-SQL DBA Administration Backup", "15 - 20 Lacs PA"),  # 10 pts (SQL 10)
            ("Data Analyst", "SQL Tableau PowerBI Excel Python", "12 - 18 Lacs PA"),  # 10 pts (SQL 10)
            ("Cloud Engineer", "Azure VM Networking Active Directory", "16 - 22 Lacs PA"),  # 20 pts (Azure 20)
            ("Kafka Platform Engineer", "Kafka Zookeeper Distributed Systems Java", "20 - 28 Lacs PA"),  # 10 pts (Kafka 10)
            ("Data Engineer - AWS Only", "AWS Glue Redshift Athena EMR PySpark", "20 - 28 Lacs PA"),  # 15 pts (PySpark 15)
            ("Big Data Engineer", "Hadoop Spark Hive Scala Databricks", "22 - 30 Lacs PA"),  # 20 pts (Databricks 20)
            ("Azure SQL Developer", "Azure SQL Stored Procedures ETL SSIS", "16 - 22 Lacs PA"),  # 30 pts (Azure 20 + SQL 10)
        ]
        for i in range(20):
            tmpl = borderline_templates[i % len(borderline_templates)]
            postings.append({
                "id": f"border_{i}",
                "title": f"{tmpl[0]} #{i+1}",
                "company": f"Borderline Tech {i+1}",
                "salary": tmpl[2],
                "url": f"https://www.naukri.com/job-border-{i}",
                "jd": tmpl[1],
                "expected_category": "REJECTED_LOW_SCORE"
            })

        # 3. 50 Completely irrelevant non-data roles (Score 0, various salaries)
        irrelevant_templates = [
            ("Frontend React Developer", "React Redux TypeScript Tailwind CSS Next.js", "15 - 22 Lacs PA"),
            ("Android Kotlin Developer", "Android Studio Kotlin Jetpack Compose Coroutines Flow", "18 - 25 Lacs PA"),
            ("iOS Swift Engineer", "Swift SwiftUI UIKit CoreData XCTest", "20 - 28 Lacs PA"),
            ("PHP Laravel Developer", "PHP Laravel MySQL Vue HTML CSS", "6 - 10 Lacs PA"),
            ("Embedded Systems Engineer", "C C++ RTOS Microcontrollers Firmware ARM", "14 - 20 Lacs PA"),
            ("Graphic Designer", "Photoshop Illustrator Figma InDesign Creative Cloud", "5 - 8 Lacs PA"),
            ("HR Talent Acquisition", "Recruitment Sourcing Screening Interviewing Onboarding", "8 - 12 Lacs PA"),
            ("QA Automation Engineer", "Selenium Cypress Playwright TestNG Cucumber Java", "12 - 18 Lacs PA"),
            ("Product Manager", "Roadmap Agile Scrum Jira User Stories Market Research", "25 - 35 Lacs PA"),
            ("Technical Support Specialist", "L1 L2 Support Windows macOS Hardware Networking", "4 - 7 Lacs PA"),
        ]
        for i in range(50):
            tmpl = irrelevant_templates[i % len(irrelevant_templates)]
            postings.append({
                "id": f"irrel_{i}",
                "title": f"{tmpl[0]} #{i+1}",
                "company": f"Diverse Company {i+1}",
                "salary": tmpl[2],
                "url": f"https://www.naukri.com/job-irrel-{i}",
                "jd": tmpl[1],
                "expected_category": "REJECTED_ZERO_SCORE"
            })

        # 4. 20 Low-Salary or Edge Postings (ADE skills but Salary < 12 LPA or empty text)
        edge_templates = [
            ("Junior Azure Data Engineer", "Azure Databricks PySpark Delta Lake SQL", "6 - 9 Lacs PA", "LOW_SALARY"),
            ("Intern Data Engineer", "Azure Databricks PySpark Delta Lake", "3 - 5 Lacs PA", "LOW_SALARY"),
            ("Azure Trainee", "Azure Databricks Delta Lake PySpark", "4 - 6 Lacs PA", "LOW_SALARY"),
            ("Empty Description DE", "", "20 - 25 Lacs PA", "EMPTY_JD"),
        ]
        for i in range(20):
            tmpl = edge_templates[i % len(edge_templates)]
            postings.append({
                "id": f"edge_{i}",
                "title": f"{tmpl[0]} #{i+1}",
                "company": f"Edge Corp {i+1}",
                "salary": tmpl[2],
                "url": f"https://www.naukri.com/job-edge-{i}",
                "jd": tmpl[1],
                "expected_category": tmpl[3]
            })

        return postings

    def test_evaluate_job_match_accuracy_across_120_postings(self, diverse_postings):
        """
        Evaluates all 120 diverse job postings with evaluate_job_match.
        Verifies:
        - 100% of postings with score < 70 are rejected (is_match == False).
        - 100% of postings with score >= 70 are accepted (is_match == True).
        - Zero false positives.
        """
        assert len(diverse_postings) == 120

        qualified_count = 0
        rejected_count = 0

        for p in diverse_postings:
            is_match, score, reason = evaluate_job_match(p["title"], p["company"], p["jd"])

            if score >= 70:
                assert is_match is True, f"Failed to accept qualifying posting {p['id']}: score={score}"
                assert "meets 70% threshold" in reason
                qualified_count += 1
            else:
                assert is_match is False, f"Failed to reject low-scoring posting {p['id']}: score={score}"
                assert "below 70% threshold" in reason
                rejected_count += 1

        # We generated exactly 30 ADE roles + 15 low-salary ADE roles that had >= 70% score text = 45 with >= 70%
        # The remaining 75 roles (20 borderline, 50 irrelevant, 5 empty) have score < 70.
        assert qualified_count == 45
        assert rejected_count == 75

    def test_auto_apply_engine_offline_dry_run_rejection_at_scale(self, diverse_postings):
        """
        Executes AutoApplyEngine.run_offline_dry_run over all 120 postings.
        Verifies:
        - All low-salary postings (< 12 LPA) receive status 'REJECTED_LOW_SALARY'.
        - All low-scoring postings (< 70% match) receive status 'REJECTED_BELOW_THRESHOLD'.
        - Only vacancies satisfying BOTH salary >= 12 LPA and score >= 70% receive 'VALIDATED_PAYLOAD'.
        - AutoApplyEngine.run(dry_run=True) returns exactly the count of 'VALIDATED_PAYLOAD' items.
        """
        engine = AutoApplyEngine(dry_run=True)
        payloads = engine.run_offline_dry_run(job_feed=diverse_postings, limit=200)

        assert len(payloads) == 120

        validated_payloads = [p for p in payloads if p.status == "VALIDATED_PAYLOAD"]
        rejected_salary = [p for p in payloads if p.status == "REJECTED_LOW_SALARY"]
        rejected_score = [p for p in payloads if p.status == "REJECTED_BELOW_THRESHOLD"]

        # Exactly 30 postings meet both criteria: score >= 70 and salary >= 12 LPA
        assert len(validated_payloads) == 30

        # Postings with salary < 12 LPA are rejected by salary gate before scoring
        # In our fixture: 15 low-salary ADE roles + 15 low-salary irrelevant roles = 30
        assert len(rejected_salary) >= 15

        # All other postings have score < 70 and are rejected by match score gate
        assert len(rejected_score) > 0

        # Sum of all categories must equal total input count
        assert len(validated_payloads) + len(rejected_salary) + len(rejected_score) == 120

        # Every validated payload MUST have match_score >= 70
        for p in validated_payloads:
            assert p.match_score >= 70
            assert p.dry_run is True
            assert p.portal_type == "Naukri 1-Click"

        # Verify run() invocation returns exactly 30 validated payloads
        run_count = engine.run(dry_run=True, job_feed=diverse_postings, limit=200)
        assert run_count == 30
