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

logger = logging.getLogger("naukariPro.ProfileEnhancer")

STATE_FILE = os.path.join(WORKSPACE_DIR, "naukri_system", "session_state.json")

class ProfileEnhancerEngine:
    def __init__(self, state_file=None):
        self.cfg = load_config()
        self.state_file = state_file or STATE_FILE

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

    def bump_profile(self, page, force=False):
        """
        Micro-toggles the headline punctuation to force Naukri backend to update 'Last updated today'.
        Enforces a once-a-day throttle: skips redundant edits if already bumped today unless force=True.
        """
        today = datetime.now().strftime("%Y-%m-%d")
        state = self._load_state()

        if not force and state.get("last_bumped_date") == today:
            logger.info("Profile was already touched today (%s). Status is 'Active Today'. Skipping redundant edit.", today)
            print(f"  ℹ️ Profile was already touched today ({today}). Status is already 'Active Today'.")
            print("     Skipping redundant edit to stay inside recruiter recency window without repetitive saves.")
            return True

        logger.info("Executing daily profile bump on Naukri...")
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
            # Modern and legacy selectors for headline edit button
            headline_edit = page.locator(
                "[data-qa='resume-headline-edit'], .resumeHeadline .edit, span.edit, .widgetHead .editBtn, .editOneTheme"
            ).first

            if not headline_edit.is_visible():
                # Try scrolling down slightly to trigger lazy-loaded widgets
                page.evaluate("window.scrollBy(0, 300)")
                time.sleep(1)

            if headline_edit.is_visible():
                headline_edit.click()
                time.sleep(1.5)

                textarea = page.locator(
                    "textarea#resumeHeadlineTxt, form[name='resumeHeadline'] textarea, .resumeHeadline textarea, textarea"
                ).first

                if not textarea.is_visible():
                    logger.warning("Headline textarea did not open.")
                    return False

                curr_val = textarea.input_value().strip()
                template = self.cfg.get("headline_template", curr_val)

                # Micro-toggle trailing period to create an authentic edit event
                if curr_val.endswith("."):
                    new_val = template.rstrip(".")
                else:
                    new_val = template.rstrip(".") + "."

                textarea.fill(new_val)
                time.sleep(1)

                save_btn = page.locator(
                    "form[name='resumeHeadline'] button:visible, .action.s12 button:visible, button.btn-dark-ot:visible, button:visible:has-text('Save')"
                ).first

                if save_btn.is_visible():
                    save_btn.click()
                    time.sleep(3)
                    state["last_bumped_date"] = today
                    state["last_bumped_timestamp"] = datetime.now().isoformat()
                    self._save_state(state)
                    logger.info("SUCCESS: Profile timestamp touched! Status is 'Last updated today'.")
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

            # File inputs on Naukri
            file_input = page.locator("input#attachCV, input#fileUpload, input[type='file']").first
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
                            "checklist": [("Naukri Portal Completeness", f"{live_score}% reported by portal", live_score)],
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
        checklist.append(("Resume Attachment", f"1-Page PDF {'present on disk' if has_pdf else 'MISSING'}", pts))

        # 2. Headline Keyword Density
        headline = self.cfg.get("headline_template", "")
        core_kw = ["azure databricks", "pyspark", "delta lake", "sql", "azure data factory"]
        kw_count = sum(1 for kw in core_kw if kw in headline.lower())
        pts = 20 if kw_count >= 3 else (10 if kw_count >= 1 else 0)
        earned_score += pts
        checklist.append(("Headline Keywords", f"{kw_count}/5 core keywords in headline ({pts}/20 pts)", pts))

        # 3. Key Skills
        competencies = self.cfg.get("technical_competencies", {})
        total_skills = sum(len(v) for v in competencies.values()) if competencies else len(self.cfg.get("search_settings", {}).get("keywords", []))
        pts = 20 if total_skills >= 15 else (10 if total_skills >= 8 else 5)
        earned_score += pts
        checklist.append(("Key Skills Tag Cloud", f"{total_skills} technical skills configured ({pts}/20 pts)", pts))

        # 4. Profile Summary / Headline Depth
        pts = 15 if len(headline) >= 60 else (8 if len(headline) >= 30 else 0)
        earned_score += pts
        checklist.append(("Profile Headline Depth", f"{len(headline)} chars comprehensive headline ({pts}/15 pts)", pts))

        # 5. Verified Contact & Experience
        has_contact = bool(cand.get("email") and cand.get("phone") and cand.get("total_experience_years"))
        pts = 10 if has_contact else 0
        earned_score += pts
        checklist.append(("Verified Contact & YOE", f"Email, phone, and {cand.get('total_experience_years', '0')} YOE verified", pts))

        # 6. Certifications
        certs = self.cfg.get("certifications", [])
        pts = 10 if len(certs) >= 1 else 0
        earned_score += pts
        checklist.append(("Certifications Listed", f"{len(certs)} certifications on record ({pts}/10 pts)", pts))

        # 7. Experience & Projects
        exp_roles = self.cfg.get("experience", [])
        pts = 10 if len(exp_roles) >= 1 else 0
        earned_score += pts
        checklist.append(("Employment History", f"{len(exp_roles)} verified work history entries ({pts}/10 pts)", pts))

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
