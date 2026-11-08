"""
naukariPro: High-Performance Autonomous CLI Interface
Targeting ₹25 LPA Azure Data Engineer Opportunities
Ground-truth metrics, real server entitlement inspection, and robust error handling.
"""

import os
import sys
import argparse

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from playwright.sync_api import sync_playwright
from playwright.async_api import async_playwright

from naukari_pro.session import get_stealth_context, ensure_authenticated, save_session_cookies, detect_challenge
from naukari_pro.config import load_config
from naukari_pro.modules.auto_apply import AutoApplyEngine
from naukari_pro.modules.job_alerts import InstantAlertsEngine
from naukari_pro.modules.profile_enhancer import ProfileEnhancerEngine
from naukari_pro.modules.hidden_jobs import HiddenJobsEngine
from naukari_pro.modules.resume_maker import AIResumeMaker
from naukari_pro.modules.interview_prep import InterviewPrepEngine
from naukari_pro.modules.skill_insights import SkillInsightsEngine
from naukari_pro.modules.hiring_trends import HiringTrendsEngine
from naukari_pro.modules.early_access import EarlyAccessEngine
from naukari_pro.modules.career_portals import CareerPortalFiller
from naukari_pro.modules.multi_search import UniversalJobSearchEngine
from naukari_pro.modules.pro_autopilot import ProAutoPilotEngine
from naukari_pro.modules.profile_performance import ProfilePerformanceEngine, ProfilePerformanceTracker
import asyncio
import inspect
from naukari_pro.modules.linkedin_session import (
    LinkedInSessionManager,
    LinkedInCookieMissingError,
    LinkedInCookieExpiredError,
    LinkedInCheckpointError,
    mask_cookie_token,
)
from naukari_pro.modules.linkedin_optimizer import (
    LINKEDIN_100K_BLUEPRINT,
    LinkedInProfileAuditor,
    export_100k_blueprint_markdown,
)
from naukari_pro.modules.recruiter_outreach import (
    RecruiterOutreachCRM,
    RecruiterTemplateGenerator,
    TOP_GCC_TARGETS,
)
from naukari_pro.modules.goal_5calls import Goal5CallsEngine


BANNER = r"""
========================================================================
   __  _ ___  __  __ __ ___  _  ___  ____  ___ 
  / / / // _ \/ / / // // _ \/ |/ _ \/ __ \/ _ \
 / /_/ // // / /_/ // // // /    / // /_/ // ___/
 \___\_/\___/\___\_/_/ \___/_/|_/_/ \____/_/    
========================================================================
   Autonomous AI Career Suite | Target: ₹25 LPA Azure Data Engineer
   Candidate: Lavkush Kumar (2.5 YOE | CGI / PNC Bank GCC | HFCL)
========================================================================
"""

def print_menu():
    print(BANNER)
    print("  [P] PRO AUTONOMOUS AUTO-PILOT (Complete All-in-One AI Career Engine)")
    print("  [W] Weekly Recruiter Performance & Keyword Diff Report (The 5 Live Numbers)")
    print("  [E] Server Entitlements & Profile Performance (JWT & Search Stats)")
    print("  [1] Auto-Apply on Naukri (1-Click & Verified Questionnaire Solver)")
    print("  [2] Instant Job Alerts (Cross-platform Desktop & In-App Alerts)")
    print("  [3] AI-Enhanced Profile (Once-a-Day Timestamp Touch & Audit)")
    print("  [4] Hidden Job Opportunities (Inquiries, Recommended Feed & GCCs)")
    print("  [5] AI Resume Maker (1-Page ATS PDF & Quality Scorecard)")
    print("  [6] AI Interview Prep Tools (Master Q&A Bank for ₹25 LPA)")
    print("  [M] Interactive AI Mock Interview Evaluator (Answer Scoring & Coaching)")
    print("  [7] In-Demand Skill Insights (Skill Matrix & Live Market Sampling)")
    print("  [8] Industry Hiring Trends (Salary Benchmarks & GCC Packages)")
    print("  [9] Early Access & NVites (Scrape Homepage & Inbox NVites)")
    print("  [S] Multi-Source Job Hunter (Search Naukri + LinkedIn + Hacker News)")
    print("  [C] Career Portal Auto-Filler (Greenhouse / Ashby / Lever / Workday)")
    print("  [D] Run Complete Daily Autonomous Cycle (Unified Naukri + LinkedIn 8-Stage Cycle)")
    print("  [G] AGY Autonomous Scheduler (Linux systemd & agy CLI schedule)")
    print("  [A] Authenticate Session (One-time Login & Cookie Persistence)")
    print("  [L-IN] Authenticate LinkedIn (Interactive Login & Cookie Sync)")
    print("  [V] LinkedIn Session Diagnostic (Verify li_at cookie & Identity)")
    print("  [L] LinkedIn Easy Apply (Autonomous Multi-Step Bot & Screening Solver)")
    print("  [K] LinkedIn 100k+ Search SEO & Recruiter Optimizer (Blueprint & Audit)")
    print("  [O] 5-Calls/Day Recruiter Outreach & Goal Achievement Engine")
    print("  [0] Exit")
    print("========================================================================")

def handle_pro(
    limit=20,
    limit_naukri=None,
    limit_linkedin=None,
    limit_external=None,
    limit_redirects=None,
    headless=False,
    dry_run=False,
    force=False,
    block=None,
    execute_outreach_live=False,
):
    engine = ProAutoPilotEngine(
        limit=limit,
        limit_naukri=limit_naukri,
        limit_linkedin=limit_linkedin,
        limit_external=limit_external,
        limit_redirects=limit_redirects,
        headless=headless,
        dry_run=dry_run,
        force=force,
        block=block,
        execute_outreach_live=execute_outreach_live,
    )
    return engine.run_full_pipeline()


def handle_track_dashboard(args: argparse.Namespace) -> int:
    from naukari_pro.tracking.dashboard import render_dashboard_html, create_app
    from naukari_pro.tracking.digest import build_weekly_digest
    from naukari_pro.tracking.notifications import NotificationQueue

    if getattr(args, "digest", False):
        digest = build_weekly_digest()
        print(digest["body"])
        # Also enqueue digest notification (idempotent per week key)
        week = __import__("datetime").date.today().strftime("%Y-W%W")
        q = NotificationQueue()
        q.enqueue(user_id="default", job_key=f"digest:{week}", channel="email", payload=digest["body"], delay_minutes=0)
        q.enqueue(user_id="default", job_key=f"digest:{week}", channel="telegram", payload=digest["body"][:500], delay_minutes=0)
        delivered = q.deliver_due()
        print(f"\n[notify] delivered={delivered}")
        return 0

    if getattr(args, "serve", False):
        try:
            import uvicorn
        except ImportError:
            print("uvicorn not installed; showing HTML snapshot instead")
            print(render_dashboard_html())
            return 0
        app = create_app()
        print("Serving tracking dashboard on http://127.0.0.1:8765")
        uvicorn.run(app, host="127.0.0.1", port=8765)
        return 0

    print(BANNER)
    print(render_dashboard_html())
    return 0


def handle_governed_apply(args: argparse.Namespace) -> int:
    from naukari_pro.config import load_config
    from naukari_pro.governed_apply.pipeline import GovernedApplyPipeline

    cfg = load_config()
    cand = cfg.get("candidate") or {}
    facts = {**(cfg.get("candidate_facts") or {}), **cand}
    dry = True if args.dry_run or not getattr(args, "auto_submit", False) else False
    # Default path is dry-run; --auto-submit still respects confirmation rules
    if not getattr(args, "auto_submit", False):
        dry = True
    # G-6 coverage law: live submit requires healthy_boards ≥ 4
    if not dry and getattr(args, "auto_submit", False):
        from naukari_pro.aggregation.gates import SubmitBootBlocked, assert_submit_boot_healthy

        try:
            assert_submit_boot_healthy()
        except SubmitBootBlocked as exc:
            print(BANNER)
            print(f"Submit boot blocked: {exc}")
            return 3
    pipe = GovernedApplyPipeline(
        facts,
        dry_run=dry,
        auto_submit=bool(getattr(args, "auto_submit", False)),
    )
    demo_fields = [
        {"id": "full_name", "label": "Full Name", "type": "text", "required": True},
        {"id": "email", "label": "Email", "type": "email", "required": True},
        {"id": "phone", "label": "Phone", "type": "tel"},
        {"id": "yoe", "label": "Years of experience", "type": "text"},
        {"id": "work_auth", "label": "Are you authorized to work?", "type": "select"},
    ]
    result = pipe.run_job(
        {
            "url": args.url,
            "company": "DemoCo",
            "title": "Azure Data Engineer",
            "fit_score": float(args.fit),
            "coverage_pct": float(args.coverage),
            "ats": "greenhouse",
        },
        dom_fields=demo_fields,
        host="boards.greenhouse.io",
        page_text="",
        page_url=args.url,
    )
    print(BANNER)
    print("=== WS5 Governed Apply ===")
    print(f"Mode           : {'DRY-RUN' if dry else 'LIVE'}")
    print(f"Status         : {result.status}")
    print(f"Field audits   : {result.field_audits}")
    print(f"Submitted      : {result.submitted}")
    print(f"Ask user       : {result.ask_user}")
    print(f"Submissions DB : {pipe.store.submission_count()}")
    return 0


def handle_resume_gen(args: argparse.Namespace) -> int:
    from pathlib import Path
    from naukari_pro.config import load_config
    from naukari_pro.resume_gen.pipeline import ResumeGenerationPipeline

    cfg = load_config()
    cand = cfg.get("candidate") or {}
    facts = cfg.get("candidate_facts") or {}
    # Merge experience from top-level config when present
    if cfg.get("experience") and "experience" not in facts:
        facts = {**facts, "experience": cfg.get("experience")}
    kws = [k.strip() for k in str(getattr(args, "jd_keywords", "")).split(",") if k.strip()]
    structured = {"must_haves": kws, "ats_keywords": kws, "nice_to_haves": []}
    out = Path(args.out) if getattr(args, "out", None) else Path("output") / "tailored_resumes"
    pipe = ResumeGenerationPipeline(facts, cand, output_dir=out, use_llm=False)
    art = pipe.generate(structured, role=args.role, company=args.company)
    print(BANNER)
    print("=== WS4 Truth-Preserving Resume Gen ===")
    print(f"PDF            : {art.pdf_path}")
    print(f"DOCX           : {art.docx_path}")
    print(f"Score          : {art.score.get('overall_score')} / 100 (gate={art.score.get('gate_threshold')})")
    print(f"Dispatch       : {'ALLOWED' if art.dispatch_allowed else 'BLOCKED'}")
    print(f"Gaps reported  : {art.gaps_reported}")
    if art.fabrication_violations:
        print(f"Violations     : {art.fabrication_violations}")
    return 0 if art.dispatch_allowed else 2


def handle_ats_score(args: argparse.Namespace) -> int:
    import json
    from pathlib import Path
    from naukari_pro.resume_gen.scorecard import ats_score_text

    resume_path = Path(args.resume)
    jd_path = Path(args.jd)
    resume_text = resume_path.read_text(encoding="utf-8", errors="replace")
    if resume_path.suffix.lower() == ".pdf":
        try:
            import pypdf

            reader = pypdf.PdfReader(str(resume_path))
            resume_text = "\n".join((p.extract_text() or "") for p in reader.pages)
        except Exception as exc:  # noqa: BLE001
            print(f"PDF extract failed ({exc}); scoring empty text")
            resume_text = ""
    jd_text = jd_path.read_text(encoding="utf-8", errors="replace")
    result = ats_score_text(resume_text, jd_text)
    print(json.dumps(result, indent=2))
    return 0


def handle_e2e_demo(args: argparse.Namespace) -> int:
    """Offline dry-run pipeline: score → tailor → ground → answers → fill verify → approval gate."""
    import json
    from pathlib import Path

    from naukari_pro.governed_apply.dedupe_rules import CompanyDedupeLedger
    from naukari_pro.governed_apply.fill_verify import verify_form
    from naukari_pro.matching.deterministic_score import score_job
    from naukari_pro.resume_gen.claim_validator import validate_text
    from naukari_pro.resume_gen.tailor import audit_no_fabrication, tailor_from_facts
    from naukari_pro.schema.v2_tables import ensure_v2_tables
    from naukari_pro.security.canary import scan_posting

    ensure_v2_tables()
    job = {
        "title": "DevOps Engineer",
        "company": "DemoCorp",
        "location": "Bengaluru",
        "description_full": "Kubernetes Python Azure CI/CD. Notice period immediate joiner welcome.",
        "url": "https://boards.greenhouse.io/democorp/jobs/1",
    }
    canary = scan_posting(job["description_full"])
    if canary.blocked:
        print(json.dumps({"status": "blocked", "reason": "canary", "detail": canary.reasons}))
        return 2

    scored = score_job(job)
    facts = {
        "summary": "DevOps engineer focused on Kubernetes and Azure pipelines.",
        "skills": ["Python", "Kubernetes", "Azure", "Docker"],
        "experience_bullets": [
            "Containerized services with Docker on Azure.",
            "Automated CI/CD with GitHub Actions for platform services.",
        ],
    }
    tailored = tailor_from_facts(
        facts,
        {"must_haves": ["Kubernetes", "Python"], "ats_keywords": ["Azure", "Docker"]},
    )
    violations = audit_no_fabrication(tailored, facts)
    grounding = validate_text(
        " ".join(tailored.get("experience_bullets") or facts["experience_bullets"]),
        facts["experience_bullets"] + [facts["summary"]],
    )
    # Re-ground using tailored bullets
    bullets = []
    for sec in tailored.get("tailored_sections") or []:
        if sec.get("name") == "experience_bullets":
            bullets.extend(str(b) for b in (sec.get("content") or []))
    grounding = validate_text(" ".join(bullets), facts["experience_bullets"] + [facts["summary"]] + facts["skills"])

    fill = verify_form(
        [
            {
                "field_id": "email",
                "expected": "demo@example.com",
                "dom_value": "demo@example.com",
                "check_validity": True,
                "error_banners": [],
                "model_value": "demo@example.com",
            },
            {
                "field_id": "name",
                "expected": "Demo",
                "dom_value": "Demo",
                "check_validity": True,
                "error_banners": [],
                "model_value": "Demo",
            },
            {
                "field_id": "phone",
                "expected": "+919999999999",
                "dom_value": "+919999999999",
                "check_validity": True,
                "error_banners": [],
                "model_value": "+919999999999",
            },
            {
                "field_id": "notice",
                "expected": "30 days",
                "dom_value": "30 days",
                "check_validity": True,
                "error_banners": [],
                "model_value": "30 days",
            },
        ]
    )
    dedupe = CompanyDedupeLedger(db_path=Path("naukari_pro") / "_e2e_dedupe.db").check(job["company"])
    # e2e-demo is dry-run by contract; --submit still requires an approval token and never live-submits.
    submit = bool(getattr(args, "submit", False))
    approval = getattr(args, "approval_token", None)
    if submit and not approval:
        status = "blocked_no_approval"
        exit_code = 2
    elif submit and approval:
        status = "approved_dry_run_only"
        exit_code = 0
    else:
        status = "dry_run_ok"
        exit_code = 0

    report = {
        "status": status,
        "score": scored.total,
        "tailor_violations": violations,
        "grounding_ok": grounding.ok,
        "fill_layers": fill["layers_summary"],
        "fill_all_ok": fill["all_ok"],
        "dedupe_allow": dedupe.allow,
        "dry_run": True,
        "ledger": {
            "url": job["url"],
            "company": job["company"],
            "title": job["title"],
            "resume_version": "e2e_demo",
        },
    }
    print(BANNER)
    print("=== E2E Demo (dry-run) ===")
    print(json.dumps(report, indent=2))
    if not (grounding.ok and fill["all_ok"] and not violations and dedupe.allow):
        return 2
    return exit_code


