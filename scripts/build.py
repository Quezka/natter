"""Build a Natter package for the current platform.

    python scripts/build.py --deb   # Linux: dist/natter_<version>_all.deb
    python scripts/build.py --exe   # Windows: dist/Natter.exe (single portable file)

The .deb ships only Natter's own Python code and depends on the distro's PyGObject and
WebKitGTK, so it stays tiny. The .exe bundles Python and pywebview; WebView2 itself is
part of Windows 10/11. PyInstaller doesn't cross-compile, so build the .exe on Windows.
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import natter  # noqa: E402  (release metadata only; no GTK imports)

PACKAGING = ROOT / "packaging"
ASSETS = ROOT / "natter" / "assets"
BUILD = ROOT / "build"
DIST = ROOT / "dist"

DEB_DEPENDS = ("python3 (>= 3.10), python3-gi, gir1.2-gtk-3.0, gir1.2-webkit2-4.1, "
               "librsvg2-common")
LAUNCHER = """#!/bin/sh
PYTHONPATH=/usr/lib/natter exec /usr/bin/python3 -m natter "$@"
"""


def build_deb() -> Path:
    stage = BUILD / "deb"
    shutil.rmtree(stage, ignore_errors=True)
    app_id = natter.APP_ID

    shutil.copytree(ROOT / "natter", stage / "usr/lib/natter/natter",
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    launcher = stage / "usr/bin/natter"
    launcher.parent.mkdir(parents=True)
    launcher.write_text(LAUNCHER)
    launcher.chmod(0o755)
    for source, target in [
        (PACKAGING / f"{app_id}.desktop", f"usr/share/applications/{app_id}.desktop"),
        (PACKAGING / f"{app_id}.metainfo.xml", f"usr/share/metainfo/{app_id}.metainfo.xml"),
        (ASSETS / "icon.svg", f"usr/share/icons/hicolor/scalable/apps/{app_id}.svg"),
    ]:
        (stage / target).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(source, stage / target)

    control = stage / "DEBIAN/control"
    control.parent.mkdir(parents=True)
    control.write_text(f"""Package: natter
Version: {natter.__version__}
Section: net
Priority: optional
Architecture: all
Depends: {DEB_DEPENDS}
Maintainer: {natter.DEVELOPER} <{natter.MAINTAINER_EMAIL}>
Homepage: {natter.HOMEPAGE}
Description: WhatsApp Web in a lightweight native window
 Natter runs WhatsApp Web in the system webview (WebKitGTK) instead of a
 bundled browser. Not affiliated with WhatsApp or Meta.
""")
    DIST.mkdir(exist_ok=True)
    target = DIST / f"natter_{natter.__version__}_all.deb"
    subprocess.run(["dpkg-deb", "--root-owner-group", "--build", str(stage), str(target)], check=True)
    return target


def write_windows_version_file() -> Path:
    """File properties shown in Windows Explorer (Details tab) for Natter.exe."""
    parts = [int(p) for p in natter.__version__.split(".")]
    nums = tuple(parts + [0] * (4 - len(parts)))
    strings = {
        "CompanyName": natter.DEVELOPER,
        "FileDescription": f"{natter.APP_NAME}: WhatsApp Web in a lightweight native window",
        "FileVersion": natter.__version__,
        "InternalName": natter.APP_NAME,
        "LegalCopyright": f"Copyright (c) {date.today().year} {natter.DEVELOPER}",
        "OriginalFilename": f"{natter.APP_NAME}.exe",
        "ProductName": natter.APP_NAME,
        "ProductVersion": natter.__version__,
    }
    entries = ",\n          ".join(f"StringStruct({k!r}, {v!r})" for k, v in strings.items())
    BUILD.mkdir(exist_ok=True)
    target = BUILD / "windows-version.txt"
    target.write_text(f"""VSVersionInfo(
  ffi=FixedFileInfo(filevers={nums}, prodvers={nums}, mask=0x3f, flags=0x0,
                    OS=0x40004, fileType=0x1, subtype=0x0, date=(0, 0)),
  kids=[
    StringFileInfo([StringTable('040904B0', [
          {entries}])]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])]),
  ],
)
""", encoding="utf-8")
    return target


def build_exe() -> Path:
    import PyInstaller.__main__

    PyInstaller.__main__.run([
        str(ROOT / "scripts" / "launcher.py"),
        "--name", natter.APP_NAME,
        "--onefile",
        "--windowed",
        "--noconfirm",
        "--icon", str(ASSETS / "icon.png"),
        "--version-file", str(write_windows_version_file()),
        "--hidden-import", "pystray._win32",  # pystray picks its backend at runtime
        "--add-data", f"{ASSETS}{';' if sys.platform == 'win32' else ':'}natter/assets",
        "--distpath", str(DIST),
        "--workpath", str(BUILD / "pyinstaller"),
        "--specpath", str(BUILD),
    ])
    return DIST / f"{natter.APP_NAME}.exe"


def main() -> None:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--deb", action="store_true")
    mode.add_argument("--exe", action="store_true")
    args = parser.parse_args()
    print(build_deb() if args.deb else build_exe())


if __name__ == "__main__":
    main()
