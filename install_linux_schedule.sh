#!/bin/bash
# ==============================================================================
# naukariPro Linux Schedule Installer (systemd + agy CLI + cron fallback)
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "========================================================================"
echo "    NaukariPro AGY Autonomous Linux Scheduler Installer"
echo "========================================================================"

# 1. Enable lingering for ubuntu user so user systemd stays active without login
if command -v loginctl &>/dev/null; then
    echo "[*] Ensuring user linger is enabled for persistent background execution..."
    loginctl enable-linger "$USER" 2>/dev/null || true
fi

# 2. Setup user systemd directory
SYSTEMD_USER_DIR="$HOME/.config/systemd/user"
mkdir -p "$SYSTEMD_USER_DIR"
mkdir -p "$SCRIPT_DIR/logs"

# 3. Copy systemd unit files
echo "[*] Installing systemd service and timer..."
cp "$SCRIPT_DIR/systemd/naukaripro-agy.service" "$SYSTEMD_USER_DIR/"
cp "$SCRIPT_DIR/systemd/naukaripro-agy.timer" "$SYSTEMD_USER_DIR/"

chmod +x "$SCRIPT_DIR/agy_schedule_runner.sh"

# 4. Reload and enable systemd user daemon
systemctl --user daemon-reload
systemctl --user enable naukaripro-agy.timer
systemctl --user restart naukaripro-agy.timer

echo "[✓] systemd timer 'naukaripro-agy.timer' enabled and started!"

# 5. Setup Crontab Fallback Entry (ensures 100% execution across any Linux environment)
CRON_JOB="45 3,9,12 * * * /bin/bash $SCRIPT_DIR/agy_schedule_runner.sh >> $SCRIPT_DIR/logs/cron_fallback.log 2>&1"
TMP_CRON="$(mktemp)"
crontab -l 2>/dev/null > "$TMP_CRON" || true

if ! grep -q "agy_schedule_runner.sh" "$TMP_CRON"; then
    echo "" >> "$TMP_CRON"
    echo "# NaukariPro AGY Autonomous Scheduler (09:15, 14:30, 18:00 IST)" >> "$TMP_CRON"
    echo "$CRON_JOB" >> "$TMP_CRON"
    crontab "$TMP_CRON"
    echo "[✓] Crontab fallback schedule installed!"
else
    echo "[*] Crontab fallback schedule already exists."
fi
rm -f "$TMP_CRON"

# 6. Verify Timer Status
echo ""
echo "========================================================================"
echo "    Active Timers on Linux Host"
echo "========================================================================"
systemctl --user list-timers --no-pager | grep -E "(UNIT|naukaripro)" || true
echo ""
echo "[✓] NaukariPro scheduled successfully with agy CLI!"
echo "[*] Recruiter Peak Schedule:"
echo "    - 09:15 AM IST (03:45 UTC)"
echo "    - 02:30 PM IST (09:00 UTC)"
echo "    - 06:00 PM IST (12:30 UTC)"
echo "[*] Logs will be recorded to: $SCRIPT_DIR/logs/"
echo "========================================================================"
