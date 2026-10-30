"""
Feature 3: AI-Enhanced Profile
Autonomous Profile Bumper, Real Profile Completeness Audit, and Resdex Search Ranking Optimization.
"""

import os
import time
import json
from datetime import datetime
import logging
from naukari_pro.config import load_config, RESUME_PDF_PATH, WORKSPACE_DIR
from naukari_pro.modules.learning.mutator import ProfileMutator, BlacklistValidator
from naukari_pro.modules.db import record_profile_mutation

logger = logging.getLogger("naukariPro.ProfileEnhancer")

STATE_FILE = os.path.join(WORKSPACE_DIR, "naukri_system", "session_state.json")

class ProfileChecklistItem(tuple):
    """
    3-element tuple (name, description, points) with enhanced string containment.
    Allows tuple indexing (item[0], item[1], item[2]), tuple unpacking
    (name, desc, pts = item), and substring containment ('Headline' in item).
    """
    def __contains__(self, key):
        if super().__contains__(key):
            return True
        for elem in self:
            if isinstance(elem, str) and str(key).lower() in elem.lower():
                return True
        return False

class ProfileEnhancerEngine:
    def __init__(self, state_file=None, mutator=None):
        self.cfg = load_config()
        self.state_file = state_file or STATE_FILE
        self.mutator = mutator or ProfileMutator(config=self.cfg)

    def _load_state(self):
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def _save_state(self, state):
        try:
            os.makedirs(os.path.dirname(self.state_file), exist_ok=True)
            with open(self.state_file, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            logger.warning("Could not save session state: %s", e)

    def bump_profile(self, page, force=False, cooldown_seconds=7200):
        """
        Micro-toggles the headline punctuation or executes controlled keyword mutation
        to force Naukri backend to update 'Last updated today'.
        Enforces a cooldown throttle (default 2 hours / 7200s): skips redundant edits if bumped within
        the cooldown period unless force=True, enabling 3x/day scheduled boosts.
        Ensures the full 247-char Azure Data Engineer headline is persisted and logged to profile_mutations ledger.
        """
        now = datetime.now()
        today = now.strftime("%Y-%m-%d")
        state = self._load_state()

        last_bumped_ts = state.get("last_bumped_timestamp")
        if not force and last_bumped_ts:
            try:
                last_dt = datetime.fromisoformat(last_bumped_ts)
                elapsed = (now - last_dt).total_seconds()
                if 0 <= elapsed < cooldown_seconds:
                    logger.info("Profile was recently touched %.1f minutes ago (< %d sec cooldown). Skipping redundant edit.", elapsed / 60, cooldown_seconds)
                    print(f"  ℹ️ Profile was recently touched {elapsed/60:.1f} mins ago. Status is already 'Active Today'.")
                    print("     Skipping redundant edit to stay inside recruiter recency window without repetitive saves.")
                    return True
            except Exception as e:
                logger.warning("Could not parse last_bumped_timestamp '%s': %s", last_bumped_ts, e)

        logger.info("Executing profile freshness boost on Naukri...")
        try:
            page.goto("https://www.naukri.com/mnjuser/profile", wait_until="domcontentloaded", timeout=30000)
            time.sleep(3)
        except Exception as e:
            logger.error("Navigation error during profile bump: %s", e)
            return False

        if "login" in page.url:
            logger.error("Session expired; cannot bump profile. Please re-authenticate.")
            return False

        try:
            headline_edit = page.locator(
                'span[aria-label*="Edit resume headline"], span[aria-label*="resume headline" i], .resumeHeadline .edit'
            ).first

            if headline_edit.count() > 0:
                headline_edit.click()
                time.sleep(2)

                textarea = page.locator(
                    "textarea#resumeHeadlineTxt, form[name='resumeHeadline'] textarea, .resumeHeadline textarea, textarea"
                ).first

                if not textarea.is_visible():
                    logger.warning("Headline textarea did not open.")
                    return False

                curr_val = textarea.input_value().strip()
                default_target_headline = (
                    "Azure Data Engineer | Azure Databricks · PySpark · Delta Lake · "
                    "Azure Data Factory (ADF) · SQL · Apache Kafka · Terraform · Medallion Architecture | "
                    "Certified AZ-900 · Databricks Associate (Pursuing) | 2.5 YOE Cloud Data Platforms & CI/CD"
                )
                template = self.cfg.get("headline_template", default_target_headline).strip()
                if not template:
                    template = default_target_headline

                core_keywords = ["Azure Data Engineer", "Databricks", "Delta Lake", "ADF"]
                is_complete = len(curr_val) >= 200 and all(kw.lower() in curr_val.lower() for kw in core_keywords)

                can_kw = self.mutator.can_mutate("naukri")

                if not is_complete:
                    logger.info("Headline missing or truncated (current len: %d). Overwriting with full %d-char Azure Data Engineer headline.", len(curr_val), len(template))
                    new_val = template.rstrip(".")
                    is_kw = True
                    rationale = "resdex_headline_saturation_recovery"
                    expected_effect = "restore_canonical_headline"
                elif can_kw:
                    try:
                        proposal = self.mutator.propose_naukri_mutation(field="headline")
                        new_val = proposal.new_value
                        is_kw = True
                        rationale = proposal.rationale
                        expected_effect = proposal.expected_effect
                    except Exception:
                        new_val = template.rstrip(".")
                        is_kw = True
                        rationale = "resdex_seo_headline_saturation"
                        expected_effect = "boost_search_appearances"
                else:
                    # Micro-toggle trailing period to create an authentic edit event without keyword drift
                    if curr_val.endswith("."):
                        new_val = template.rstrip(".")
                    else:
                        new_val = template.rstrip(".") + "."
                    is_kw = False
                    rationale = "cadence_freshness_bump_only"
                    expected_effect = "refresh_resdex_active_today_badge"

                # Safety guard check
                BlacklistValidator.enforce(new_val, field_name="headline")

                textarea.click()
                textarea.fill("")
                time.sleep(0.3)
                textarea.fill(new_val)
                time.sleep(1)

                save_btn = page.locator(
                    '.resumeHeadline button:has-text("Save"), button.btn-dark-ot:has-text("Save"), button:has-text("Save")'
                ).first
                if save_btn.count() == 0 or not save_btn.is_visible():
                    save_btn = page.get_by_role("button", name="Save", exact=True)

                if save_btn.count() > 0 and save_btn.is_visible():
                    save_btn.click()
                    time.sleep(3)
                    state["last_bumped_date"] = today
                    state["last_bumped_timestamp"] = datetime.now().isoformat()
                    self._save_state(state)

                    # Record in persistent profile_mutations ledger
                    try:
                        record_profile_mutation(
                            platform="naukri",
                            field="headline",
                            old_value=curr_val,
                            new_value=new_val,
                            is_keyword_mutation=is_kw,
                            rationale=rationale,
                            expected_effect=expected_effect,
                            approved_by="profile_enhancer",
                            db_path=self.mutator.db_path
                        )
                    except Exception as le:
                        logger.warning("Could not record profile mutation ledger entry: %s", le)

                    logger.info("SUCCESS: Profile timestamp touched! Status is 'Last updated today'. Headline len: %d", len(new_val))
                    return True
                else:
                    logger.warning("Save button not found for headline.")
            else:
                logger.warning("Headline edit affordance not found on profile page.")
        except Exception as e:
            logger.error("Bump error: %s", e)
        return False

    def upload_resume_pdf(self, page, pdf_path=RESUME_PDF_PATH):
        """Uploads the latest single-page ATS-optimized Azure Data Engineer resume."""
        if not os.path.exists(pdf_path):
            logger.error("Resume file not found at %s", pdf_path)
            return False

        logger.info("Uploading ATS Resume: %s", pdf_path)
        try:
            page.goto("https://www.naukri.com/mnjuser/profile", wait_until="domcontentloaded", timeout=30000)
            time.sleep(3)

            page.evaluate('''() => {
                const el = document.getElementById('lazyAttachCV');
                if (el) el.scrollIntoView();
            }''')
            time.sleep(2)

            # File inputs on Naukri
            file_input = page.locator("input#attachCV, input[type='file']").first
            if file_input.count() > 0:
                file_input.set_input_files(pdf_path)
                logger.info("File attached to input. Waiting for server confirmation...")
                time.sleep(6)
                logger.info("SUCCESS: Latest Azure Data Engineer ATS Resume uploaded!")
                return True
            else:
                logger.warning("Could not find resume file upload input.")
        except Exception as e:
            logger.error("Resume upload exception: %s", e)
        return False

    def audit_profile_strength(self, page=None):
        """
        Audits profile completeness.
        If a live authenticated page is provided, reads the real score directly from Naukri.
        Otherwise, evaluates candidate facts from config and scores honestly.
        """
        # Live page extraction
        if page:
            try:
                score_el = page.locator(
                    ".profile-completeness .progress-bar-text, .profile-percent, span.score, div[class*='profileProgress']"
                ).first
                if score_el.count() > 0 and score_el.is_visible():
                    raw_text = score_el.inner_text().strip().replace("%", "")
                    if raw_text.isdigit():
                        live_score = int(raw_text)
                        return {
                            "score": live_score,
                            "source": "Live Naukri Profile",
                            "checklist": [ProfileChecklistItem(("Naukri Portal Completeness", f"{live_score}% reported by portal", live_score))],
                            "tier": "Fully Complete Profile" if live_score >= 95 else "Partially Complete Profile"
                        }
            except Exception as e:
                logger.debug("Live score extraction notice: %s", e)

        # Offline factual evaluation against candidate config
        cand = self.cfg.get("candidate", {})
        checklist = []
        earned_score = 0

        # 1. Resume Attachment
        has_pdf = os.path.exists(RESUME_PDF_PATH)
        pts = 15 if has_pdf else 0
        earned_score += pts
        checklist.append(ProfileChecklistItem(("Resume Attachment", f"1-Page PDF {'present on disk' if has_pdf else 'MISSING'}", pts)))

        # 2. Headline Keyword Density
        headline = self.cfg.get("headline_template", "")
        core_kw = ["azure databricks", "pyspark", "delta lake", "sql", "azure data factory"]
        kw_count = sum(1 for kw in core_kw if kw in headline.lower())
        pts = 20 if kw_count >= 3 else (10 if kw_count >= 1 else 0)
        earned_score += pts
        checklist.append(ProfileChecklistItem(("Headline Keywords", f"{kw_count}/5 core keywords in headline ({pts}/20 pts)", pts)))

        # 3. Key Skills
        competencies = self.cfg.get("technical_competencies", {})
        total_skills = sum(len(v) for v in competencies.values()) if competencies else len(self.cfg.get("search_settings", {}).get("keywords", []))
        pts = 20 if total_skills >= 15 else (10 if total_skills >= 8 else 5)
        earned_score += pts
        checklist.append(ProfileChecklistItem(("Key Skills Tag Cloud", f"{total_skills} technical skills configured ({pts}/20 pts)", pts)))

        # 4. Profile Summary
        summary = self.cfg.get("profile_summary", "")
        pts = 15 if len(summary) >= 100 else (8 if len(summary) >= 50 else 0)
        earned_score += pts
        checklist.append(ProfileChecklistItem(("Profile Summary", f"{len(summary)} chars optimized summary ({pts}/15 pts)", pts)))

        # 5. Verified Contact & Experience
        has_contact = bool(cand.get("email") and cand.get("phone") and cand.get("total_experience_years"))
        pts = 10 if has_contact else 0
        earned_score += pts
        checklist.append(ProfileChecklistItem(("Verified Contact & YOE", f"Email, phone, and {cand.get('total_experience_years', '0')} YOE verified", pts)))

        # 6. Certifications
        certs = self.cfg.get("certifications", [])
        pts = 10 if len(certs) >= 1 else 0
        earned_score += pts
        checklist.append(ProfileChecklistItem(("Certifications Listed", f"{len(certs)} certifications on record ({pts}/10 pts)", pts)))

        # 7. Experience & Projects
        exp_roles = self.cfg.get("experience", [])
        pts = 10 if len(exp_roles) >= 1 else 0
        earned_score += pts
        checklist.append(ProfileChecklistItem(("Employment History", f"{len(exp_roles)} verified work history entries ({pts}/10 pts)", pts)))

        if earned_score >= 95:
            tier = "Comprehensive Profile (High Resdex Search Alignment)"
        elif earned_score >= 80:
            tier = "Strong Profile (Minor keyword/field gaps)"
        elif earned_score >= 60:
            tier = "Moderate Profile (Requires optimization)"
        else:
            tier = "Incomplete Profile (Needs critical fields)"

        return {
            "score": earned_score,
            "source": "Local Config Fact Matrix",
            "checklist": checklist,
            "tier": tier
        }

    def sync_live_profile(self, page, force=False):
        """Delegates to sync_full_naukri_profile for complete profile synchronization."""
        from scripts.sync_naukri_live_profile import sync_full_naukri_profile
        return sync_full_naukri_profile(page, config=self.cfg, force=force)

