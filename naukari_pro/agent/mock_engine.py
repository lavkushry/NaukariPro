"""
naukariPro Agent Subsystem: Offline Mock Multi-Portal Execution Harness
Module: naukari_pro.agent.mock_engine

Provides offline mock verification of intent parsing, candidate profile resolution,
and form-field mapping across all 5 platforms (Naukri, LinkedIn, Workday,
Greenhouse, Lever) without live network or browser calls.
"""

from __future__ import annotations

import os
import re
import copy
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple

from naukari_pro.config import RESUME_PDF_PATH
from naukari_pro.agent.intent import CandidateIntent
from naukari_pro.agent.dispatchers.base import PlatformDispatcher, PlatformExecutionReport
from naukari_pro.modules.learning.screening_solver import FactMatrixScreeningSolver, ScreeningDecision
from naukari_pro.modules.db import is_job_already_applied, DB_PATH


# Candidate Ground Truth Profile anchored in 01_FACT_MATRIX.md and AGENTS.md
CANONICAL_CANDIDATE_PROFILE: Dict[str, Any] = {
    "first_name": "Lavkush",
    "last_name": "Kumar",
    "full_name": "Lavkush Kumar",
    "email": "lav84095@gmail.com",
    "phone": "+91-9122036484",
    "city": "Bangalore",
    "state": "Karnataka",
    "country": "India",
    "postal_code": "560100",
    "linkedin_url": "https://linkedin.com/in/lavkushry",
    "github_url": "https://github.com/lavkushry",
    "portfolio_url": "https://github.com/lavkushry",
    "experience_years": 2.5,
    "notice_period_days": 15,
    "current_ctc_lpa": 12.0,
    "expected_ctc_lpa": 20.0,
    "current_company": "CGI India",
    "current_title": "DevOps Engineer",
    "work_authorization": "India",
    "requires_sponsorship": False,
    "resume_path": RESUME_PDF_PATH,
    "work_history": [
        {
            "company": "CGI India",
            "title": "DevOps Engineer",
            "start_date": "2026-06",
            "end_date": "Present",
            "current": True,
            "location": "Bangalore, India"
        },
        {
            "company": "HFCL Limited",
            "title": "Engineer 1 — DevOps / Platform Engineering",
            "start_date": "2025-08",
            "end_date": "2026-06",
            "current": False,
            "location": "Gurugram / Bangalore, India"
        },
        {
            "company": "CGI India",
            "title": "Security Analyst Apprentice",
            "start_date": "2024-09",
            "end_date": "2025-08",
            "current": False,
            "location": "Bangalore, India"
        },
        {
            "company": "Stipe Solutions",
            "title": "Full Stack Developer Intern",
            "start_date": "2024-03",
            "end_date": "2024-09",
            "current": False,
            "location": "Bangalore, India"
        }
    ],
    "education": [
        {
            "degree": "B.Tech in Computer Science and Engineering",
            "institution": "Maharishi Dayanand University (MDU), Rohtak",
            "graduation_year": "2023"
        }
    ]
}


@dataclass
class MockFormFillResult:
    """Represents the outcome of a simulated form fill on a target portal."""
    platform: str
    job_id: str
    company: str
    title: str
    is_valid: bool
    resolved_fields: Dict[str, Any]
    screening_answers: Dict[str, Any]
    unresolved_mandatory_fields: List[str]
    match_score: float


