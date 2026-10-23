#!/bin/bash
# ==============================================================================
# naukariPro AGY Autonomous Career Scheduler Runner
# Powered by Google Antigravity CLI (agy)
# ==============================================================================
set -euo pipefail

# 1. Resolve workspace paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE="${WORKSPACE:-$SCRIPT_DIR}"
LOG_DIR="$WORKSPACE/logs"
mkdir -p "$LOG_DIR"

TIMESTAMP="$(date +'%Y-%m-%d_%H-%M-%S')"
RUN_LOG="$LOG_DIR/agy_run_${TIMESTAMP}.log"
HISTORY_LOG="$LOG_DIR/agy_schedule_history.log"

echo "========================================================================" | tee -a "$RUN_LOG" "$HISTORY_LOG"
echo "[*] NaukariPro AGY Autonomous Cycle Started: $(date)" | tee -a "$RUN_LOG" "$HISTORY_LOG"
echo "[*] Host: $(hostname) | Workspace: $WORKSPACE" | tee -a "$RUN_LOG" "$HISTORY_LOG"

# 2. Environment Setup
export PATH="$HOME/.local/bin:$HOME/.cargo/bin:/usr/local/bin:/usr/bin:/bin:$PATH"
export PYTHONUNBUFFERED=1

if [ -f "$WORKSPACE/.venv/bin/activate" ]; then
    # shellcheck disable=SC1091
    source "$WORKSPACE/.venv/bin/activate"
    echo "[+] Activated Python venv: $WORKSPACE/.venv" | tee -a "$RUN_LOG"
fi

cd "$WORKSPACE"

# 3. Locate agy CLI binary
AGY_BIN=""
if [ -x "$HOME/.local/bin/agy" ]; then
    AGY_BIN="$HOME/.local/bin/agy"
elif command -v agy &>/dev/null; then
    AGY_BIN="$(command -v agy)"
fi

# 4. Formulate Agentic Execution Prompt for agy
AGY_PROMPT='You are the autonomous AI career agent running for Lavkush Kumar (Azure Data Engineer, 2.5 YOE, ₹25 LPA target CTC, 30 days notice).
Execute the complete scheduled career cycle in this workspace:
1. Run `./naukariPro pro --headless --limit 15` to:
   - Bump and refresh the live Naukri profile to maintain "Active Today" Resdex visibility.
   - Scan recommended and search vacancies for Azure Data Engineer roles in Hyderabad, Bengaluru, Pune, and Remote.
   - Submit applications to high-match roles (1-click and chatbot screening).
   - Ingest off-market and startup roles across LinkedIn and Hacker News "Who'\''s Hiring".
   - Check and fill external ATS portals (Greenhouse, Lever, Ashby, Workday).
   - Log all submissions to `Naukri_Live_Application_Tracker.xlsx`.
2. Inspect the output and verify that profile recency, application counts, and the Excel tracker were updated.
3. Print a concise, structured markdown report summarizing:
   - Profile bump status
   - Total new applications submitted
   - Top 3 high-match roles applied
   - Any manual recruiter actions needed'

# 5. Execute via agy CLI (with graceful fallback to direct ./naukariPro pro)
if [ -n "$AGY_BIN" ]; then
    echo "[*] Executing autonomous cycle using agy CLI: $AGY_BIN" | tee -a "$RUN_LOG"
    set +e
    "$AGY_BIN" -p "$AGY_PROMPT" --dangerously-skip-permissions 2>&1 | tee -a "$RUN_LOG"
    AGY_STATUS=${PIPESTATUS[0]}
    set -e

    if [ "$AGY_STATUS" -eq 0 ]; then
        echo "[✓] agy CLI autonomous cycle completed successfully." | tee -a "$RUN_LOG" "$HISTORY_LOG"
    else
        echo "[!] agy CLI exited with status $AGY_STATUS. Triggering autonomous fallback..." | tee -a "$RUN_LOG" "$HISTORY_LOG"
        ./naukariPro pro --headless --limit 15 2>&1 | tee -a "$RUN_LOG"
        echo "[✓] Fallback pipeline completed." | tee -a "$RUN_LOG" "$HISTORY_LOG"
    fi
else
    echo "[!] agy CLI not found in PATH or ~/.local/bin/agy. Running direct Pro pipeline..." | tee -a "$RUN_LOG" "$HISTORY_LOG"
    ./naukariPro pro --headless --limit 15 2>&1 | tee -a "$RUN_LOG"
fi

echo "[*] Cycle Finished: $(date)" | tee -a "$RUN_LOG" "$HISTORY_LOG"
echo "========================================================================" | tee -a "$RUN_LOG" "$HISTORY_LOG"
