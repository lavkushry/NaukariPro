"""
Governed apply pipeline.
- AUTO_APPLY only when fit>=80 AND coverage>=70 AND user enabled AUTO_SUBMIT
- dry_run fills + audits but never submits
- live submit only after confirmation detector fires
"""

from __future__ import annotations

import os
import random
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from naukari_pro.governed_apply.answers import answer_from_facts
from naukari_pro.governed_apply.approval import ApprovalQueue
from naukari_pro.governed_apply.attention import AttentionQueue, BlockerClass, detect_blocker
from naukari_pro.governed_apply.confirmation import detect_submission_confirmation
from naukari_pro.governed_apply.field_inventory import inventory_from_dom_snapshot
from naukari_pro.governed_apply.sensitivity import mask_for_log


AUTO_FIT = 80.0
AUTO_COVERAGE = 70.0
PER_BOARD_DAILY_CAP = 15


@dataclass
class GovernedResult:
    job_url: str
    status: str  # filled | applied | blocked | skipped | needs_approval | quarantined
    field_audits: int = 0
    submitted: bool = False
    confirmation: Optional[str] = None
    blockers: List[str] = field(default_factory=list)
    ask_user: List[str] = field(default_factory=list)


class GovernedApplyPipeline:
    def __init__(
        self,
        candidate_facts: Dict[str, Any],
        *,
        dry_run: bool = True,
        auto_submit: Optional[bool] = None,
        store: Optional[ApprovalQueue] = None,
        db_path: Optional[Path] = None,
    ) -> None:
        self.facts = candidate_facts
        self.dry_run = dry_run
        self.auto_submit = (
            bool(auto_submit)
            if auto_submit is not None
            else os.environ.get("NAUKARI_AUTO_SUBMIT", "").lower() in ("1", "true", "yes")
        )
        self.store = store or ApprovalQueue(db_path=db_path)
        self.attention = AttentionQueue()
        self._board_counts: Dict[str, int] = {}

    def _delay(self) -> None:
        if self.dry_run:
            return
        time.sleep(random.uniform(0.8, 2.2))

    def run_job(
        self,
        job: Dict[str, Any],
        *,
        dom_fields: List[Dict[str, Any]],
        page_text: str = "",
        page_url: str = "",
        host: str = "",
        approved: bool = False,
    ) -> GovernedResult:
        url = job.get("url") or page_url or ""
        fit = float(job.get("fit_score") or 0)
        cov = float(job.get("coverage_pct") or 0)
        result = GovernedResult(job_url=url, status="skipped")

        blocker = detect_blocker(page_text, url=url)
        if blocker == BlockerClass.CAPTCHA:
            self.attention.push(blocker, url, "captcha_detected")
            result.status = "blocked"
            result.blockers.append(blocker.value)
            return result
        if blocker:
            self.attention.push(blocker, url, page_text[:120])
            result.status = "blocked"
            result.blockers.append(blocker.value)
            return result

        board = host or (job.get("ats") or "generic")
        self._board_counts[board] = self._board_counts.get(board, 0) + 1
        if self._board_counts[board] > PER_BOARD_DAILY_CAP:
            result.status = "skipped"
            result.blockers.append("daily_cap")
            return result

        # Auto-submit eligibility
        can_auto = (
            self.auto_submit
            and fit >= AUTO_FIT
            and cov >= AUTO_COVERAGE
        )
        if not can_auto and not approved and not self.dry_run:
            # enqueue for HITL
            items = self.store.enqueue_batch([{
                **job,
                "fit_score": fit,
                "coverage_pct": cov,
                "url": url,
            }])
            result.status = "needs_approval"
            result.ask_user = [i.token for i in items]
            return result

        hints = inventory_from_dom_snapshot(dom_fields, host=host)
        audits = 0
        for hint in hints:
            ans = answer_from_facts(hint, self.facts)
            if ans["action"] == "ASK_USER":
                self.store.quarantine_ask(hint.label, hint.sensitivity.value, url)
                result.ask_user.append(hint.label)
            self.store.audit_field(
                job_url=url,
                field_id=hint.field_id,
                label=hint.label,
                sensitivity=hint.sensitivity.value,
                action=ans["action"],
                value_masked=ans.get("value_masked") or mask_for_log(ans.get("value"), hint.sensitivity),
                dry_run=self.dry_run,
            )
            audits += 1
            self._delay()

        result.field_audits = audits
        result.status = "filled"

        if self.dry_run:
            # Never submit in dry-run
            result.submitted = False
            return result

        if result.ask_user and not can_auto:
            result.status = "quarantined"
            return result

        # Live path: only record applied after confirmation
        conf = detect_submission_confirmation(page_text=page_text, page_url=page_url)
        if conf.confirmed:
            self.store.record_confirmed_submit(
                job_url=url,
                company=job.get("company") or "",
                title=job.get("title") or "",
                confirmation_text=conf.matched_text,
                confirmation_url=conf.matched_url,
            )
            result.submitted = True
            result.status = "applied"
            result.confirmation = conf.matched_text or conf.matched_url
        else:
            # Filled but not confirmed → do NOT mark applied
            result.submitted = False
            result.status = "filled"
        return result