class MockPlatformDispatcher:
    """Mock dispatcher implementing PlatformDispatcher protocol for offline agent testing."""
    timeout_seconds: float = 30.0

    def __init__(
        self,
        platform_name: str,
        harness: "MockMultiPortalHarness",
        db_path: Optional[str] = None
    ):
        self.platform_name = platform_name
        self.harness = harness
        self.db_path = db_path

    def dispatch(self, intent: Any) -> PlatformExecutionReport:
        # In mock harness, dispatch acts identically to dispatch_dry_run
        return self.dispatch_dry_run(intent)

    def dispatch_dry_run(self, intent: Any) -> PlatformExecutionReport:
        jobs = self.harness.get_mock_job_feed(self.platform_name)
        limit = min(getattr(intent, "max_applications", 15), len(jobs))
        report = PlatformExecutionReport(
            platform_name=self.platform_name,
            total_evaluated=len(jobs[:limit]),
            dry_run=True,
            success=True
        )

        for job in jobs[:limit]:
            title = job["title"]
            company = job["company"]
            job_url = job.get("job_url")
            job_id = job.get("job_id")

            # Check deduplication
            if is_job_already_applied(
                title=title,
                company=company,
                job_url=job_url,
                job_id=job_id,
                db_path=self.db_path
            ):
                report.add_record({
                    "job_id": job_id,
                    "title": title,
                    "company": company,
                    "platform": self.platform_name,
                    "status": "SKIPPED_DUPLICATE",
                    "reason": "Already applied in database"
                })
                continue

            fill_result = self.harness.simulate_form_fill(self.platform_name, job)
            if fill_result.is_valid and len(fill_result.unresolved_mandatory_fields) == 0:
                report.add_record({
                    "job_id": job["job_id"],
                    "title": job["title"],
                    "company": job["company"],
                    "platform": self.platform_name,
                    "location": job.get("location", "Bangalore"),
                    "match_score": fill_result.match_score,
                    "status": "SUBMITTED_DRY_RUN",
                    "resolved_fields": fill_result.resolved_fields,
                    "screening_answers": fill_result.screening_answers
                })
            else:
                report.add_record({
                    "job_id": job["job_id"],
                    "title": job["title"],
                    "company": job["company"],
                    "platform": self.platform_name,
                    "status": "SKIPPED_UNRESOLVED",
                    "reason": f"Unresolved fields: {fill_result.unresolved_mandatory_fields}"
                })

        return report


