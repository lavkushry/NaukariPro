"""Opaque-box E2E acceptance test suite for selection recovery (A1-A6).

Derived strictly from ORIGINAL_REQUEST.md (R1-R4 & Acceptance Criteria),
PROJECT.md Interface Contracts, AGENTS.md §§3/9, 01_FACT_MATRIX.md, and TEST_INFRA.md.
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, List, Optional, Tuple
from unittest.mock import AsyncMock, MagicMock

import openpyxl
import pypdf
import pytest

pytestmark = pytest.mark.acceptance

ROOT = Path(__file__).resolve().parent.parent

# Construct forbidden tokens dynamically so this file never self-triggers hygiene scans.
BAD_SLUG = "lavkush" + "-kumar"
GHOST_REPOS = (
    "mlops-platform-" + "automation",
    "genai-observability-" + "platform",
)

CANONICAL_LINKEDIN = "https://www.linkedin.com/in/lavkushry/"
CANONICAL_GITHUB = "https://github.com/lavkushry"
PUBLIC_REPOS_AZURE_DE = (
    "aegisagent",
    "vulcan",
    "azure-data-engineering-medallion-lakehouse-project",
)
PUBLIC_REPOS_MLOPS = PUBLIC_REPOS_AZURE_DE

FORBIDDEN_BULLET_VERBS = (
    "helped",
    "worked on",
    "responsible for",
    "assisted",
    "handled",
    "participated in",
    "used",
    "managed",
)

REJECTED_SENIOR_AND_OFFDOMAIN_TITLES = (
    "Staff DevOps Engineer",
    "Staff Site Reliability Engineer",
    "Sr-Mgr Software Development",
    "Senior DevOps Engineer",
    "Principal Databricks Engineer",
    "Lead Data Engineer",
    "Data Engineer Architect",
    "Sr Manager - Data Engineering",
    "Forward Deployed Finance Engineer",
    "Legal Engineer",
)

ACCEPTED_MIDLEVEL_TITLES = (
    "DevOps Engineer",
    "MLOps Engineer",
    "Platform Engineer",
    "Cloud Infrastructure Engineer",
    "Data Engineer",
)

MIDLEVEL_REALISTIC_JD = (
    "Seeking a mid-level engineer with 2-4 years experience in Azure, Kubernetes, "
    "Terraform, Docker, PySpark, Databricks, MLflow, SQL, and CI/CD pipelines."
)


def _extract_pdf_text_and_uris(pdf_path: Path) -> Tuple[int, str, str, List[str]]:
    reader = pypdf.PdfReader(str(pdf_path))
    default_pages: List[str] = []
    layout_pages: List[str] = []
    uris: List[str] = []
    for page in reader.pages:
        default_pages.append(page.extract_text() or "")
        layout_pages.append(page.extract_text(extraction_mode="layout") or "")
        annots = page.get("/Annots") or []
        for annot in annots:
            try:
                obj = annot.get_object()
                action = obj.get("/A")
                if action is not None and hasattr(action, "get_object"):
                    action = action.get_object()
                if action and hasattr(action, "get"):
                    uri = action.get("/URI")
                    if uri:
                        uris.append(str(uri))
            except Exception:
                continue
    default_text = "\n".join(default_pages)
    layout_text = "\n".join(layout_pages)
    norm_text = re.sub(r"\s+", " ", default_text or layout_text).strip()
    return len(reader.pages), layout_text, norm_text, uris


@pytest.fixture
def _isolated_e2e_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Dict[str, Any]:
    """Strict isolation fixture binding all module-level paths and env vars to tmp_path."""
    import naukari_pro.agent.mock_engine as mock_engine_mod
    import naukari_pro.config as cfg_mod
    import naukari_pro.modules.auto_apply as auto_apply_mod
    import naukari_pro.modules.autonomous_loop as loop_mod
    import naukari_pro.modules.candidate_profile as cand_prof_mod
    import naukari_pro.modules.career_portals as portals_mod
    import naukari_pro.modules.db as db_mod
    import naukari_pro.modules.learning.evidence as evidence_mod
    import naukari_pro.modules.learning.policy as policy_mod
    import naukari_pro.modules.learning.volume_guard as volume_guard_mod
    import naukari_pro.modules.linkedin_apply as linkedin_apply_mod
    import naukari_pro.modules.recruiter_outreach as outreach_mod
    import naukari_pro.modules.resume_maker as resume_maker_mod
    import naukari_pro.modules.scorecard as scorecard_mod

    db_file = tmp_path / "applied_jobs.db"
    tracker_file = tmp_path / "Naukri_Live_Application_Tracker.xlsx"
    profile_file = tmp_path / ".job-apply" / "profile.json"
    profile_file.parent.mkdir(parents=True, exist_ok=True)
    attention_file = tmp_path / "attention_queue.json"
    skip_file = tmp_path / "skip_list.json"
    log_file = tmp_path / "naukri_applications_log.json"
    outreach_json = tmp_path / "outreach_tracker.json"
    portals_session = tmp_path / "career_portals_system" / "browser_session"
    portals_session.mkdir(parents=True, exist_ok=True)
    (tmp_path / "logs").mkdir(parents=True, exist_ok=True)
    (tmp_path / "evidence").mkdir(parents=True, exist_ok=True)

    # Copy repo config.json read-only into tmp_path so load_config() inspects real config
    # while any writes target tmp_path only.
    tmp_cfg_dir = tmp_path / "naukri_system"
    tmp_cfg_dir.mkdir(parents=True, exist_ok=True)
    tmp_cfg_file = tmp_cfg_dir / "config.json"
    repo_cfg = ROOT / "naukri_system" / "config.json"
    if repo_cfg.exists():
        shutil.copy2(repo_cfg, tmp_cfg_file)
    else:
        tmp_cfg_file.write_text("{}", encoding="utf-8")

    # Home & Candidate Env isolation (clear live .env URL overrides by default so code defects cannot hide)
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("WORKSPACE_DIR", str(tmp_path))
    for env_key in (
        "CANDIDATE_LINKEDIN",
        "CANDIDATE_GITHUB",
        "CANDIDATE_PORTFOLIO",
        "CANDIDATE_CITY",
        "CANDIDATE_LOCATION",
        "CANDIDATE_STATE",
        "CANDIDATE_PHONE",
        "CANDIDATE_EMAIL",
        "NOTICE_PERIOD",
        "CURRENT_CTC",
        "EXPECTED_CTC",
        "TOTAL_EXPERIENCE",
    ):
        monkeypatch.delenv(env_key, raising=False)

    # Bind naukari_pro.config globals
    monkeypatch.setattr(cfg_mod, "BASE_DIR", str(tmp_path))
    monkeypatch.setattr(cfg_mod, "WORKSPACE_DIR", str(tmp_path))
    monkeypatch.setattr(cfg_mod, "DB_PATH", str(db_file))
    monkeypatch.setattr(cfg_mod, "TRACKER_PATH", str(tracker_file))
    monkeypatch.setattr(cfg_mod, "CONFIG_FILE", str(tmp_cfg_file))
    monkeypatch.setattr(cfg_mod, "CONFIG_PATH", str(tmp_cfg_file), raising=False)

    # Bind db, scorecard, career_portals, autonomous_loop, auto_apply, candidate_profile
    monkeypatch.setattr(db_mod, "DB_PATH", str(db_file))
    monkeypatch.setattr(db_mod, "BASE_DIR", str(tmp_path))
    monkeypatch.setattr(db_mod, "TRACKER_PATH", str(tracker_file))

    monkeypatch.setattr(scorecard_mod, "DB_PATH", str(db_file))
    monkeypatch.setattr(scorecard_mod, "TRACKER_PATH", str(tracker_file))

    monkeypatch.setattr(portals_mod, "TRACKER_PATH", str(tracker_file))
    monkeypatch.setattr(portals_mod, "BASE_DIR", str(tmp_path))
    monkeypatch.setattr(portals_mod, "PROFILE_PATH", profile_file)
    monkeypatch.setattr(portals_mod, "PORTALS_SESSION_DIR", str(portals_session), raising=False)

    monkeypatch.setattr(loop_mod, "DB_PATH", db_file)
    monkeypatch.setattr(loop_mod, "ATTENTION_PATH", attention_file)
    monkeypatch.setattr(loop_mod, "WORKSPACE_DIR", str(tmp_path), raising=False)

    monkeypatch.setattr(linkedin_apply_mod, "TRACKER_PATH", str(tracker_file), raising=False)
    monkeypatch.setattr(linkedin_apply_mod, "WORKSPACE_DIR", str(tmp_path), raising=False)

    monkeypatch.setattr(auto_apply_mod, "BASE_DIR", str(tmp_path), raising=False)
    monkeypatch.setattr(auto_apply_mod, "WORKSPACE_DIR", str(tmp_path))
    monkeypatch.setattr(auto_apply_mod, "SKIP_FILE", str(skip_file))
    monkeypatch.setattr(auto_apply_mod, "LOG_FILE", str(log_file))
    monkeypatch.setattr(auto_apply_mod, "TRACKER_PATH", str(tracker_file))

    monkeypatch.setattr(cand_prof_mod, "PROFILE_PATH", profile_file)

    monkeypatch.setattr(evidence_mod, "BASE_DIR", str(tmp_path))
    monkeypatch.setattr(policy_mod, "DB_PATH", str(db_file))
    monkeypatch.setattr(policy_mod, "WORKSPACE_DIR", str(tmp_path))
    monkeypatch.setattr(volume_guard_mod, "DB_PATH", str(db_file))
    monkeypatch.setattr(mock_engine_mod, "DB_PATH", str(db_file), raising=False)

    monkeypatch.setattr(outreach_mod, "DEFAULT_OUTREACH_JSON", str(outreach_json), raising=False)
    monkeypatch.setattr(outreach_mod, "TRACKER_PATH", str(tracker_file), raising=False)

    monkeypatch.setattr(resume_maker_mod, "CONFIG_FILE", str(tmp_cfg_file), raising=False)

    db_mod.init_db(str(db_file))

    return {
        "tmp_path": tmp_path,
        "db_path": str(db_file),
        "db_path_obj": db_file,
        "tracker_path": str(tracker_file),
        "profile_path": profile_file,
        "attention_path": attention_file,
        "skip_file": skip_file,
        "log_file": log_file,
        "config_file": tmp_cfg_file,
        "evidence_dir": tmp_path / "evidence",
    }


# ==============================================================================
# A1 — PDF Text, Embedded /Annots /URI Links & Fact Grounding
# ==============================================================================


class TestA1ResumePdfCompliance:
    @pytest.mark.parametrize(
        "filename,required,expected_repos",
        [
            ("Lavkush_Kumar_Azure_Data_Engineer_Resume.pdf", True, PUBLIC_REPOS_AZURE_DE),
            ("Lavkush_Kumar_MLOps_Resume.pdf", False, PUBLIC_REPOS_MLOPS),
        ],
    )
    def test_a1_pdf_structure_selectability_and_canonical_uris(
        self,
        filename: str,
        required: bool,
        expected_repos: Tuple[str, ...],
    ) -> None:
        pdf_path = ROOT / filename
        if not pdf_path.exists():
            if required:
                pytest.fail(f"Required resume PDF missing: {pdf_path}")
            pytest.skip(f"Optional PDF not present: {pdf_path}")

        pages, _, norm_text, uris = _extract_pdf_text_and_uris(pdf_path)
        assert pages == 1, f"{filename} must be strictly 1 page, got {pages}"
        assert len(norm_text) > 1000, f"{filename} must have selectable text (>1000 chars), got {len(norm_text)}"

        uris_lower = [u.lower() for u in uris]
        assert any(u.rstrip("/") == CANONICAL_LINKEDIN.rstrip("/") for u in uris_lower), (
            f"{filename} clickable /URI annotations must include {CANONICAL_LINKEDIN}, found {uris}"
        )
        assert any(u.rstrip("/") == CANONICAL_GITHUB.rstrip("/") for u in uris_lower), (
            f"{filename} clickable /URI annotations must include {CANONICAL_GITHUB}, found {uris}"
        )

        text_lower = norm_text.lower()
        for repo in expected_repos:
            expected_repo_uri = f"{CANONICAL_GITHUB}/{repo}".lower()
            assert any(u.rstrip("/") == expected_repo_uri for u in uris_lower), (
                f"{filename} missing clickable public repo /URI '{expected_repo_uri}' in {uris}"
            )
            if repo == "azure-data-engineering-medallion-lakehouse-project":
                assert ("medallion lakehouse" in text_lower or repo in text_lower), (
                    f"{filename} extracted text missing Medallion Lakehouse project reference"
                )
            else:
                assert repo in text_lower, f"{filename} extracted text missing public repo '{repo}'"

    @pytest.mark.parametrize(
        "filename,required",
        [
            ("Lavkush_Kumar_Azure_Data_Engineer_Resume.pdf", True),
            ("Lavkush_Kumar_MLOps_Resume.pdf", False),
        ],
    )
    def test_a1_pdf_zero_bad_urls_and_zero_ghost_repos(self, filename: str, required: bool) -> None:
        pdf_path = ROOT / filename
        if not pdf_path.exists():
            if required:
                pytest.fail(f"Required resume PDF missing: {pdf_path}")
            pytest.skip(f"Optional PDF not present: {pdf_path}")

        _, _, norm_text, uris = _extract_pdf_text_and_uris(pdf_path)
        combined = f"{norm_text}\n" + "\n".join(uris)
        combined_low = combined.lower()

        assert BAD_SLUG not in combined_low, f"{filename} still contains forbidden profile slug"
        for ghost in GHOST_REPOS:
            assert ghost not in combined_low, f"{filename} contains forbidden ghost repo '{ghost}'"

    @pytest.mark.parametrize(
        "filename,required",
        [
            ("Lavkush_Kumar_Azure_Data_Engineer_Resume.pdf", True),
            ("Lavkush_Kumar_MLOps_Resume.pdf", False),
        ],
    )
    def test_a1_pdf_canonical_employment_facts_and_no_inflation(
        self, filename: str, required: bool
    ) -> None:
        pdf_path = ROOT / filename
        if not pdf_path.exists():
            if required:
                pytest.fail(f"Required resume PDF missing: {pdf_path}")
            pytest.skip(f"Optional PDF not present: {pdf_path}")

        _, layout_text, norm_text, _ = _extract_pdf_text_and_uris(pdf_path)
        low = norm_text.lower()

        # Canonical employers & exact titles from AGENTS.md §9 & 01_FACT_MATRIX.md
        for required_phrase in (
            "cgi india",
            "devops engineer",
            "hfcl",
            "engineer 1",
            "security analyst apprentice",
            "stipe solutions",
            "full stack developer intern",
        ):
            assert required_phrase in low, f"{filename} missing canonical fact '{required_phrase}'"

        # Canonical date anchors (Jun/June 2026, Aug/August 2025, Sep/September 2024, Mar/March 2024)
        for date_pat in (
            r"\bjun(?:e)?\s+2026\b",
            r"\baug(?:ust)?\s+2025\b",
            r"\bsep(?:tember)?\s+2024\b",
            r"\bmar(?:ch)?\s+2024\b",
        ):
            assert re.search(date_pat, low), f"{filename} missing canonical date anchor matching /{date_pat}/"

        # Isolate PROFESSIONAL EXPERIENCE section first before slicing CGI/HFCL blocks
        exp_match = re.search(
            r"(?:professional|work)\s+experience\b.*?(?=\b(?:key\s+projects|projects|education|certifications|technical\s+skills)\b|\Z)",
            low,
        )
        assert exp_match is not None, f"{filename} could not isolate PROFESSIONAL EXPERIENCE section"
        exp_block = exp_match.group(0)

        # No CGI Lakehouse / ADF / Databricks / Unity Catalog / Snowflake / PySpark role inflation
        assert "devops engineer / azure data engineer" not in low, (
            f"{filename} inflates CGI India title to 'DevOps Engineer / Azure Data Engineer'"
        )
        assert "senior devops engineer" not in exp_block, (
            f"{filename} inflates employment title to 'Senior DevOps Engineer'"
        )
        assert re.search(r"engineer\s*1\b.{0,25}\b(?:devops|platform)\b", exp_block), (
            f"{filename} HFCL Engineer 1 title missing DevOps / Platform Engineering context"
        )
        cgi_match = re.search(r"cgi india.*?(?=hfcl|engineer\s*1)", exp_block)
        assert cgi_match is not None, f"{filename} could not isolate CGI India current-role block"
        cgi_block = cgi_match.group(0)
        assert "present" in cgi_block, f"{filename} CGI India current role missing 'Present' date anchor"
        assert "azure data engineer" not in cgi_block, (
            f"{filename} inflates CGI India title with 'Azure Data Engineer'"
        )
        assert "senior devops engineer" not in cgi_block, (
            f"{filename} inflates CGI India title with 'Senior DevOps Engineer'"
        )
        for inflated_tok in (
            "lakehouse",
            "azure data factory",
            "databricks",
            "unity catalog",
            "adls gen2",
            "snowflake",
            "aws glue",
            "delta lake",
            "pyspark",
        ):
            assert inflated_tok not in cgi_block, (
                f"{filename} inflates CGI India employment block with '{inflated_tok}'"
            )

        # No fabricated HFCL ML/GPU/Triton/vLLM claims or AGENTS.md §3 red-flag metrics in Experience
        assert "12+ production ml" not in low, f"{filename} contains fabricated '12+ production ml' claim"
        assert "nvidia mps" not in low, f"{filename} contains fabricated 'NVIDIA MPS' claim"
        for forbidden_exp_pat, label in (
            (r"\btriton\b", "Triton"),
            (r"\bvllm\b", "vLLM"),
            (r"\bmodel\s+validation\b", "model validation"),
            (r"\b200\+\s*models\b", "200+ models"),
            (r"99\.99%", "99.99%"),
            (r"\bsub-1\s*ms\b", "sub-1ms"),
            (r"\b100x\b", "100x"),
        ):
            assert not re.search(forbidden_exp_pat, exp_block), (
                f"{filename} contains fabricated/red-flag '{label}' claim in PROFESSIONAL EXPERIENCE"
            )

        # No forbidden bullet-leading verbs per AGENTS.md §3
        for raw_line in layout_text.splitlines():
            stripped = raw_line.strip()
            bullet_match = re.match(r"^(?:[•\-\*▪◦‣]|\u2022)\s*(.+)$", stripped)
            if not bullet_match:
                continue
            bullet_body = bullet_match.group(1).strip().lower()
            for verb in FORBIDDEN_BULLET_VERBS:
                assert not re.match(rf"^{re.escape(verb)}\b", bullet_body), (
                    f"{filename} starts bullet with forbidden verb '{verb}': {bullet_body[:60]}"
                )


# ==============================================================================
# A2 — Repo-Wide URL Hygiene
# ==============================================================================


class TestA2RepoWideUrlHygiene:
    SKIP_DIR_NAMES = {
        ".git",
        ".venv",
        "__pycache__",
        ".pytest_cache",
        "logs",
        "evidence",
        "browser_session",
        ".agents",
    }
    SKIP_SUFFIXES = (".db", ".sqlite", ".sqlite3", ".xlsx", ".pdf", ".pyc", ".png", ".jpg")
    SKIP_REL_PATHS = {
        "docs/V2_RUN_LOG.md",
        "docs/PROFILE_UPDATES_AND_DIAGNOSIS.md",
    }

    @classmethod
    def _should_skip(cls, path: Path) -> bool:
        rel_path = path.relative_to(ROOT)
        rel = rel_path.as_posix()
        if rel in cls.SKIP_REL_PATHS:
            return True
        if any(part in cls.SKIP_DIR_NAMES for part in rel_path.parts):
            return True
        name = path.name
        if ".bak" in name or name.endswith(cls.SKIP_SUFFIXES):
            return True
        return False

    @classmethod
    def _scan_file(cls, path: Path, *, redact_line: bool = False) -> List[str]:
        hits: List[str] = []
        if not path.is_file() or cls._should_skip(path):
            return hits
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return hits
        rel = path.relative_to(ROOT).as_posix()
        is_md = path.suffix.lower() == ".md"
        in_changelog = False
        for idx, line in enumerate(content.splitlines(), start=1):
            low = line.lower()
            if is_md:
                stripped_low = low.strip()
                if re.match(r"^##\s+changelog\b", stripped_low):
                    in_changelog = True
                elif re.match(r"^##\s+", stripped_low):
                    in_changelog = False
            has_url_bad = (
                f"linkedin.com/in/{BAD_SLUG}" in low
                or f"github.com/{BAD_SLUG}" in low
            )
            has_bare_bad = BAD_SLUG in low
            if (in_changelog and has_url_bad) or (not in_changelog and has_bare_bad):
                if redact_line:
                    hits.append(f"{rel}:{idx} [redacted]")
                else:
                    hits.append(f"{rel}:{idx}")
        return hits

    def test_a2_code_config_and_active_docs_zero_bad_slug(self) -> None:
        violations: List[str] = []

        for dir_name in ("naukari_pro", "scripts", "playbooks", ".github"):
            target_dir = ROOT / dir_name
            if target_dir.exists():
                for p in sorted(target_dir.rglob("*")):
                    if p.is_file():
                        violations.extend(self._scan_file(p))

        active_files = [
            "naukri_system/config.json",
            "naukri_system/engine.py",
            "outreach_tracker.json",
            ".env",
            ".env.example",
        ]
        seen: set[Path] = set()
        for rel_file in active_files:
            p = ROOT / rel_file
            if p.exists():
                seen.add(p.resolve())
                violations.extend(self._scan_file(p, redact_line=(rel_file == ".env")))

        for p in sorted(ROOT.iterdir()):
            if p.is_file() and p.suffix.lower() in {".md", ".tex"} and p.resolve() not in seen:
                seen.add(p.resolve())
                violations.extend(self._scan_file(p))

        assert violations == [], f"Forbidden stale URL slug found in active repo files: {violations}"

    def test_a2_tests_directory_zero_bad_slug(self) -> None:
        this_file = Path(__file__).resolve()
        violations: List[str] = []
        tests_dir = ROOT / "tests"
        for p in sorted(tests_dir.rglob("*")):
            if not p.is_file() or p.resolve() == this_file:
                continue
            violations.extend(self._scan_file(p))
        assert violations == [], f"Forbidden stale URL slug found in tests/: {violations}"


# ==============================================================================
# A3 — Profile Generators, Precedence & URL Propagation
# ==============================================================================


class TestA3ProfileGeneratorsAndPropagation:
    def test_a3_candidate_profile_and_career_portals_precedence_and_urls(
        self, _isolated_e2e_env: Dict[str, Any], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from naukari_pro.modules.candidate_profile import load_hybrid_profile
        from naukari_pro.modules.career_portals import load_applicant_profile

        profile_path: Path = _isolated_e2e_env["profile_path"]

        # 1. Defaults only (no profile.json, no CANDIDATE_* URL env vars)
        hybrid_default = load_hybrid_profile()
        app_default = load_applicant_profile()

        for prof_name, prof in (("load_hybrid_profile", hybrid_default), ("load_applicant_profile", app_default)):
            assert prof["linkedInUrl"] == CANONICAL_LINKEDIN, f"{prof_name} default linkedInUrl mismatch"
            assert prof["githubUrl"] == CANONICAL_GITHUB, f"{prof_name} default githubUrl mismatch"
            assert prof["portfolioUrl"] == CANONICAL_GITHUB, f"{prof_name} default portfolioUrl mismatch"
            assert BAD_SLUG not in json.dumps(prof).lower(), f"{prof_name} contains stale URL slug"
            assert prof["currentTitle"] == "DevOps Engineer"
            assert len(prof["workHistory"]) == 4

        # 2. profile.json overrides defaults while official titles stay locked
        json_li = "https://www.linkedin.com/in/json-override/"
        json_gh = "https://github.com/json-override"
        json_portfolio = "https://portfolio.json-override.example"
        profile_path.write_text(
            json.dumps(
                {
                    "profile": {
                        "firstName": "Lavkush",
                        "lastName": "Kumar",
                        "email": "lav84095@gmail.com",
                        "phone": "+91-9122036484",
                        "linkedInUrl": json_li,
                        "githubUrl": json_gh,
                        "portfolioUrl": json_portfolio,
                        "currentTitle": "Principal Architect",
                    }
                }
            ),
            encoding="utf-8",
        )
        hybrid_json = load_hybrid_profile()
        app_json = load_applicant_profile()
        assert hybrid_json["linkedInUrl"] == json_li
        assert hybrid_json["githubUrl"] == json_gh
        assert hybrid_json["portfolioUrl"] == json_portfolio
        assert hybrid_json["currentTitle"] == "DevOps Engineer"
        assert app_json["linkedInUrl"] == json_li
        assert app_json["githubUrl"] == json_gh
        assert app_json["portfolioUrl"] == json_portfolio
        assert app_json["currentTitle"] == "DevOps Engineer"

        # 3. .env / os.environ overrides profile.json (CANDIDATE_GITHUB & CANDIDATE_PORTFOLIO independent)
        env_li = "https://www.linkedin.com/in/env-override/"
        env_gh = "https://github.com/env-override"
        env_portfolio = "https://portfolio.env-override.example"
        monkeypatch.setenv("CANDIDATE_LINKEDIN", env_li)
        monkeypatch.setenv("CANDIDATE_GITHUB", env_gh)

        hybrid_gh_only = load_hybrid_profile()
        assert hybrid_gh_only["linkedInUrl"] == env_li
        assert hybrid_gh_only["githubUrl"] == env_gh
        assert hybrid_gh_only["portfolioUrl"] == json_portfolio

        monkeypatch.setenv("CANDIDATE_PORTFOLIO", env_portfolio)
        hybrid_env = load_hybrid_profile()
        app_env = load_applicant_profile()
        assert hybrid_env["linkedInUrl"] == env_li
        assert hybrid_env["githubUrl"] == env_gh
        assert hybrid_env["portfolioUrl"] == env_portfolio
        assert app_env["linkedInUrl"] == env_li
        assert app_env["githubUrl"] == env_gh
        assert app_env["portfolioUrl"] == env_portfolio

        # 4. When profile.json omits portfolioUrl and CANDIDATE_PORTFOLIO is unset,
        # portfolioUrl falls back to canonical GitHub / CANDIDATE_GITHUB (never stale JSON portfolio).
        monkeypatch.delenv("CANDIDATE_PORTFOLIO", raising=False)
        profile_path.write_text(
            json.dumps(
                {
                    "profile": {
                        "firstName": "Lavkush",
                        "lastName": "Kumar",
                        "email": "lav84095@gmail.com",
                        "phone": "+91-9122036484",
                        "linkedInUrl": json_li,
                        "githubUrl": json_gh,
                    }
                }
            ),
            encoding="utf-8",
        )
        hybrid_fb = load_hybrid_profile()
        app_fb = load_applicant_profile()
        for prof_name, prof in (("load_hybrid_profile", hybrid_fb), ("load_applicant_profile", app_fb)):
            assert prof["linkedInUrl"] == env_li, f"{prof_name} fallback linkedInUrl mismatch"
            assert prof["githubUrl"] == env_gh, f"{prof_name} fallback githubUrl mismatch"
            assert prof["portfolioUrl"] in {CANONICAL_GITHUB, env_gh}, (
                f"{prof_name} fallback portfolioUrl mismatch: {prof['portfolioUrl']}"
            )
            assert BAD_SLUG not in prof["portfolioUrl"].lower()

        titles = [w["title"] for w in app_env["workHistory"]]
        assert titles == [
            "DevOps Engineer",
            "Engineer 1 — DevOps / Platform Engineering",
            "Security Analyst Apprentice",
            "Full Stack Developer Intern",
        ]

    def test_a3_ai_resume_maker_builds_1page_pdf_with_canonical_urls(
        self, _isolated_e2e_env: Dict[str, Any]
    ) -> None:
        from naukari_pro.modules.resume_maker import AIResumeMaker

        out_pdf = _isolated_e2e_env["tmp_path"] / "ai_resume_out.pdf"
        maker = AIResumeMaker(output_pdf_path=str(out_pdf))
        maker.build_ats_resume_pdf()

        assert out_pdf.exists() and out_pdf.stat().st_size > 1000
        pages, _, norm_text, uris = _extract_pdf_text_and_uris(out_pdf)
        assert pages == 1
        combined = f"{norm_text}\n" + "\n".join(uris)
        assert BAD_SLUG not in combined.lower()
        assert "lavkushry" in combined.lower()
        quality = maker.calculate_resume_quality_score()
        assert quality["overall_score"] >= 70.0

    def test_a3_resume_generation_pipeline_renders_dates_cleanly(
        self, _isolated_e2e_env: Dict[str, Any]
    ) -> None:
        from naukari_pro.resume_gen.pipeline import ResumeGenerationPipeline

        master_facts = {
            "summary": "DevOps Engineer with 2.5 years of Kubernetes, Terraform, and CI/CD automation experience.",
            "skills": ["Kubernetes", "Terraform", "Docker", "Ansible", "Python", "AWS EKS", "Jenkins"],
            "experience": [
                {
                    "company": "CGI India",
                    "title": "DevOps Engineer",
                    "duration": "Jun 2026 – Present",
                    "bullets": [
                        "Standardized AWS EKS container platform deployments using Terraform and Ansible."
                    ],
                },
                {
                    "company": "HFCL Limited",
                    "title": "Engineer 1 — DevOps / Platform Engineering",
                    "duration": "Aug 2025 – Jun 2026",
                    "bullets": [
                        "Operated a 50-node Kubernetes platform for 15+ microservices with 99.95% uptime."
                    ],
                },
            ],
            "projects": [
                {
                    "name": "AegisAgent",
                    "tech_stack": "Rust, Cedar, Kubernetes, Helm",
                    "bullets": ["Engineered an AI security gateway with sub-75ms policy evaluation latency."],
                }
            ],
            "education": [
                {
                    "degree": "B.Tech in Computer Science and Engineering",
                    "institution": "Maharishi Dayanand University (MDU), Rohtak",
                    "dates": "2020 – 2023",
                }
            ],
        }
        candidate = {
            "name": "Lavkush Kumar",
            "email": "lav84095@gmail.com",
            "phone": "+91-9122036484",
            "location": "Bangalore, India",
            "linkedin": CANONICAL_LINKEDIN,
            "github": CANONICAL_GITHUB,
        }
        structured_jd = {
            "ats_keywords": ["Kubernetes", "Terraform", "Docker", "Ansible", "AWS EKS", "Python"],
            "must_haves": ["Kubernetes", "Terraform"],
        }

        pipe = ResumeGenerationPipeline(
            master_facts,
            candidate,
            output_dir=_isolated_e2e_env["tmp_path"] / "tailored_resumes",
        )
        art = pipe.generate(structured_jd, role="DevOps Engineer", company="AcmeCorp", also_docx=False)
        assert art.pdf_path is not None and art.pdf_path.exists()
        _, _, norm_text, _ = _extract_pdf_text_and_uris(art.pdf_path)

        assert "Jun 2026" in norm_text and "Present" in norm_text, (
            f"Rendered PDF lost role dates: {norm_text}"
        )
        for bad_date in ("( – )", "( - )", "(None – None)", "None – None", "None - None"):
            assert bad_date not in norm_text, f"Rendered PDF contains broken date placeholder '{bad_date}'"
        assert BAD_SLUG not in norm_text.lower()

    @pytest.mark.parametrize("persona", ["mlops", "de"])
    def test_a3_linkedin_optimizer_blueprints_and_auditor(
        self, _isolated_e2e_env: Dict[str, Any], persona: str
    ) -> None:
        from naukari_pro.modules.linkedin_optimizer import (
            LinkedInProfileAuditor,
            export_100k_blueprint_markdown,
            get_100k_blueprint,
        )

        bp = get_100k_blueprint(persona)
        bp_json = json.dumps(bp)
        assert BAD_SLUG not in bp_json.lower()
        for ghost in GHOST_REPOS:
            assert ghost not in bp_json.lower()
        assert "lavkushry" in bp.get("about", "").lower()
        assert len(bp.get("headline", "")) <= 220
        assert len(bp.get("about", "")) <= 2600

        exp_entries = bp.get("experience") or []
        assert exp_entries, "Blueprint experience cannot be empty"
        cgi_entry = exp_entries[0]
        assert cgi_entry.get("title") == "DevOps Engineer", (
            f"Blueprint '{persona}' CGI title must be 'DevOps Engineer', got {cgi_entry.get('title')}"
        )
        cgi_blob = json.dumps(cgi_entry).lower()
        assert "lakehouse" not in cgi_blob and "azure data factory" not in cgi_blob

        audit_res = LinkedInProfileAuditor().audit(bp)
        assert audit_res["score"] >= 80.0

        md_out = _isolated_e2e_env["tmp_path"] / f"bp_{persona}.md"
        exported_path = Path(export_100k_blueprint_markdown(output_path=str(md_out)))
        assert exported_path.exists()
        assert BAD_SLUG not in exported_path.read_text(encoding="utf-8").lower()

    def test_a3_recruiter_outreach_templates_note_limit_and_canonical_urls(
        self, _isolated_e2e_env: Dict[str, Any], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from naukari_pro.modules.recruiter_outreach import CANDIDATE_FACTS, RecruiterTemplateGenerator

        assert BAD_SLUG not in json.dumps(CANDIDATE_FACTS).lower()

        monkeypatch.setenv("CANDIDATE_LINKEDIN", CANONICAL_LINKEDIN)
        monkeypatch.setenv("CANDIDATE_GITHUB", CANONICAL_GITHUB)

        for gen in (
            RecruiterTemplateGenerator(),
            RecruiterTemplateGenerator(candidate={"name": "Lavkush Kumar"}),
        ):
            for note in (
                gen.generate_mlops_connection_note("Priya Sharma", "Microsoft"),
                gen.generate_connection_note("Priya Sharma", "Microsoft", persona="mlops"),
                gen.generate_connection_note("Recruiting Lead", "Very Long Enterprise Cloud & AI Infrastructure Company Name Limited"),
            ):
                assert len(note) <= 300
                assert note.endswith("- Lavkush")
                assert BAD_SLUG not in note.lower()

            for msg in (
                gen.generate_mlops_inmail("Priya Sharma", "Microsoft", role="MLOps Engineer"),
                gen.generate_direct_inmail("Priya Sharma", "Walmart", role="Data Engineer"),
                gen.generate_tech_lead_pitch("Arjun Nair", "Databricks", role="Platform Engineer"),
                gen.generate_48h_followup("Priya Sharma", "Microsoft", role="MLOps Engineer"),
                gen.generate_application_followup("Priya Sharma", "Google", role="DevOps Engineer", portal_or_req_id="Greenhouse"),
            ):
                body = msg["body"]
                assert "linkedin.com/in/lavkushry" in body.lower()
                assert BAD_SLUG not in body.lower()

    def test_a3_screening_solvers_no_double_scheme_and_grounded_facts(
        self, _isolated_e2e_env: Dict[str, Any], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from naukari_pro.modules.learning.screening_solver import FactMatrixScreeningSolver
        from naukari_pro.modules.linkedin_bot import LinkedInScreeningSolver

        monkeypatch.setenv("CANDIDATE_LINKEDIN", CANONICAL_LINKEDIN)
        monkeypatch.setenv("CANDIDATE_GITHUB", CANONICAL_GITHUB)

        for solver in (
            FactMatrixScreeningSolver(),
            FactMatrixScreeningSolver(config_data={"candidate": {"name": "Lavkush Kumar"}}),
        ):
            li_ans, _, _ = solver.solve_question("LinkedIn Profile URL")
            gh_ans, _, _ = solver.solve_question("GitHub Profile URL")
            exp_ans, _, _ = solver.solve_question("What is your total experience in years?")
            co_ans, _, _ = solver.solve_question("What is your current company?")
            title_ans, _, _ = solver.solve_question("What is your current job title?")
            triton_ans, _, _ = solver.solve_question("Years of production experience with Triton Inference Server?")

            assert li_ans and "linkedin.com/in/lavkushry" in li_ans.lower()
            assert BAD_SLUG not in li_ans.lower()
            assert gh_ans and "github.com/lavkushry" in gh_ans.lower()
            assert BAD_SLUG not in gh_ans.lower()
            assert exp_ans == "2.5"
            assert co_ans and "cgi" in co_ans.lower()
            assert title_ans and "devops engineer" in title_ans.lower()
            assert triton_ans == "0"

        for li_solver in (
            LinkedInScreeningSolver(),
            LinkedInScreeningSolver(
                candidate={
                    "linkedin": CANONICAL_LINKEDIN,
                    "github": CANONICAL_GITHUB,
                    "first_name": "Lavkush",
                    "last_name": "Kumar",
                }
            ),
        ):
            li_val = li_solver.determine_text_answer("LinkedIn Profile URL") or ""
            gh_val = li_solver.determine_text_answer("GitHub Profile URL") or ""
            assert "linkedin.com/in/lavkushry" in li_val.lower()
            assert "github.com/lavkushry" in gh_val.lower()
            assert BAD_SLUG not in li_val.lower()
            assert BAD_SLUG not in gh_val.lower()
            assert "https://www.https://" not in li_val.lower()
            assert "https://https://" not in li_val.lower()
            assert "https://https://" not in gh_val.lower()

    def test_a3_mock_harness_and_career_portal_dry_run_url_propagation(
        self, _isolated_e2e_env: Dict[str, Any]
    ) -> None:
        from naukari_pro.agent.mock_engine import MockMultiPortalHarness
        from naukari_pro.modules.career_portals import CareerPortalManager

        harness = MockMultiPortalHarness()
        results = harness.verify_all_platforms()
        assert set(results.keys()) == {"naukri", "linkedin", "workday", "greenhouse", "lever"}
        for plat, items in results.items():
            assert items, f"No mock jobs returned for {plat}"
            for item in items:
                assert item.is_valid is True, f"Mock fill failed on {plat}: {item.unresolved_mandatory_fields}"
                blob = json.dumps(
                    {
                        "resolved": item.resolved_fields,
                        "answers": item.screening_answers,
                    }
                ).lower()
                assert BAD_SLUG not in blob

        gh_blob = json.dumps(results["greenhouse"][0].resolved_fields).lower()
        assert "linkedin.com/in/lavkushry" in gh_blob
        assert "github.com/lavkushry" in gh_blob

        mgr = CareerPortalManager()
        payload = mgr.fill_dry_run(
            "https://boards.greenhouse.io/example/jobs/1",
            company="ExampleCorp",
            role="MLOps Engineer",
            raw_jd=MIDLEVEL_REALISTIC_JD,
            match_score=80,
        )
        assert "linkedin.com/in/lavkushry" in payload.answers["linkedin"].lower()
        assert "github.com/lavkushry" in payload.answers["github"].lower()
        assert BAD_SLUG not in json.dumps(payload.answers).lower()

    def test_a3_secret_hygiene_across_generated_outputs(
        self, _isolated_e2e_env: Dict[str, Any], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from naukari_pro.agent.mock_engine import MockMultiPortalHarness
        from naukari_pro.modules.candidate_profile import load_hybrid_profile
        from naukari_pro.modules.career_portals import load_applicant_profile
        from naukari_pro.modules.linkedin_optimizer import get_100k_blueprint
        from naukari_pro.modules.recruiter_outreach import RecruiterTemplateGenerator
        from naukari_pro.modules.resume_maker import AIResumeMaker

        sentinel_secrets = {
            "NAUKRI_PASSWORD": "__SENTINEL_NAUKRI_PWD_001__",
            "LINKEDIN_PASSWORD": "__SENTINEL_LI_PWD_002__",
            "LINKEDIN_LI_AT": "__SENTINEL_LI_AT_003__",
            "LINKEDIN_JSESSIONID": "__SENTINEL_JSESSION_004__",
            "GMAIL_APP_PASSWORD": "__SENTINEL_GMAIL_PWD_005__",
            "PORTAL_PASSWORD": "__SENTINEL_PORTAL_PWD_006__",
        }
        for k, v in sentinel_secrets.items():
            monkeypatch.setenv(k, v)

        out_pdf = _isolated_e2e_env["tmp_path"] / "secret_check.pdf"
        AIResumeMaker(output_pdf_path=str(out_pdf)).build_ats_resume_pdf()
        _, _, pdf_text, uris = _extract_pdf_text_and_uris(out_pdf)

        gen = RecruiterTemplateGenerator()
        outputs = [
            json.dumps(load_hybrid_profile()),
            json.dumps(load_applicant_profile()),
            pdf_text,
            "\n".join(uris),
            json.dumps(get_100k_blueprint("mlops")),
            json.dumps(get_100k_blueprint("de")),
            gen.generate_mlops_inmail("Priya", "Acme")["body"],
            json.dumps(
                {
                    k: [r.resolved_fields for r in v]
                    for k, v in MockMultiPortalHarness().verify_all_platforms().items()
                }
            ),
        ]
        combined = "\n".join(outputs)
        for env_key, sentinel in sentinel_secrets.items():
            assert sentinel not in combined, f"Secret env var {env_key} leaked into generated output"


# ==============================================================================
# A4 — Auto-Apply Seniority, Off-Domain & Score Filtering E2E
# ==============================================================================


class TestA4SeniorityAndScoreFiltering:
    @pytest.mark.parametrize("title", REJECTED_SENIOR_AND_OFFDOMAIN_TITLES)
    @pytest.mark.parametrize("score", [0.0, 80.0])
    def test_a4_role_guard_rejects_senior_and_offdomain_titles(
        self, title: str, score: float
    ) -> None:
        from naukari_pro.modules.role_guard import is_strictly_data_or_cloud_role

        ok, reason = is_strictly_data_or_cloud_role(
            title,
            raw_jd="Azure Databricks Kubernetes Terraform Python",
            score=score,
            company="AcmeCorp",
        )
        assert ok is False, f"role_guard leaked '{title}' at score={score}: {reason}"

    @pytest.mark.parametrize("title", REJECTED_SENIOR_AND_OFFDOMAIN_TITLES)
    def test_a4_external_portal_batch_runner_rejects_even_universal_apply(
        self, _isolated_e2e_env: Dict[str, Any], title: str
    ) -> None:
        from naukari_pro.modules.career_portals import ExternalPortalBatchRunner

        runner = ExternalPortalBatchRunner(
            dry_run=True,
            db_path=_isolated_e2e_env["db_path"],
            universal_apply=True,
        )
        vacancy = {
            "company": "AcmeCorp",
            "title": title,
            "url": "https://boards.greenhouse.io/acmecorp/jobs/12345",
            "ats": "Greenhouse",
            "location": "Bengaluru",
            "exp": "2-4 Yrs",
            "salary": "25 LPA",
            "jd": "Azure Databricks PySpark Kubernetes Terraform Python",
        }
        res = runner.run_batch(vacancies=[vacancy], universal_apply=True)
        assert res["submitted"] == 0, f"BatchRunner leaked '{title}' under universal_apply=True: {res}"
        assert res["skipped"] == 1
        assert res["jobs"][0]["status"].startswith("REJECTED_")

    @pytest.mark.parametrize("title", REJECTED_SENIOR_AND_OFFDOMAIN_TITLES)
    def test_a4_career_portal_filler_and_dry_run_reject_all_10(
        self, _isolated_e2e_env: Dict[str, Any], monkeypatch: pytest.MonkeyPatch, title: str
    ) -> None:
        from naukari_pro.modules.career_portals import CareerPortalFiller, FillResult

        filler = CareerPortalFiller(db_path=_isolated_e2e_env["db_path"])
        monkeypatch.setattr(
            filler,
            "fill_in_playwright",
            lambda *a, **kw: FillResult(True, [], None, status="LEAKED_TO_BROWSER"),
        )
        monkeypatch.setattr(
            filler,
            "fill_in_chrome",
            lambda *a, **kw: FillResult(True, [], None, status="LEAKED_TO_CHROME"),
        )
        url = "https://boards.greenhouse.io/acmecorp/jobs/555"

        fill_res = filler.fill(
            portal_url=url,
            company="AcmeCorp",
            role=title,
            headless=True,
            dry_run=False,
            page=MagicMock(),
            raw_jd="Azure Kubernetes Terraform Python",
            match_score=80,
        )
        assert fill_res.success is False
        assert str(fill_res.status).startswith("REJECTED_"), f"CareerPortalFiller.fill leaked '{title}': {fill_res.status}"

        payload = filler.fill_dry_run(
            portal_url=url,
            company="AcmeCorp",
            role=title,
            raw_jd="Azure Kubernetes Terraform Python",
            match_score=80,
        )
        assert payload.status.startswith("REJECTED_"), f"fill_dry_run leaked '{title}': {payload.status}"

    def test_a4_fetch_live_ats_vacancies_filters_all_10_across_all_4_ats(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import requests
        from naukari_pro.modules.career_portals import fetch_live_ats_vacancies

        gh_jobs = [
            {"title": t, "absolute_url": f"https://boards.greenhouse.io/gitlab/jobs/{i}", "content": "Azure Kubernetes Terraform"}
            for i, t in enumerate(REJECTED_SENIOR_AND_OFFDOMAIN_TITLES[:5], start=1)
        ] + [
            {"title": "DevOps Engineer", "absolute_url": "https://boards.greenhouse.io/gitlab/jobs/901", "content": MIDLEVEL_REALISTIC_JD}
        ]
        ashby_jobs = [
            {"title": t, "jobUrl": f"https://jobs.ashbyhq.com/sentry/{i}", "descriptionPlain": "Azure Databricks Python"}
            for i, t in enumerate(REJECTED_SENIOR_AND_OFFDOMAIN_TITLES[5:], start=1)
        ] + [
            {"title": "MLOps Engineer", "jobUrl": "https://jobs.ashbyhq.com/sentry/902", "descriptionPlain": MIDLEVEL_REALISTIC_JD}
        ]
        wd_postings = [
            {"title": "Principal Databricks Engineer", "externalPath": "/job/wd-bad-1", "locationsText": "Bengaluru"},
            {"title": "Data Engineer Architect", "externalPath": "/job/wd-bad-2", "locationsText": "Remote"},
            {"title": "Data Engineer", "externalPath": "/job/wd-ok-1", "locationsText": "Bengaluru"},
        ]
        lever_postings = [
            {"text": "Lead Data Engineer", "hostedUrl": "https://jobs.lever.co/spotify/bad-1", "descriptionPlain": "PySpark Databricks"},
            {"text": "Legal Engineer", "hostedUrl": "https://jobs.lever.co/spotify/bad-2", "descriptionPlain": "Compliance Python"},
            {"text": "Platform Engineer", "hostedUrl": "https://jobs.lever.co/spotify/ok-1", "descriptionPlain": MIDLEVEL_REALISTIC_JD},
        ]

        def fake_get(url: str, *args: Any, **kwargs: Any) -> MagicMock:
            resp = MagicMock()
            resp.status_code = 200
            if "greenhouse.io" in url:
                resp.json.return_value = {"jobs": gh_jobs if "gitlab" in url else []}
            elif "ashbyhq.com" in url:
                resp.json.return_value = {"jobs": ashby_jobs if "sentry" in url else []}
            elif "lever.co" in url:
                resp.json.return_value = lever_postings if "spotify" in url else []
            else:
                resp.json.return_value = {}
            return resp

        def fake_post(url: str, *args: Any, **kwargs: Any) -> MagicMock:
            resp = MagicMock()
            resp.status_code = 200
            resp.json.return_value = {"jobPostings": wd_postings if "nvidia" in url else []}
            return resp

        monkeypatch.setattr(requests, "get", fake_get)
        monkeypatch.setattr(requests, "post", fake_post)

        vacancies = fetch_live_ats_vacancies(limit=50)
        returned_titles = {v["title"] for v in vacancies}

        leaked = returned_titles.intersection(set(REJECTED_SENIOR_AND_OFFDOMAIN_TITLES))
        assert not leaked, f"fetch_live_ats_vacancies leaked rejected titles: {leaked}"
        assert {"DevOps Engineer", "MLOps Engineer", "Data Engineer", "Platform Engineer"}.issubset(returned_titles)

    @pytest.mark.parametrize("title", REJECTED_SENIOR_AND_OFFDOMAIN_TITLES)
    def test_a4_native_chrome_runner_rejects_even_universal_apply(
        self, _isolated_e2e_env: Dict[str, Any], title: str
    ) -> None:
        from naukari_pro.modules.auto_apply import NativeChromeRunner

        runner = NativeChromeRunner(set(), dry_run=True, universal_apply=True)
        ok, reason = runner.apply_to_job(
            "https://www.naukri.com/job-listings-test-123",
            title,
            "AcmeCorp",
            "25 LPA",
            raw_jd="Azure Databricks PySpark Kubernetes Terraform",
            match_score=80,
            universal_apply=True,
        )
        assert ok is False, f"NativeChromeRunner leaked '{title}': {reason}"

        if title == "Senior DevOps Engineer":
            ok_zero, reason_zero = runner.apply_to_job(
                "https://www.naukri.com/job-listings-test-000",
                title,
                "AcmeCorp",
                "25 LPA",
                raw_jd="",
                match_score=0,
                universal_apply=True,
            )
            assert ok_zero is False, f"NativeChromeRunner leaked 0%-match Senior DevOps Engineer: {reason_zero}"

    @pytest.mark.parametrize("title", REJECTED_SENIOR_AND_OFFDOMAIN_TITLES)
    def test_a4_job_match_scorer_rejects_all_10(self, title: str) -> None:
        from naukari_pro.modules.linkedin_search import JobMatchScorer

        res = JobMatchScorer().evaluate(
            job_title=title,
            job_description=MIDLEVEL_REALISTIC_JD,
            min_threshold=70.0,
        )
        assert res.passed is False, (
            f"JobMatchScorer leaked '{title}' with score={res.score}, reasons={res.match_reasons}"
        )

    @pytest.mark.parametrize("title", ["DevOps Engineer", "MLOps Engineer", "Platform Engineer"])
    def test_a4_low_score_midlevel_jd_rejected(
        self, _isolated_e2e_env: Dict[str, Any], title: str
    ) -> None:
        from naukari_pro.modules.career_portals import ExternalPortalBatchRunner
        from naukari_pro.modules.linkedin_search import JobMatchScorer

        unrelated_jd = "Manage retail storefront inventory, POS cash register, and cold-call walk-in leads."
        score_res = JobMatchScorer().evaluate(
            job_title=title,
            job_description=unrelated_jd,
            min_threshold=70.0,
        )
        assert score_res.passed is False and score_res.score < 70.0, (
            f"JobMatchScorer passed unrelated JD for '{title}' at score={score_res.score}"
        )

        runner = ExternalPortalBatchRunner(
            dry_run=True,
            min_score=70.0,
            db_path=_isolated_e2e_env["db_path"],
            universal_apply=False,
        )
        batch_res = runner.run_batch(
            vacancies=[
                {
                    "company": "RetailCo",
                    "title": title,
                    "url": f"https://boards.greenhouse.io/retailco/jobs/{abs(hash(title)) % 10000}",
                    "ats": "Greenhouse",
                    "location": "Bengaluru",
                    "exp": "2-4 Yrs",
                    "salary": "18 LPA",
                    "jd": unrelated_jd,
                }
            ]
        )
        assert batch_res["submitted"] == 0, f"BatchRunner leaked low-score JD for '{title}': {batch_res}"
        assert batch_res["skipped"] == 1

    @pytest.mark.parametrize("universal_flag", [False, True])
    def test_a4_linkedin_apply_engine_rejects_senior_and_low_score_offline(
        self, _isolated_e2e_env: Dict[str, Any], monkeypatch: pytest.MonkeyPatch, universal_flag: bool
    ) -> None:
        import naukari_pro.modules.linkedin_apply as li_apply_mod
        from naukari_pro.modules.linkedin_apply import (
            LinkedInApplicationTracker,
            LinkedInApplyEngine,
            LinkedInCircuitBreaker,
        )

        tmp_path = _isolated_e2e_env["tmp_path"]
        fake_lock = MagicMock()
        fake_lock.acquire.return_value = True
        fake_lock.release.return_value = None

        fake_page = MagicMock()
        fake_page.goto = AsyncMock()
        fake_context = MagicMock()
        fake_context.pages = [fake_page]
        fake_context.close = AsyncMock()

        fake_session = MagicMock()
        fake_session.get_lock.return_value = fake_lock
        fake_session.create_stealth_context = AsyncMock(return_value=fake_context)
        fake_session.verify_session = AsyncMock(
            return_value={"status": "VALID", "candidate_name": "Lavkush Kumar"}
        )

        vacancies = [
            {
                "job_id": f"9900{i}",
                "title": title,
                "company": "AcmeCorp",
                "location": "Bengaluru",
                "url": f"https://www.linkedin.com/jobs/view/9900{i}/",
                "raw_snippet": MIDLEVEL_REALISTIC_JD,
            }
            for i, title in enumerate(REJECTED_SENIOR_AND_OFFDOMAIN_TITLES, start=1)
        ] + [
            {
                "job_id": "99099",
                "title": "DevOps Engineer",
                "company": "RetailCo",
                "location": "Bengaluru",
                "url": "https://www.linkedin.com/jobs/view/99099/",
                "raw_snippet": "Manage retail storefront inventory and cold-call walk-in leads.",
            }
        ]

        fake_search = SimpleNamespace(search_jobs=AsyncMock(return_value={"jobs": vacancies}))

        fake_navigator = MagicMock()
        fake_navigator.circuit_breaker = LinkedInCircuitBreaker()
        fake_navigator.execute_easy_apply = AsyncMock(
            return_value={"status": "APPLIED", "success": True, "steps": 1}
        )

        tracker = LinkedInApplicationTracker(
            excel_path=_isolated_e2e_env["tracker_path"],
            json_log_path=str(tmp_path / "li_log.json"),
            skip_file_path=str(tmp_path / "li_skip.json"),
            fallback_csv_path=str(tmp_path / "li_fb.csv"),
        )

        fake_pw_cm = MagicMock()
        fake_pw_cm.__aenter__ = AsyncMock(return_value=MagicMock())
        fake_pw_cm.__aexit__ = AsyncMock(return_value=False)
        monkeypatch.setattr("playwright.async_api.async_playwright", lambda: fake_pw_cm)
        monkeypatch.setattr(li_apply_mod, "humanized_delay", AsyncMock(return_value=None))

        engine = LinkedInApplyEngine(
            session_manager=fake_session,
            search_engine=fake_search,
            navigator=fake_navigator,
            tracker=tracker,
            circuit_breaker=fake_navigator.circuit_breaker,
            min_score=70.0,
            universal_apply=universal_flag,
        )
        engine.db_path = _isolated_e2e_env["db_path"]

        stats = asyncio.run(
            engine.run_apply_cycle(
                keywords=["DevOps Engineer"],
                locations=["Bengaluru"],
                limit=20,
                dry_run=False,
                headless=True,
                universal_apply=universal_flag,
            )
        )
        assert fake_navigator.execute_easy_apply.await_count == 0, (
            f"LinkedInApplyEngine invoked execute_easy_apply on rejected/low-score jobs "
            f"(universal_apply={universal_flag}): calls={fake_navigator.execute_easy_apply.call_args_list}"
        )
        assert stats["applied"] == 0
        assert stats["skipped"] == len(vacancies)

    @pytest.mark.parametrize("title", ACCEPTED_MIDLEVEL_TITLES)
    def test_a4_accepts_legitimate_midlevel_roles_with_valid_match(
        self, _isolated_e2e_env: Dict[str, Any], title: str
    ) -> None:
        from naukari_pro.modules.auto_apply import NativeChromeRunner
        from naukari_pro.modules.career_portals import CareerPortalFiller, ExternalPortalBatchRunner
        from naukari_pro.modules.role_guard import is_strictly_data_or_cloud_role

        ok_rg, reason_rg = is_strictly_data_or_cloud_role(
            title, raw_jd=MIDLEVEL_REALISTIC_JD, score=75.0, company="AcmeCorp"
        )
        assert ok_rg is True, f"role_guard falsely rejected '{title}': {reason_rg}"

        batch = ExternalPortalBatchRunner(
            dry_run=True,
            min_score=70.0,
            db_path=_isolated_e2e_env["db_path"],
            universal_apply=False,
        )
        res = batch.run_batch(
            vacancies=[
                {
                    "company": "AcmeCorp",
                    "title": title,
                    "url": f"https://boards.greenhouse.io/acmecorp/jobs/{abs(hash(title)) % 10000}",
                    "ats": "Greenhouse",
                    "location": "Bengaluru",
                    "exp": "2-4 Yrs",
                    "salary": "22 LPA",
                    "jd": MIDLEVEL_REALISTIC_JD,
                }
            ]
        )
        assert res["submitted"] == 1, f"BatchRunner rejected legitimate '{title}': {res}"
        assert res["jobs"][0]["status"] == "SUBMITTED_DRY_RUN"

        runner = NativeChromeRunner(set(), dry_run=True, universal_apply=False)
        ok_nc, reason_nc = runner.apply_to_job(
            f"https://www.naukri.com/job-valid-{abs(hash(title)) % 10000}",
            title,
            "AcmeCorp",
            "22 LPA",
            raw_jd=MIDLEVEL_REALISTIC_JD,
            match_score=80,
        )
        assert ok_nc is True, f"NativeChromeRunner rejected legitimate '{title}': {reason_nc}"

        filler = CareerPortalFiller(db_path=_isolated_e2e_env["db_path"])
        payload = filler.fill_dry_run(
            portal_url="https://boards.greenhouse.io/acmecorp/jobs/888",
            company="AcmeCorp",
            role=title,
            raw_jd=MIDLEVEL_REALISTIC_JD,
            match_score=80,
        )
        assert payload.status == "VALIDATED_PAYLOAD", f"fill_dry_run rejected legitimate '{title}': {payload.status}"


# ==============================================================================
# A5 — career_portal Fallback Tracking, DB Dedup, Scorecard & Bounded Drain
# ==============================================================================


class TestA5CareerPortalFallbackAndDrain:
    def test_a5_db_treats_both_fallback_and_bare_clicked_as_unapplied_and_upgradeable(
        self, _isolated_e2e_env: Dict[str, Any]
    ) -> None:
        from naukari_pro.modules.db import (
            get_daily_application_count,
            get_db_connection,
            is_job_already_applied,
            record_applied_job,
        )

        db_path = _isolated_e2e_env["db_path"]

        ok1, jid1 = record_applied_job(
            title="DevOps Engineer",
            company="AcmeOne",
            platform="career_portal",
            job_url="https://boards.greenhouse.io/acmeone/jobs/101",
            status="FALLBACK (CLICKED_NO_CONFIRMATION)",
            db_path=db_path,
        )
        ok2, jid2 = record_applied_job(
            title="Platform Engineer",
            company="AcmeTwo",
            platform="career_portal",
            job_url="https://jobs.lever.co/acmetwo/202",
            status="CLICKED_NO_CONFIRMATION",
            db_path=db_path,
        )
        assert ok1 and ok2

        assert (
            is_job_already_applied(
                title="DevOps Engineer",
                company="AcmeOne",
                job_url="https://boards.greenhouse.io/acmeone/jobs/101",
                job_id=jid1,
                db_path=db_path,
            )
            is False
        )
        assert (
            is_job_already_applied(
                title="Platform Engineer",
                company="AcmeTwo",
                job_url="https://jobs.lever.co/acmetwo/202",
                job_id=jid2,
                db_path=db_path,
            )
            is False
        )
        assert get_daily_application_count(platform="career_portal", db_path=db_path) == 0

        png_path = _isolated_e2e_env["evidence_dir"] / "confirmed.png"
        png_path.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 2048)

        up1, res1 = record_applied_job(
            title="DevOps Engineer",
            company="AcmeOne",
            platform="career_portal",
            job_url="https://boards.greenhouse.io/acmeone/jobs/101",
            status="Submitted (Confirmed)",
            evidence_path=str(png_path),
            db_path=db_path,
        )
        up2, res2 = record_applied_job(
            title="Platform Engineer",
            company="AcmeTwo",
            platform="career_portal",
            job_url="https://jobs.lever.co/acmetwo/202",
            status="Submitted (Confirmed)",
            evidence_path=str(png_path),
            db_path=db_path,
        )
        assert up1 is True and not str(res1).startswith("BLOCKED_DUPLICATE"), f"Upgrade blocked: {res1}"
        assert up2 is True and not str(res2).startswith("BLOCKED_DUPLICATE"), f"Upgrade blocked: {res2}"

        conn = get_db_connection(db_path)
        try:
            statuses = {
                r["job_id"]: r["status"]
                for r in conn.execute("SELECT job_id, status FROM applied_jobs").fetchall()
            }
        finally:
            conn.close()
        assert statuses[jid1] == "Submitted (Confirmed)"
        assert statuses[jid2] == "Submitted (Confirmed)"
        assert get_daily_application_count(platform="career_portal", db_path=db_path) == 2

    def test_a5_scorecard_never_counts_fallback_or_clicked_as_applied(
        self, _isolated_e2e_env: Dict[str, Any]
    ) -> None:
        from naukari_pro.modules.db import record_applied_job
        from naukari_pro.modules.scorecard import CycleScorecard

        sc = CycleScorecard()
        sc.record_status("career_portal", "FALLBACK (CLICKED_NO_CONFIRMATION)")
        sc.record_status("career_portal", "CLICKED_NO_CONFIRMATION")

        assert sc.platforms["external_ats"].applied == 0
        assert sc.platforms["external_ats"].confirmed == 0
        assert sc.platforms["external_ats"].form_autofilled == 0
        assert sc.generate_summary()["totals"]["applied"] == 0

        db_path = _isolated_e2e_env["db_path"]
        record_applied_job(
            title="DevOps Engineer",
            company="ScoreOne",
            platform="career_portal",
            job_url="https://boards.greenhouse.io/scoreone/jobs/11",
            status="FALLBACK (CLICKED_NO_CONFIRMATION)",
            db_path=db_path,
        )
        record_applied_job(
            title="MLOps Engineer",
            company="ScoreTwo",
            platform="career_portal",
            job_url="https://jobs.lever.co/scoretwo/22",
            status="CLICKED_NO_CONFIRMATION",
            db_path=db_path,
        )

        sc_db = CycleScorecard()
        summary = sc_db.sync_from_db(db_path=db_path, since=datetime.now() - timedelta(hours=1))
        assert summary["totals"]["applied"] == 0
        assert summary["by_platform"]["external_ats"]["applied"] == 0
        assert summary["by_platform"]["external_ats"]["confirmed"] == 0
        assert summary["by_platform"]["external_ats"]["form_autofilled"] == 0

    def test_a5_process_external_redirects_returns_submitted_zero_on_no_confirmation(
        self, _isolated_e2e_env: Dict[str, Any], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import naukari_pro.modules.career_portals as portals_mod
        from naukari_pro.modules.career_portals import CareerPortalFiller
        from naukari_pro.modules.db import get_db_connection

        tracker_path = Path(_isolated_e2e_env["tracker_path"])
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Applications_Log"
        ws.append([
            "Application Date",
            "Company Name",
            "Job Title",
            "Match Score (%)",
            "Role Category",
            "Experience Required",
            "Location",
            "Application Type",
            "Status",
            "Job URL",
            "Recruiter Response",
        ])
        ws.append([
            "2026-11-20 10:00",
            "AcmeRedirect",
            "DevOps Engineer",
            "85%",
            "DevOps Engineer",
            "2-4 Yrs",
            "Bengaluru",
            "External Redirect",
            "External Redirect",
            "https://boards.greenhouse.io/acmeredirect/jobs/777",
            "",
        ])
        wb.save(tracker_path)

        fake_locator = MagicMock()
        fake_locator.count.return_value = 0
        fake_locator.first = fake_locator

        fake_page = MagicMock()
        fake_page.url = "https://boards.greenhouse.io/acmeredirect/jobs/777"
        fake_page.content.return_value = "<html><body><form>Apply</form></body></html>"
        fake_page.evaluate.return_value = json.dumps({"filled": ["first_name"]})
        fake_page.locator.return_value = fake_locator

        fake_context = MagicMock()
        fake_context.pages = [fake_page]
        fake_context.new_page.return_value = fake_page

        fake_pw_cm = MagicMock()
        fake_pw_cm.__enter__.return_value = MagicMock()
        fake_pw_cm.__exit__.return_value = False

        monkeypatch.setattr("playwright.sync_api.sync_playwright", lambda: fake_pw_cm)
        monkeypatch.setattr("naukari_pro.session.get_stealth_context", lambda *a, **kw: fake_context)
        monkeypatch.setattr(portals_mod.time, "sleep", lambda _s: None)

        fake_handler = MagicMock()
        fake_handler.detect_barriers.return_value = None
        fake_handler.fill_form.return_value = {"filled": ["first_name"]}
        fake_handler.upload_resume.return_value = True
        fake_handler.submit_form.return_value = True
        fake_handler.verify_confirmation.return_value = False
        fake_handler.field_records = []

        filler = CareerPortalFiller(db_path=_isolated_e2e_env["db_path"])
        filler.policy = SimpleNamespace(select_action=lambda *a, **kw: ("APPLY", 0.9, {}))
        monkeypatch.setattr(filler, "get_handler", lambda _ats: fake_handler)

        res = filler.process_external_redirects(
            limit=5,
            headless=True,
            dry_run=False,
            min_score=70.0,
            max_exp=4.0,
            universal_apply=False,
        )
        assert res["processed"] == 1
        assert res["submitted"] == 0, f"Unconfirmed fallback click must not count as submitted: {res}"

        conn = get_db_connection(_isolated_e2e_env["db_path"])
        try:
            row = conn.execute("SELECT status FROM applied_jobs WHERE company = 'AcmeRedirect'").fetchone()
        finally:
            conn.close()
        assert row is not None
        assert row["status"] == "FALLBACK (CLICKED_NO_CONFIRMATION)"

    def test_a5_drain_incomplete_portal_applies_converges_with_bounded_retries(
        self, _isolated_e2e_env: Dict[str, Any], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from naukari_pro.modules.autonomous_loop import (
            drain_incomplete_portal_applies,
            list_incomplete_portal_jobs,
        )
        from naukari_pro.modules.career_portals import CareerPortalFiller, FillResult
        from naukari_pro.modules.db import record_applied_job

        db_path = _isolated_e2e_env["db_path"]
        db_obj = _isolated_e2e_env["db_path_obj"]

        record_applied_job(
            title="DevOps Engineer",
            company="DrainOne",
            platform="career_portal (Greenhouse)",
            job_url="https://boards.greenhouse.io/drainone/jobs/101",
            status="FALLBACK (CLICKED_NO_CONFIRMATION)",
            match_score=80.0,
            db_path=db_path,
        )
        record_applied_job(
            title="Platform Engineer",
            company="DrainTwo",
            platform="career_portal (Lever)",
            job_url="https://jobs.lever.co/draintwo/202",
            status="CLICKED_NO_CONFIRMATION",
            match_score=80.0,
            db_path=db_path,
        )

        initial_jobs = list_incomplete_portal_jobs(limit=25, db_path=db_obj)
        initial_statuses = {j["status"] for j in initial_jobs}
        assert len(initial_jobs) == 2
        assert initial_statuses == {"FALLBACK (CLICKED_NO_CONFIRMATION)", "CLICKED_NO_CONFIRMATION"}

        fill_calls: List[str] = []
        calls_per_cycle: List[int] = []

        def fake_fill(self: Any, portal_url: str = "", **kwargs: Any) -> FillResult:
            fill_calls.append(portal_url)
            return FillResult(False, ["email"], None, status="CLICKED_NO_CONFIRMATION")

        monkeypatch.setattr(CareerPortalFiller, "fill", fake_fill)

        results = []
        for _ in range(6):
            before_count = len(fill_calls)
            drain_res = drain_incomplete_portal_applies(limit=15, headless=True, dry_run=False)
            assert drain_res.submitted == 0
            results.append(drain_res)
            calls_per_cycle.append(len(fill_calls) - before_count)

        assert len(fill_calls) < 12, (
            f"Unbounded re-drain loop detected: {len(fill_calls)} fill() calls across 6 drain cycles for 2 jobs"
        )
        assert calls_per_cycle[-1] == 0, (
            f"Drain loop did not converge to 0 fill() calls on final cycle: calls_per_cycle={calls_per_cycle}"
        )
        assert all(r.submitted == 0 for r in results)
        assert (
            (results[-1].evaluated == 0 and list_incomplete_portal_jobs(limit=25, db_path=db_obj) == [])
            or (results[-1].skipped == results[-1].evaluated and calls_per_cycle[-1] == 0)
        ), (
            f"Drain loop did not converge cleanly: last_result={results[-1]}, "
            f"remaining={list_incomplete_portal_jobs(limit=25, db_path=db_obj)}"
        )


# ==============================================================================
# A6 — docs/PROFILE_UPDATES_AND_DIAGNOSIS.md Verification
# ==============================================================================


def _has_unnegated_pattern(text: str, pattern: str) -> Optional[str]:
    """Return matched token if pattern occurs without a clause-local negation prefix."""
    neg_re = re.compile(
        r"\b(?:never|do\s+not|don't|zero|no|without|not|avoid|prohibit\w*|forbid\w*)\b"
    )
    for raw_line in text.splitlines():
        line = raw_line.lower()
        for m in re.finditer(pattern, line):
            prefix = line[: m.start()]
            clause_prefix = re.split(r"[.;!?\n]", prefix)[-1][-60:]
            if not neg_re.search(clause_prefix):
                return m.group(0)
    return None


class TestA6ProfileUpdatesAndDiagnosisDoc:
    def test_a6_diagnosis_and_ready_to_use_copy_complete_and_compliant(self) -> None:
        doc_path = ROOT / "docs" / "PROFILE_UPDATES_AND_DIAGNOSIS.md"
        assert doc_path.exists(), f"Missing diagnosis & profile copy doc: {doc_path}"
        text = doc_path.read_text(encoding="utf-8")
        assert len(text) > 1500, "Diagnosis doc is unexpectedly short"
        low = text.lower()

        # 5 required diagnostic areas
        assert "lavkushry" in low and ("404" in low or "broken" in low), "Missing Diagnosis Area 1 (broken URLs / 404s)"
        assert ("01_fact_matrix" in low or "agents.md" in low) and ("cgi" in low and "hfcl" in low), (
            "Missing Diagnosis Area 2 (resume credibility & fact grounding)"
        )
        assert "naukri" in low and ("ctr" in low or "click" in low or "appearance" in low) and (
            "otp" in low or "captcha" in low or "auth" in low
        ), "Missing Diagnosis Area 3 (Naukri CTR & auth freeze)"
        assert "linkedin" in low and ("session" in low or "cookie" in low or "li_at" in low), (
            "Missing Diagnosis Area 4 (LinkedIn session expiry & URL)"
        )
        assert any(k in low for k in ("staff", "senior", "0%", "clicked_no_confirmation", "fallback")), (
            "Missing Diagnosis Area 5 (auto-apply seniority / score mismatch)"
        )

        # Ready-to-use Naukri & LinkedIn copy sections (Parts II & III)
        assert re.search(r"naukri.*headline|headline.*naukri", low) or ("naukri" in low and "headline" in low)
        assert "linkedin" in low and ("about" in low or "summary" in low) and "experience" in low

        copy_match = re.search(
            r"##\s+part\s+ii\b.*?(?=##\s+part\s+iv\b|##\s+changelog\b|\Z)",
            low,
            flags=re.DOTALL,
        )
        assert copy_match is not None, "Doc missing Part II / Part III ready-to-use profile copy sections"
        copy_low = copy_match.group(0)

        # Canonical URLs & grounded facts
        assert CANONICAL_LINKEDIN in low, f"Doc missing canonical LinkedIn URL {CANONICAL_LINKEDIN}"
        assert CANONICAL_GITHUB in low, f"Doc missing canonical GitHub URL {CANONICAL_GITHUB}"
        for grounded in (
            "cgi india",
            "hfcl",
            "stipe solutions",
            "aegisagent",
            "vulcan",
            "azure-data-engineering-medallion-lakehouse-project",
        ):
            assert grounded in low, f"Doc missing grounded fact/repo '{grounded}'"

        # Ready-to-use copy (Parts II & III) must have zero stale slug, zero inflated title,
        # zero un-negated Triton/vLLM/NVIDIA MPS claims, and zero ghost repos.
        assert BAD_SLUG not in copy_low, "Ready-to-use profile copy (Parts II & III) contains stale slug"
        assert "devops engineer / azure data engineer" not in copy_low, (
            "Ready-to-use profile copy inflates CGI India title to 'DevOps Engineer / Azure Data Engineer'"
        )
        bad_lab_claim = _has_unnegated_pattern(copy_low, r"\b(?:triton|vllm|nvidia\s+mps)\b")
        assert bad_lab_claim is None, (
            f"Ready-to-use profile copy contains unverified '{bad_lab_claim}' claim"
        )

        # No ghost repo URLs anywhere in doc, and no ghost repo names in Parts II & III copy
        for ghost in GHOST_REPOS:
            assert f"github.com/lavkushry/{ghost}" not in low, f"Doc contains ghost repo URL '{ghost}'"
            assert ghost not in copy_low, f"Profile copy (Parts II & III) references forbidden ghost repo '{ghost}'"

        # Zero un-negated auth / CAPTCHA bypass claims (allow negated policy statements like "never bypass CAPTCHA")
        for bypass_pat, label in (
            (r"\bbypass\s+captchas?\b", "bypass captcha"),
            (r"\bauto-solve\s+captchas?\b", "auto-solve captcha"),
            (r"\bsolve\s+captchas?\s+automatically\b", "solve captcha automatically"),
            (r"\bcrack\s+otps?\b", "crack otp"),
            (r"\bbypass\s+otps?\b", "bypass otp"),
        ):
            assert _has_unnegated_pattern(low, bypass_pat) is None, f"Doc must never claim '{label}'"
