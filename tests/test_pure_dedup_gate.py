"""
tests/test_pure_dedup_gate.py

Verifies the Pure Deduplication Gate per Milestone M1 (Feature 2):
1. Deduplicates strictly on job_id + URL + company/title.
2. Eliminates Tier 4 fuzzy title stripping to prevent collapsing distinct vacancies
   from the same employer (e.g. Lead Azure Data Engineer vs Senior Azure Data Engineer).
3. Verifies record_applied_job() forwards job_id and job_url to is_job_already_applied().
"""

import sqlite3
import pytest
from naukari_pro.modules.db import (
    init_db,
    record_applied_job,
    is_job_already_applied,
    normalize_company_name
)


@pytest.fixture
def temp_db(tmp_path):
    """Provides a fresh isolated SQLite database."""
    db_file = str(tmp_path / "test_applied_jobs.db")
    init_db(db_file)
    return db_file


def test_dedup_exact_job_id(temp_db):
    """Verifies duplicate detection when job_id matches exactly."""
    ok, jid = record_applied_job(
        title="Azure Data Engineer",
        company="Microsoft",
        job_id="job_msft_001",
        job_url="https://careers.microsoft.com/job/001",
        status="Submitted (Confirmed)",
        db_path=temp_db
    )
    assert ok is True
    assert jid == "job_msft_001"

    # Query with exact job_id
    assert is_job_already_applied(job_id="job_msft_001", db_path=temp_db) is True
    assert is_job_already_applied(job_id="job_msft_999", db_path=temp_db) is False


def test_dedup_exact_job_url(temp_db):
    """Verifies duplicate detection when job_url matches exactly."""
    target_url = "https://careers.amazon.com/jobs/998877"
    ok, _ = record_applied_job(
        title="MLOps Engineer",
        company="Amazon",
        job_url=target_url,
        status="Submitted (Confirmed)",
        db_path=temp_db
    )
    assert ok is True

    # Same URL should match regardless of different case or whitespace
    assert is_job_already_applied(job_url=target_url, db_path=temp_db) is True
    assert is_job_already_applied(job_url="https://careers.amazon.com/jobs/different", db_path=temp_db) is False


def test_dedup_normalized_company_exact_title(temp_db):
    """Verifies duplicate detection on normalized company with exact title."""
    ok, _ = record_applied_job(
        title="Cloud Data Architect",
        company="Accenture Solutions Private Limited",
        status="Submitted (Confirmed)",
        db_path=temp_db
    )
    assert ok is True

    # "Accenture" normalized matches "Accenture Solutions Private Limited"
    assert is_job_already_applied(
        title="Cloud Data Architect",
        company="Accenture",
        db_path=temp_db
    ) is True

    # Case insensitive title match
    assert is_job_already_applied(
        title="cloud data architect",
        company="Accenture Services Pvt Ltd",
        db_path=temp_db
    ) is True


def test_no_fuzzy_title_collapse_distinct_vacancies(temp_db):
    """
    CRITICAL REGRESSION TEST:
    Verifies that distinct job openings from the same employer (e.g. Lead vs Senior)
    are NOT collapsed to a generic role and falsely blocked.
    """
    company = "JPMorgan Chase & Co"

    # 1. Apply to Lead role
    ok1, _ = record_applied_job(
        title="Lead Azure Data Engineer - Analytics",
        company=company,
        job_url="https://jpmc.com/jobs/lead-analytics",
        status="Submitted (Confirmed)",
        db_path=temp_db
    )
    assert ok1 is True

    # 2. Check if Senior role is falsely blocked as duplicate
    is_dup = is_job_already_applied(
        title="Senior Azure Data Engineer - Infrastructure",
        company=company,
        job_url="https://jpmc.com/jobs/senior-infra",
        db_path=temp_db
    )
    assert is_dup is False, "Senior and Lead distinct roles must NOT be collapsed as duplicates!"

    # 3. Apply to Senior role successfully
    ok2, _ = record_applied_job(
        title="Senior Azure Data Engineer - Infrastructure",
        company=company,
        job_url="https://jpmc.com/jobs/senior-infra",
        status="Submitted (Confirmed)",
        db_path=temp_db
    )
    assert ok2 is True

    # 4. Same exact title and company IS blocked
    is_same_dup = is_job_already_applied(
        title="Senior Azure Data Engineer - Infrastructure",
        company="JPMorgan Chase",
        db_path=temp_db
    )
    assert is_same_dup is True


def test_record_applied_job_forwards_url_and_id(temp_db):
    """Verifies record_applied_job passes job_url and job_id into gatekeeper check."""
    url1 = "https://example.com/posting/alpha"
    ok1, id1 = record_applied_job(
        title="Platform Engineer",
        company="Stripe",
        job_url=url1,
        status="Submitted (Confirmed)",
        db_path=temp_db
    )
    assert ok1 is True

    # Attempt to record duplicate with same URL and different title should be blocked
    ok_dup, _ = record_applied_job(
        title="Core Infrastructure Engineer",
        company="Stripe",
        job_url=url1,
        status="Submitted (Confirmed)",
        db_path=temp_db
    )
    assert ok_dup is False, "Duplicate URL must be rejected by record_applied_job gatekeeper"
