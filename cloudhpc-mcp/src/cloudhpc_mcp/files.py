"""Local archive helpers (used only in local mode)."""

from __future__ import annotations

import os
import tarfile

UPLOAD_ARCHIVE = "upload.tar.gz"

# Result archives produced by cloudHPC (docs.cloudhpc.cloud/storage)
RESULT_PATTERNS = (
    "FDS.tar.gz",
    "OPENFOAM-solution.tar.gz", "OPENFOAM-constant.tar.gz", "OPENFOAM-system.tar.gz",
    "SATURNE-solution.tar.gz",
    "CODE-ASTER.tar.gz",
    "CALCULIX.tar.gz",
    "OPENRADIOSS.tar.gz",
)
RESULT_SUFFIXES = (".tar.gz", ".rmed", ".frd")
SKIP_PREFIXES = ("CloudHPC-massive-files",)  # e.g. CloudHPC-massive-files-20260925000914.tar.gz


def is_result_file(name: str) -> bool:
    base = os.path.basename(name)
    if base == UPLOAD_ARCHIVE or base.startswith(SKIP_PREFIXES):
        return False
    return base in RESULT_PATTERNS or base.endswith(RESULT_SUFFIXES)


def make_case_archive(folder: str, out_dir: str) -> str:
    """tar.gz the CONTENT of folder (files at archive root, hidden files skipped).

    Same layout as the bash cloudHPCexec ('tar -czf upload.tar.gz *'), i.e.
    upload method 2: archive placed inside a storage folder with the same name.
    """
    archive = os.path.join(out_dir, UPLOAD_ARCHIVE)
    with tarfile.open(archive, "w:gz", compresslevel=6) as tar:
        for entry in sorted(os.listdir(folder)):
            if entry.startswith("."):
                continue
            tar.add(os.path.join(folder, entry), arcname=entry,
                    filter=lambda ti: None if os.path.basename(ti.name).startswith(".") else ti)
    return archive


def safe_extract(archive: str, dest: str) -> int:
    """Extract a tar.gz refusing absolute paths, '..' and links outside dest."""
    dest_real = os.path.realpath(dest)
    count = 0
    with tarfile.open(archive, "r:*") as tar:
        members = []
        for m in tar.getmembers():
            target = os.path.realpath(os.path.join(dest_real, m.name))
            if not (target == dest_real or target.startswith(dest_real + os.sep)):
                raise ValueError(f"Unsafe path in archive: {m.name}")
            if m.issym() or m.islnk():
                link = os.path.realpath(os.path.join(os.path.dirname(target), m.linkname))
                if not link.startswith(dest_real + os.sep):
                    raise ValueError(f"Unsafe link in archive: {m.name}")
            if m.isdev():
                continue
            members.append(m)
        try:
            tar.extractall(dest_real, members=members, filter="data")
        except TypeError:  # Python < 3.12 without extraction filters
            tar.extractall(dest_real, members=members)
        count = len(members)
    return count
