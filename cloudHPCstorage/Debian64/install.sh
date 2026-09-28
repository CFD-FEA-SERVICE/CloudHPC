#!/usr/bin/env bash
# cloudHPCstorage setup for Ubuntu / Debian (amd64).
# Mounts the cloudHPC storage in $HOME/cloudHPCstorage through rclone.
#
# Usage:  bash install.sh [activation-file.json]
#
# - removes any previous installation (service account version included)
# - installs rclone (bundled .deb), fuse3 and jq
# - copies the activation file (service account key + "storage" field) and writes
#   ~/.config/cloudHPCstorage/rclone.conf
# - creates and starts the systemd service cloudHPCstorage.service
# Logs: sudo journalctl -u cloudHPCstorage.service
set -euo pipefail

APP=cloudHPCstorage
REMOTE=cloudHPCstorage
KEY_NAME=cfd-fea-service-cloud.json
SUPPORT=info@cloudhpc.cloud
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONF_DIR="$HOME/.config/$APP"
CONF="$CONF_DIR/rclone.conf"
MOUNT="$HOME/$APP"
UNIT="/etc/systemd/system/$APP.service"

info() { printf '\033[1;34m==>\033[0m %s\n' "$*"; }
ok()   { printf '\033[1;32m OK\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33mWARNING:\033[0m %s\n' "$*"; }
die()  { printf '\033[1;31mERROR:\033[0m %s\n' "$*" >&2; exit 1; }

[ "$(id -u)" -ne 0 ] || die "Run this script as your normal user, without sudo: the storage is mounted for that user. The sudo password is asked when needed."
command -v apt-get >/dev/null || die "Only Debian / Ubuntu (apt) are supported."
[ -d /run/systemd/system ] || die "systemd is required."
[ "$(dpkg --print-architecture)" = amd64 ] || die "Only amd64 (x86_64) systems are supported."

