import configparser
import sys

import pytest

from natter import APP_ID, autostart


def parse(text):
    entry = configparser.ConfigParser(interpolation=None)
    entry.optionxform = str
    entry.read_string(text)
    return entry["Desktop Entry"]


def test_exec_line_quotes_only_what_needs_it():
    assert autostart.desktop_exec(["natter", "--background"]) == "natter --background"
    assert (autostart.desktop_exec(["/home/me/My Apps/python", "-m", "natter"])
            == '"/home/me/My Apps/python" -m natter')
    assert autostart.desktop_exec(['a"b$c`d\\e']) == '"a\\"b\\$c\\`d\\\\e"'


def test_entry_starts_hidden_and_is_enabled():
    entry = parse(autostart.desktop_entry(["natter", "--background"]))
    assert entry["Type"] == "Application"
    assert entry["Exec"] == "natter --background"
    assert entry["Icon"] == APP_ID
    assert entry["X-GNOME-Autostart-enabled"] == "true"


def test_launch_command_from_source_runs_the_module_in_background(monkeypatch):
    monkeypatch.delattr(sys, "frozen", raising=False)
    monkeypatch.setattr(autostart.sys, "platform", "linux")
    cmd = autostart.launch_command()
    assert cmd[0] == sys.executable
    assert cmd[1:] == ["-m", "natter", "--background"]


def test_launch_command_for_the_exe(monkeypatch):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", r"C:\Apps\Natter.exe")
    assert autostart.launch_command() == [r"C:\Apps\Natter.exe", "--background"]


@pytest.mark.skipif(sys.platform == "win32", reason="the .deb is Linux-only")
def test_launch_command_for_the_deb(monkeypatch):
    monkeypatch.delattr(sys, "frozen", raising=False)
    monkeypatch.setattr(autostart, "__file__", "/usr/lib/natter/natter/autostart.py")
    assert autostart.launch_command() == ["natter", "--background"]


def test_linux_toggle_writes_and_removes_the_entry(monkeypatch, tmp_path):
    monkeypatch.setattr(autostart.sys, "platform", "linux")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    path = tmp_path / "autostart" / f"{APP_ID}.desktop"
    autostart.set_enabled(True)
    assert "--background" in parse(path.read_text())["Exec"]
    autostart.set_enabled(False)
    assert not path.exists()
    autostart.set_enabled(False)  # already off: no error
