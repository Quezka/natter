import hashlib
import io
import json
import urllib.error
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from natter.state import Preferences
from natter.updates import (
    AvailableUpdate, DebInstaller, GitHubReleaseFeed, NoInstaller, ReleaseAsset, ReleaseInfo,
    UpdateError, Updater, WindowsSetupInstaller, parse_version,
)

DEB = ReleaseAsset("natter_9.0.0_all.deb", "https://x/n.deb", 10, None)
EXE = ReleaseAsset("Natter-9.0.0-windows-x64-setup.exe", "https://x/n.exe", 10, None)


class Response(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *_a):
        self.close()


def opener_for(payload=None, error=None, body=b""):
    def opener(request, timeout=0):
        if error:
            raise error
        return Response(json.dumps(payload).encode() if payload is not None else body)
    return opener


RELEASE = {"tag_name": "v9.0.0", "body": "- new", "html_url": "https://x/r", "draft": False,
           "prerelease": False, "assets": [
               {"name": DEB.name, "browser_download_url": DEB.url, "size": 10,
                "digest": "sha256:" + hashlib.sha256(b"0123456789").hexdigest()}]}


def test_versions_compare_numerically():
    assert parse_version("v0.10.0") > parse_version("0.9.9") > parse_version("0.9")
    assert parse_version("garbage") == (0,)


def test_feed_reads_the_latest_release():
    release = GitHubReleaseFeed("a/b", "0.5.0", opener_for(RELEASE)).latest()
    assert release.version == "9.0.0" and release.assets[0].name == DEB.name
    assert release.assets[0].sha256 == hashlib.sha256(b"0123456789").hexdigest()


@pytest.mark.parametrize("data", [dict(RELEASE, draft=True), dict(RELEASE, prerelease=True)])
def test_drafts_and_prereleases_are_ignored(data):
    assert GitHubReleaseFeed("a/b", "1", opener_for(data)).latest() is None


def http_error(code):
    return urllib.error.HTTPError("u", code, "x", {}, None)


def test_no_release_or_a_private_repo_is_not_an_error():
    assert GitHubReleaseFeed("a/b", "1", opener_for(error=http_error(404))).latest() is None


@pytest.mark.parametrize("error, text", [
    (http_error(403), "limiting"), (http_error(500), r"error \(500\)"),
    (urllib.error.URLError("down"), "Can't reach GitHub")])
def test_feed_problems_become_messages(error, text):
    with pytest.raises(UpdateError, match=text):
        GitHubReleaseFeed("a/b", "1", opener_for(error=error)).latest()


def test_garbage_from_github_is_an_error():
    with pytest.raises(UpdateError, match="doesn't understand"):
        GitHubReleaseFeed("a/b", "1", opener_for(body=b"<html>")).latest()


def test_download_checks_size_and_checksum(tmp_path):
    asset = ReleaseAsset("n.deb", "https://x/n.deb", 10, hashlib.sha256(b"0123456789").hexdigest())
    feed = GitHubReleaseFeed("a/b", "1", lambda r, timeout=0: Response(b"0123456789"), tmp_path)
    seen = []
    path = feed.download(asset, lambda done, total: seen.append((done, total)))
    assert Path(path).read_bytes() == b"0123456789" and seen[-1] == (10, 10)
    bad = ReleaseAsset("n.deb", "https://x/u", 10, "0" * 64)
    with pytest.raises(UpdateError, match="damaged"):
        feed.download(bad, lambda *_a: None)
    assert not list(tmp_path.glob("*.part"))
    short = ReleaseAsset("m.deb", "https://x/u", 99, None)
    with pytest.raises(UpdateError, match="damaged"):
        feed.download(short, lambda *_a: None)


class FakeFeed:
    def __init__(self, release=None):
        self.release, self.downloads = release, []

    def latest(self):
        return self.release

    def download(self, asset, progress):
        progress(5, 10)
        self.downloads.append(asset.name)
        return "/tmp/" + asset.name


class FakeInstaller:
    def __init__(self, supported=True, takes_over=False):
        self._supported, self.takes_over, self.installed = supported, takes_over, []

    def supported(self):
        return self._supported

    def pick(self, assets):
        return next((a for a in assets if a.name.endswith(".deb")), None)

    def install(self, path):
        self.installed.append(path)
        return self.takes_over


