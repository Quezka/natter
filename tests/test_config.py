import pytest

from natter import config


@pytest.mark.parametrize("uri", [
    "https://web.whatsapp.com/",
    "https://web.whatsapp.com/send?phone=123",
    "blob:https://web.whatsapp.com/1f2e",
    "data:image/png;base64,AAAA",
    "about:blank",
])
def test_internal_uris_stay_in_the_app(uri):
    assert config.is_internal(uri)
    assert not config.is_external_link(uri)


@pytest.mark.parametrize("uri", [
    "https://example.com/article",
    "http://web.whatsapp.com/",  # not https: don't trust it inside the session
    "https://faq.whatsapp.com/",
    "mailto:someone@example.com",
    "tel:+390000000",
])
def test_external_links_go_to_the_default_browser(uri):
    assert not config.is_internal(uri)
    assert config.is_external_link(uri)


@pytest.mark.parametrize("uri", ["javascript:alert(1)", "file:///etc/passwd", "ftp://example.com"])
def test_unsafe_schemes_are_neither_loaded_nor_launched(uri):
    assert not config.is_internal(uri)
    assert not config.is_external_link(uri)


@pytest.mark.parametrize("title, count", [
    ("WhatsApp", 0),
    ("(3) WhatsApp", 3),
    ("(120) WhatsApp", 120),
    ("", 0),
    (None, 0),
    ("WhatsApp (3)", 0),
])
def test_unread_count_from_page_title(title, count):
    assert config.unread_count(title) == count


def test_window_title():
    assert config.window_title(0) == "Natter"
    assert config.window_title(4) == "(4) Natter"


def test_unique_path_never_overwrites(tmp_path):
    assert config.unique_path(tmp_path, "photo.jpg") == tmp_path / "photo.jpg"
    (tmp_path / "photo.jpg").touch()
    (tmp_path / "photo (1).jpg").touch()
    assert config.unique_path(tmp_path, "photo.jpg") == tmp_path / "photo (2).jpg"


def test_unique_path_strips_directories(tmp_path):
    assert config.unique_path(tmp_path, "../../evil.sh") == tmp_path / "evil.sh"
    assert config.unique_path(tmp_path, "") == tmp_path / "download"


def test_data_dir_follows_xdg(monkeypatch, tmp_path):
    monkeypatch.setattr(config.sys, "platform", "linux")
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))
    assert config.data_dir() == tmp_path / "data" / "natter"
    assert config.cache_dir() == tmp_path / "cache" / "natter"


def test_data_dir_on_windows(monkeypatch, tmp_path):
    monkeypatch.setattr(config.sys, "platform", "win32")
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    assert config.data_dir() == tmp_path / "Natter"
    assert config.cache_dir() == tmp_path / "Natter" / "cache"


# ---- Linux browser engine ------------------------------------------------------------

def fake_which(installed):
    return lambda name: f"/usr/bin/{name}" if name in installed else None


def test_find_browser_prefers_chrome_then_falls_back():
    assert config.find_browser(fake_which({"microsoft-edge", "chromium"}), {}) == "/usr/bin/chromium"
    assert config.find_browser(fake_which({"microsoft-edge"}), {}) == "/usr/bin/microsoft-edge"
    assert config.find_browser(fake_which(set()), {}) is None


def test_find_browser_honours_the_override():
    which = fake_which({"brave-browser", "chromium"})
    assert config.find_browser(which, {"NATTER_BROWSER": "brave-browser"}) == "/usr/bin/brave-browser"
    assert config.find_browser(which, {"NATTER_BROWSER": "opera"}) is None


def test_webkit_can_be_forced():
    assert config.use_browser({})
    assert not config.use_browser({"NATTER_ENGINE": "WebKit"})


def test_browser_command_opens_whatsapp_as_an_app_in_its_own_profile(tmp_path):
    command = config.browser_command("/usr/bin/microsoft-edge", tmp_path / "p")
    assert command[0] == "/usr/bin/microsoft-edge"
    assert f"--user-data-dir={tmp_path / 'p'}" in command
    assert f"--class={config.APP_ID}" in command
    assert command[-1] == f"--app={config.URL}"
    assert "--auto-open-devtools-for-tabs" in config.browser_command("x", tmp_path, debug=True)


def test_profiles_are_per_browser_and_snaps_use_their_own_folder(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    assert config.browser_profile("/usr/bin/microsoft-edge") == (
        tmp_path / "data" / "natter" / "browser" / "microsoft-edge")
    assert config.browser_profile("/snap/bin/chromium", home=tmp_path) == (
        tmp_path / "snap" / "chromium" / "common" / "natter-profile")


def test_profile_in_use_reads_chromiums_singleton_lock(tmp_path):
    import os
    import socket
    assert not config.profile_in_use(tmp_path)
    lock = tmp_path / "SingletonLock"
    lock.symlink_to(f"{socket.gethostname()}-{os.getpid()}")
    assert config.profile_in_use(tmp_path)
    lock.unlink()
    lock.symlink_to(f"{socket.gethostname()}-999999999")  # a dead process
    assert not config.profile_in_use(tmp_path)
    lock.unlink()
    lock.symlink_to(f"another-host-{os.getpid()}")
    assert not config.profile_in_use(tmp_path)
