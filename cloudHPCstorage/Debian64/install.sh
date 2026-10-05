#!/usr/bin/env bash
# cloudHPCstorage setup for Ubuntu / Debian (amd64).
# Mounts a cloudHPC storage in $HOME/cloudHPCstorage/<storage> through rclone.
#
# Usage:  bash install.sh [activation-file.json]
#
# Several storages can be mounted at the same time: run the script once per
# activation file. Each storage has its own folder, configuration and systemd
# service (cloudHPCstorage-<user>-<storage>.service); installing an activation file
# whose storage is already mounted replaces only that mount. Other users of the same
# machine can install their own storages too.
#
# - converts the previous single-mount installation (storage mounted directly in
#   ~/cloudHPCstorage) to this layout, keeping its storage mounted
# - installs rclone (bundled .deb), fuse3 and jq
# - copies the activation file (service account key + "storage" field) and writes
#   ~/.config/cloudHPCstorage/<storage>/rclone.conf
# - creates and starts the systemd service of the storage
# Logs: sudo journalctl -u 'cloudHPCstorage-*'
set -euo pipefail

APP=cloudHPCstorage
REMOTE=cloudHPCstorage
KEY_NAME=cfd-fea-service-cloud.json
SUPPORT=info@cloudhpc.cloud
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ME="$(id -un)"
CONF_ROOT="$HOME/.config/$APP"
BASE="$HOME/$APP"
UNIT_DIR=/etc/systemd/system
# Previous layout: a single storage, mounted in $BASE itself by $APP.service
LEGACY_UNIT="$UNIT_DIR/$APP.service"
BUCKET_RE='^[a-z0-9][a-z0-9._-]{1,221}[a-z0-9]$'

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

# --- Helpers --------------------------------------------------------------------
unit_name() { printf '%s-%s-%s.service' "$APP" "$ME" "$1"; }  # $1 = storage

list_storages() {  # storages mounted by this user, one per line
    local f
    for f in "$UNIT_DIR/$APP"-*.service; do
        [ -f "$f" ] || continue
        grep -qx "X-CloudHPC-User=$ME" "$f" || continue
        sed -n 's/^X-CloudHPC-Storage=//p' "$f"
    done
}

unmount() {  # $1 = folder
    if mountpoint -q "$1"; then
        "$FUSERMOUNT" -uz "$1" 2>/dev/null || sudo umount -l "$1" || true
    fi
}

set_aside() {  # $1 = folder: rclone does not mount on a non-empty folder, keep local leftovers
    if [ -d "$1" ] && [ -n "$(ls -A "$1" 2>/dev/null)" ]; then
        local saved
        saved="$1.local-$(date +%Y%m%d-%H%M%S)"
        mv "$1" "$saved"
        warn "$1 contained local files: moved to $saved"
    fi
}

write_conf() (  # $1 = destination, $2 = key file
    umask 077
    {
        echo "[$REMOTE]"
        echo "type = google cloud storage"
        echo "service_account_file = $2"
        echo "anonymous = false"
        echo "object_acl = bucketOwnerFullControl"
        echo "bucket_acl = private"
        if [ "$(jq -r '.bucket_policy_only // false' "$2")" = true ]; then echo "bucket_policy_only = true"; fi
    } > "$1"
)

remove_storage() {  # $1 = storage: stops and removes its service, mount and configuration
    local unit
    unit="$(unit_name "$1")"
    sudo systemctl disable --now "$unit" >/dev/null 2>&1 || true
    unmount "$BASE/$1"
    sudo rm -f "$UNIT_DIR/$unit"
    rm -rf "${CONF_ROOT:?}/$1"
}

install_storage() {  # $1 = key file, $2 = storage; returns 1 if the mount does not start
    local key="$1" bucket="$2" dir="$CONF_ROOT/$2" mnt="$BASE/$2" unit
    unit="$(unit_name "$bucket")"
    info "Mounting the storage '$bucket' in $mnt..."
    mkdir -p "$dir"
    chmod 700 "$CONF_ROOT" "$dir"
    install -m 600 "$key" "$dir/$KEY_NAME"
    write_conf "$dir/rclone.conf" "$dir/$KEY_NAME"
    set_aside "$mnt"
    mkdir -p "$mnt"

    sudo tee "$UNIT_DIR/$unit" >/dev/null <<EOF
[Unit]
Description=cloudHPCstorage - storage $bucket mounted in $mnt
Wants=network-online.target
After=network-online.target
X-CloudHPC-User=$ME
X-CloudHPC-Storage=$bucket

[Service]
Type=notify
User=$ME
Group=$(id -gn)
ExecStart=$RCLONE mount "$REMOTE:$bucket" "$mnt" --config "$dir/rclone.conf" --vfs-cache-mode full --log-level NOTICE
ExecStop=$FUSERMOUNT -uz "$mnt"
Restart=on-failure
RestartSec=15

[Install]
WantedBy=multi-user.target
EOF
    sudo systemctl daemon-reload
    sudo systemctl enable --now "$unit" >/dev/null 2>&1 || true

    for _ in $(seq 1 20); do mountpoint -q "$mnt" && return 0; sleep 1; done
    sudo journalctl -u "$unit" -n 30 --no-pager || true
    return 1
}