def handle_browser_bridge(args: argparse.Namespace) -> int:
    from naukari_pro.browser_bridge.server import BrowserBridge

    port = int(getattr(args, "port", 7433) or 7433)
    print(BANNER)
    BrowserBridge(port=port).serve_forever()
    return 0


def handle_match_eval(args: argparse.Namespace) -> int:
    from pathlib import Path
    from naukari_pro.matching.eval import run_eval, write_benchmark_report, auto_apply_allowed

    metrics = run_eval(use_llm=bool(getattr(args, "use_llm", False)), expand_to=int(getattr(args, "expand", 100)))
    report_path = Path(args.report) if getattr(args, "report", None) else None
    out = write_benchmark_report(metrics, path=report_path)
    print(BANNER)
    print("=== WS3 Matching Golden Eval ===")
    d = metrics.to_dict()
    for k, v in d.items():
        if k != "confusion":
            print(f"  {k}: {v}")
    allowed = auto_apply_allowed(metrics)
    print(f"  AUTO_APPLY gate: {'PASS' if allowed else 'BLOCK'}")
    print(f"  Report: {out}")
    return 0 if allowed or not getattr(args, "use_llm", False) else 1


def handle_llm_status(args: argparse.Namespace) -> int:
    from naukari_pro.llm.gateway import LLMGateway
    from naukari_pro.llm.registry import PromptRegistry

    reg = PromptRegistry()
    gw = LLMGateway(registry=reg, mode=getattr(args, "mode", None))
    st = gw.status()
    print(BANNER)
    print("=== AI Gateway Status (M1) ===")
    print(f"Mode              : {st['mode']}")
    print(f"Default provider  : {st['default_provider']}")
    print(f"Available         : {', '.join(st['available_providers']) or '(none — set AI_PROVIDER_*_API_KEY)'}")
    print(f"Registered prompts: {', '.join(st['prompts'])}")
    print(f"Routed tasks      : {', '.join(st['tasks'])}")
    summary = st["ledger"]
    print(f"Month spend       : ${summary['spent_usd']:.6f} / ${summary['cap_usd']:.2f}")
    print(f"Day spend         : ${summary.get('day_spent_usd', 0):.6f} / ${summary.get('daily_cap_usd', 0):.2f}")
    print(f"paused_budget     : {summary.get('paused_budget')}")
    print(f"deterministic_only: {summary.get('deterministic_only')}")
    print(f"Ledger            : {summary['ledger_path']}")
    if summary.get("alerts"):
        for a in summary["alerts"]:
            print(f"ALERT: {a}")
    return 0


def handle_mcp(args: argparse.Namespace) -> int:
    from naukari_pro.mcp.server import main as mcp_main

    if getattr(args, "http", False):
        port = int(getattr(args, "port", 7432) or 7432)
        return mcp_main(["http", str(port)])
    if getattr(args, "list_tools", False):
        from naukari_pro.mcp.server import list_tools
        import json as _json

        print(_json.dumps(list_tools(), indent=2))
        return 0
    return mcp_main([])


def handle_api_serve(args: argparse.Namespace) -> int:
    """Serve OpenAPI REST mirror of MCP tools."""
    try:
        import uvicorn
    except ImportError:
        print("uvicorn required: pip install uvicorn fastapi")
        return 1
    from naukari_pro.api.app import create_api_app

    host = getattr(args, "host", "127.0.0.1") or "127.0.0.1"
    port = int(getattr(args, "port", 8000) or 8000)
    app = create_api_app()
    print(BANNER)
    print(f"NaukariPro OpenAPI on http://{host}:{port}  (docs at /docs)")
    uvicorn.run(app, host=host, port=port)
    return 0


def handle_boards_import(args: argparse.Namespace) -> int:
    from pathlib import Path
    from naukari_pro.aggregation.boards_registry import import_boards_csv
    from naukari_pro.aggregation.storage import AggregationStore

    db_path = Path(args.db) if getattr(args, "db", None) else None
    csv_path = Path(args.csv) if getattr(args, "csv", None) else None
    store = AggregationStore(db_path=db_path) if db_path else AggregationStore()
    n = import_boards_csv(csv_path, store=store)
    print(BANNER)
    print(f"Imported {n} boards into {store.db_path}")
    return 0


def handle_ingest_jobs(args: argparse.Namespace) -> int:
    """WS1 aggregation: seed sources.json → fetch → content-hash upsert (no fabricated fields)."""
    from pathlib import Path
    from naukari_pro.aggregation.ingest_lock import IngestLockError, ingest_lock
    from naukari_pro.aggregation.pipeline import run_ingest_cycle

    db_path = Path(args.db) if getattr(args, "db", None) else None
    try:
        with ingest_lock():
            result = run_ingest_cycle(
                seed=not getattr(args, "no_seed", False),
                limit_sources=getattr(args, "limit_sources", None),
                db_path=db_path,
            )
    except IngestLockError as exc:
        print(BANNER)
        print(f"Ingest skipped (lock): {exc}")
        return 2
    print(BANNER)
    print("=== WS1 Job Aggregation Ingest ===")
    print(f"Seeded sources : {result.get('seeded_sources')}")
    print(f"Boards CSV     : {result.get('boards_imported')}")
    print(f"Adapters       : {', '.join(result.get('adapters') or [])}")
    store = result.get("store_stats") or {}
    print(f"Active sources : {store.get('active_sources')}")
    print(f"Active jobs    : {store.get('active_jobs')}")
    print(f"Healthy boards : {len(result.get('healthy_boards') or [])}")
    print(f"Verified total : {result.get('verified_boards_total')}")
    ingest = result.get("ingest") or {}
    for k in (
        "sources_attempted", "sources_ok", "sources_failed", "sources_missing",
        "inserted", "updated", "unchanged", "removed", "dedup_skipped", "age_filtered",
        "empty_success_rejected",
    ):
        print(f"  {k}: {ingest.get(k)}")
    errors = ingest.get("errors") or []
    if errors:
        print("Sample errors:")
        for e in errors[:10]:
            print(f"  - {e}")
    print(f"Finished at    : {result.get('finished_at')}")
    return 0 if int(ingest.get("sources_failed") or 0) < int(ingest.get("sources_attempted") or 1) else 1


def handle_mail_test():
    from naukari_pro.modules.mail_reader import mail_test
    result = mail_test()
    return 0 if result.get("ok") else 1

def handle_performance(headless=False):
    engine = ProfilePerformanceEngine()
    try:
        with sync_playwright() as p:
            context = get_stealth_context(p, headless=headless)
            page = context.pages[0] if context.pages else context.new_page()
            if ensure_authenticated(page, headless=headless):
                engine.display_report(page=page)
            else:
                engine.display_report()
            context.close()
    except Exception as e:
        print(f"  [!] Notice launching browser for performance report: {e}")
        engine.display_report()

def handle_weekly_report(headless=False):
    engine = ProfilePerformanceEngine()
    try:
        with sync_playwright() as p:
            context = get_stealth_context(p, headless=headless)
            page = context.pages[0] if context.pages else context.new_page()
            if ensure_authenticated(page, headless=headless):
                engine.display_weekly_report(page=page)
            else:
                engine.display_weekly_report()
            context.close()
    except Exception as e:
        print(f"  [!] Notice launching browser for weekly report: {e}")
        engine.display_weekly_report()

def handle_auto_apply(headless=False, limit=20, dry_run=False):
    print("\n[*] Starting Auto-Apply on Naukri...")
    engine = AutoApplyEngine(dry_run=dry_run)
    engine.run(headless=headless, limit=limit, dry_run=dry_run)

def handle_alerts(headless=False):
    print("\n[*] Scanning for Instant Job Alerts...")
    engine = InstantAlertsEngine()
    with sync_playwright() as p:
        context = get_stealth_context(p, headless=headless)
        page = context.pages[0] if context.pages else context.new_page()
        if ensure_authenticated(page, headless=headless):
            alerts = engine.scan_for_alerts(page)
            print(f"\n[+] Identified {len(alerts)} High-Priority Vacancies:")
            for a in alerts:
                print(f" -> [{a['match_score']}% Match] {a['title']} | {a['company']} | {a['location']} | {a['salary']}")
                print(f"    URL: {a['url']}")
        context.close()

def handle_profile(headless=False, force=False):
    print("\n[*] Running AI-Enhanced Profile Module (Once-a-Day Recency Throttle)...")
    engine = ProfileEnhancerEngine()
    
    with sync_playwright() as p:
        context = get_stealth_context(p, headless=headless)
        page = context.pages[0] if context.pages else context.new_page()
        
        audit = engine.audit_profile_strength(page=page if not headless else None)
        print(f"\n[+] Profile Resdex Strength Score: {audit['score']}/100 ({audit['tier']})")
        print(f"    Source: {audit.get('source', 'Config Facts')}")
        for name, desc, pts in audit['checklist']:
            print(f"  [✓] {name:<26} (+{pts} pts) : {desc}")

        if ensure_authenticated(page, headless=headless):
            engine.bump_profile(page, force=force)
        context.close()

def handle_hidden_jobs(headless=False):
    print("\n[*] Discovering Hidden & Off-Market Opportunities...")
    engine = HiddenJobsEngine()
    with sync_playwright() as p:
        context = get_stealth_context(p, headless=headless)
        page = context.pages[0] if context.pages else context.new_page()
        if ensure_authenticated(page, headless=headless):
            jobs = engine.discover_hidden_opportunities(page)
            print(f"\n[+] Discovered {len(jobs)} Off-Market Openings:")
            for j in jobs:
                gcc_tag = " [TOP GCC]" if j.get("is_gcc") else ""
                print(f" -> {j['title']} | {j['company']}{gcc_tag} | {j['location']} ({j['source']})")
                print(f"    URL: {j['url']}")
        context.close()

def handle_resume_maker(jd=None):
    print("\n[*] Compiling AI ATS Resume strictly from config facts...")
    jd_content = None
    if jd:
        if os.path.exists(jd):
            try:
                with open(jd, "r", encoding="utf-8") as f:
                    jd_content = f.read()
                print(f"  [✓] Loaded target JD from file: {jd}")
            except Exception as e:
                print(f"  [!] Could not read JD file ({e}), treating as raw text.")
                jd_content = jd
        else:
            jd_content = jd
        print("  [✓] Tailoring skills and bullets against target Job Description keywords.")

    maker = AIResumeMaker()
    out = maker.build_ats_resume_pdf(jd_text=jd_content)
    print(f"\n[✓] ATS Resume generated successfully: {out}")

    # Generate objective Quality Scorecard
    score = maker.calculate_resume_quality_score(jd_text=jd_content)
    print("\n" + "=" * 65)
    print(f"  📋 ATS RESUME QUALITY SCORECARD — {score['overall_score']}/100")
    print("=" * 65)
    print(f"  • ATS Layout Compliance:    {score.get('ats_compliance_display', score['ats_compliance_score'])}")
    print(f"  • Quantified Metrics Ratio: {score.get('quantified_metrics_display', score['quantified_metrics_score'])}")
    print(f"  • Target Keyword Coverage:  {score.get('keyword_alignment_display', score['keyword_alignment_score'])}")
    print(f"  • Key Matched Keywords:     {', '.join(score['matched_keywords'])}")
    print("  • Evaluator Recommendations:")
    for rec in score['recommendations']:
        print(f"    👉 {rec}")
    print("=" * 65 + "\n")

def handle_interview_prep(mock=False):
    engine = InterviewPrepEngine()
    if mock:
        engine.run_interactive_mock_interview()
    else:
        engine.display_full_prep_guide()

def handle_skill_insights(headless=False):
    engine = SkillInsightsEngine()
    live_samples = None
    if not headless:
        try:
            with sync_playwright() as p:
                context = get_stealth_context(p, headless=True)
                page = context.pages[0] if context.pages else context.new_page()
                live_samples = engine.sample_live_skill_demand(page)
                context.close()
        except Exception:
            pass
    engine.display_insights(live_data=live_samples)

def handle_hiring_trends(headless=False):
    engine = HiringTrendsEngine()
    live_samples = None
    if not headless:
        try:
            with sync_playwright() as p:
                context = get_stealth_context(p, headless=True)
                page = context.pages[0] if context.pages else context.new_page()
                live_samples = engine.sample_live_salary_disclosure(page)
                context.close()
        except Exception:
            pass
    engine.display_market_report(live_data=live_samples)

