#!/bin/bash
# ==============================================================================
# naukariPro Linux Schedule Installer (systemd authoritative + crontab sanitization)
# Feature 14: Schedule Collision Resolution
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "========================================================================"
echo "    NaukariPro AGY Autonomous Linux Scheduler Installer"
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

    # 3. Dynamic path substitution for service unit
    sed "s|/home/ubuntu/Resume|$SCRIPT_DIR|g" "$SCRIPT_DIR/systemd/naukaripro-agy.service" > "$SYSTEMD_USER_DIR/naukaripro-agy.service"
    cp "$SCRIPT_DIR/systemd/naukaripro-agy.timer" "$SYSTEMD_USER_DIR/"

    # 4. Enable and start systemd timer
    systemctl --user daemon-reload
    systemctl --user enable naukaripro-agy.timer
    systemctl --user restart naukaripro-agy.timer

    echo "[✓] systemd timer 'naukaripro-agy.timer' enabled and started as authoritative scheduler!"

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

    # Install properly calibrated 3x daily crontab fallback:
    # 09:15 AM IST (03:45 UTC), 02:30 PM IST (09:00 UTC), 06:00 PM IST (12:30 UTC)
    TMP_CRON="$(mktemp)"
    crontab -l 2>/dev/null > "$TMP_CRON" || true
    echo "" >> "$TMP_CRON"
    echo "# NaukariPro AGY Autonomous Scheduler Fallback (09:15, 14:30, 18:00 IST)" >> "$TMP_CRON"
    echo "45 3 * * * /bin/bash $SCRIPT_DIR/agy_schedule_runner.sh >> $SCRIPT_DIR/logs/cron_fallback.log 2>&1" >> "$TMP_CRON"
    echo "0 9 * * * /bin/bash $SCRIPT_DIR/agy_schedule_runner.sh >> $SCRIPT_DIR/logs/cron_fallback.log 2>&1" >> "$TMP_CRON"
    echo "30 12 * * * /bin/bash $SCRIPT_DIR/agy_schedule_runner.sh >> $SCRIPT_DIR/logs/cron_fallback.log 2>&1" >> "$TMP_CRON"
    crontab "$TMP_CRON"
    rm -f "$TMP_CRON"
    echo "[✓] Crontab fallback schedule installed with 3 distinct IST peak triggers."
fi

echo ""
echo "[✓] NaukariPro scheduled successfully!"
echo "[*] Recruiter Peak Schedule:"
echo "    - 09:15 AM IST (03:45 UTC) [Morning opening queue]"
echo "    - 02:30 PM IST (09:00 UTC) [Post-lunch search batch]"
echo "    - 06:00 PM IST (12:30 UTC) [Evening shortlisting review]"
echo "[*] Logs recorded to: $SCRIPT_DIR/logs/"
echo "========================================================================"
