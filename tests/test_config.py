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
