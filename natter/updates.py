"""Updating Natter from GitHub releases: the feed, an installer per platform, and the rules
(when to check, what to skip). No windows here: the backends show the dialogs.

- Linux (the .deb, which lives in /usr/lib/natter): the new .deb is installed with `pkexec
  apt-get`, which asks for your password in the system's own dialog; then Natter restarts.
- Windows (installed with the setup wizard): the new setup runs silently; it closes Natter,
  upgrades it in place and starts it again.
- Anything else (running from source, a portable build): the dialog links to the release
  page instead.

The repository has to be public for GitHub to answer without a token.
"""
from __future__ import annotations

import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable

import natter
from natter.i18n import _

API = "https://api.github.com/repos/{repo}/releases/latest"
CHUNK = 256 * 1024
CHECK_EVERY = timedelta(hours=20)
DEB_PREFIX = Path("/usr/lib/natter")


class UpdateError(Exception):
    """Something the user can understand; the message is shown (already translated)."""


@dataclass(frozen=True)
class ReleaseAsset:
    name: str
    url: str
    size: int
    sha256: str | None = None  # the checksum GitHub publishes, when it does


@dataclass(frozen=True)
class ReleaseInfo:
    version: str
    notes: str
    page_url: str
    assets: tuple[ReleaseAsset, ...]


@dataclass(frozen=True)
class AvailableUpdate:
    version: str
    current: str
    notes: str
    page_url: str
    asset: ReleaseAsset | None  # the file for this computer
    can_install: bool  # False: send the user to the download page instead


def parse_version(text: str) -> tuple[int, ...]:
    """"v0.11.0" -> (0, 11, 0); anything unparseable sorts as oldest."""
    numbers = re.findall(r"\d+", text.split("-")[0])
    return tuple(int(n) for n in numbers[:3]) if numbers else (0,)


# ---- the feed ----------------------------------------------------------------------

class GitHubReleaseFeed:
    def __init__(self, repo: str, version: str, opener: Callable = urllib.request.urlopen,
                 folder: Path | None = None, timeout: float = 30):
        self._repo = repo
        self._headers = {"Accept": "application/vnd.github+json",
                         "User-Agent": f"Natter/{version}"}
        self._open = opener
        self._folder = folder
        self._timeout = timeout

    def latest(self) -> ReleaseInfo | None:
        request = urllib.request.Request(API.format(repo=self._repo), headers=self._headers)
        try:
            with self._open(request, timeout=self._timeout) as response:
                data = json.loads(response.read().decode())
        except urllib.error.HTTPError as e:
            if e.code == 404:  # no release yet, or the repository isn't public
                return None
            if e.code in (403, 429):
                raise UpdateError(_("GitHub is limiting update checks right now: try again "
                                    "in an hour.")) from e
            raise UpdateError(_("GitHub answered with an error ({code}).").format(
                code=e.code)) from e
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            raise UpdateError(_("Can't reach GitHub to check for updates. Check your internet "
                                "connection.")) from e
        except ValueError as e:
            raise UpdateError(_("GitHub sent an answer Natter doesn't understand.")) from e
        if data.get("draft") or data.get("prerelease"):
            return None
        assets = []
        for a in data.get("assets", []):
            digest = a.get("digest") or ""
            assets.append(ReleaseAsset(a["name"], a["browser_download_url"], int(a["size"]),
                                       digest.split(":", 1)[1] if digest.startswith("sha256:")
                                       else None))
        return ReleaseInfo(data["tag_name"].lstrip("v"), data.get("body") or "",
                           data.get("html_url", ""), tuple(assets))

    def download(self, asset: ReleaseAsset, progress: Callable[[int, int], None]) -> str:
        folder = self._folder or Path(tempfile.gettempdir()) / "natter-update"
        folder.mkdir(parents=True, exist_ok=True)
        target = folder / Path(asset.name).name
        partial = target.with_name(target.name + ".part")
        request = urllib.request.Request(asset.url, headers={"User-Agent":
                                                             self._headers["User-Agent"]})
        digest, done = hashlib.sha256(), 0
        try:
            with self._open(request, timeout=self._timeout) as response, \
                    open(partial, "wb") as out:
                while chunk := response.read(CHUNK):
                    out.write(chunk)
                    digest.update(chunk)
                    done += len(chunk)
                    progress(done, asset.size)
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            partial.unlink(missing_ok=True)
            raise UpdateError(_("The download didn't finish. Check your internet connection "
                                "and try again.")) from e
        if done != asset.size or (asset.sha256 and digest.hexdigest() != asset.sha256.lower()):
            partial.unlink(missing_ok=True)
            raise UpdateError(_("The download was damaged (its checksum doesn't match), so it "
                                "wasn't installed. Try again."))
        partial.replace(target)
        return str(target)


# ---- installers ----------------------------------------------------------------------

def deb_architecture() -> str:
    machine = platform.machine().lower()
    return {"x86_64": "amd64", "amd64": "amd64", "aarch64": "arm64", "arm64": "arm64"}.get(
        machine, machine)