def updater(release=None, installer=None, now=datetime(2026, 10, 2, 10), prefs=None):
    prefs = prefs if prefs is not None else Preferences()
    saved = []
    result = Updater(FakeFeed(release), installer or FakeInstaller(), prefs,
                     lambda: saved.append(True), "0.5.0", lambda: now)
    result.saved = saved
    result.prefs = prefs
    return result


def info(version="9.0.0"):
    return ReleaseInfo(version, "- notes", "https://x/r", (DEB,))


def test_only_a_newer_release_is_an_update():
    assert updater(info("0.5.0")).check() is None
    assert updater(info("0.4.9")).check() is None
    assert updater(None).check() is None
    found = updater(info()).check()
    assert found.version == "9.0.0" and found.asset == DEB and found.can_install


def test_an_unsupported_install_points_at_the_download_page():
    found = updater(info(), FakeInstaller(supported=False)).check()
    assert found.asset == DEB and not found.can_install


def test_a_release_without_a_file_for_this_computer():
    release = ReleaseInfo("9.0.0", "", "u", (EXE,))
    found = updater(release).check()
    assert found.asset is None and not found.can_install
    with pytest.raises(UpdateError, match="no download"):
        updater(release).download(found, lambda *_a: None)


def test_the_check_is_due_about_once_a_day_and_only_when_allowed():
    now = datetime(2026, 10, 2, 10)
    fresh = updater(now=now)
    assert fresh.due()
    fresh.mark_checked()
    assert not fresh.due() and fresh.saved
    later = updater(now=now + timedelta(hours=21), prefs=fresh.prefs)
    assert later.due()
    later.set_auto_check(False)
    assert not later.due() and not later.auto_check()
    assert updater(prefs=Preferences(update_last_check="junk")).due()


def test_skipping_a_version_is_remembered_for_that_version_only():
    u = updater()
    u.skip("9.0.0")
    assert u.skipped("9.0.0") and not u.skipped("9.1.0") and u.saved


def test_download_then_install():
    u = updater(info())
    found = u.check()
    path = u.download(found, lambda *_a: None)
    assert path.endswith(DEB.name) and u.install(path) is False


def test_preferences_round_trip_the_update_choices(tmp_path):
    path = tmp_path / "p.json"
    Preferences(auto_update_check=False, update_last_check="x", update_skipped="1.0").save(path)
    loaded = Preferences.load(path)
    assert (loaded.auto_update_check, loaded.update_last_check, loaded.update_skipped) == (
        False, "x", "1.0")


def test_deb_installer_only_for_the_packaged_copy_and_picks_the_all_package(tmp_path):
    calls = []

    class Done:
        returncode, stdout, stderr = 0, "", ""

    deb = DebInstaller("/usr/lib/natter/natter", lambda cmd, **kw: calls.append(cmd) or Done())
    assert deb.pick((EXE, DEB)) == DEB and deb.pick((EXE,)) is None
    assert deb.install("/tmp/x.deb") is False
    assert calls[0][:3] == ["pkexec", "apt-get", "install"] and calls[0][-1] == "/tmp/x.deb"
    assert not DebInstaller(str(tmp_path)).supported()  # running from source


@pytest.mark.parametrize("code, text", [(126, "cancelled"), (127, "cancelled"), (100, "failed: boom")])
def test_install_failures_are_explained(code, text):
    class Failed:
        returncode, stdout, stderr = code, "", "boom"

    deb = DebInstaller("/usr/lib/natter/natter", lambda *a, **k: Failed())
    with pytest.raises(UpdateError, match=text):
        deb.install("/tmp/x.deb")


def test_windows_setup_runs_silently_and_takes_over(tmp_path):
    launched = []
    win = WindowsSetupInstaller(str(tmp_path / "Natter.exe"),
                                lambda cmd, **kw: launched.append(cmd))
    assert win.pick((DEB, EXE)) == EXE and not win.supported()
    assert win.install("C:/x/setup.exe") is True
    assert launched[0][0] == "C:/x/setup.exe" and "/SILENT" in launched[0]


def test_other_installs_cannot_update_themselves():
    assert not NoInstaller().supported() and NoInstaller().pick((DEB,)) is None
    with pytest.raises(UpdateError):
        NoInstaller().install("x")
    assert isinstance(AvailableUpdate("1", "0", "", "", None, False), AvailableUpdate)
