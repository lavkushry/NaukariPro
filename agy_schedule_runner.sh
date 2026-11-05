#!/bin/bash
# ==============================================================================
# ONE BEAST SYSTEM — Daily cycle runner (single brain: ./naukariPro pro)
# Feature 15: Process-Level Mutual Exclusion via flock
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE="${WORKSPACE:-$SCRIPT_DIR}"
LOG_DIR="$WORKSPACE/logs"
mkdir -p "$LOG_DIR"

TIMESTAMP="$(date +'%Y-%m-%d_%H-%M-%S')"
RUN_LOG="$LOG_DIR/agy_run_${TIMESTAMP}.log"
HISTORY_LOG="$LOG_DIR/agy_schedule_history.log"

LOCK_FILE="/tmp/naukaripro_runner.lock"
exec 200>"$LOCK_FILE"

acquire_lock() {
    if command -v flock &>/dev/null; then
        flock -n 200
        return $?
    else
        python3 -c "import fcntl; fcntl.flock(200, fcntl.LOCK_EX | fcntl.LOCK_NB)" 200>&200 2>/dev/null
        return $?
    fi
}

if ! acquire_lock; then
    ACTIVE_PID="$(cat "$LOCK_FILE" 2>/dev/null || echo 'unknown')"
    echo "========================================================================" | tee -a "$HISTORY_LOG"
    echo "[!] [MUTUAL_EXCLUSION] Overlapping execution prevented at $(date)." | tee -a "$HISTORY_LOG"
    echo "[!] Another instance is running (PID: $ACTIVE_PID)." | tee -a "$HISTORY_LOG"
    echo "========================================================================" | tee -a "$HISTORY_LOG"
    exit 0
fi

echo "$$" >&200

echo "========================================================================" | tee -a "$RUN_LOG" "$HISTORY_LOG"
echo "[*] ONE BEAST cycle started: $(date)" | tee -a "$RUN_LOG" "$HISTORY_LOG"
echo "[*] Host: $(hostname) | Workspace: $WORKSPACE | PID: $$" | tee -a "$RUN_LOG" "$HISTORY_LOG"

export PATH="$HOME/.local/bin:$HOME/.cargo/bin:/usr/local/bin:/usr/bin:/bin:$PATH"
export PYTHONUNBUFFERED=1

if [ -f "$WORKSPACE/.venv/bin/activate" ]; then
    # shellcheck disable=SC1091
    source "$WORKSPACE/.venv/bin/activate"
    echo "[+] Activated Python venv: $WORKSPACE/.venv" | tee -a "$RUN_LOG"
fi

cd "$WORKSPACE"

# Resolve Beast block from local hour (IST on VM)
HOUR="$(date +%H)"
HOUR=$((10#$HOUR))
if [ "$HOUR" -lt 12 ]; then
    BLOCK=1
elif [ "$HOUR" -lt 17 ]; then
    BLOCK=2
else
    BLOCK=3
fi

echo "[*] Beast Block: $BLOCK" | tee -a "$RUN_LOG" "$HISTORY_LOG"

# Single brain — no duplicate linkedin-apply / portal-apply / goal-5calls chain
# 20,20,20,20 targets: Naukri (20), LinkedIn (20), External ATS (20), Redirects (20)
set +e
./naukariPro pro --headless --limit 20 --limit-naukri 20 --limit-linkedin 20 --limit-external 20 --limit-redirects 20 --force --block "$BLOCK" 2>&1 | tee -a "$RUN_LOG"
PRO_STATUS=${PIPESTATUS[0]}
set -e

if [ "$PRO_STATUS" -eq 0 ]; then
    echo "[✓] Beast pro cycle completed successfully." | tee -a "$RUN_LOG" "$HISTORY_LOG"
else
    echo "[!] Beast pro cycle exited with status $PRO_STATUS." | tee -a "$RUN_LOG" "$HISTORY_LOG"
fi

# Closed-loop keyword mining after every cycle
./naukariPro mine-keywords --limit 15 2>&1 | tee -a "$RUN_LOG" || echo "[!] Keyword mining notice: non-critical." | tee -a "$RUN_LOG"

echo "[*] Cycle Finished: $(date)" | tee -a "$RUN_LOG" "$HISTORY_LOG"
echo "========================================================================" | tee -a "$RUN_LOG" "$HISTORY_LOG"

find "$LOG_DIR" -name "agy_run_*.log" -type f -mtime +30 -delete 2>/dev/null || true
