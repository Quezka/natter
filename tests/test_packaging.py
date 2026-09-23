"""Packaging metadata stays in sync with natter/__init__.py."""
import ast
import configparser
import importlib.util
import xml.etree.ElementTree as ET
from pathlib import Path

import natter

ROOT = Path(__file__).resolve().parent.parent
PACKAGING = ROOT / "packaging"
DESKTOP = PACKAGING / f"{natter.APP_ID}.desktop"
METAINFO = PACKAGING / f"{natter.APP_ID}.metainfo.xml"


def metainfo():
    return ET.parse(METAINFO).getroot()


def load_script(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_metainfo_identifies_app_and_developer():
    root = metainfo()
    assert root.findtext("id") == natter.APP_ID
    assert root.findtext("name") == natter.APP_NAME
    developer = root.find("developer")
    assert developer.get("id") == natter.DEVELOPER_ID
    assert developer.findtext("name") == natter.DEVELOPER
    assert root.find("url[@type='homepage']").text == natter.HOMEPAGE
    assert root.findtext("update_contact") == natter.MAINTAINER_EMAIL


def test_current_version_is_the_newest_release():
    releases = metainfo().findall("releases/release")
    assert releases, "metainfo has no <release> entries"
    assert releases[0].get("version") == natter.__version__, (
        f"add <release version=\"{natter.__version__}\"> at the top of {METAINFO.name}")


def test_desktop_file_points_at_app_id():
    entry = configparser.ConfigParser(interpolation=None)
    entry.optionxform = str
    entry.read(DESKTOP, encoding="utf-8")
    assert entry["Desktop Entry"]["Icon"] == natter.APP_ID
    assert entry["Desktop Entry"]["StartupWMClass"] == natter.APP_ID
    assert entry["Desktop Entry"]["Exec"].split()[0] == "natter"


def test_windows_version_file_names_the_publisher(tmp_path, monkeypatch):
    build = load_script("build")
    monkeypatch.setattr(build, "BUILD", tmp_path)
    text = build.write_windows_version_file().read_text(encoding="utf-8")
    ast.parse(text)
    assert f"'CompanyName', '{natter.DEVELOPER}'" in text
    assert f"'ProductVersion', '{natter.__version__}'" in text
    assert f"{natter.DEVELOPER}'" in text.split("LegalCopyright")[1].splitlines()[0]


def test_changelog_has_notes_for_current_version():
    notes = load_script("release_notes").notes_for(natter.__version__)
    assert notes and not notes.startswith("## ")