def handle_portal_apply(url=None, company="Company", role="Azure Data Engineer", jd="", headless=False, dry_run=False, batch=False, limit=10):
    filler = CareerPortalFiller()
    if batch or (not url and (headless or not sys.stdin.isatty() or dry_run)):
        return filler.process_external_redirects(limit=limit, headless=headless, dry_run=dry_run)

    if not url:
        print("\n" + "=" * 65)
        print("  🌐 CAREER PORTAL AUTO-FILLER (Job-Apply Engine)")
        print("  Supported: Greenhouse, Ashby, Lever, Workday, Rippling, Portals")
        print("=" * 65)
        url = input("Enter job application URL (or press Enter for batch mode): ").strip()
        if not url:
            return filler.process_external_redirects(limit=limit, headless=headless, dry_run=dry_run)
        c_in = input("Company name (optional, press Enter for auto): ").strip()
        if c_in: company = c_in
        r_in = input("Role title (optional, press Enter for 'Azure Data Engineer'): ").strip()
        if r_in: role = r_in

    return filler.fill(url, company=company, role=role, headless=headless, dry_run=dry_run, raw_jd=jd)

def handle_external_batch(limit=25, headless=True, dry_run=False, ats=None, remote_first=True, roles=None, locations=None):
    from naukari_pro.modules.career_portals import ExternalPortalBatchRunner
    ats_list = [a.strip() for a in ats.split(",")] if ats else None
    role_list = [r.strip() for r in roles.split(",")] if roles else None
    loc_list = [l.strip() for l in locations.split(",")] if locations else None
    runner = ExternalPortalBatchRunner(headless=headless, dry_run=dry_run, limit=limit)
    print(f"\n[*] Launching External ATS Portal Batch Runner (Limit: {limit}, Remote First: {remote_first}, Headless: {headless}, Dry Run: {dry_run})...")
    stats = runner.run_batch(ats_types=ats_list, roles=role_list, locations=loc_list)
    print(f"\n[✓] Batch Completed: Total Evaluated={stats['total_evaluated']}, Submitted={stats['submitted']}, Skipped={stats['skipped']}")
    return stats

def handle_multi_search(dry_run=False):
    engine = UniversalJobSearchEngine()
    return engine.run_multi_search(dry_run=dry_run)

def handle_daily_cycle(headless=False, dry_run=False, force=False, limit=20):
    print("\n[*] Launching Complete Autonomous Daily Cycle (Unified Naukri + LinkedIn 8-Stage Pipeline)...")
    engine = ProAutoPilotEngine(limit=limit, headless=headless, dry_run=dry_run, force=force)
    return engine.run_full_pipeline()

def handle_auth():
    print("\n[*] Launching browser window for authentic Naukri login...")
    with sync_playwright() as p:
        context = get_stealth_context(p, headless=False)
        page = context.pages[0] if context.pages else context.new_page()

        try:
            page.goto("https://www.naukri.com/nlogin/login", wait_until="domcontentloaded", timeout=30000)
            import time
            time.sleep(2)

            # Auto-fill credentials from config/.env if login form is displayed
            if "nlogin" in page.url or page.locator("#usernameField").count() > 0:
                cfg = load_config()
                cand = cfg.get("candidate", {})
                email = os.getenv("NAUKRI_EMAIL") or cand.get("email", "")
                password = os.getenv("NAUKRI_PASSWORD", "")

                user_field = page.locator("#usernameField").first
                if user_field.is_visible() and email:
                    user_field.fill(email)
                    time.sleep(0.3)
                pass_field = page.locator("#passwordField").first
                if pass_field.is_visible() and password:
                    pass_field.fill(password)
                    time.sleep(0.3)
                login_btn = page.locator("button[type='submit']").first
                if login_btn.is_visible() and password:
                    login_btn.click()
                    time.sleep(2)
                elif not password:
                    print("[!] Notice: NAUKRI_PASSWORD not found in .env. Please type your password in the browser window.")

            challenge = detect_challenge(page)
            if challenge:
                print(f"\n⚠️ {challenge} detected on login page!")

            print("\n" + "=" * 65)
            print("  🔑 CREDENTIALS SUBMITTED!")
            print("  If a visual challenge (Captcha/OTP) appears in the browser window,")
            print("  please complete it manually. Waiting up to 3 minutes for confirmation...")
            print("=" * 65 + "\n")

            page.wait_for_url("**/mnjuser/**", timeout=180000)
            save_session_cookies(context)
            print("\n[✓] SUCCESS: Authenticated session confirmed and cookies synchronized to disk!")
        except Exception as e:
            print(f"\n[!] Notice during login: {e}")

        context.close()

def handle_early_access(headless=False):
    print("\n[*] Scanning Early Access Roles and Recruiter NVites...")
    engine = EarlyAccessEngine()
    with sync_playwright() as p:
        context = get_stealth_context(p, headless=headless)
        page = context.pages[0] if context.pages else context.new_page()
        if ensure_authenticated(page, headless=headless):
            res = engine.scan_early_access(page)
            print(f"\n[+] Profile Status: {res['profile_status']}")
            print(f"[+] Early Access Roles Detected: {res['early_roles_detected']}")
            if res['nvites']:
                print(f"[+] Direct Recruiter Shortlists / NVites:")
                for n in res['nvites']:
                    print(f"  • {n}")
        context.close()

def handle_agy_schedule(action="status"):
    import subprocess
    import os
    workspace = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    runner = os.path.join(workspace, "agy_schedule_runner.sh")
    installer = os.path.join(workspace, "install_linux_schedule.sh")

    if action == "install":
        print("\n[*] Installing NaukariPro AGY Autonomous Linux Scheduler...")
        subprocess.run(["bash", installer], check=False)
    elif action == "run":
        print("\n[*] Triggering immediate AGY Autonomous Cycle...")
        subprocess.run(["bash", runner], check=False)
    elif action == "logs":
        history = os.path.join(workspace, "logs", "agy_schedule_history.log")
        if os.path.exists(history):
            print(f"\n[*] Recent logs from {history}:")
            subprocess.run(["tail", "-n", "50", history])
        else:
            print(f"\n[*] No schedule logs found yet in {history}")
    else:  # status
        print("\n[*] Checking Linux systemd user timers (naukaripro-agy):")
        subprocess.run(["systemctl", "--user", "list-timers", "--no-pager"], check=False)
        print("\n[*] Checking Crontab Fallback:")
        subprocess.run(["crontab", "-l"], check=False)

def handle_linkedin_auth(timeout: int = 300, headless: bool = False) -> int:
    """Runs interactive browser login and saves fresh LinkedIn session cookies."""
    manager = LinkedInSessionManager()
    res = manager.interactive_login(timeout_seconds=timeout, headless=headless)
    return 0 if res.get("status") == "VALID" else 1

def handle_linkedin_verify(args=None, headless: bool = True) -> int:
    """
    Executes LinkedIn session diagnostic verification and prints structured status box.
    Uses pure async Playwright inside asyncio.run() to prevent event loop collisions.
    Returns:
        0 if session is VALID
        1 if session is EXPIRED, COOKIE_MISSING, or UNREACHABLE
        2 if session is CHECKPOINT
    """
    if hasattr(args, "headed"):
        headless = not getattr(args, "headed", False)
    elif hasattr(args, "headless"):
        headless = getattr(args, "headless", True)
    elif isinstance(args, bool):
        headless = args

    manager = LinkedInSessionManager()

    # Direct token update via CLI flag if provided
    if hasattr(args, "set_token") and args.set_token:
        set_js = getattr(args, "set_jsessionid", None)
        manager.set_li_at_token(args.set_token, set_js)
        print(f"\n[✓] Updated LINKEDIN_LI_AT in .env and session_cookies.json! Running verification...")

    token = None
    try:
        token = manager.get_li_at_cookie(raise_if_missing=True)
    except LinkedInCookieMissingError:
        token = None

    if not token:
        print("\n" + "=" * 72)
        print("   LINKEDIN SESSION DIAGNOSTIC & IDENTITY VERIFICATION")
        print("=" * 72)
        print("  • Cookie Source:          NONE (Checked .env and linkedin_system/)")
        print("  • Cookie Present:         NO")
        print("  • Session Status:         COOKIE_MISSING")
        print("  • Authenticated Identity: UNKNOWN")
        print("=" * 72)
        print("  DIAGNOSTIC DETAILS & REMEDIATION:")
        print("  [!] No LinkedIn authentication cookie found.")
        print("  👉 Remediation Instructions:")
        print("     1. Open Chrome on your desktop and log in to https://www.linkedin.com.")
        print("     2. Open DevTools (F12) -> Application tab -> Cookies -> https://www.linkedin.com.")
        print("     3. Copy the value of cookie named 'li_at'.")
        print("     4. Add to /Users/lavkushkumar/Desktop/Resume/.env:")
        print('        LINKEDIN_LI_AT="your_li_at_cookie_value_here"')
        print("     5. Alternatively, export LINKEDIN_LI_AT=\"your_cookie\" in your environment.")
        print("=" * 72 + "\n")
        return 1

    masked_token = mask_cookie_token(token)
    source_desc = getattr(manager, "last_cookie_source", ".env (LINKEDIN_LI_AT)")

    async def _run_verify_async():
        async with async_playwright() as p:
            context = await manager.create_stealth_context(p, headless=headless)
            try:
                page = context.pages[0] if (hasattr(context, "pages") and context.pages) else await context.new_page()
                res = await manager.verify_session(page, raise_for_status=False)
                return res
            finally:
                if hasattr(context, "close"):
                    c_res = context.close()
                    if inspect.isawaitable(c_res):
                        await c_res

    diag = {}
    try:
        diag = asyncio.run(_run_verify_async())
    except LinkedInCheckpointError as e:
        diag = {
            "status": "CHECKPOINT",
            "authenticated": False,
            "checkpoint_detected": True,
            "candidate_name": None,
            "headline": None,
            "final_url": getattr(e, "checkpoint_url", "https://www.linkedin.com/checkpoint/challenge"),
            "detail": str(e)
        }
    except LinkedInCookieExpiredError as e:
        diag = {
            "status": "EXPIRED",
            "authenticated": False,
            "candidate_name": None,
            "headline": None,
            "final_url": getattr(e, "redirect_url", "https://www.linkedin.com/authwall"),
            "detail": str(e)
        }
    except Exception as e:
        err_msg = str(e)
        if "timeout" in err_msg.lower() or "err_" in err_msg.lower() or "dns" in err_msg.lower():
            status_val = "UNREACHABLE"
        else:
            status_val = "EXPIRED"
        diag = {
            "status": status_val,
            "authenticated": False,
            "candidate_name": None,
            "headline": None,
            "detail": f"Verification error: {e}"
        }

    status = diag.get("status", "UNKNOWN")
    candidate_name = diag.get("candidate_name") or "UNKNOWN"
    headline = diag.get("headline") or diag.get("candidate_headline") or "N/A"
    final_url = diag.get("final_url") or diag.get("feed_url") or "N/A"
    dom_verified = diag.get("dom_verified", False)

    print("\n" + "=" * 72)
    print("   LINKEDIN SESSION DIAGNOSTIC & IDENTITY VERIFICATION")
    print("=" * 72)
    print(f"  • Cookie Source:          {source_desc}")
    print("  • Cookie Present:         YES")
    print(f"  • Cookie Token:           {masked_token}")
    print(f"  • Session Status:         {status}")
    print(f"  • Authenticated Identity: {candidate_name}")
    print(f"  • Professional Headline:  {headline}")
    if final_url != "N/A":
        print(f"  • Verified URL:           {final_url}")
    print("=" * 72)
    print("  DIAGNOSTIC DETAILS & REMEDIATION:")

    if status == "VALID":
        print("  [✓] LinkedIn session is active, valid, and authenticated.")
        if dom_verified:
            print(f"  [✓] Verified candidate identity on live DOM: {candidate_name}.")
        print("  [✓] System is fully ready for autonomous Easy Apply execution.")
        print("=" * 72 + "\n")
        return 0
    elif status == "CHECKPOINT":
        print("  ⚠️ LinkedIn security checkpoint or CAPTCHA challenge encountered!")
        print("  👉 Remediation Instructions:")
        print("     1. Run with visible GUI: './naukariPro linkedin-verify --headed'")
        print("     2. Complete the visual challenge or email/SMS OTP in the browser window.")
        print("     3. Once at https://www.linkedin.com/feed/, copy the refreshed 'li_at' cookie and update .env.")
        print("=" * 72 + "\n")
        return 2
    elif status == "UNREACHABLE":
        print("  [!] LinkedIn is unreachable. Check network connection or DNS resolution.")
        print(f"  👉 Diagnostic Detail: {diag.get('detail', 'Network timeout or unreachable host')}")
        print("=" * 72 + "\n")
        return 1
    elif status == "RATE_LIMITED":
        print("  ⚠️ LinkedIn returned HTTP 429 (Too Many Requests / IP Cooldown).")
        print("  👉 Remediation Instructions:")
        print("     1. LinkedIn has temporarily throttled this IP address from repeated rapid page requests.")
        print("     2. Wait 10-15 minutes for the rate limit cooldown to automatically expire.")
        print("     3. Or run with residential proxy in .env (e.g. LINKEDIN_PROXY=http://user:pass@host:port).")
        print("=" * 72 + "\n")
        return 1
    else:  # EXPIRED, UNKNOWN or other
        print("  [!] The provided li_at cookie has expired or was revoked by LinkedIn.")
        print("  👉 Remediation Instructions:")
        print("     1. Open Chrome on your desktop and log in to https://www.linkedin.com.")
        print("     2. Open DevTools (F12) -> Application -> Cookies -> https://www.linkedin.com.")
        print("     3. Copy the fresh value of cookie named 'li_at'.")
        print("     4. Update LINKEDIN_LI_AT in .env.")
        print("=" * 72 + "\n")
        return 1

