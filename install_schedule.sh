#!/bin/bash
# Installs Always-on Beast LaunchAgents: Block 1 (09:15), Block 2 (14:31), Block 3 (18:00)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_DIR="$HOME/Library/LaunchAgents"

mkdir -p "$TARGET_DIR"
mkdir -p "$SCRIPT_DIR/logs"
chmod +x "$SCRIPT_DIR/naukariPro" 2>/dev/null || true

install_plist() {
  local src="$1"
  local label
  label="$(basename "$src")"
  local target="$TARGET_DIR/$label"
  if [ -f "$target" ]; then
    launchctl bootout "gui/$(id -u)/${label%.plist}" 2>/dev/null || true
    launchctl unload "$target" 2>/dev/null || true
    rm -f "$target"
  fi
  # Rewrite workspace path in ProgramArguments[0] to this checkout
  /usr/bin/python3 - "$src" "$target" "$SCRIPT_DIR" <<'PY'
import plistlib, sys
src, dst, root = sys.argv[1], sys.argv[2], sys.argv[3]
with open(src, "rb") as f:
    data = plistlib.load(f)
args = data.get("ProgramArguments") or []
if args:
    args[0] = f"{root}/naukariPro"
    # Ensure autonomous drain + force for beast blocks
    if "pro" in args:
        if "--force" not in args:
            args.append("--force")
        if "--drain-pending" not in args:
            args.append("--drain-pending")
    data["ProgramArguments"] = args
with open(dst, "wb") as f:
    plistlib.dump(data, f)
print(f"[✓] Wrote {dst}")
PY
  launchctl bootstrap "gui/$(id -u)" "$target" 2>/dev/null || launchctl load "$target"
  echo "[✓] Loaded $label"
}

echo "========================================================================"
echo "  NaukariPro Always-on Beast schedule installer (macOS LaunchAgents)"
echo "========================================================================"

for plist in \
  "$SCRIPT_DIR/com.lavkush.naukaripro.plist" \
  "$SCRIPT_DIR/com.lavkush.naukaripro.block2.plist" \
  "$SCRIPT_DIR/com.lavkush.naukaripro.block3.plist"
do
  if [ -f "$plist" ]; then
    install_plist "$plist"
  else
    echo "[!] Missing $plist"
  fi
done

# Ensure morning agent runs beast-autonomous style (pro --force --drain-pending)
# block1 uses daily historically — upgrade ProgramArguments if still 'daily'
MORNING="$TARGET_DIR/com.lavkush.naukaripro.plist"
if [ -f "$MORNING" ]; then
  /usr/bin/python3 - "$MORNING" "$SCRIPT_DIR" <<'PY'
import plistlib, sys
path, root = sys.argv[1], sys.argv[2]
with open(path, "rb") as f:
    data = plistlib.load(f)
data["ProgramArguments"] = [
    f"{root}/naukariPro",
    "beast-autonomous",
    "--headless",
    "--block", "1",
    "--limit", "35",
    "--limit-external", "25",
    "--limit-redirects", "25",
]
with open(path, "wb") as f:
    plistlib.dump(data, f)
print("[✓] Morning agent set to beast-autonomous --block 1")
PY
  launchctl bootout "gui/$(id -u)/com.lavkush.naukaripro" 2>/dev/null || true
  launchctl bootstrap "gui/$(id -u)" "$MORNING" 2>/dev/null || launchctl load "$MORNING"
fi

echo
echo "[✓] Always-on Beast schedule installed."
echo "    Block 1 ~09:15  |  Block 2 ~14:31 (+outreach)  |  Block 3 ~18:00"
echo "    Manual run:  ./naukariPro beast-autonomous --block 1"
echo "    CAPTCHA: set CAPTCHA_MODE=human (default) or vendor,vendor_allowlist + keys"
echo "    Logs: ~/naukaripro_*.log and $SCRIPT_DIR/logs/"
