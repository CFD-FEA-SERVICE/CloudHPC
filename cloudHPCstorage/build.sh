#!/usr/bin/env bash
# Builds dist/cloudHPCstorage.zip for the customers.
#
# rclone and WinFsp are not stored in git: they are downloaded into vendor/ at the
# versions pinned in vendor.lock and checked against its SHA256.
#
# Usage:  ./build.sh            download the pinned rclone/WinFsp (if missing) and package
#         ./build.sh --update   pin the latest rclone (Windows + .deb) and WinFsp in
#                               vendor.lock, verifying the upstream checksums, then package
#
# Requires: zip, curl, unzip, jq, sha256sum, dpkg-deb
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WIN="$ROOT/Win64"
DEB="$ROOT/Debian64"
VENDOR="$ROOT/vendor"
LOCK="$ROOT/vendor.lock"
DIST="$ROOT/dist"

die()  { printf 'ERROR: %s\n' "$*" >&2; exit 1; }
warn() { printf '\033[1;33mWARNING:\033[0m %s\n' "$*"; }

update() {
    local ver sums win_sha deb_sha json msi_url msi_sha
    ver="$(curl -fsSL https://downloads.rclone.org/version.txt | awk '{print $2}')"
    [[ "$ver" =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]] || die "unexpected rclone version '$ver'"
    echo "==> rclone $ver"
    sums="$(curl -fsSL "https://downloads.rclone.org/$ver/SHA256SUMS")"
    win_sha="$(awk -v f="rclone-$ver-windows-amd64.zip" '$2 == f {print $1}' <<<"$sums")"
    deb_sha="$(awk -v f="rclone-$ver-linux-amd64.deb" '$2 == f {print $1}' <<<"$sums")"
    [ -n "$win_sha" ] && [ -n "$deb_sha" ] || die "checksums of rclone $ver not found"

    json="$(curl -fsSL https://api.github.com/repos/winfsp/winfsp/releases/latest)"
    msi_url="$(jq -r '[.assets[] | select(.name | endswith(".msi"))][0].browser_download_url // empty' <<<"$json")"
    msi_sha="$(jq -r '[.assets[] | select(.name | endswith(".msi"))][0].digest // empty' <<<"$json")"
    msi_sha="${msi_sha#sha256:}"
    [ -n "$msi_url" ] || die "WinFsp .msi not found in the latest GitHub release"
    echo "==> WinFsp $(basename "$msi_url")"
    if [ -z "$msi_sha" ]; then
        warn "GitHub gives no digest for $(basename "$msi_url"): pinning the SHA256 of the downloaded file"
        msi_sha="$(curl -fsSL "$msi_url" | sha256sum | cut -d' ' -f1)"
    fi

    cat > "$LOCK" <<EOF
# Third-party binaries bundled in cloudHPCstorage.zip. They are not stored in git:
# build.sh downloads them into vendor/ and checks these SHA256.
# Updated by "./build.sh --update": commit this file once the new package is tested.
RCLONE_VERSION=${ver#v}
RCLONE_WIN_ZIP_SHA256=$win_sha
RCLONE_DEB_SHA256=$deb_sha
WINFSP_URL=$msi_url
WINFSP_SHA256=$msi_sha
EOF
    echo "==> vendor.lock updated"
}

# $1 = URL, $2 = destination, $3 = expected SHA256
fetch() {
    [ -f "$2" ] && echo "$3  $2" | sha256sum -c --quiet 2>/dev/null && return 0
    echo "==> downloading $(basename "$2")"
    curl -fL --progress-bar -o "$2.part" "$1"
    echo "$3  $2.part" | sha256sum -c --quiet || { rm -f "$2.part"; die "checksum mismatch for $1"; }
    mv "$2.part" "$2"
}

vendor() {
    mkdir -p "$VENDOR"
    fetch "https://downloads.rclone.org/v$RCLONE_VERSION/$RCLONE_WIN_ZIP" "$VENDOR/$RCLONE_WIN_ZIP" "$RCLONE_WIN_ZIP_SHA256"
    fetch "https://downloads.rclone.org/v$RCLONE_VERSION/$RCLONE_DEB" "$VENDOR/$RCLONE_DEB" "$RCLONE_DEB_SHA256"
    fetch "$WINFSP_URL" "$VENDOR/$WINFSP_MSI" "$WINFSP_SHA256"
}

package() {
    local stage pkg exe_ok=0
    for cmd in zip unzip sha256sum dpkg-deb; do command -v "$cmd" >/dev/null || die "$cmd not found"; done

    if [ -f "$WIN/install.exe" ] && [ -f "$WIN/install.exe.sha256" ] &&
       [ "$(sha256sum "$WIN/install.ps1" | cut -d' ' -f1)" = "$(tr -d '[:space:]' < "$WIN/install.exe.sha256")" ]; then
        exe_ok=1
    else
        warn "Win64/install.exe missing or older than install.ps1: NOT included."
        warn "Rebuild it on Windows with admin/build-exe.ps1 (customers can use install.cmd meanwhile)."
    fi

    stage="$(mktemp -d)"
    trap 'rm -rf "$stage"' RETURN
    pkg="$stage/cloudHPCstorage"
    mkdir -p "$pkg/Win64" "$pkg/Debian64"

    unzip -q -j "$VENDOR/$RCLONE_WIN_ZIP" '*/rclone.exe' -d "$pkg/Win64"
    cp "$VENDOR/$WINFSP_MSI" "$WIN/install.ps1" "$WIN/install.cmd" "$WIN/uninstall.cmd" "$pkg/Win64/"
    [ "$exe_ok" = 1 ] && cp "$WIN/install.exe" "$pkg/Win64/"
    cp "$VENDOR/$RCLONE_DEB" "$DEB/install.sh" "$DEB/uninstall.sh" "$pkg/Debian64/"
    chmod 755 "$pkg/Debian64/"*.sh
    cp "$ROOT/INSTALL.md" "$pkg/"

    {
        echo "cloudHPCstorage package built on $(date -Iseconds)"
        echo "rclone (Windows): $RCLONE_VERSION"
        echo "rclone (Linux):   $(dpkg-deb -f "$VENDOR/$RCLONE_DEB" Version)"
        echo "WinFsp:           $(basename "$WINFSP_MSI" .msi | sed 's/^winfsp-//')"
        echo "Setup:            $(sed -n "s/^\$SetupVersion *= *'\(.*\)'.*/\1/p" "$WIN/install.ps1")"
    } > "$pkg/VERSIONS.txt"

    # Windows text files with CRLF line endings
    for f in "$pkg"/Win64/*.ps1 "$pkg"/Win64/*.cmd "$pkg"/*.txt "$pkg"/*.md; do sed -i 's/\r*$/\r/' "$f"; done

    # Never ship a credential by mistake
    if find "$pkg" -name '*.json' | grep -q .; then die "a .json file ended up in the package"; fi

    mkdir -p "$DIST"
    rm -f "$DIST/cloudHPCstorage.zip"
    (cd "$stage" && zip -q -r -X "$DIST/cloudHPCstorage.zip" cloudHPCstorage)
    cp "$pkg/VERSIONS.txt" "$DIST/VERSIONS.txt"
    echo
    sed 's/\r$//' "$pkg/VERSIONS.txt"
    echo
    echo "==> $DIST/cloudHPCstorage.zip ($(du -h "$DIST/cloudHPCstorage.zip" | cut -f1))"
    (cd "$stage" && find cloudHPCstorage -type f | sort | sed 's/^/    /')
}

case "${1:-}" in
    --update) update ;;
    "")       ;;
    *)        die "usage: $0 [--update]" ;;
esac

# shellcheck source=vendor.lock
. "$LOCK"
RCLONE_WIN_ZIP="rclone-v$RCLONE_VERSION-windows-amd64.zip"
RCLONE_DEB="rclone-v$RCLONE_VERSION-linux-amd64.deb"
WINFSP_MSI="$(basename "$WINFSP_URL")"
vendor
package