class DebInstaller:
    """For the .deb build (Python code in /usr/lib/natter, no bundled runtime)."""

    def __init__(self, code_dir: str | None = None, runner: Callable = subprocess.run):
        self._code = Path(code_dir or Path(natter.__file__).resolve().parent)
        self._run = runner

    def supported(self) -> bool:
        return self._code.is_relative_to(DEB_PREFIX) and shutil.which("pkexec") is not None

    def pick(self, assets):
        # The package has no compiled code, so it is built once for every architecture.
        return next((a for a in assets if a.name.endswith("_all.deb")), None) or next(
            (a for a in assets if a.name.endswith(f"_{deb_architecture()}.deb")), None)

    def install(self, path: str) -> bool:
        # pkexec shows the system's password dialog; apt checks the package and upgrades.
        result = self._run(["pkexec", "apt-get", "install", "-y", "--allow-downgrades",
                            os.path.abspath(path)], capture_output=True, text=True)
        if result.returncode in (126, 127):
            raise UpdateError(_("Installing was cancelled."))
        if result.returncode != 0:
            detail = (result.stderr or result.stdout or "").strip().splitlines()[-1:]
            raise UpdateError(_("Installing the update failed: {detail}").format(
                detail=detail[0] if detail else "?"))
        return False  # installed: restart to use it


class WindowsSetupInstaller:
    """For the copy installed by the setup wizard (it has an uninstaller next to it)."""

    def __init__(self, executable: str | None = None, launcher: Callable = subprocess.Popen):
        self._executable = Path(executable or sys.executable)
        self._launch = launcher

    def supported(self) -> bool:
        return getattr(sys, "frozen", False) and any(self._executable.parent.glob("unins*.exe"))

    def pick(self, assets):
        return next((a for a in assets if a.name.endswith("-windows-x64-setup.exe")), None)

    def install(self, path: str) -> bool:
        flags = getattr(subprocess, "DETACHED_PROCESS", 0) | getattr(
            subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
        try:
            self._launch([path, "/SILENT", "/SUPPRESSMSGBOXES", "/NORESTART",
                          "/CLOSEAPPLICATIONS"], creationflags=flags, close_fds=True)
        except OSError as e:
            raise UpdateError(_("Couldn't start the installer.")) from e
        return True  # setup takes over: quit so it can replace the files


class NoInstaller:
    """Running from source or a portable build: point at the download page instead."""

    def supported(self) -> bool:
        return False

    def pick(self, assets):
        return None

    def install(self, path: str) -> bool:
        raise UpdateError(_("This copy of Natter can't update itself."))


def platform_installer():
    if sys.platform == "win32":
        return WindowsSetupInstaller()
    if sys.platform.startswith("linux"):
        return DebInstaller()
    return NoInstaller()


# ---- the rules -----------------------------------------------------------------------

class Updater:
    """When to check, what to skip, and the three steps. `check` and `download` only use the
    network and `install` may wait for the system installer: run them off the UI thread.
    The choices live in the preferences (`auto_update_check`, `update_last_check`,
    `update_skipped`); `save` writes them out."""

    def __init__(self, feed, installer, prefs, save: Callable[[], None],
                 current_version: str = natter.__version__,
                 now: Callable[[], datetime] = datetime.now):
        self._feed, self._installer, self._prefs, self._save = feed, installer, prefs, save
        self._now = now
        self.current_version = current_version

    def auto_check(self) -> bool:
        return self._prefs.auto_update_check

    def set_auto_check(self, on: bool) -> None:
        self._prefs.auto_update_check = on
        self._save()

    def due(self) -> bool:
        """Time for the automatic check (about once a day)."""
        if not self.auto_check():
            return False
        last = self._prefs.update_last_check
        try:
            return not last or self._now() - datetime.fromisoformat(last) >= CHECK_EVERY
        except ValueError:
            return True

    def mark_checked(self) -> None:
        self._prefs.update_last_check = self._now().isoformat(timespec="seconds")
        self._save()

    def skip(self, version: str) -> None:
        self._prefs.update_skipped = version
        self._save()

    def skipped(self, version: str) -> bool:
        return self._prefs.update_skipped == version

    def check(self) -> AvailableUpdate | None:
        """The newest release, if it's newer than this copy."""
        release = self._feed.latest()
        if release is None or parse_version(release.version) <= parse_version(
                self.current_version):
            return None
        asset = self._installer.pick(release.assets)
        return AvailableUpdate(release.version, self.current_version, release.notes,
                               release.page_url, asset,
                               asset is not None and self._installer.supported())

    def download(self, update: AvailableUpdate, progress) -> str:
        if update.asset is None:
            raise UpdateError(_("There's no download for this computer in that release."))
        return self._feed.download(update.asset, progress)

    def install(self, path: str) -> bool:
        return self._installer.install(path)


def default_updater(prefs, save) -> Updater:
    return Updater(GitHubReleaseFeed(natter.HOMEPAGE.removeprefix("https://github.com/"),
                                     natter.__version__), platform_installer(), prefs, save)
