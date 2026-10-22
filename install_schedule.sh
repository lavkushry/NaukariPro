#!/bin/bash
# Installs daily 09:15 AM macOS LaunchAgent for naukariPro

PLIST_NAME="com.lavkush.naukaripro.plist"
SOURCE_PLIST="/Users/lavkushkumar/Desktop/Resume/$PLIST_NAME"
TARGET_DIR="$HOME/Library/LaunchAgents"
TARGET_PLIST="$TARGET_DIR/$PLIST_NAME"

mkdir -p "$TARGET_DIR"

# Unload previous if exists
if [ -f "$TARGET_PLIST" ]; then
    launchctl unload "$TARGET_PLIST" 2>/dev/null || true
    rm -f "$TARGET_PLIST"
fi

cp "$SOURCE_PLIST" "$TARGET_PLIST"
launchctl load "$TARGET_PLIST"

echo "[✓] naukariPro automated schedule installed successfully!"
echo "[*] It will run automatically every day at 09:15 AM IST (Peak recruiter search window)."
echo "[*] Logs will be saved to: ~/naukaripro_cron.log"