def handle_linkedin_apply(args=None, limit=25, dry_run=False, headless=True, min_score=70.0, keyword=None, location=None):
    """
    Executes autonomous LinkedIn Easy Apply workflow across target hubs and keywords.
    When dry_run=True, executes 100% offline without launching browser or opening network sockets.
    Strictly gates jobs by score (>= 70.0%) and handles multi-step screening forms.
    """
    if args:
        if hasattr(args, "limit") and args.limit is not None:
            limit = args.limit
        if hasattr(args, "dry_run"):
            dry_run = getattr(args, "dry_run", dry_run)
        if hasattr(args, "headed"):
            headless = not getattr(args, "headed", False)
        elif hasattr(args, "headless"):
            headless = getattr(args, "headless", headless)
        if hasattr(args, "min_score") and args.min_score is not None:
            min_score = args.min_score
        if hasattr(args, "keyword") and args.keyword:
            keyword = args.keyword
        if hasattr(args, "location") and args.location:
            location = args.location

    # Parse comma-delimited keywords and locations into clean lists
    keywords_list = None
    if keyword:
        keywords_list = [k.strip() for k in str(keyword).split(",") if k.strip()]

    locations_list = None
    if location:
        locations_list = [l.strip() for l in str(location).split(",") if l.strip()]

    print("\n" + "=" * 76)
    print("   LINKEDIN AUTONOMOUS EASY APPLY ENGINE")
    print("=" * 76)
    mode_str = "DRY-RUN OFFLINE SIMULATION (NO SUBMISSIONS)" if dry_run else "LIVE AUTONOMOUS SUBMISSIONS"
    print(f"  • Execution Mode:        {mode_str}")
    print(f"  • Daily Cycle Limit:     {limit} applications")
    print(f"  • Minimum Match Gate:    {min_score}%")
    print(f"  • Browser Mode:          {'Offline (No Browser)' if dry_run else ('Headless' if headless else 'Visible GUI')}")
    if keywords_list:
        print(f"  • Keyword Filter:        {', '.join(keywords_list)}")
    if locations_list:
        print(f"  • Location Filter:       {', '.join(locations_list)}")
    print("=" * 76)

    from naukari_pro.modules.linkedin_apply import LinkedInApplyEngine
    apply_engine = LinkedInApplyEngine(min_score=min_score)

    try:
        if dry_run:
            # 100% Offline execution path
            stats = apply_engine.run_offline_dry_run(
                keywords=keywords_list,
                locations=locations_list,
                limit=limit,
                min_score=min_score
            )
        else:
            # Live execution path
            stats = asyncio.run(apply_engine.run_apply_cycle(
                keywords=keywords_list,
                locations=locations_list,
                limit=limit,
                dry_run=False,
                headless=headless
            ))
    except Exception as e:
        print(f"\n[!] Execution error during LinkedIn apply cycle: {e}")
        return 1

    # Formatted Vacancy Results Table
    jobs = stats.get("jobs", [])
    if jobs:
        print("\n" + "-" * 76)
        print(f"  {'#':<3} {'Job ID':<12} {'Company':<20} {'Match':<8} {'Status':<18} {'Steps'}")
        print("-" * 76)
        for idx, j in enumerate(jobs, 1):
            score_val = j.get('score', 0)
            score_str = f"{score_val:.1f}%" if isinstance(score_val, (int, float)) else str(score_val)
            print(f"  {idx:<3} {j.get('job_id', 'N/A'):<12} {j.get('company', 'Unknown')[:18]:<20} {score_str:<8} {j.get('status', 'N/A'):<18} {j.get('steps', 0)}")
        print("-" * 76)

    print("\n" + "=" * 76)
    print("   LINKEDIN APPLY CYCLE RESULTS SUMMARY")
    print("=" * 76)
    print(f"  • Vacancies Discovered:  {stats.get('discovered', 0)}")
    print(f"  • Passed Match Gate:     {stats.get('scored_above_threshold', 0)}")
    if dry_run:
        print(f"  • Dry-Run Verified:      {stats.get('dry_run_verified', 0)}")
    else:
        print(f"  • Applications Sent:     {stats.get('applied', 0)}")
    print(f"  • Skipped / Gated Out:   {stats.get('skipped', 0)}")
    print(f"  • Errors / Stalled:      {stats.get('failed', 0)}")
    print("  • Excel Tracker:         Naukri_Live_Application_Tracker.xlsx")
    print("  • Tracker Worksheet:     LinkedIn_Applications_Log")
    print("=" * 76 + "\n")
    return 0

def handle_linkedin_seo(args=None, output_path: str = None) -> int:
    """
    Audits candidate profile parameters and generates the 100k+ monthly recruiter
    search optimization blueprint (Headline, About, Top 3 Pinned skills, 50-skills taxonomy,
    and hidden Open-to-Work configuration).
    """
    target_out = output_path
    if args and hasattr(args, "output") and args.output:
        target_out = args.output

    auditor = LinkedInProfileAuditor()
    bp = LINKEDIN_100K_BLUEPRINT

    result = auditor.audit(
        headline=bp["headline"],
        about=bp["about"],
        skills=bp["top_50_skills"],
        current_title="DevOps Engineer / Azure Data Engineer"
    )

    md_file = export_100k_blueprint_markdown(target_out)

    print("\n" + "=" * 76)
    print("   LINKEDIN 100K+ RECRUITER SEARCH APPEARANCES & SEO OPTIMIZER")
    print("=" * 76)
    print(f"  • Candidate:             Lavkush Kumar (2.5 YOE | ₹20-25 LPA Target)")
    print(f"  • Target Specialization: Azure Data Engineer / Lakehouse Platform")
    print(f"  • Profile SEO Score:     {result['seo_score']}/100.0 [{result['grade']}]")
    print(f"  • Core Keywords Active:  {len(result['critical_keywords_covered'])}/{len(auditor.CRITICAL_RECRUITER_KEYWORDS)} matched")
    print(f"  • Skills Saturation:     {len(bp['top_50_skills'])}/50 skills defined (100% capacity)")
    print("=" * 76)

    print("\n📌 1. RECRUITER-OPTIMIZED HEADLINE (208 / 220 chars):")
    print("-" * 76)
    print(f"  {bp['headline']}")
    print("-" * 76)

    print("\n📌 2. TOP 3 PINNED SKILLS (Recruiter Boolean Priority 1):")
    print("-" * 76)
    for idx, sk in enumerate(bp['top_50_skills'][:3], 1):
        print(f"  {idx}. {sk}")
    print("-" * 76)

    print("\n📌 3. OPEN TO WORK CONFIGURATION (Recruiters Only):")
    print("-" * 76)
    otw = bp['open_to_work_settings']
    print(f"  • Target Titles:    {', '.join(otw['job_titles'])}")
    print(f"  • Target Hubs:      {', '.join(otw['locations_on_site'])} + Remote")
    print(f"  • Availability:     {otw['start_date']}")
    print(f"  • Visibility:       {otw['visibility']}")
    print("-" * 76)

    print("\n📌 4. STANDALONE BLUEPRINT EXPORT:")
    print("-" * 76)
    print(f"  ✓ Exported to: {md_file}")
    print(f"  ✓ Includes full 2,600-char 'About' section, 50-skills taxonomy, and experience bullets.")
    print("-" * 76 + "\n")
    return 0

def handle_goal_5calls(
    args=None,
    outreach=False,
    pacing=False,
    status=False,
    block=None,
    dry_run=False,
    company=None,
    recruiter=None,
    role="Azure Data Engineer",
    msg_type=None,
    update_status=None,
    lead_id=None,
    notes=None,
    send_outreach=False,
    limit=5,
    headed=False,
    profile_url=None,
    note=None
):
    """
    Handles 5-Calls/Day Goal Pacing, Recruiter Outreach Engine, and Daily 3-Block Execution.
    """
    if args and getattr(args, "interactive", False) is True:
        return handle_goal_5calls_interactive()

    if args:
        val_send = getattr(args, "send_outreach", False)
        if val_send is True or (isinstance(val_send, bool) and val_send):
            send_outreach = True
        raw_limit = getattr(args, "limit", None)
        if isinstance(raw_limit, int):
            limit = raw_limit
        elif raw_limit is not None and not isinstance(raw_limit, type(args)):
            try:
                limit = int(raw_limit)
            except (ValueError, TypeError):
                pass
        raw_headed = getattr(args, "headed", False)
        if raw_headed is True or (isinstance(raw_headed, bool) and raw_headed):
            headed = True
        raw_url = getattr(args, "profile_url", None)
        if isinstance(raw_url, str):
            profile_url = raw_url
        raw_note = getattr(args, "note", None)
        if isinstance(raw_note, str):
            note = raw_note

        val_outreach = getattr(args, "outreach", False)
        if val_outreach is True or (isinstance(val_outreach, bool) and val_outreach):
            outreach = True
        val_pacing = getattr(args, "pacing", False)
        if val_pacing is True or (isinstance(val_pacing, bool) and val_pacing):
            pacing = True
        val_status = getattr(args, "status", False)
        if val_status is True or (isinstance(val_status, bool) and val_status):
            status = True
        val_block = getattr(args, "block", None)
        if isinstance(val_block, int):
            block = val_block
        elif val_block is not None and not isinstance(val_block, type(args)):
            try:
                block = int(val_block)
            except (ValueError, TypeError):
                pass
        val_dry = getattr(args, "dry_run", False)
        if val_dry is True or (isinstance(val_dry, bool) and val_dry):
            dry_run = True
        val_comp = getattr(args, "company", None)
        if isinstance(val_comp, str):
            company = val_comp
        val_rec = getattr(args, "recruiter", None)
        if isinstance(val_rec, str):
            recruiter = val_rec
        val_role = getattr(args, "role", None)
        if isinstance(val_role, str):
            role = val_role
        val_type = getattr(args, "msg_type", None)
        if isinstance(val_type, str):
            msg_type = val_type
        val_up = getattr(args, "update_status", None)
        if isinstance(val_up, str):
            update_status = val_up
        val_lid = getattr(args, "lead_id", None)
        if isinstance(val_lid, str):
            lead_id = val_lid
        val_notes = getattr(args, "notes", None)
        if isinstance(val_notes, str):
            notes = val_notes

    # 0. Autonomous Recruiter Connection Bot (Playwright Stealth)
    if send_outreach:
        from naukari_pro.modules.linkedin_outreach import LinkedInOutreachSender
        sender = LinkedInOutreachSender(headless=not headed, max_daily_limit=min(limit, 8))

        print("\n" + "=" * 76)
        print("   🤖 AUTONOMOUS LINKEDIN RECRUITER CONNECTION BOT (PLAYWRIGHT STEALTH)")
        print("   Candidate: Lavkush Kumar (₹20–25 LPA | 15-Day Notice | Azure Data Engineer)")
        print("=" * 76)
        mode_desc = "[DRY-RUN SIMULATION] (Safe: Modal verified, no live invitations sent)" if dry_run else "[LIVE DISPATCH] (Sending live connection requests)"
        print(f"  • Mode:              {mode_desc}")
        print(f"  • Browser:           {'Headed (Visible GUI)' if headed else 'Headless (Stealth)'}")
        print(f"  • Daily Limit:       {min(limit, 8)} profiles max")
        print("-" * 76)

        if company or recruiter or profile_url:
            rec = recruiter or "Hiring Team"
            comp = company or "Target Company"
            print(f"[*] Navigating to {rec} at {comp} (URL: {profile_url or 'LinkedIn Search'})...")
            res = sender.run_outreach(
                recruiter_name=rec,
                company=comp,
                profile_url=profile_url,
                note=note,
                dry_run=dry_run,
                max_daily_limit=min(limit, 8)
            )
            print("-" * 76)
            print(f"  • Recruiter:         {res.get('recruiter_name')}")
            print(f"  • Company:           {res.get('company')}")
            print(f"  • Status:            {res.get('status')}")
            print(f"  • Invitation Sent:   {res.get('sent')}")
            if res.get("note"):
                print(f"  • Note ({res.get('note_length', len(res['note']))}/300 chars):")
                print(f"    \"{res.get('note')}\"")
            print(f"  • Diagnostic Detail: {res.get('detail')}")
            print("=" * 76 + "\n")
            return 0 if res.get("status") in ["SENT", "DRY_RUN_VERIFIED", "ALREADY_CONNECTED", "PENDING"] else 1
        else:
            print(f"[*] Executing Autonomous Outreach Batch (up to {min(limit, 8)} GCC Recruiters)...")
            batch_res = sender.run_batch(
                limit=min(limit, 8),
                dry_run=dry_run,
                headless=not headed,
                custom_note=note
            )
            print("\n" + "=" * 76)
            print("   RECRUITER OUTREACH BATCH EXECUTION RESULTS")
            print("=" * 76)
            print(f"  • Batch Status:      {batch_res.get('status')}")
            print(f"  • Processed:         {batch_res.get('total_processed', 0)}")
            print(f"  • Live Invites Sent: {batch_res.get('sent_count', 0)}")
            print(f"  • Dry-Run Verified:  {batch_res.get('dry_run_count', 0)}")
            print("-" * 76)
            results_list = batch_res.get("results", [])
            if results_list:
                print(f"  {'#':<3} {'Company':<22} {'Recruiter':<22} {'Status':<18} {'Length'}")
                print("-" * 76)
                for i, r in enumerate(results_list, 1):
                    c_name = str(r.get("company", ""))[:20]
                    r_name = str(r.get("recruiter_name", ""))[:20]
                    st = str(r.get("status", ""))[:16]
                    n_len = f"{r.get('note_length', 0)}/300" if r.get("note") else "N/A"
                    print(f"  {i:<3} {c_name:<22} {r_name:<22} {st:<18} {n_len}")
            print("=" * 76 + "\n")
            return 0 if batch_res.get("status") == "COMPLETED" else 1

    engine = Goal5CallsEngine()

    # 1. Update lead status if requested
    if update_status:
        target_id = lead_id or recruiter or company
        if not target_id:
            print("[!] Error: Must specify --lead-id, --recruiter, or --company with --update-status.")
            return 1
        updated = engine.crm.update_status(target_id, update_status, notes=notes)
        if updated:
            print(f"\n[✓] Successfully updated lead '{updated.get('lead_id')}' ({updated.get('company')}) to {update_status}.")
            print(f"    Notes: {updated.get('notes')}")
        else:
            print(f"\n[!] Lead '{target_id}' not found in outreach CRM.")
            return 1
        return 0

    # 2. Daily Block Execution
    if block is not None:
        print(f"\n[*] Executing Daily Block {block} (Dry-Run: {dry_run})...")
        res = engine.run_block(block_number=int(block), dry_run=dry_run)
        print("\n" + "=" * 76)
        print(f"   5-CALLS/DAY DAILY BLOCK {block} EXECUTION SUMMARY")
        print("=" * 76)
        print(f"  • Timestamp: {res.get('timestamp')}")
        print(f"  • Status:    {res.get('status')}")
        print("  • Actions Executed:")
        for act in res.get("actions_executed", []):
            print(f"    - {act.get('action')}: {act.get('details', '')}")
            if "count" in act:
                print(f"      Count: {act['count']}")
        print("=" * 76 + "\n")
        return 0

    # 3. Outreach Pitch Generation
    if outreach:
        gen = engine.generator
        if company:
            rec = recruiter or "Hiring Team"
            t_type = msg_type or "inmail"
            template_res = gen.generate_template(t_type, rec, company, role=role)
            conn_note = gen.generate_connection_note(rec, company)

            print("\n" + "=" * 76)
            print(f"   RECRUITER OUTREACH TEMPLATES: {company.upper()}")
            print("=" * 76)
            print(f"  • Recruiter / Lead: {rec}")
            print(f"  • Role Target:      {role}")
            print(f"  • Template Type:    {t_type}")
            print("-" * 76)
            print(f"📌 1. LINKEDIN CONNECTION NOTE (Length: {len(conn_note)}/300 chars):")
            print(f"   {conn_note}")
            print("-" * 76)
            print(f"📌 2. {template_res.get('subject', 'MESSAGE')}:")
            print(template_res.get("body", ""))
            print("-" * 76)

            if not dry_run:
                entry = engine.crm.log_outreach(
                    recruiter_name=rec,
                    company=company,
                    target_role=role,
                    platform="LinkedIn",
                    message_type=t_type,
                    status="CONTACTED",
                    notes=notes or "Generated via naukariPro goal-5calls CLI",
                    message_content=template_res.get("body", "")
                )
                print(f"[✓] Logged outreach lead: {entry.get('lead_id')} to outreach_tracker.json & Excel.")
            else:
                print("[*] Dry-run mode: CRM entry not persisted.")
            print("=" * 76 + "\n")
            return 0
        else:
            # Batch generate for top 10 GCCs
            print("\n[*] Batch-generating recruiter pitches across top 10 GCC target companies...")
            pitches = engine.crm.batch_generate_gcc_outreach()
            print("\n" + "=" * 76)
            print(f"   TOP 10 GCC RECRUITER OUTREACH PITCHES GENERATED")
            print("=" * 76)
            for idx, p in enumerate(pitches, 1):
                lead = p["lead"]
                print(f"  {idx:2d}. {lead.get('company'):<22} | {lead.get('recruiter_name'):<32} | {lead.get('message_type')}")
                print(f"      Connection Note ({len(p['connection_note'])} chars): {p['connection_note']}")
            print("-" * 76)
            print(f"[✓] Synchronized {len(pitches)} leads into outreach_tracker.json & Recruiter_Outreach_Log.")
            print("=" * 76 + "\n")
            return 0

    # 4. Status / CRM Summary
    if status:
        leads = engine.crm.list_active_leads()
        summary = engine.crm.get_summary()
        print("\n" + "=" * 76)
        print("   RECRUITER OUTREACH CRM & ACTIVE PIPELINE STATUS")
        print("=" * 76)
        print(f"  • Total Leads Logged:        {summary.get('total_leads', 0)}")
        print(f"  • Outreaches Today:          {summary.get('today_outreaches', 0)}")
        print(f"  • Recruiter Calls Booked:    {summary.get('today_calls_scheduled', 0)}")
        print("  • Leads by Status:")
        for st, count in summary.get("by_status", {}).items():
            print(f"    - {st:<16}: {count}")
        print("-" * 76)
        if leads:
            print(f"  {'Lead ID':<18} {'Date':<17} {'Company':<20} {'Status':<16} {'Recruiter'}")
            print("-" * 76)
            for l in leads[-10:]:
                print(f"  {l.get('lead_id', 'N/A'):<18} {l.get('date', '')[:16]:<17} {l.get('company', '')[:18]:<20} {l.get('status', ''):<16} {l.get('recruiter_name', '')[:20]}")
            print("-" * 76)
        print("=" * 76 + "\n")
        return 0

    # 5. Default / Pacing Dashboard
    dashboard = engine.format_dashboard()
    print("\n" + dashboard + "\n")
    return 0

