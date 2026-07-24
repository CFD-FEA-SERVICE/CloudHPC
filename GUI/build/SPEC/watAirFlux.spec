# -*- mode: python ; coding: utf-8 -*-

# OCC (pythonocc-core / OpenCASCADE) is imported lazily at runtime by the
# CAD tab, and its hundreds of compiled submodules + TK*.dll libraries are
# not fully discoverable by static analysis — collect the whole package
# explicitly so the frozen app ships a working GEO tab.
# Requires building inside a conda env with pythonocc-core installed
# (see .github/workflows/cloudhpc-tools.yml and build/compilation.ps1).
from PyInstaller.utils.hooks import collect_all

occ_datas, occ_binaries, occ_hidden = collect_all('OCC')

block_cipher = None


a = Analysis(['../../src/xmlreader.py'],
             pathex=[],
             binaries=occ_binaries,
             datas=occ_datas,
             hiddenimports=occ_hidden,
             hookspath=[],
             hooksconfig={},
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)


# ── Qt / shared-library de-duplication ────────────────────────────────────
# "DLL load failed while importing QtWidgets: procedure not found" (Windows
# error 127) does not mean a missing DLL: it means the WRONG one was loaded.
# The conda build environment (pythonocc-core -> occt and its dependencies)
# ships its own copies of libraries that PySide6 also bundles — not only
# Qt6*.dll but also freetype, zlib, pcre2, harfbuzz, icu, zstd, brotli, ...
# PyInstaller flattens everything into one folder, so whichever copy wins the
# name collision is the one Qt gets. If it is the conda build, the exported
# symbols do not match and QtWidgets fails to import.
#
# Rule: for every file name that PySide6 provides, keep ONLY the PySide6 copy.
import os as _os

try:
    import PySide6 as _ps6
    _ps6_dir = _os.path.dirname(_ps6.__file__)
    _ps6_libs = set()
    for _root, _dirs, _files in _os.walk(_ps6_dir):
        for _f in _files:
            if _f.lower().endswith(('.dll', '.pyd')):
                _ps6_libs.add(_f.lower())
except Exception as _e:      # PySide6 missing: nothing to de-duplicate
    _ps6_libs = set()
    print('[spec] WARNING: PySide6 not importable (%s)' % _e)


def _foreign_copy(entry):
    """True if this binary shadows a library PySide6 ships, but comes from
    somewhere else (typically the conda env)."""
    dest = (entry[0] or '')
    src = (entry[1] or '')
    name = _os.path.basename(dest).lower()
    if name in _ps6_libs and 'pyside6' not in src.lower():
        return True
    # conda keeps its Qt plugins under Library\plugins
    low = src.lower()
    if '\\library\\plugins\\' in low or '/library/plugins/' in low:
        return True
    return False


_dropped = [b for b in a.binaries if _foreign_copy(b)]
for _b in _dropped:
    print('[spec] dropping shadowing copy: %s  <-  %s' % (_b[0], _b[1]))
print('[spec] PySide6 provides %d libraries; dropped %d shadowing copies'
      % (len(_ps6_libs), len(_dropped)))
a.binaries = [b for b in a.binaries if not _foreign_copy(b)]

pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)

exe = EXE(pyz,
          a.scripts, 
          [],
          exclude_binaries=True,
          name='watAirFlux',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          console=False,
          disable_windowed_traceback=False,
          target_arch=None,
          codesign_identity=None,
          entitlements_file=None , icon='icon.ico')
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas, 
               strip=False,
               upx=True,
               upx_exclude=[],
               name='watAirFlux')