# Previous single-mount installation of this user: stopped and removed; its storage,
# when different from the one being installed, is mounted again in the new layout.
MIGRATE_KEY="" MIGRATE_BUCKET=""
migrate_legacy() {  # $1 = storage being installed
    [ -f "$LEGACY_UNIT" ] || return 0
    local owner old_key="$CONF_ROOT/$KEY_NAME" old_bucket=""
    owner="$(sed -n 's/^User=//p' "$LEGACY_UNIT")"
    if [ -n "$owner" ] && [ "$owner" != "$ME" ]; then
        warn "The previous cloudHPCstorage installation of user '$owner' is left untouched."
        return 0
    fi
    [ -f "$old_key" ] && old_bucket="$(jq -r '.storage // empty' "$old_key" 2>/dev/null || true)"
    info "Converting the previous installation (storage '${old_bucket:-?}' mounted in $BASE)..."
    sudo systemctl disable --now "$APP.service" >/dev/null 2>&1 || true
    unmount "$BASE"
    sudo rm -f "$LEGACY_UNIT" /usr/bin/cloudHPCstorage-service
    sudo systemctl daemon-reload
    set_aside "$BASE"
    if [[ "$old_bucket" =~ $BUCKET_RE ]] && [ "$old_bucket" != "$1" ]; then
        install -m 600 "$old_key" "$TMP/legacy-key.json"
        MIGRATE_KEY="$TMP/legacy-key.json" MIGRATE_BUCKET="$old_bucket"
    fi
    rm -f "$old_key" "$CONF_ROOT/rclone.conf"
}

# --- Configuration --------------------------------------------------------------
jq -e '.type == "service_account" and .storage and .client_email and .private_key' "$KEY" >/dev/null 2>&1 \
    || die "$(basename "$KEY") is not a valid cloudHPCstorage activation file."
BUCKET="$(jq -r .storage "$KEY")"
[[ "$BUCKET" =~ $BUCKET_RE ]] || die "Invalid storage name '$BUCKET' in the activation file."

info "Checking the access to the storage '$BUCKET'..."
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
# Work on a copy: the key may be the one of the installation removed below
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
info "Removing the previous installation of '$BUCKET' (if any)..."
migrate_legacy "$BUCKET"
# Oldest version: remote inside the default rclone.conf + JSON key
OLD_CONF="$HOME/.config/rclone/rclone.conf"
if [ -f "$OLD_CONF" ] && grep -q "^\[$REMOTE\]" "$OLD_CONF"; then
    "$RCLONE" config delete "$REMOTE" --config "$OLD_CONF" || true
fi
rm -f "$HOME/.config/rclone/cfd-fea-service-cloud.json"
remove_storage "$BUCKET"
sudo systemctl daemon-reload

# --- Install ------------------------------------------------------------------
mkdir -p "$BASE"
install_storage "$KEY" "$BUCKET" || die "The storage '$BUCKET' could not be mounted (see the log above). Contact $SUPPORT."

if [ -n "$MIGRATE_KEY" ]; then
    remove_storage "$MIGRATE_BUCKET"
    install_storage "$MIGRATE_KEY" "$MIGRATE_BUCKET" \
        || warn "The previous storage '$MIGRATE_BUCKET' could not be mounted again: run this script with its activation file."
fi

# Bookmark in the file manager sidebar (GNOME / Nautilus)
BOOKMARKS="$HOME/.config/gtk-3.0/bookmarks"
if [ -f "$BOOKMARKS" ] && ! grep -q "^file://$BASE " "$BOOKMARKS"; then
    echo "file://$BASE cloudHPCstorage" >> "$BOOKMARKS"
fi

echo
ok "cloudHPCstorage is ready: your storage '$BUCKET' is in $BASE/$BUCKET"
echo "    Storages mounted for $ME (automatically at every boot):"
list_storages | sort | sed "s|^|        $BASE/|"
echo "    Add another storage: bash $HERE/install.sh <activation-file.json>"
echo "    Logs:      sudo journalctl -u '$APP-$ME-*'"
echo "    Uninstall: bash $HERE/uninstall.sh [storage]"