def handle_goal_5calls_interactive():
    """
    Interactive terminal controller for 5-Calls/Day Goal Pacing, Outreach Generator & CRM.
    """
    engine = Goal5CallsEngine()
    while True:
        print("\n" + "=" * 76)
        print("   🎯 5-CALLS/DAY RECRUITER OUTREACH & GOAL PACING CONTROL CENTER")
        print("   Candidate: Lavkush Kumar (₹20–25 LPA | 15-Day Notice | Azure Data Engineer)")
        print("=" * 76)
        print("  [1] View 5-Calls/Day Funnel Pacing & Diagnostic Report")
        print("  [2] Generate Recruiter Outreach Pitch (Custom or Top GCCs)")
        print("  [3] Execute Daily High-Impact Block (Block 1: Morning, 2: Afternoon, 3: Evening)")
        print("  [4] Update Recruiter Lead Status (CONTACTED -> CONNECTED -> CALL_SCHEDULED)")
        print("  [5] View Recruiter Outreach CRM Active Pipeline & Summary")
        print("  [B] Execute Autonomous Recruiter Connection Bot (Playwright Stealth)")
        print("  [0] Return to Main Menu")
        print("=" * 76)
        choice = input("Select an option [0-5, B]: ").strip()
        if choice == "1":
            print("\n" + engine.format_dashboard() + "\n")
        elif choice == "2":
            comp = input("\nEnter Company Name (leave blank for Top 10 GCC batch): ").strip()
            if comp:
                rec = input("Enter Recruiter Name (or leave blank for Hiring Team): ").strip() or "Hiring Team"
                role = input("Enter Target Role [default: Azure Data Engineer]: ").strip() or "Azure Data Engineer"
                print("\nMessage Types:")
                print("  [1] LinkedIn Connection Note (<= 300 chars)")
                print("  [2] Direct InMail / First Message")
                print("  [3] Tech Lead / Hiring Manager Pitch")
                print("  [4] 48-Hour Urgent Follow-Up")
                print("  [5] External Application Follow-Up")
                t_choice = input("Select message type [1-5, default 2]: ").strip() or "2"
                t_map = {"1": "note", "2": "inmail", "3": "tech-lead", "4": "followup", "5": "app-followup"}
                t_type = t_map.get(t_choice, "inmail")
                dry_in = input("Dry-run mode (do not log to CRM)? [Y/n]: ").strip().lower()
                is_dry = dry_in != "n"
                handle_goal_5calls(outreach=True, company=comp, recruiter=rec, role=role, msg_type=t_type, dry_run=is_dry)
            else:
                handle_goal_5calls(outreach=True)
        elif choice == "3":
            print("\nExecution Blocks:")
            print("  [1] Block 1 (09:00 - 11:00): Morning Resdex bump + 25 batch applications")
            print("  [2] Block 2 (14:00 - 16:00): 10 Top GCC InMail & Tech Lead pitches")
            print("  [3] Block 3 (18:00 - 20:00): Evening Resdex bump + 5 follow-ups + funnel audit")
            blk_in = input("Select block to execute [1-3]: ").strip()
            if blk_in in ["1", "2", "3"]:
                dry_in = input("Execute in dry-run mode? [Y/n]: ").strip().lower()
                is_dry = dry_in != "n"
                handle_goal_5calls(block=int(blk_in), dry_run=is_dry)
        elif choice == "4":
            ident = input("\nEnter Lead ID, Company, or Recruiter Name: ").strip()
            if ident:
                print("\nAvailable Statuses:")
                print("  [1] CONTACTED")
                print("  [2] CONNECTED")
                print("  [3] PITCH_SENT")
                print("  [4] CALL_SCHEDULED")
                print("  [5] REJECTED")
                st_in = input("Select new status [1-5]: ").strip()
                st_map = {"1": "CONTACTED", "2": "CONNECTED", "3": "PITCH_SENT", "4": "CALL_SCHEDULED", "5": "REJECTED"}
                st = st_map.get(st_in)
                if st:
                    notes = input("Enter notes (optional): ").strip()
                    handle_goal_5calls(update_status=st, lead_id=ident, notes=notes or None)
        elif choice == "5":
            handle_goal_5calls(status=True)
        elif choice.upper() == "B":
            print("\nAutonomous Recruiter Connection Bot Modes:")
            print("  [1] Batch Run: Top GCC Recruiters (Microsoft, Walmart, JPMorgan, etc.)")
            print("  [2] Single Recruiter Target (Custom Company & Recruiter Name / Profile URL)")
            bot_mode = input("Select outreach mode [1-2, default 1]: ").strip() or "1"

            comp = None
            rec = None
            prof_url = None
            if bot_mode == "2":
                comp = input("Enter Company Name: ").strip() or "Target Company"
                rec = input("Enter Recruiter Name: ").strip() or "Hiring Team"
                prof_url = input("Enter Direct Profile URL (optional, leave blank to search): ").strip() or None

            limit_in = input("Enter connection limit [1-8, default 5]: ").strip()
            limit_val = int(limit_in) if limit_in.isdigit() and 1 <= int(limit_in) <= 8 else 5

            dry_in = input("Run in Dry-Run simulation mode? [Y/n]: ").strip().lower()
            is_dry = dry_in != "n"

            headed_in = input("Run with visible browser window (headed)? [y/N]: ").strip().lower()
            is_headed = headed_in == "y"

            handle_goal_5calls(
                send_outreach=True,
                company=comp,
                recruiter=rec,
                profile_url=prof_url,
                limit=limit_val,
                dry_run=is_dry,
                headed=is_headed
            )
        elif choice == "0":
            break
        else:
            print("\n[!] Invalid choice. Please select from [0-5, B].")
        input("\nPress Enter to continue...")
    return 0


def handle_mutate(platform: str = "naukri", field: str = "headline", auto_bump: bool = False, dry_run: bool = False, headless: bool = True):
    from naukari_pro.modules.learning.mutator import ProfileMutator, CadenceScheduler
    mutator = ProfileMutator()
    can_kw = mutator.can_mutate(platform)
    print(f"\n[Controlled Profile Mutation Engine] Target: {platform.upper()} | Field: {field}")
    print(f"Weekly keyword mutation quota available: {can_kw}")
    if auto_bump:
        eligible, allow_kw, reason = CadenceScheduler.evaluate_mutation_eligibility(platform=platform)
        print(f"Cadence Schedule Status: {reason}")
    if dry_run:
        print("[DRY RUN] Simulation mode active. No live profile edits executed.")
        if platform == "naukri":
            prop = mutator.propose_naukri_mutation(field=field)
            print(f"Proposed Naukri Mutation:\n  Field: {prop.field.value}\n  New Value ({len(prop.new_value)} chars): {prop.new_value}\n  New Hash: {prop.new_hash}\n  Rationale: {prop.rationale}")
        elif platform == "linkedin":
            from naukari_pro.modules.learning.mutator import LinkedInTokenRotator
            rot = LinkedInTokenRotator()
            hl = rot.generate_rotated_headline()
            print(f"Proposed LinkedIn Rotated Headline ({len(hl)} chars):\n  {hl}")


def handle_label_outcomes(min_age_hours: float = 24.0, dry_run: bool = False, db_path: Optional[str] = None):
    from naukari_pro.modules.learning.outcome_labeler import label_unlabeled_outcomes, get_unlabeled_count
    print(f"\n[*] Running Daily Recruitment Outcome Labeler (min_age_hours={min_age_hours}, dry_run={dry_run})...")
    res = label_unlabeled_outcomes(min_age_hours=min_age_hours, dry_run=dry_run, db_path=db_path)
    print(f"[+] Scanned: {res['scanned']} | Labeled: {res['labeled']}")
    print(f"    Outcome Breakdown: {res['breakdown']}")
    unresolved_72h = get_unlabeled_count(hours=72.0, db_path=db_path)
    print(f"    SLA Check (>72h unlabeled count): {unresolved_72h} rows")
    return res


def handle_mine_keywords(limit: int = 10, claimable_only: bool = True, db_path: Optional[str] = None):
    from naukari_pro.modules.learning.keyword_miner import KeywordMiner
    print("\n[*] Mining Keyword Utility from Job Descriptions (U = Demand / Saturation)...")
    miner = KeywordMiner(db_path=db_path)
    miner.mine_and_store()
    top = miner.get_top_utility_keywords(limit=limit, claimable_only=claimable_only)
    print(f"[+] Top {len(top)} Keyword Utility Rankings (Claimable: {claimable_only}):")
    print(f"    {'TOKEN':<22} | {'UTILITY':<8} | {'DEMAND':<6} | {'SATURATION':<10} | {'CLAIMABLE'}")
    print("    " + "-" * 65)
    for k in top:
        print(f"    {k['token']:<22} | {k['utility_score']:<8.2f} | {k['demand_frequency']:<6} | {k['saturation_count']:<10} | {k['claimable']}")
    return top


def handle_attribution(mutation_week: Optional[str] = None, benchmark_control_delta: float = 0.0, db_path: Optional[str] = None):
    from naukari_pro.modules.learning.attribution import AttributionEngine
    print("\n[*] Evaluating Difference-in-Differences (DiD) Profile Mutation Attribution...")
    engine = AttributionEngine(db_path=db_path)
    history = engine.get_weekly_history()
    print(f"[+] Total weekly appearance records: {len(history)}")
    target_week = mutation_week or (history[-1]["week_start_date"] if history else "2026-10-15")
    res = engine.evaluate_mutation_impact(mutation_week=target_week, benchmark_control_delta=benchmark_control_delta)
    print(f"    Target Mutation Week: {target_week}")
    print(f"    DiD Net Estimate: {res['did_estimate']}")
    print(f"    Status: {res['status']}")
    print(f"    Causal Assertion Allowed: {res['causal_assertion_allowed']}")
    print(f"    Diagnostic Reason: {res['reason']}")
    return res


