#!/usr/bin/env bash
# Removes cloudHPCstorage storages of the current user. rclone and fuse3 are left installed.
# Usage:  bash uninstall.sh             remove all your storages
#         bash uninstall.sh STORAGE     remove only that storage
#         bash uninstall.sh --list      list your storages
set -euo pipefail

APP=cloudHPCstorage
REMOTE=cloudHPCstorage
KEY_NAME=cfd-fea-service-cloud.json
ME="$(id -un)"
CONF_ROOT="$HOME/.config/$APP"
BASE="$HOME/$APP"
UNIT_DIR=/etc/systemd/system
LEGACY_UNIT="$UNIT_DIR/$APP.service"

[ "$(id -u)" -ne 0 ] || { echo "Run this script as your normal user, without sudo." >&2; exit 1; }

list_storages() {
    local f
    for f in "$UNIT_DIR/$APP"-*.service; do
        [ -f "$f" ] || continue
        grep -qx "X-CloudHPC-User=$ME" "$f" || continue
        sed -n 's/^X-CloudHPC-Storage=//p' "$f"
    done
}

# Storage of the previous single-mount installation of this user ("-" if unknown)
legacy_storage() {
    [ -f "$LEGACY_UNIT" ] || return 0
    local owner
    owner="$(sed -n 's/^User=//p' "$LEGACY_UNIT")"
    [ -z "$owner" ] || [ "$owner" = "$ME" ] || return 0
    jq -r '.storage // "-"' "$CONF_ROOT/$KEY_NAME" 2>/dev/null || echo -
}

unmount() {
    if mountpoint -q "$1"; then
        fusermount3 -uz "$1" 2>/dev/null || fusermount -uz "$1" 2>/dev/null || sudo umount -l "$1" || true
    fi
}

remove_storage() {
    local unit="$APP-$ME-$1.service"
    echo "==> Removing the storage '$1'..."
    sudo systemctl disable --now "$unit" >/dev/null 2>&1 || true
    unmount "$BASE/$1"
    sudo rm -f "$UNIT_DIR/$unit"
    rm -rf "${CONF_ROOT:?}/$1"
    rmdir "$BASE/$1" 2>/dev/null || true
}

remove_legacy() {
    echo "==> Removing the previous installation..."
    sudo systemctl disable --now "$APP.service" >/dev/null 2>&1 || true
    unmount "$BASE"
    sudo rm -f "$LEGACY_UNIT" /usr/bin/cloudHPCstorage-service
    rm -f "$CONF_ROOT/$KEY_NAME" "$CONF_ROOT/rclone.conf"
}

mapfile -t STORAGES < <(list_storages | sort)
LEGACY="$(legacy_storage)"

case "${1:-}" in
    --list)
        for s in "${STORAGES[@]}"; do echo "$s    $BASE/$s"; done
        [ -z "$LEGACY" ] || echo "$LEGACY    $BASE (previous version)"
        exit 0 ;;
    -h|--help)
        sed -n '2,6p' "$0" | sed 's/^# \{0,1\}//'
        exit 0 ;;
    "")
        echo "(your sudo password may be requested)"
        for s in "${STORAGES[@]}"; do remove_storage "$s"; done
        [ -z "$LEGACY" ] || remove_legacy
        # Oldest version: remote inside the default rclone.conf + JSON key
        OLD_CONF="$HOME/.config/rclone/rclone.conf"
        if [ -f "$OLD_CONF" ] && grep -q "^\[$REMOTE\]" "$OLD_CONF" && command -v rclone >/dev/null; then
            rclone config delete "$REMOTE" --config "$OLD_CONF" || true
        fi
        rm -f "$HOME/.config/rclone/cfd-fea-service-cloud.json" ;;
    *)
        if printf '%s\n' "${STORAGES[@]}" | grep -qxF -- "$1"; then
            remove_storage "$1"
        elif [ -n "$LEGACY" ] && [ "$LEGACY" = "$1" ]; then
            remove_legacy
        else
            echo "The storage '$1' is not installed for $ME. Installed: $(list_storages | sort | tr '\n' ' ')${LEGACY}" >&2
            exit 1
        fi ;;
esac
sudo systemctl daemon-reload

if [ -z "$(list_storages)" ] && [ -z "$(legacy_storage)" ]; then
    BOOKMARKS="$HOME/.config/gtk-3.0/bookmarks"
    [ -f "$BOOKMARKS" ] && sed -i "\#^file://$BASE #d" "$BOOKMARKS"
    rmdir "$BASE" "$CONF_ROOT" 2>/dev/null || true
    echo " OK cloudHPCstorage removed."
    echo "    rclone is still installed (remove it with: sudo apt remove rclone)."
else
    echo " OK Done. Storages still mounted: $(list_storages | sort | tr '\n' ' ')$(legacy_storage)"
fi
echo "    Files still waiting in the local cache, if any: ~/.cache/rclone/vfs/$REMOTE"