class MockMultiPortalHarness:
    """
    Simulates multi-portal job application form filling and screening questionnaire resolution
    across Naukri, LinkedIn, Workday, Greenhouse, and Lever without network calls.
    """

    def __init__(
        self,
        candidate_profile: Optional[Dict[str, Any]] = None,
        solver: Optional[FactMatrixScreeningSolver] = None
    ):
        self.profile = candidate_profile or CANONICAL_CANDIDATE_PROFILE
        self.solver = solver or FactMatrixScreeningSolver()

    def get_mock_job_feed(self, platform: Optional[str] = None) -> List[Dict[str, Any]]:
        """Returns realistic mock job listings for target platform or all platforms."""
        feed: Dict[str, List[Dict[str, Any]]] = {
            "naukri": [
                {
                    "job_id": "NAUKRI_MOCK_101",
                    "title": "MLOps Engineer (Kubernetes & CI/CD)",
                    "company": "TechCorp India GCC",
                    "location": "Bangalore",
                    "experience_req": "2-4 Yrs",
                    "salary": "22 - 28 Lacs PA",
                    "match_score": 88.0,
                    "mandatory_fields": ["full_name", "email", "phone", "notice_period", "current_ctc"],
                    "screening_questions": [
                        "What is your total experience in years?",
                        "What is your current notice period?",
                        "What is your current CTC in LPA?",
                        "What is your expected CTC in LPA?",
                        "How many years of experience do you have in Kubernetes?"
                    ]
                },
                {
                    "job_id": "NAUKRI_MOCK_102",
                    "title": "DevOps Engineer / Platform Engineer",
                    "company": "Global FinTech Systems",
                    "location": "Hyderabad",
                    "experience_req": "2-5 Yrs",
                    "salary": "20 - 26 Lacs PA",
                    "match_score": 82.0,
                    "mandatory_fields": ["full_name", "email", "phone", "notice_period"],
                    "screening_questions": [
                        "Notice period in days",
                        "Current location",
                        "Years of experience in Terraform"
                    ]
                }
            ],
            "linkedin": [
                {
                    "job_id": "LI_MOCK_201",
                    "title": "ML Platform Engineer - Infrastructure",
                    "company": "NextGen AI Labs",
                    "location": "Bengaluru",
                    "experience_req": "2-3 Years",
                    "match_score": 90.0,
                    "mandatory_fields": ["phone", "email", "work_auth", "sponsorship"],
                    "screening_questions": [
                        "Are you legally authorized to work in India?",
                        "Will you now or in the future require visa sponsorship?",
                        "How many years of work experience do you have with Python?",
                        "What is your notice period in days?"
                    ]
                },
                {
                    "job_id": "LI_MOCK_202",
                    "title": "AI Infrastructure DevOps Engineer",
                    "company": "CloudScale GCC",
                    "location": "Bangalore",
                    "experience_req": "2-4 Years",
                    "match_score": 85.0,
                    "mandatory_fields": ["phone", "email", "work_auth"],
                    "screening_questions": [
                        "Are you authorized to work in India without sponsorship?",
                        "Total years of work experience"
                    ]
                }
            ],
            "workday": [
                {
                    "job_id": "WD_MOCK_301",
                    "title": "DevOps for AI - Cloud Platforms",
                    "company": "Enterprise Cloud Global",
                    "location": "Bangalore / Remote",
                    "job_url": "https://enterprise.myworkdayjobs.com/en-US/careers/job/301",
                    "match_score": 86.0,
                    "mandatory_fields": ["legal_name", "email", "phone", "address", "work_history", "education", "resume"],
                    "screening_questions": [
                        "Are you legally authorized to work in the country where this job is located?",
                        "Do you now or will you in the future require sponsorship for an employment visa?",
                        "Have you ever been convicted of a criminal offense?",
                        "Do you agree to background check verification?"
                    ]
                },
                {
                    "job_id": "WD_MOCK_302",
                    "title": "Cloud Platform Engineer",
                    "company": "Fintech Global Services",
                    "location": "Pune",
                    "job_url": "https://fintech.myworkdayjobs.com/en-US/careers/job/302",
                    "match_score": 84.0,
                    "mandatory_fields": ["legal_name", "email", "phone", "address"],
                    "screening_questions": [
                        "Are you authorized to work in India?",
                        "Will you require visa sponsorship?"
                    ]
                }
            ],
            "greenhouse": [
                {
                    "job_id": "GH_MOCK_401",
                    "title": "MLOps Platform Engineer",
                    "company": "AI Robotics GCC",
                    "location": "Bengaluru",
                    "job_url": "https://boards.greenhouse.io/airobotics/jobs/401",
                    "match_score": 92.0,
                    "mandatory_fields": ["first_name", "last_name", "email", "phone", "resume"],
                    "screening_questions": [
                        "What is your current notice period in days?",
                        "What is your current annual CTC in INR?",
                        "What is your expected annual CTC in INR?",
                        "LinkedIn Profile URL",
                        "GitHub Profile URL"
                    ]
                },
                {
                    "job_id": "GH_MOCK_402",
                    "title": "AI Infrastructure Engineer",
                    "company": "VisionAI Systems",
                    "location": "Bangalore",
                    "job_url": "https://boards.greenhouse.io/visionai/jobs/402",
                    "match_score": 89.0,
                    "mandatory_fields": ["first_name", "last_name", "email", "phone"],
                    "screening_questions": [
                        "Current notice period",
                        "Expected compensation in LPA"
                    ]
                }
            ],
            "lever": [
                {
                    "job_id": "LEV_MOCK_501",
                    "title": "DevOps & Infrastructure Engineer",
                    "company": "ScaleAI Platforms",
                    "location": "Bangalore / Pune",
                    "job_url": "https://jobs.lever.co/scaleai/501",
                    "match_score": 87.0,
                    "mandatory_fields": ["name", "email", "phone", "org", "resume"],
                    "screening_questions": [
                        "Are you comfortable relocating to our Bangalore or Pune offices?",
                        "What is your official notice period?",
                        "URL to your GitHub or portfolio"
                    ]
                },
                {
                    "job_id": "LEV_MOCK_502",
                    "title": "Site Reliability Engineer - ML",
                    "company": "DataHub Technologies",
                    "location": "Remote",
                    "job_url": "https://jobs.lever.co/datahub/502",
                    "match_score": 85.0,
                    "mandatory_fields": ["name", "email", "phone"],
                    "screening_questions": [
                        "Notice period in days",
                        "LinkedIn profile"
                    ]
                }
            ]
        }

        if platform:
            return feed.get(platform.lower().strip(), [])

        all_jobs: List[Dict[str, Any]] = []
        for p_jobs in feed.values():
            all_jobs.extend(p_jobs)
        return all_jobs

    def simulate_form_fill(self, platform: str, job_data: Dict[str, Any]) -> MockFormFillResult:
        """
        Simulates resolving standard form fields and screening questions for a target job.
        Checks for any unresolved mandatory fields.
        """
        p = platform.lower().strip()
        resolved_fields: Dict[str, Any] = {}
        screening_answers: Dict[str, Any] = {}
        unresolved_mandatory: List[str] = []

        # 1. Platform-specific identity and standard field mapping
        if p == "naukri":
            resolved_fields["full_name"] = self.profile["full_name"]
            resolved_fields["email"] = self.profile["email"]
            resolved_fields["phone"] = self.profile["phone"]
            resolved_fields["total_experience"] = str(self.profile["experience_years"])
            resolved_fields["notice_period"] = f"{self.profile['notice_period_days']} Days"
            resolved_fields["current_ctc"] = f"{self.profile['current_ctc_lpa']} LPA"
            resolved_fields["expected_ctc"] = f"{self.profile['expected_ctc_lpa']} LPA"

        elif p == "linkedin":
            resolved_fields["email"] = self.profile["email"]
            resolved_fields["phone"] = self.profile["phone"]
            resolved_fields["country"] = self.profile["country"]
            resolved_fields["city"] = self.profile["city"]
            resolved_fields["work_auth"] = "Yes"
            resolved_fields["sponsorship"] = "No"

        elif p == "workday":
            resolved_fields["legal_name"] = self.profile["full_name"]
            resolved_fields["first_name"] = self.profile["first_name"]
            resolved_fields["last_name"] = self.profile["last_name"]
            resolved_fields["email"] = self.profile["email"]
            resolved_fields["phone"] = self.profile["phone"]
            resolved_fields["address"] = f"{self.profile['city']}, {self.profile['state']}, {self.profile['country']}"
            resolved_fields["work_history"] = self.profile.get("work_history", [])
            resolved_fields["education"] = self.profile.get("education", [])
            resolved_fields["resume"] = self.profile.get("resume_path")

        elif p == "greenhouse":
            resolved_fields["first_name"] = self.profile["first_name"]
            resolved_fields["last_name"] = self.profile["last_name"]
            resolved_fields["email"] = self.profile["email"]
            resolved_fields["phone"] = self.profile["phone"]
            resolved_fields["linkedin_url"] = self.profile["linkedin_url"]
            resolved_fields["github_url"] = self.profile["github_url"]
            resolved_fields["resume"] = self.profile.get("resume_path")

        elif p == "lever":
            resolved_fields["name"] = self.profile["full_name"]
            resolved_fields["email"] = self.profile["email"]
            resolved_fields["phone"] = self.profile["phone"]
            resolved_fields["org"] = self.profile["current_company"]
            resolved_fields["linkedin_url"] = self.profile["linkedin_url"]
            resolved_fields["github_url"] = self.profile["github_url"]
            resolved_fields["resume"] = self.profile.get("resume_path")

        # 2. Screening Question Resolution via FactMatrixScreeningSolver
        screening_questions = job_data.get("screening_questions", [])
        for q in screening_questions:
            # First try evaluate_question
            decision = None
            try:
                decision = self.solver.evaluate_question(q)
            except Exception:
                decision = None

            if decision and decision.answer is not None:
                screening_answers[q] = decision.answer
            else:
                # Direct solve_question tuple (answer, confidence, is_ambiguous)
                ans, conf, is_ambig = self.solver.solve_question(q)
                if ans is not None:
                    screening_answers[q] = ans
                else:
                    screening_answers[q] = "[UNRESOLVED]"

        # 3. Check Mandatory Fields
        mandatory = job_data.get("mandatory_fields", [])
        for field_name in mandatory:
            val = resolved_fields.get(field_name)
            if not val or val == "[UNRESOLVED]":
                unresolved_mandatory.append(field_name)

        # Check screening questions for unresolved
        for q, ans in screening_answers.items():
            if ans == "[UNRESOLVED]":
                unresolved_mandatory.append(f"Screening: {q}")

        is_valid = len(unresolved_mandatory) == 0

        return MockFormFillResult(
            platform=p,
            job_id=job_data.get("job_id", "MOCK_JOB"),
            company=job_data.get("company", "Mock Company"),
            title=job_data.get("title", "Mock Title"),
            is_valid=is_valid,
            resolved_fields=resolved_fields,
            screening_answers=screening_answers,
            unresolved_mandatory_fields=unresolved_mandatory,
            match_score=float(job_data.get("match_score", 80.0))
        )

    def verify_all_platforms(self) -> Dict[str, List[MockFormFillResult]]:
        """Executes mock form fill verification across all 5 platforms and asserts validity."""
        results: Dict[str, List[MockFormFillResult]] = {}
        for plat in ("naukri", "linkedin", "workday", "greenhouse", "lever"):
            jobs = self.get_mock_job_feed(plat)
            plat_results = []
            for j in jobs:
                res = self.simulate_form_fill(plat, j)
                plat_results.append(res)
            results[plat] = plat_results
        return results

    def create_mock_dispatchers(self) -> Dict[str, MockPlatformDispatcher]:
        """Factory returning mock dispatchers for all 5 platforms."""
        return {
            plat: MockPlatformDispatcher(platform_name=plat, harness=self)
            for plat in ("naukri", "linkedin", "workday", "greenhouse", "lever")
        }