def handle_policy_status(db_path: Optional[str] = None):
    from naukari_pro.modules.learning.policy import LinUCBBanditPolicy, PolicyAction, extract_context_vector
    from naukari_pro.modules.learning.volume_guard import VolumeGuard
    from naukari_pro.modules.db import get_policy_state

    print("\n[*] Contextual Bandit LinUCB Selection Policy Status...")
    state = get_policy_state(db_path=db_path)
    vg = VolumeGuard(db_path=db_path)
    vol_stats = vg.get_volume_stats(db_path=db_path)
    decisions = vol_stats["decision_distribution"]

    policy = LinUCBBanditPolicy()
    bootstrapped = policy.bootstrap_from_history(db_path=db_path)
    effective_eps = policy.get_effective_epsilon(decisions_count=state.get("decisions_count", 0), db_path=db_path)

    print(f"[+] Policy Mode: {state.get('mode', 'ACTIVE')} | Policy Version: {policy.policy_version}")
    print(f"    Effective Epsilon (ε): {effective_eps:.4f} | Decisions to Date: {state.get('decisions_count', 0)}")
    sub_last = vol_stats.get("submission_last_7d_count", vol_stats.get("last_7d_count", 0))
    sub_prior = vol_stats.get("submission_prior_7d_count", vol_stats.get("prior_7d_count", 0))
    raw_last = vol_stats.get("raw_last_7d_count", vol_stats.get("last_7d_count", 0))
    raw_prior = vol_stats.get("raw_prior_7d_count", vol_stats.get("prior_7d_count", 0))
    print(f"    Volume Guard (7d): Submissions: Last 7d: {sub_last} | Prior 7d: {sub_prior} | Drop: {vol_stats['drop_pct']}% | Raw: Last 7d: {raw_last} | Prior 7d: {raw_prior}")
    print(f"    Decision Mix: APPLY={decisions.get('APPLY', 0)} | SKIP={decisions.get('SKIP', 0)} | DEFER={decisions.get('DEFER', 0)} | APPLY_FLOOR={decisions.get('APPLY_FLOOR', 0)} | DEFER_FLOOR={decisions.get('APPLY_FLOOR', 0)}")
    print(f"[+] Bootstrap from SQLite: {bootstrapped} historical outcome samples incorporated.")
    print(f"    Policy Version: {policy.policy_version} | Feature Dimension: {policy.d} | Exploration Alpha: {policy.alpha}")

    sample_job = {
        "match_score": 85.0,
        "required_yoe": 2.5,
        "posting_age_hours": 12.0,
        "company": "Microsoft",
        "platform": "1-Click Direct",
        "jd": "Databricks PySpark Delta Lake Kafka ADF SQL",
        "salary": 24.0
    }
    x_sample = extract_context_vector(sample_job)
    _, apply_payoff, _ = policy.predict_ucb(x_sample, PolicyAction.APPLY)
    print(f"    Historical Replay APPLY Expected Payoff: {apply_payoff:.4f} (Assert >= 0.0: {'PASS' if apply_payoff >= 0.0 else 'FAIL'})")
    assert apply_payoff >= 0.0, f"Replayed APPLY expected payoff {apply_payoff} must be >= 0.0"

    best_act, ucb, diag = policy.select_action(sample_job, db_path=db_path, explore=False)
    print(f"    Sample Action Prediction (Tier 1 Azure DE): {best_act.name} (UCB: {ucb:.4f})")
    for a_name, scores in diag.items():
        if isinstance(scores, dict) and "payoff" in scores:
            print(f"     * Action {a_name:<16}: payoff={scores['payoff']:.4f}, width={scores['width']:.4f}, ucb={scores['ucb']:.4f}")
    return policy


def handle_policy_arm(db_path: Optional[str] = None) -> bool:
    from naukari_pro.modules.learning.volume_guard import VolumeGuard
    vg = VolumeGuard(db_path=db_path)
    ok = vg.rearm_policy(db_path=db_path)
    if ok:
        print("\n[✓] Policy circuit breaker manually re-armed. Mode: ACTIVE (LinUCB contextual bandit)")
    return ok


def handle_monday_digest(output: Optional[str] = None, db_path: Optional[str] = None, send_email: bool = False):
    from naukari_pro.modules.learning.monday_digest import generate_monday_digest, send_monday_digest_email
    digest = generate_monday_digest(output_path=output, db_path=db_path)
    print(digest)
    if send_email:
        send_monday_digest_email(digest_content=digest)
    return digest


def handle_intent_apply(
    intent: str = "",
    roles: Optional[List[str]] = None,
    locations: Optional[List[str]] = None,
    platforms: Optional[List[str]] = None,
    min_score: Optional[float] = None,
    min_salary: Optional[float] = None,
    limit: Optional[int] = None,
    dry_run: bool = False,
    headless: bool = True
):
    """Executes intent-based multi-platform application workflow."""
    from naukari_pro.modules.intent_agent import IntentJobApplyAgent, IntentParser
    agent = IntentJobApplyAgent(dry_run=dry_run, headless=headless, min_score=min_score or 70.0)
    overrides: Dict[str, Any] = {}
    if roles:
        overrides["roles"] = roles
    if locations:
        overrides["locations"] = locations
    if platforms:
        overrides["platforms"] = platforms
    if min_score is not None:
        overrides["min_match_score"] = float(min_score)
    if min_salary is not None:
        overrides["min_salary_lpa"] = float(min_salary)
    if limit is not None:
        overrides["limit"] = int(limit)
    if dry_run is not None:
        overrides["dry_run"] = bool(dry_run)
    if headless is not None:
        overrides["headless"] = bool(headless)

    parsed_intent = IntentParser.parse(intent, **overrides)
    return agent.execute_intent(parsed_intent)


def handle_apply_intent(args: argparse.Namespace) -> int:
    """
    Controller executing intent-based autonomous application engine (Milestone 1).
    Parses CLI flags or intent configuration and delegates to AutonomousJobApplyAgent.
    """
    from naukari_pro.agent.parser import IntentParser
    from naukari_pro.agent.intent import CandidateIntent
    from naukari_pro.agent.orchestrator import AutonomousJobApplyAgent

    try:
        intent = IntentParser.from_args(args)
    except Exception as e:
        print(f"\n[!] Error parsing candidate intent: {e}")
        return 1

    print("\n" + "=" * 74)
    print("  🤖 NAUKARIPRO: AUTONOMOUS INTENT APPLICATION ENGINE (MILESTONE 1)")
    print(f"  Target Roles:      {', '.join(intent.target_roles)}")
    print(f"  Target Hubs:       {', '.join(intent.target_locations)}")
    print(f"  Target Platforms:  {', '.join(intent.platforms)}")
    print(f"  Salary Floor:      ₹{intent.min_salary_lpa} LPA (Max: {f'₹{intent.max_salary_lpa} LPA' if intent.max_salary_lpa else 'Uncapped'})")
    print(f"  Score Threshold:   >= {intent.strict_match_threshold}%")
    print(f"  Max Applications:  {intent.max_applications}")
    print(f"  Work Auth:         {intent.work_authorization} (Sponsorship: {'Required' if intent.requires_sponsorship else 'Not Required'})")
    print(f"  Execution Mode:    {'DRY-RUN (Simulated)' if intent.dry_run else 'LIVE SUBMISSION'}")
    print("=" * 74)

    try:
        agent = AutonomousJobApplyAgent(dry_run=intent.dry_run, headless=intent.headless)
        summary = agent.execute_intent(intent)
        print(summary.format_summary_report())
        print(f"\n[+] Execution complete. Dispatched: {summary.total_submitted} | Skipped: {summary.total_skipped}")
        return 0 if summary.status != "FAILED" else 1
    except Exception as err:
        print(f"\n[!] Intent execution failed: {err}")
        return 1


def handle_boost_visibility(
    day: int = 1,
    platform: str = "all",
    rotate_headline: bool = False,
    rotate_skills: bool = False,
    audit: bool = False,
    dry_run: bool = False,
    headless: bool = True
):
    """Executes 30-day algorithmic visibility growth engine step."""
    from naukari_pro.modules.visibility_growth import VisibilityGrowthEngine
    engine = VisibilityGrowthEngine(dry_run=dry_run, headless=headless)
    if audit:
        print("\n[*] Running 30-Day Recruiter SEO Keyword & Pacing Audit...")
        audit_res = engine.audit_profile_variations()
        for vname, vdata in audit_res.items():
            print(f"  • {vdata['name']}: Saturation Score: {vdata['saturation_score']}% | Tier 1: {vdata['tier1_coverage_pct']}%")
        telemetry = engine.get_telemetry_status()
        print(f"\n[*] Live Pacing Status: {telemetry['status']} | Daily Pace: {telemetry['daily_pace']:.1f} / {telemetry['daily_target']:.1f}")
        return audit_res

    return engine.execute_daily_visibility_boost(
        day=day,
        platform=platform,
        rotate_headline=rotate_headline,
        rotate_skills=rotate_skills,
        dry_run=dry_run,
        headless=headless
    )


def handle_audit_fields(job_id: Optional[str] = None, recent: int = 5, platform: Optional[str] = None, db_path: Optional[str] = None):
    """
    Displays the exhaustive step-by-step and field-by-field audit trail
    of filled application inputs with zero human intervention.
    """
    from naukari_pro.modules.db import get_application_field_audit, get_recent_field_audits, DB_PATH
    from collections import defaultdict
    t_path = db_path or DB_PATH
    print("\n" + "=" * 78)
    print("  📋 DETAILED APPLICATION STEP & FIELD AUDIT LEDGER")
    print("=" * 78)

    if job_id:
        records = get_application_field_audit(job_id=job_id, db_path=t_path)
        if not records:
            print(f"  [!] No field audit records found for Job ID: {job_id}")
            return
        print(f"  Target Job ID: {job_id} | Total Recorded Field Interactions: {len(records)}\n")
        print(f"  {'Step':<6} | {'Step Name':<18} | {'Field Label / Prompt':<28} | {'Type':<8} | {'Value Filled':<24} | {'Action':<10}")
        print("  " + "-" * 102)
        for r in records:
            s_num = str(r.get("step_number", 1))
            s_name = str(r.get("step_name", "FORM"))[:17]
            f_lbl = str(r.get("field_label", ""))[:27]
            f_type = str(r.get("field_type", "text"))[:7]
            f_val = str(r.get("field_value", ""))[:23]
            act = str(r.get("action_type", "FILLED"))[:9]
            print(f"  {s_num:<6} | {s_name:<18} | {f_lbl:<28} | {f_type:<8} | {f_val:<24} | {act:<10}")
    else:
        records = get_recent_field_audits(limit=recent * 20, platform=platform, db_path=t_path)
        if not records:
            print(f"  [!] No recent field audit records found in SQLite DB.")
            return
        grouped = defaultdict(list)
        for r in records:
            grouped[r.get("job_id")].append(r)

        print(f"  Showing {min(len(grouped), recent)} Most Recent Applications Audited:\n")
        shown = 0
        for jid, items in list(grouped.items())[:recent]:
            shown += 1
            first = items[0]
            co = first.get("company", "Company")
            title = first.get("title", "Role")
            plat = first.get("platform", "Platform")
            rec_at = first.get("recorded_at", "")
            print(f"  [{shown}] {title} @ {co} ({plat}) — Job ID: {jid} ({rec_at})")
            print(f"      {'Step':<5} | {'Step Name':<16} | {'Field Label':<26} | {'Type':<8} | {'Value Filled':<24} | {'Action':<9}")
            print("      " + "-" * 96)
            for item in items:
                s_num = str(item.get("step_number", 1))
                s_name = str(item.get("step_name", "FORM"))[:15]
                f_lbl = str(item.get("field_label", ""))[:25]
                f_type = str(item.get("field_type", "text"))[:7]
                f_val = str(item.get("field_value", ""))[:23]
                act = str(item.get("action_type", "FILLED"))[:8]
                print(f"      {s_num:<5} | {s_name:<16} | {f_lbl:<26} | {f_type:<8} | {f_val:<24} | {act:<9}")
            print()

    print("=" * 78)


def interactive_loop():
    while True:
        print_menu()
        choice = input("Select an option [0-9, P, W, E, M, S, C, D, G, A, V, L, K, O]: ").strip().upper()
        if choice == "P":
            handle_pro()
        elif choice == "W":
            handle_weekly_report()
        elif choice == "E":
            handle_performance()
        elif choice == "G":
            handle_agy_schedule("status")
        elif choice == "1":
            handle_auto_apply()
        elif choice == "2":
            handle_alerts()
        elif choice == "3":
            handle_profile()
        elif choice == "4":
            handle_hidden_jobs()
        elif choice == "5":
            handle_resume_maker()
        elif choice == "6":
            handle_interview_prep()
        elif choice == "M":
            handle_interview_prep(mock=True)
        elif choice == "7":
            handle_skill_insights()
        elif choice == "8":
            handle_hiring_trends()
        elif choice == "9":
            handle_early_access()
        elif choice == "S":
            handle_multi_search()
        elif choice == "C":
            handle_portal_apply()
        elif choice == "D":
            handle_daily_cycle()
        elif choice == "A":
            handle_auth()
        elif choice in ("L-IN", "LIN"):
            handle_linkedin_auth()
        elif choice == "V":
            handle_linkedin_verify(headless=True)
        elif choice == "L":
            handle_linkedin_apply(dry_run=True)
        elif choice == "K":
            handle_linkedin_seo()
        elif choice == "O":
            handle_goal_5calls_interactive()
        elif choice == "0":
            print("\nExiting naukariPro. Good luck with your ₹25 LPA goal!\n")
            break
        else:
            print("\nInvalid choice. Please select from the menu.")
        input("\nPress Enter to return to main menu...")

