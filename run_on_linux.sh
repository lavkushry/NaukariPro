#!/bin/bash
# ==============================================================================
# naukariPro Linux Remote Execution Wrapper
# Executes naukariPro & agy scheduler on the remote Ubuntu instance (141.148.195.233)
# ==============================================================================

SSH_KEY="$HOME/.ssh/ssh-key-2026-08-30.key"
REMOTE_HOST="ubuntu@141.148.195.233"
REMOTE_DIR="/home/ubuntu/Resume"

if [ $# -eq 0 ]; then
    echo "Usage: ./run_on_linux.sh [command]"
    echo ""
    echo "Autonomous AGY Scheduler Commands:"
    echo "  ./run_on_linux.sh agy-schedule install    # Install systemd timer + cron fallback on Linux"
    echo "  ./run_on_linux.sh agy-schedule run        # Trigger one immediate AGY autonomous cycle"
    echo "  ./run_on_linux.sh agy-schedule status     # Check active timers & next run time"
    echo "  ./run_on_linux.sh agy-schedule logs       # View recent AGY execution logs"
    echo ""
    echo "Direct naukariPro Commands:"
    echo "  ./run_on_linux.sh pro --limit 15 --headless"
    echo "  ./run_on_linux.sh bump --headless"
    echo "  ./run_on_linux.sh daily --headless"
    echo "  ./run_on_linux.sh resume-maker"
    echo "  ./run_on_linux.sh search-all"
    exit 0
fi

if [ "$1" = "agy-schedule" ]; then
    SUB_CMD="${2:-status}"
    case "$SUB_CMD" in
        install)
            echo "[*] Installing AGY autonomous scheduler on Linux ($REMOTE_HOST)..."
            ssh -i "$SSH_KEY" -o BatchMode=yes "$REMOTE_HOST" "cd $REMOTE_DIR && git pull origin main 2>/dev/null || true; ./install_linux_schedule.sh"
            ;;
        run)
            echo "[*] Triggering immediate AGY autonomous cycle on Linux..."
            ssh -i "$SSH_KEY" -o BatchMode=yes "$REMOTE_HOST" "cd $REMOTE_DIR && ./agy_schedule_runner.sh"
            ;;
        status)
            echo "[*] Checking AGY autonomous timer status on Linux..."
            ssh -i "$SSH_KEY" -o BatchMode=yes "$REMOTE_HOST" "systemctl --user list-timers --no-pager | grep -E '(UNIT|naukaripro)'; echo '---'; crontab -l | grep -E '(agy|Naukari)' || true"
            ;;
        logs)
            echo "[*] Tailing latest AGY scheduler logs..."
            ssh -i "$SSH_KEY" -o BatchMode=yes "$REMOTE_HOST" "cd $REMOTE_DIR && tail -n 50 logs/agy_schedule_history.log 2>/dev/null || tail -n 50 logs/*.log"
            ;;
        *)
            echo "Unknown agy-schedule subcommand: $SUB_CMD (use: install | run | status | logs)"
            exit 1
            ;;
    esac
    exit 0
fi

ssh -i "$SSH_KEY" -o BatchMode=yes "$REMOTE_HOST" "cd $REMOTE_DIR && ./naukariPro $*"