# --- Activation file ----------------------------------------------------------
KEY="${1:-}"
if [ -z "$KEY" ]; then
    if [ -f "$HERE/$KEY_NAME" ]; then
        KEY="$HERE/$KEY_NAME"
    else
        for f in "$HERE"/*.json; do
            if [ -f "$f" ] && grep -q '"service_account"' "$f"; then KEY="$f"; break; fi
        done
    fi
fi
[ -n "$KEY" ] && [ -f "$KEY" ] || die "Activation file not found. Put $KEY_NAME in $HERE (or pass its path as argument). To get one write to $SUPPORT."
KEY="$(realpath "$KEY")"

DEB="$(ls -1 "$HERE"/rclone-*-linux-amd64.deb 2>/dev/null | sort -V | tail -n 1 || true)"
[ -n "$DEB" ] || die "rclone package (rclone-*-linux-amd64.deb) not found in $HERE"

# --- Packages -----------------------------------------------------------------
info "Installing rclone, fuse3 and jq (your sudo password may be requested)..."
sudo -v
sudo apt-get update -qq || warn "apt-get update failed, trying with the current package lists."
PKGS=(fuse3 jq ca-certificates)
DEB_VER="$(dpkg-deb -f "$DEB" Version)"
CUR_VER="$(rclone version 2>/dev/null | sed -n '1s/^rclone v//p' || true)"
if [ -n "$CUR_VER" ] && dpkg --compare-versions "$CUR_VER" ge "$DEB_VER"; then
    ok "rclone $CUR_VER already installed."
else
    PKGS+=("$DEB")
fi
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -qq "${PKGS[@]}"
RCLONE="$(command -v rclone)"
FUSERMOUNT="$(command -v fusermount3 || command -v fusermount)"
ok "$("$RCLONE" version | head -n 1)"

# --- Configuration --------------------------------------------------------------
jq -e '.type == "service_account" and .storage and .client_email and .private_key' "$KEY" >/dev/null 2>&1 \
    || die "$(basename "$KEY") is not a valid cloudHPCstorage activation file."
BUCKET="$(jq -r .storage "$KEY")"
[[ "$BUCKET" =~ ^[a-z0-9][a-z0-9._-]{1,221}[a-z0-9]$ ]] || die "Invalid storage name '$BUCKET' in the activation file."

write_conf() (  # $1 = destination, $2 = key file
    umask 077
    {
        echo "[$REMOTE]"
        echo "type = google cloud storage"
        echo "service_account_file = $2"
        echo "anonymous = false"
        echo "object_acl = bucketOwnerFullControl"
        echo "bucket_acl = private"
        if [ "$(jq -r '.bucket_policy_only // false' "$KEY")" = true ]; then echo "bucket_policy_only = true"; fi
    } > "$1"
)

info "Checking the access to the storage '$BUCKET'..."
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
# Work on a copy: the key may be the one of the previous installation, removed below
install -m 600 "$KEY" "$TMP/key.json"
KEY="$TMP/key.json"
write_conf "$TMP/rclone.conf" "$KEY"
if ! timeout 120 "$RCLONE" lsf "$REMOTE:$BUCKET" --max-depth 1 --config "$TMP/rclone.conf" \
        --retries 1 --low-level-retries 2 >/dev/null 2>"$TMP/err"; then
    cat "$TMP/err" >&2
    if grep -qE 'invalid_grant|invalid_client|unauthorized_client' "$TMP/err"; then
        die "Google rejected the activation file (key disabled or deleted). Please ask $SUPPORT for a new one."
    fi
    die "Cannot access the storage '$BUCKET' (see the messages above). Check the internet connection or contact $SUPPORT."
fi
ok "Access OK."

# --- Previous installation ------------------------------------------------------
info "Removing the previous installation (if any)..."
sudo systemctl disable --now "$APP.service" >/dev/null 2>&1 || true
if mountpoint -q "$MOUNT"; then
    "$FUSERMOUNT" -uz "$MOUNT" 2>/dev/null || sudo umount -l "$MOUNT" || true
fi
sudo rm -f "$UNIT" /usr/bin/cloudHPCstorage-service
# Service account version: remote inside the default rclone.conf + JSON key
OLD_CONF="$HOME/.config/rclone/rclone.conf"
if [ -f "$OLD_CONF" ] && grep -q "^\[$REMOTE\]" "$OLD_CONF"; then
    "$RCLONE" config delete "$REMOTE" --config "$OLD_CONF" || true
fi
rm -f "$HOME/.config/rclone/cfd-fea-service-cloud.json"
sudo systemctl daemon-reload

# rclone refuses to mount on a non-empty folder: keep local leftovers aside
if [ -d "$MOUNT" ] && [ -n "$(ls -A "$MOUNT" 2>/dev/null)" ]; then
    SAVED="$MOUNT.local-$(date +%Y%m%d-%H%M%S)"
    mv "$MOUNT" "$SAVED"
    warn "$MOUNT contained local files: moved to $SAVED"
fi
mkdir -p "$MOUNT"

# --- Install ------------------------------------------------------------------
info "Saving the configuration in $CONF..."
mkdir -p "$CONF_DIR"
chmod 700 "$CONF_DIR"
install -m 600 "$KEY" "$CONF_DIR/$KEY_NAME"
write_conf "$CONF" "$CONF_DIR/$KEY_NAME"

info "Creating the service $APP.service..."
sudo tee "$UNIT" >/dev/null <<EOF
[Unit]
Description=cloudHPCstorage - cloudHPC storage mounted in $MOUNT
Wants=network-online.target
After=network-online.target

[Service]
Type=notify
User=$(id -un)
Group=$(id -gn)
ExecStart=$RCLONE mount "$REMOTE:$BUCKET" "$MOUNT" --config "$CONF" --vfs-cache-mode full --log-level NOTICE
ExecStop=$FUSERMOUNT -uz "$MOUNT"
Restart=on-failure
RestartSec=15

[Install]
WantedBy=multi-user.target
EOF
sudo systemctl daemon-reload
sudo systemctl enable --now "$APP.service" >/dev/null 2>&1 || true

for _ in $(seq 1 20); do mountpoint -q "$MOUNT" && break; sleep 1; done
if ! mountpoint -q "$MOUNT"; then
    sudo journalctl -u "$APP.service" -n 30 --no-pager || true
    die "The storage could not be mounted (see the log above). Contact $SUPPORT."
fi

# Bookmark in the file manager sidebar (GNOME / Nautilus)
BOOKMARKS="$HOME/.config/gtk-3.0/bookmarks"
if [ -f "$BOOKMARKS" ] && ! grep -q "^file://$MOUNT " "$BOOKMARKS"; then
    echo "file://$MOUNT cloudHPCstorage" >> "$BOOKMARKS"
fi

echo
ok "cloudHPCstorage is ready: your storage is in $MOUNT"
echo "    It is mounted automatically at every boot."
echo "    Logs:      sudo journalctl -u $APP.service"
echo "    Uninstall: bash $HERE/uninstall.sh"
