#!/bin/bash
# naukariPro Linux Remote Execution Wrapper
# Executes naukariPro seamlessly on the remote Ubuntu cloud instance (141.148.195.233)

SSH_KEY="$HOME/.ssh/ssh-key-2026-08-30.key"
REMOTE_HOST="ubuntu@141.148.195.233"
REMOTE_DIR="/home/ubuntu/Resume"

if [ $# -eq 0 ]; then
    echo "Usage: ./run_on_linux.sh [command]"
    echo "Examples:"
    echo "  ./run_on_linux.sh skill-insights"
    echo "  ./run_on_linux.sh hiring-trends"
    echo "  ./run_on_linux.sh interview-prep"
    echo "  ./run_on_linux.sh resume-maker"
    echo "  ./run_on_linux.sh bump"
    echo "  ./run_on_linux.sh daily --headless"
    exit 0
fi

ssh -i "$SSH_KEY" -o BatchMode=yes "$REMOTE_HOST" "cd $REMOTE_DIR && ./naukariPro $*"
