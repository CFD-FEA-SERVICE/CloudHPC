#!/usr/bin/env bash
# Removes cloudHPCstorage (current and previous versions). rclone and fuse3 are left installed.
# Usage:  bash uninstall.sh
set -euo pipefail

APP=cloudHPCstorage
REMOTE=cloudHPCstorage
MOUNT="$HOME/$APP"

[ "$(id -u)" -ne 0 ] || { echo "Run this script as your normal user, without sudo." >&2; exit 1; }

echo "==> Stopping and removing the service (your sudo password may be requested)..."
sudo systemctl disable --now "$APP.service" >/dev/null 2>&1 || true
if mountpoint -q "$MOUNT"; then
    fusermount3 -uz "$MOUNT" 2>/dev/null || fusermount -uz "$MOUNT" 2>/dev/null || sudo umount -l "$MOUNT" || true
fi
sudo rm -f "/etc/systemd/system/$APP.service" /usr/bin/cloudHPCstorage-service
sudo systemctl daemon-reload

echo "==> Removing the configuration..."
rm -rf "$HOME/.config/$APP"
OLD_CONF="$HOME/.config/rclone/rclone.conf"
if [ -f "$OLD_CONF" ] && grep -q "^\[$REMOTE\]" "$OLD_CONF" && command -v rclone >/dev/null; then
    rclone config delete "$REMOTE" --config "$OLD_CONF" || true
fi
rm -f "$HOME/.config/rclone/cfd-fea-service-cloud.json"

BOOKMARKS="$HOME/.config/gtk-3.0/bookmarks"
[ -f "$BOOKMARKS" ] && sed -i "\#^file://$MOUNT #d" "$BOOKMARKS"
rmdir "$MOUNT" 2>/dev/null || true

echo " OK cloudHPCstorage removed."
echo "    rclone is still installed (remove it with: sudo apt remove rclone)."
echo "    Files still waiting in the local cache, if any: ~/.cache/rclone/vfs/$REMOTE"
