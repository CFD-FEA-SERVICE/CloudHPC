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

# ── Qt de-duplication ─────────────────────────────────────────────────────
# The conda build environment (pythonocc-core and its dependencies) can ship
# its own Qt runtime under Library\bin and Library\plugins. If those DLLs end
# up in the bundle they get loaded instead of the ones PySide6 was compiled
# against, and QtWidgets then fails at import with
#   "DLL load failed while importing QtWidgets: procedure not found"
# Keep only the Qt runtime that ships inside PySide6 itself.
import os as _os


def _foreign_qt(entry):
    dest = (entry[0] or '').lower()
    src = (entry[1] or '').lower()
    name = _os.path.basename(dest)
    if (name.startswith('qt6') or name.startswith('qt5')) and 'pyside6' not in src:
        return True
    if '\\library\\plugins\\' in src or '/library/plugins/' in src:
        return True
    return False


_dropped = [b for b in a.binaries if _foreign_qt(b)]
for _b in _dropped:
    print('[spec] dropping non-PySide6 Qt binary: %s  <-  %s' % (_b[0], _b[1]))
print('[spec] dropped %d non-PySide6 Qt binaries' % len(_dropped))
a.binaries = [b for b in a.binaries if not _foreign_qt(b)]

pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)

exe = EXE(pyz,
          a.scripts, 
          [],
          exclude_binaries=True,
          name='fea',
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
               name='fea')
