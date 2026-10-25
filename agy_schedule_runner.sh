#!/bin/bash
# ==============================================================================
# naukariPro AGY Autonomous Career Scheduler Runner
# Feature 15: Process-Level Mutual Exclusion File Locking via flock
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

# ==============================================================================
# 2. Process-Level File Locking (flock mutual exclusion)
# Prevents overlapping runs across systemd, cron, and manual CLI invocations
# ==============================================================================
LOCK_FILE="/tmp/naukaripro_runner.lock"
exec 200>"$LOCK_FILE"

acquire_lock() {
    if command -v flock &>/dev/null; then
        flock -n 200
        return $?
    else
        # Portable fallback for environments without util-linux flock (e.g., macOS local testing)
        python3 -c "import fcntl; fcntl.flock(200, fcntl.LOCK_EX | fcntl.LOCK_NB)" 200>&200 2>/dev/null
        return $?
    fi
}

if ! acquire_lock; then
    ACTIVE_PID="$(cat "$LOCK_FILE" 2>/dev/null || echo 'unknown')"
    echo "========================================================================" | tee -a "$HISTORY_LOG"
    echo "[!] [MUTUAL_EXCLUSION] Overlapping execution prevented at $(date)." | tee -a "$HISTORY_LOG"
    echo "[!] Another instance of agy_schedule_runner is actively running (PID: $ACTIVE_PID, Lock: $LOCK_FILE)." | tee -a "$HISTORY_LOG"
    echo "[*] Exiting cleanly with status 0 to preserve system integrity." | tee -a "$HISTORY_LOG"
    echo "========================================================================" | tee -a "$HISTORY_LOG"
    exit 0
fi

# Write current PID into lock file for tracking
echo "$$" >&200

echo "========================================================================" | tee -a "$RUN_LOG" "$HISTORY_LOG"
echo "[*] NaukariPro AGY Autonomous Cycle Started: $(date)" | tee -a "$RUN_LOG" "$HISTORY_LOG"
echo "[*] Host: $(hostname) | Workspace: $WORKSPACE | PID: $$" | tee -a "$RUN_LOG" "$HISTORY_LOG"

# ==============================================================================
# 3. Environment Setup
# ==============================================================================
export PATH="$HOME/.local/bin:$HOME/.cargo/bin:/usr/local/bin:/usr/bin:/bin:$PATH"
export PYTHONUNBUFFERED=1

if [ -f "$WORKSPACE/.venv/bin/activate" ]; then
    # shellcheck disable=SC1091
    source "$WORKSPACE/.venv/bin/activate"
    echo "[+] Activated Python venv: $WORKSPACE/.venv" | tee -a "$RUN_LOG"
fi

cd "$WORKSPACE"

# ==============================================================================
# 4. Locate agy CLI binary
# ==============================================================================
AGY_BIN=""
if [ -x "$HOME/.local/bin/agy" ]; then
    AGY_BIN="$HOME/.local/bin/agy"
elif command -v agy &>/dev/null; then
    AGY_BIN="$(command -v agy)"
fi

# ==============================================================================
# 5. Formulate Agentic Execution Prompt for agy
# ==============================================================================
AGY_PROMPT='You are the autonomous AI career agent running for Lavkush Kumar (Azure Data Engineer, 2.5 YOE, ₹20 LPA target CTC, 15 days or less notice).
Execute the complete scheduled career cycle in this workspace:
1. Run `./naukariPro pro --headless --limit 15 --force` to:
   - Bump and refresh the live Naukri profile to maintain "Active Today" Resdex visibility across all 3 daily runs (morning, afternoon, evening).
   - Scan recommended and search vacancies for Azure Data Engineer roles across 7 Tier-1 tech hubs (Bengaluru, Hyderabad, Pune, Gurugram, Noida, Mumbai, Chennai) and Remote.
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

# ==============================================================================
# 6. Execute via agy CLI (with graceful fallback to direct ./naukariPro pro)
# ==============================================================================
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
        ./naukariPro pro --headless --limit 15 --force 2>&1 | tee -a "$RUN_LOG"
        echo "[✓] Fallback pipeline completed." | tee -a "$RUN_LOG" "$HISTORY_LOG"
    fi
else
    echo "[!] agy CLI not found in PATH or ~/.local/bin/agy. Running direct Pro pipeline..." | tee -a "$RUN_LOG" "$HISTORY_LOG"
    ./naukariPro pro --headless --limit 15 --force 2>&1 | tee -a "$RUN_LOG"
fi

echo "[*] Cycle Finished: $(date)" | tee -a "$RUN_LOG" "$HISTORY_LOG"
echo "========================================================================" | tee -a "$RUN_LOG" "$HISTORY_LOG"

# 7. Long-Term 5+ Month Unattended Maintenance: Prune run logs older than 30 days
find "$LOG_DIR" -name "agy_run_*.log" -type f -mtime +30 -delete 2>/dev/null || true