def main():
    common_parser = argparse.ArgumentParser(add_help=False)
    common_parser.add_argument("--headless", action="store_true", help="Run browser in background")
    common_parser.add_argument("--limit", type=int, default=20, help="Max daily applications")
    common_parser.add_argument("--dry-run", action="store_true", help="Simulate job matches, answers, and tracker logging without submitting live applications")

    parser = argparse.ArgumentParser(description="naukariPro Career Suite", parents=[common_parser])
    subparsers = parser.add_subparsers(dest="command")
    pro_parser = subparsers.add_parser("pro", help="Run Complete All-in-One Pro Autonomous Pipeline", parents=[common_parser])
    pro_parser.add_argument("--force", action="store_true", help="Force profile sync and bump even if already updated today")
    pro_parser.add_argument("--block", type=int, choices=[1, 2, 3], default=None, help="Beast time block: 1 morning, 2 afternoon outreach, 3 evening follow-ups")
    pro_parser.add_argument("--live-outreach", action="store_true", default=False, help="Send LinkedIn outreach live (Mac/residential only)")
    pro_parser.add_argument("--limit-naukri", type=int, default=None, help="Naukri apply target per cycle (default: 20)")
    pro_parser.add_argument("--limit-linkedin", type=int, default=None, help="LinkedIn Easy Apply target per cycle (default: 20)")
    pro_parser.add_argument("--limit-external", type=int, default=None, help="External ATS apply target per cycle (default: 20)")
    pro_parser.add_argument("--limit-redirects", type=int, default=None, help="External redirects target per cycle (default: 20)")

    for cmd, hlp in [
        ("weekly-report", "Run weekly 5-number recruiter performance & keyword diff audit"),
        ("performance", "Inspect Server-Side Entitlements & Profile Analytics"),
        ("auto-apply", "Auto-Apply to target vacancies"),
        ("dry-run", "Execute offline dry-run simulation across multi-channel and 1-click apply"),
        ("alerts", "Scan instant hot alerts"),
        ("hidden-jobs", "Discover hidden/off-market jobs"),
        ("early-access", "Scan early access roles and NVites"),
        ("search-all", "Search across Naukri, LinkedIn, and Hacker News Who's Hiring"),
        ("multi-search", "Search across Naukri, LinkedIn, and Hacker News Who's Hiring"),
        ("skill-insights", "In-demand skills intelligence"),
        ("hiring-trends", "Salary & GCC hiring report"),
        ("auth", "Authenticate session"),
        ("menu", "Launch interactive menu"),
    ]:
        subparsers.add_parser(cmd, help=hlp, parents=[common_parser])

    bump_parser = subparsers.add_parser("bump", help="Bump profile to Today (Once-a-day throttle)", parents=[common_parser])
    bump_parser.add_argument("--force", action="store_true", help="Force profile bump even if already touched today")

    daily_parser = subparsers.add_parser("daily", help="Run full daily autonomous cycle", parents=[common_parser])
    daily_parser.add_argument("--force", action="store_true", help="Force profile bump even if already touched today")

    prep_parser = subparsers.add_parser("interview-prep", help="Interview prep master bank and mock evaluator", parents=[common_parser])
    prep_parser.add_argument("--mock", action="store_true", help="Launch interactive AI mock interview evaluator with scoring")

    resume_parser = subparsers.add_parser("resume-maker", help="Generate ATS Resume PDF & Quality Scorecard (Supports --jd tailoring)", parents=[common_parser])
    resume_parser.add_argument("--jd", type=str, help="Path to target Job Description text file or raw JD string for tailoring")

    portal_parser = subparsers.add_parser("portal-apply", help="Auto-fill external career portal application (Greenhouse, Ashby, Lever, Workday)", parents=[common_parser])
    portal_parser.add_argument("--url", default=None, nargs="?", help="Job application URL")
    portal_parser.add_argument("--company", default="Company", help="Company name")
    portal_parser.add_argument("--role", default="Azure Data Engineer", help="Role title")
    portal_parser.add_argument("--jd", default="", help="Target job description or keywords")
    portal_parser.add_argument("--batch", action="store_true", default=False, help="Batch process eligible external redirects from tracker")
    portal_parser.add_argument("--external-batch", "--live-batch", dest="external_batch", action="store_true", default=False, help="Run live multi-ATS external batch runner")
    portal_parser.add_argument("--ats", default=None, help="Comma-separated target ATS list (e.g. greenhouse,ashby,lever,workday)")
    portal_parser.add_argument("--remote-first", action="store_true", default=True, help="Prioritize Remote vacancies first (default: True)")

    ext_batch_parser = subparsers.add_parser("external-batch", help="Autonomous Batch Execution for External ATS Portals (Greenhouse, Ashby, Lever, Workday)", parents=[common_parser])
    ext_batch_parser.add_argument("--remote-first", action="store_true", default=True, help="Prioritize Remote vacancies first (default: True)")
    ext_batch_parser.add_argument("--ats", default=None, help="Comma-separated target ATS list (e.g. greenhouse,ashby,lever,workday)")
    ext_batch_parser.add_argument("--role", "--roles", dest="role", default=None, help="Filter by role(s), comma-separated")
    ext_batch_parser.add_argument("--location", "--locations", dest="location", default=None, help="Filter by location(s), comma-separated")
    ext_batch_parser.set_defaults(limit=25)

    sched_parser = subparsers.add_parser("agy-schedule", help="Manage Linux AGY Autonomous Scheduler (systemd timer + agy CLI)", parents=[common_parser])
    sched_parser.add_argument("action", nargs="?", default="status", choices=["install", "run", "status", "logs"], help="Action to perform: install | run | status | logs")

    auth_li_parser = subparsers.add_parser("linkedin-auth", help="Interactive LinkedIn login & cookie synchronization", parents=[common_parser])
    auth_li_parser.add_argument("--timeout", type=int, default=300, help="Timeout in seconds to complete login (default: 300)")

    verify_parser = subparsers.add_parser("linkedin-verify", help="Validate LinkedIn session freshness & extract candidate identity", parents=[common_parser])
    verify_parser.add_argument("--headed", action="store_true", default=False, help="Run browser in visible GUI mode (default: headless)")
    verify_parser.add_argument("--set-token", type=str, default=None, help="Directly update LINKEDIN_LI_AT cookie token in .env and verify")
    verify_parser.add_argument("--set-jsessionid", type=str, default=None, help="Optionally update LINKEDIN_JSESSIONID in .env")
    verify_parser.add_argument("--login", action="store_true", default=False, help="Launch interactive browser login if session is expired")

    apply_parser = subparsers.add_parser("linkedin-apply", help="Run autonomous LinkedIn Easy Apply engine across target vacancies", parents=[common_parser])
    apply_parser.add_argument("--headed", action="store_true", default=False, help="Run browser in visible GUI mode (default: headless)")
    apply_parser.add_argument("--min-score", type=float, default=70.0, help="Minimum job match score cutoff (default: 70.0)")
    apply_parser.add_argument("--keyword", "--keywords", dest="keyword", type=str, default=None, help="Override search keyword(s), comma-separated (e.g. 'Azure Data Engineer,Databricks')")
    apply_parser.add_argument("--location", "--locations", dest="location", type=str, default=None, help="Override search location(s), comma-separated (e.g. 'Bengaluru,Hyderabad')")
    apply_parser.set_defaults(limit=25)

    seo_parser = subparsers.add_parser("linkedin-seo", help="Audit and export LinkedIn 100k+ Recruiter Search SEO blueprint", parents=[common_parser])
    seo_parser.add_argument("--output", type=str, default=None, help="Custom export path for the markdown blueprint")

    optimize_parser = subparsers.add_parser("linkedin-optimize", help="Alias for linkedin-seo", parents=[common_parser])
    optimize_parser.add_argument("--output", type=str, default=None, help="Custom export path for the markdown blueprint")

    goal_parser = subparsers.add_parser("goal-5calls", help="5-Calls/Day Recruiter Outreach & Goal Achievement Engine", parents=[common_parser])
    goal_parser.add_argument("--interactive", action="store_true", help="Launch interactive 5-calls/day console")
    goal_parser.add_argument("--send-outreach", action="store_true", help="Execute Autonomous LinkedIn Recruiter Connection Bot (Playwright Stealth)")
    goal_parser.add_argument("--headed", action="store_true", default=False, help="Run browser in visible GUI mode (default: headless)")
    goal_parser.add_argument("--profile-url", type=str, default=None, help="Direct LinkedIn profile URL to send connection request to")
    goal_parser.add_argument("--note", type=str, default=None, help="Custom connection note (<= 300 characters)")
    goal_parser.add_argument("--outreach", action="store_true", help="Generate and log recruiter outreach pitch(es)")
    goal_parser.add_argument("--pacing", action="store_true", help="Display 5-calls/day funnel pacing & diagnostic report")
    goal_parser.add_argument("--status", action="store_true", help="Show outreach CRM active leads and funnel status")
    goal_parser.add_argument("--block", type=int, choices=[1, 2, 3], help="Execute daily high-impact block: 1 (Morning), 2 (Afternoon), 3 (Evening)")
    goal_parser.add_argument("--company", type=str, default=None, help="Target company name for outreach pitch")
    goal_parser.add_argument("--recruiter", type=str, default=None, help="Recruiter or Engineering Lead name")
    goal_parser.add_argument("--role", type=str, default="Azure Data Engineer", help="Target role title")
    goal_parser.add_argument("--type", type=str, default=None, dest="msg_type", choices=["note", "inmail", "tech-lead", "followup", "app-followup"], help="Message template type to generate")
    goal_parser.add_argument("--update-status", type=str, default=None, choices=["CONTACTED", "CONNECTED", "PITCH_SENT", "CALL_SCHEDULED", "REJECTED"], help="Update lead status in CRM")
    goal_parser.add_argument("--lead-id", type=str, default=None, help="Lead ID or recruiter identifier to update")
    goal_parser.add_argument("--notes", type=str, default=None, help="Optional notes for status update or lead logging")

    mutate_parser = subparsers.add_parser("mutate", help="Controlled profile mutation engine (Naukri & LinkedIn)", parents=[common_parser])
    mutate_parser.add_argument("--platform", type=str, default="naukri", choices=["naukri", "linkedin"], help="Platform to mutate")
    mutate_parser.add_argument("--field", type=str, default="headline", help="Field to mutate (headline, key_skills, summary, about)")
    mutate_parser.add_argument("--auto-bump", action="store_true", help="Execute scheduled cadence bump or keyword mutation")

    label_parser = subparsers.add_parser("label-outcomes", help="Run daily outcome labeling on applied jobs", parents=[common_parser])
    label_parser.add_argument("--min-age-hours", type=float, default=24.0, help="Minimum age in hours to label outcomes (default: 24.0)")

    mine_parser = subparsers.add_parser("mine-keywords", help="Mine keyword and skill utility (U = Demand / Saturation)", parents=[common_parser])
    mine_parser.set_defaults(limit=10)
    mine_parser.add_argument("--all", dest="claimable_only", action="store_false", default=True, help="Include unclaimable/forbidden keywords")

    attr_parser = subparsers.add_parser("attribution", help="Compute Difference-in-Differences profile mutation impact", parents=[common_parser])
    attr_parser.add_argument("--mutation-week", type=str, default=None, help="Target mutation week start date (YYYY-MM-DD)")
    attr_parser.add_argument("--control-delta", type=float, default=0.0, help="Benchmark control delta")

    subparsers.add_parser("policy-status", help="Inspect LinUCB contextual bandit parameters and predictions", parents=[common_parser])
    subparsers.add_parser("policy-arm", help="Manually re-arm policy circuit breaker to ACTIVE mode", parents=[common_parser])

    digest_parser = subparsers.add_parser("monday-digest", help="Generate consolidated weekly Monday digest markdown report", parents=[common_parser])
    digest_parser.add_argument("--output", "-o", type=str, default=None, help="Output markdown path")
    digest_parser.add_argument("--send-email", action="store_true", default=False, help="Send digest email via Gmail SMTP")

    subparsers.add_parser("mail-test", help="Test Gmail IMAP connection for ATS verification links", parents=[common_parser])

    intent_parser = subparsers.add_parser("intent-apply", help="Autonomous Intent-Based Job Apply Agent (Naukri, LinkedIn, Greenhouse, Lever, Ashby, Workday)", parents=[common_parser])
    intent_parser.add_argument("--intent", "-i", type=str, default="", help="Natural-language application intent description")
    intent_parser.add_argument("--roles", nargs="+", default=None, help="Target roles (e.g. 'Azure Data Engineer' 'Databricks Engineer')")
    intent_parser.add_argument("--locations", nargs="+", default=None, help="Target locations (e.g. Bengaluru Hyderabad Remote)")
    intent_parser.add_argument("--platforms", nargs="+", default=None, help="Target platforms (e.g. linkedin naukri greenhouse lever workday)")
    intent_parser.add_argument("--min-score", type=float, default=None, help="Minimum match score threshold (default: 70.0)")
    intent_parser.add_argument("--min-salary", type=float, default=20.0, help="Minimum salary in LPA (default: 20.0)")

    apply_intent_parser = subparsers.add_parser(
        "apply-intent",
        help="Autonomous Intent-Based Application Orchestration Engine (Milestone 1)",
        parents=[common_parser]
    )
    apply_intent_parser.add_argument("--intent", "-i", type=str, default="", help="Natural-language application intent description")
    apply_intent_parser.add_argument("--roles", nargs="+", default=None, help="Target roles (e.g. 'MLOps Engineer' 'ML Platform Engineer')")
    apply_intent_parser.add_argument("--locations", nargs="+", default=None, help="Target locations (e.g. Bengaluru Pune Hyderabad Remote)")
    apply_intent_parser.add_argument("--platforms", nargs="+", default=None, help="Target platforms (e.g. naukri linkedin workday greenhouse lever)")
    apply_intent_parser.add_argument("--min-salary", "--min-salary-lpa", type=float, default=20.0, dest="min_salary_lpa", help="Minimum expected CTC in LPA (default: 20.0)")
    apply_intent_parser.add_argument("--max-salary", "--max-salary-lpa", type=float, default=None, dest="max_salary_lpa", help="Maximum salary bound in LPA")
    apply_intent_parser.add_argument("--threshold", "--min-score", type=float, default=70.0, dest="strict_match_threshold", help="Strict match score threshold cutoff (default: 70.0)")
    apply_intent_parser.add_argument("--config", "--intent-file", type=str, default=None, dest="config_path", help="Path to JSON file containing CandidateIntent definition")
    apply_intent_parser.add_argument("--work-auth", type=str, default="India", dest="work_authorization", help="Work authorization status (default: India)")
    apply_intent_parser.add_argument("--requires-sponsorship", action="store_true", default=False, help="Flag if visa sponsorship is required")
    apply_intent_parser.add_argument("--headed", action="store_true", default=False, help="Run browser in visible mode (default: headless)")

    boost_parser = subparsers.add_parser("boost-visibility", help="30-day algorithmic growth engine scaling profile impressions to 100K+ across Naukri and LinkedIn", parents=[common_parser])
    boost_parser.add_argument("--day", "-d", type=int, default=1, help="Day number in 30-day roadmap (1-30, default: 1)")
    boost_parser.add_argument("--platform", "-p", type=str, default="all", choices=["all", "naukri", "linkedin"], help="Target platform (all, naukri, linkedin)")
    boost_parser.add_argument("--rotate-headline", action="store_true", help="Trigger algorithmic headline variation rotation")
    boost_parser.add_argument("--rotate-skills", action="store_true", help="Trigger secondary skill rotation")
    boost_parser.add_argument("--audit", action="store_true", help="Audit variations and show 100K pacing scorecard")

    audit_parser = subparsers.add_parser("audit-fields", help="Inspect step-by-step and field-by-field audit logs for applications", parents=[common_parser])
    audit_parser.add_argument("--job-id", type=str, default=None, help="Filter audit records by specific job ID")
    audit_parser.add_argument("--recent", type=int, default=5, help="Number of recent applications to show (default: 5)")
    audit_parser.add_argument("--platform", type=str, default=None, help="Filter by platform (e.g. linkedin, career_portal, naukri)")

    ingest_parser = subparsers.add_parser(
        "ingest-jobs",
        help="WS1: seed ATS sources and run aggregation ingest (honest NormalizedJob fields)",
        parents=[common_parser],
    )
    ingest_parser.add_argument("--limit-sources", type=int, default=None, help="Cap number of boards this cycle")
    ingest_parser.add_argument("--no-seed", action="store_true", help="Skip reseeding sources.json")
    ingest_parser.add_argument("--db", type=str, default=None, help="Optional aggregation SQLite path")

    boards_parser = subparsers.add_parser(
        "boards-import",
        help="M2: import config/boards.csv registry into aggregation sources",
        parents=[common_parser],
    )
    boards_parser.add_argument("--csv", type=str, default=None, help="Path to boards.csv")
    boards_parser.add_argument("--db", type=str, default=None, help="Optional aggregation SQLite path")

    llm_parser = subparsers.add_parser(
        "llm-status",
        help="M1/WS2: show AI gateway providers, task routes, spend ledger, and cache mode",
        parents=[common_parser],
    )
    llm_parser.add_argument("--mode", type=str, default=None, help="Override NAUKARI_LLM_MODE")

    mcp_parser = subparsers.add_parser(
        "mcp",
        help="M1: run NaukariPro MCP server (stdio) or localhost HTTP bridge",
        parents=[common_parser],
    )
    mcp_parser.add_argument("--http", action="store_true", help="Serve HTTP on 127.0.0.1 (default port 7432)")
    mcp_parser.add_argument("--port", type=int, default=7432, help="HTTP port when --http is set")
    mcp_parser.add_argument("--list-tools", action="store_true", help="Print tool schemas and exit")

    api_parser = subparsers.add_parser(
        "api-serve",
        help="M1: OpenAPI REST mirror of MCP tools (FastAPI /docs)",
        parents=[common_parser],
    )
    api_parser.add_argument("--host", type=str, default="127.0.0.1")
    api_parser.add_argument("--port", type=int, default=8000)

    match_parser = subparsers.add_parser(
        "match-eval",
        help="WS3: run golden-set matching benchmark (recall/precision/cost)",
        parents=[common_parser],
    )
    match_parser.add_argument("--use-llm", action="store_true", help="Use LLM Stage B/C (default: deterministic offline)")
    match_parser.add_argument("--expand", type=int, default=100, help="Golden set size (default 100)")
    match_parser.add_argument("--report", type=str, default=None, help="Write markdown report path")

    rgen_parser = subparsers.add_parser(
        "resume-gen",
        help="WS4: truth-preserving tailored resume (PDF) with ATS score gate >=85",
        parents=[common_parser],
    )
    rgen_parser.add_argument("--role", type=str, default="Azure Data Engineer")
    rgen_parser.add_argument("--company", type=str, default="Target")
    rgen_parser.add_argument("--out", type=str, default=None, help="Output directory")
    rgen_parser.add_argument("--jd-keywords", type=str, default="Python,Azure,Databricks,SQL,Delta Lake")

    ats_parser = subparsers.add_parser(
        "ats-score",
        help="M4: ATS keyword score {score, matched_keywords, missing_keywords}",
        parents=[common_parser],
    )
    ats_parser.add_argument("resume", type=str, help="Resume PDF or text file")
    ats_parser.add_argument("--jd", type=str, required=True, help="Job description text file")

    e2e_parser = subparsers.add_parser(
        "e2e-demo",
        help="M5/§9: offline dry-run pipeline demo (score→tailor→ground→fill→approval gate)",
        parents=[common_parser],
    )
    e2e_parser.add_argument("--submit", action="store_true", help="Attempt submit (still requires --approval-token)")
    e2e_parser.add_argument("--approval-token", type=str, default=None)

    bridge_parser = subparsers.add_parser(
        "browser-bridge",
        help="M1/§4.2: localhost browser-extension bridge (default :7433)",
        parents=[common_parser],
    )
    bridge_parser.add_argument("--port", type=int, default=7433)

    gov_parser = subparsers.add_parser(
        "governed-apply",
        help="WS5: dry-run governed auto-apply (field audit, zero submissions by default)",
        parents=[common_parser],
    )
    gov_parser.add_argument("--url", type=str, default="https://boards.greenhouse.io/example/jobs/1")
    gov_parser.add_argument("--fit", type=float, default=85.0)
    gov_parser.add_argument("--coverage", type=float, default=75.0)
    gov_parser.add_argument("--auto-submit", action="store_true", help="Allow submit when thresholds met (still needs confirmation)")

    track_parser = subparsers.add_parser(
        "track-dashboard",
        help="WS6: print tracking funnel HTML snapshot or run FastAPI server",
        parents=[common_parser],
    )
    track_parser.add_argument("--serve", action="store_true", help="Run uvicorn on :8765")
    track_parser.add_argument("--digest", action="store_true", help="Print weekly digest")

    args = parser.parse_args()

    if args.command == "intent-apply":
        handle_intent_apply(
            intent=getattr(args, "intent", ""),
            roles=getattr(args, "roles", None),
            locations=getattr(args, "locations", None),
            platforms=getattr(args, "platforms", None),
            min_score=getattr(args, "min_score", None),
            min_salary=getattr(args, "min_salary", None),
            limit=getattr(args, "limit", None),
            dry_run=args.dry_run,
            headless=args.headless
        )
    elif args.command == "apply-intent":
        exit_code = handle_apply_intent(args)
        sys.exit(exit_code or 0)
    elif args.command == "boost-visibility":
        handle_boost_visibility(
            day=getattr(args, "day", 1),
            platform=getattr(args, "platform", "all"),
            rotate_headline=getattr(args, "rotate_headline", False),
            rotate_skills=getattr(args, "rotate_skills", False),
            audit=getattr(args, "audit", False),
            dry_run=args.dry_run,
            headless=args.headless
        )
    elif args.command == "mutate":
        handle_mutate(
            platform=getattr(args, "platform", "naukri"),
            field=getattr(args, "field", "headline"),
            auto_bump=getattr(args, "auto_bump", False),
            dry_run=args.dry_run,
            headless=args.headless
        )
    elif args.command == "label-outcomes":
        handle_label_outcomes(min_age_hours=getattr(args, "min_age_hours", 24.0), dry_run=args.dry_run)
    elif args.command == "mine-keywords":
        handle_mine_keywords(limit=getattr(args, "limit", 10), claimable_only=getattr(args, "claimable_only", True))
    elif args.command == "attribution":
        handle_attribution(mutation_week=getattr(args, "mutation_week", None), benchmark_control_delta=getattr(args, "control_delta", 0.0))
    elif args.command == "policy-status":
        handle_policy_status()
    elif args.command == "policy-arm":
        handle_policy_arm()
    elif args.command == "monday-digest":
        handle_monday_digest(output=getattr(args, "output", None), send_email=getattr(args, "send_email", False))
    elif args.command == "mail-test":
        sys.exit(handle_mail_test())
    elif args.command == "pro":
        pro_kwargs = {
            "limit": args.limit,
            "headless": args.headless,
            "dry_run": args.dry_run,
            "force": getattr(args, "force", False),
            "block": getattr(args, "block", None),
            "execute_outreach_live": getattr(args, "live_outreach", False),
        }
        for attr in ("limit_naukri", "limit_linkedin", "limit_external", "limit_redirects"):
            val = getattr(args, attr, None)
            if val is not None:
                pro_kwargs[attr] = val
        handle_pro(**pro_kwargs)
    elif args.command == "weekly-report":
        handle_weekly_report(headless=args.headless)
    elif args.command == "performance":
        handle_performance(headless=args.headless)
    elif args.command == "agy-schedule":
        handle_agy_schedule(action=args.action)
    elif args.command == "auto-apply":
        handle_auto_apply(headless=args.headless, limit=args.limit, dry_run=args.dry_run)
    elif args.command == "dry-run":
        handle_auto_apply(headless=args.headless, limit=args.limit, dry_run=True)
    elif args.command == "alerts":
        handle_alerts(headless=args.headless)
    elif args.command == "bump":
        handle_profile(headless=args.headless, force=getattr(args, "force", False))
    elif args.command == "hidden-jobs":
        handle_hidden_jobs(headless=args.headless)
    elif args.command == "early-access":
        handle_early_access(headless=args.headless)
    elif args.command in ("search-all", "multi-search"):
        handle_multi_search(dry_run=args.dry_run)
    elif args.command == "resume-maker":
        handle_resume_maker(jd=args.jd)
    elif args.command == "interview-prep":
        handle_interview_prep(mock=getattr(args, "mock", False))
    elif args.command == "skill-insights":
        handle_skill_insights(headless=args.headless)
    elif args.command == "hiring-trends":
        handle_hiring_trends(headless=args.headless)
    elif args.command == "daily":
        handle_daily_cycle(headless=args.headless, dry_run=args.dry_run, force=getattr(args, "force", False), limit=getattr(args, "limit", 20))
    elif args.command == "portal-apply":
        if getattr(args, "external_batch", False):
            handle_external_batch(
                limit=getattr(args, "limit", 25),
                headless=args.headless,
                dry_run=args.dry_run,
                ats=getattr(args, "ats", None),
                remote_first=getattr(args, "remote_first", True),
                roles=getattr(args, "role", None),
                locations=getattr(args, "location", None)
            )
        else:
            handle_portal_apply(
                url=args.url,
                company=args.company,
                role=args.role,
                jd=getattr(args, "jd", ""),
                headless=args.headless,
                dry_run=args.dry_run,
                batch=getattr(args, "batch", False),
                limit=getattr(args, "limit", 10)
            )
    elif args.command == "external-batch":
        handle_external_batch(
            limit=getattr(args, "limit", 25),
            headless=args.headless,
            dry_run=args.dry_run,
            ats=getattr(args, "ats", None),
            remote_first=getattr(args, "remote_first", True),
            roles=getattr(args, "role", None),
            locations=getattr(args, "location", None)
        )
    elif args.command == "auth":
        handle_auth()
    elif args.command == "linkedin-auth":
        exit_code = handle_linkedin_auth(timeout=getattr(args, "timeout", 300), headless=args.headless)
        sys.exit(exit_code)
    elif args.command == "linkedin-verify":
        is_headless = not getattr(args, "headed", False)
        exit_code = handle_linkedin_verify(args, headless=is_headless)
        sys.exit(exit_code)
    elif args.command == "linkedin-apply":
        exit_code = handle_linkedin_apply(args)
        sys.exit(exit_code)
    elif args.command in ("linkedin-seo", "linkedin-optimize"):
        exit_code = handle_linkedin_seo(args)
        sys.exit(exit_code)
    elif args.command in ("goal-5calls", "goal", "outreach"):
        exit_code = handle_goal_5calls(args=args)
        if exit_code:
            sys.exit(exit_code)
    elif args.command == "audit-fields":
        handle_audit_fields(
            job_id=getattr(args, "job_id", None),
            recent=getattr(args, "recent", 5),
            platform=getattr(args, "platform", None)
        )
    elif args.command == "ingest-jobs":
        sys.exit(handle_ingest_jobs(args))
    elif args.command == "boards-import":
        sys.exit(handle_boards_import(args))
    elif args.command == "llm-status":
        sys.exit(handle_llm_status(args))
    elif args.command == "mcp":
        sys.exit(handle_mcp(args))
    elif args.command == "api-serve":
        sys.exit(handle_api_serve(args))
    elif args.command == "match-eval":
        sys.exit(handle_match_eval(args))
    elif args.command == "resume-gen":
        sys.exit(handle_resume_gen(args))
    elif args.command == "ats-score":
        sys.exit(handle_ats_score(args))
    elif args.command == "e2e-demo":
        sys.exit(handle_e2e_demo(args))
    elif args.command == "browser-bridge":
        sys.exit(handle_browser_bridge(args))
    elif args.command == "governed-apply":
        sys.exit(handle_governed_apply(args))
    elif args.command == "track-dashboard":
        sys.exit(handle_track_dashboard(args))
    else:
        interactive_loop()

if __name__ == "__main__":
    main()
