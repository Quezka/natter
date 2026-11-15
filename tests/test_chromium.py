from natter import chromium

QT_UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) QtWebEngine/6.10.2 "
         "Chrome/134.0.6998.208 Safari/537.36")


def test_the_user_agent_is_plain_chrome():
    ua = chromium.user_agent(QT_UA)
    assert "QtWebEngine" not in ua and "Chrome/134.0.6998.208" in ua and ua.endswith("Safari/537.36")
    assert chromium.chrome_version(QT_UA) == "134.0.6998.208"
    assert chromium.chrome_version("nothing") == ""


def test_client_hints_say_google_chrome():
    assert chromium.brands("134.0.1")["Google Chrome"] == "134.0.1"
    assert "QtWebEngine" not in chromium.brands("134.0.1")


def test_calls_need_shared_array_buffer_and_the_engine_stays_light():
    flags = chromium.flags("--foo")
    assert flags.startswith("--foo ")
    assert "SharedArrayBuffer" in flags  # WhatsApp: "missing_shared_array_buffer" without it
    assert "--renderer-process-limit=1" in flags


def test_permissions_only_for_whatsapp():
    assert chromium.allowed("MediaAudioCapture", "web.whatsapp.com")
    assert chromium.allowed("Notifications", "web.whatsapp.com")
    assert not chromium.allowed("MediaAudioCapture", "evil.example")
    assert not chromium.allowed("Geolocation", "web.whatsapp.com")


def test_the_page_script_adds_window_chrome():
    script = chromium.chrome_shim("134")
    assert "window.chrome" in script and "'Google Chrome', version: '134'" in script
