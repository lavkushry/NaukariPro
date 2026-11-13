#!/bin/bash
# ==============================================================================
# naukariPro Linux Schedule Installer (systemd authoritative + crontab sanitization)
# Feature 14: Schedule Collision Resolution
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "========================================================================"
echo "    NaukariPro Always-on Beast — Linux Scheduler (systemd / cron)"
echo "    Runner: agy_schedule_runner.sh → beast-autonomous (blocks 1/2/3)"
echo "========================================================================"

ACTION="${1:-install}"

purge_crontab_entries() {
    local tmp_cron
    tmp_cron="$(mktemp)"
    if crontab -l 2>/dev/null > "$tmp_cron"; then
        if grep -q "agy_schedule_runner.sh" "$tmp_cron" || grep -q "NaukariPro AGY" "$tmp_cron"; then
            echo "[*] Purging redundant crontab entries to prevent schedule collisions..."
            grep -v "agy_schedule_runner.sh" "$tmp_cron" | grep -v "# NaukariPro AGY" > "${tmp_cron}.clean" || true
            crontab "${tmp_cron}.clean" 2>/dev/null || true
            rm -f "${tmp_cron}.clean"
            echo "[✓] Crontab sanitized: redundant triggers eliminated."
        else
            echo "[*] No conflicting crontab entries found."
        fi
    fi
    rm -f "$tmp_cron"
}

uninstall_schedule() {
    echo "[*] Uninstalling NaukariPro schedules..."
    if command -v systemctl &>/dev/null; then
        systemctl --user stop naukaripro-agy.timer 2>/dev/null || true
        systemctl --user disable naukaripro-agy.timer 2>/dev/null || true
        rm -f "$HOME/.config/systemd/user/naukaripro-agy.service" "$HOME/.config/systemd/user/naukaripro-agy.timer"
        systemctl --user daemon-reload 2>/dev/null || true
        echo "[✓] systemd timer and service removed."
    fi
    purge_crontab_entries
    echo "[✓] Uninstall completed."
    exit 0
}

if [ "$ACTION" = "--uninstall" ] || [ "$ACTION" = "uninstall" ]; then
    uninstall_schedule
fi

# 1. Enable lingering for user session persistence across logouts
if command -v loginctl &>/dev/null; then
    echo "[*] Ensuring user linger is enabled for persistent background execution..."
    loginctl enable-linger "${USER:-$(whoami)}" 2>/dev/null || true
fi

# 2. Check systemd user manager availability
HAS_SYSTEMD=false
if command -v systemctl &>/dev/null; then
    if systemctl --user list-timers &>/dev/null; then
        HAS_SYSTEMD=true
    fi
fi

SYSTEMD_USER_DIR="$HOME/.config/systemd/user"
mkdir -p "$SYSTEMD_USER_DIR"
mkdir -p "$SCRIPT_DIR/logs"
chmod +x "$SCRIPT_DIR/agy_schedule_runner.sh"

if [ "$HAS_SYSTEMD" = true ]; then
    echo "[+] Systemd user manager detected. Installing authoritative systemd timer..."

    # 3. Dynamic path substitution for service units
    for unit in naukaripro-agy naukaripro-label naukaripro-mutate naukaripro-learn naukaripro-digest; do
        if [ -f "$SCRIPT_DIR/systemd/${unit}.service" ]; then
            sed "s|/home/ubuntu/Resume|$SCRIPT_DIR|g" "$SCRIPT_DIR/systemd/${unit}.service" > "$SYSTEMD_USER_DIR/${unit}.service"
            if [ -f "$SCRIPT_DIR/systemd/${unit}.timer" ]; then
                cp "$SCRIPT_DIR/systemd/${unit}.timer" "$SYSTEMD_USER_DIR/"
            fi
        fi
    done

    # 4. Enable and start systemd timers
    systemctl --user daemon-reload
    for unit in naukaripro-agy naukaripro-label naukaripro-mutate naukaripro-learn naukaripro-digest; do
        if [ -f "$SYSTEMD_USER_DIR/${unit}.timer" ]; then
            systemctl --user enable "${unit}.timer" 2>/dev/null || true
            systemctl --user restart "${unit}.timer" 2>/dev/null || true
        fi
    done

    echo "[✓] systemd timers (agy, label, mutate, learn, digest) enabled and started as authoritative scheduler!"

    # 5. PURGE redundant crontab entry so ONLY systemd timer triggers the schedule
    purge_crontab_entries

    echo ""
    echo "========================================================================"
    echo "    Active Timers on Linux Host (systemd authoritative)"
    echo "========================================================================"
    systemctl --user list-timers --no-pager | grep -E "(UNIT|naukaripro)" || true

else
    echo "[!] systemd --user is not available on this host. Falling back to crontab..."
    purge_crontab_entries

    # Crontab fallback (UTC ≈ IST−5:30): 09:15, 12:00, 14:31, 18:00 IST
    TMP_CRON="$(mktemp)"
    crontab -l 2>/dev/null > "$TMP_CRON" || true
    echo "" >> "$TMP_CRON"
    echo "# NaukariPro Always-on Beast Fallback (09:15, 12:00, 14:31, 18:00 IST)" >> "$TMP_CRON"
    echo "45 3 * * * /bin/bash $SCRIPT_DIR/agy_schedule_runner.sh >> $SCRIPT_DIR/logs/cron_fallback.log 2>&1" >> "$TMP_CRON"
    echo "30 6 * * * /bin/bash $SCRIPT_DIR/agy_schedule_runner.sh >> $SCRIPT_DIR/logs/cron_fallback.log 2>&1" >> "$TMP_CRON"
    echo "1 9 * * * /bin/bash $SCRIPT_DIR/agy_schedule_runner.sh >> $SCRIPT_DIR/logs/cron_fallback.log 2>&1" >> "$TMP_CRON"
    echo "30 12 * * * /bin/bash $SCRIPT_DIR/agy_schedule_runner.sh >> $SCRIPT_DIR/logs/cron_fallback.log 2>&1" >> "$TMP_CRON"
    crontab "$TMP_CRON"
    rm -f "$TMP_CRON"
    echo "[✓] Crontab fallback schedule installed (4 IST peak triggers → beast-autonomous)."
fi

echo ""
echo "[✓] Always-on Beast scheduled successfully on Linux!"
echo "[*] Recruiter Peak Schedule (Asia/Kolkata via systemd timer):"
echo "    - 09:15 IST  Block 1  (beast-autonomous)"
echo "    - 12:00 IST  Mid-day catch-up"
echo "    - 14:31 IST  Block 2  (+ outreach when hour maps to block 2)"
echo "    - 18:00 IST  Block 3"
echo "[*] Manual:  ./agy_schedule_runner.sh   or   ./naukariPro beast-autonomous --block 1"
echo "[*] Remote:  ./run_on_linux.sh agy-schedule install|run|status|logs"
echo "[*] Logs:    $SCRIPT_DIR/logs/"
echo "========================================================================"
