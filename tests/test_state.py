import json

from natter.state import WindowState


def test_round_trip(tmp_path):
    path = tmp_path / "sub" / "window.json"
    WindowState(width=900, height=700, maximized=True, zoom=1.2).save(path)
    assert WindowState.load(path) == WindowState(width=900, height=700, maximized=True, zoom=1.2)


def test_missing_or_corrupt_file_gives_defaults(tmp_path):
    assert WindowState.load(tmp_path / "nope.json") == WindowState()
    bad = tmp_path / "bad.json"
    bad.write_text("{not json")
    assert WindowState.load(bad) == WindowState()
    bad.write_text("[1, 2]")
    assert WindowState.load(bad) == WindowState()


def test_wrong_types_and_out_of_range_values_are_ignored_or_clamped(tmp_path):
    path = tmp_path / "window.json"
    path.write_text(json.dumps({"width": 10, "height": "tall", "maximized": 1, "zoom": 99}))
    state = WindowState.load(path)
    assert state.width == 480
    assert state.height == WindowState().height
    assert state.maximized is False
    assert state.zoom == 3.0


def test_preferences_default_to_starting_on_login(tmp_path):
    from natter.state import Preferences

    path = tmp_path / "preferences.json"
    assert Preferences.load(path).start_on_login is True
    Preferences(start_on_login=False).save(path)
    assert Preferences.load(path).start_on_login is False
    path.write_text('{"start_on_login": "no"}')
    assert Preferences.load(path).start_on_login is True


def test_preferences_remember_the_language(tmp_path):
    from natter.state import Preferences

    path = tmp_path / "preferences.json"
    assert Preferences.load(path).language == ""
    Preferences(language="ru").save(path)
    assert Preferences.load(path).language == "ru"
    path.write_text('{"language": 7}')
    assert Preferences.load(path).language == ""


def test_window_sizes_fit_the_screen():
    from natter.state import fit_size
    assert fit_size(1100, 760, 1366, 728) == (1100, 688)
    assert fit_size(1100, 760, 1920, 1040) == (1100, 760)
    assert fit_size(1100, 760, 300, 200) == (480, 400)  # never below the minimum


def test_small_screens_start_zoomed_out_until_you_zoom():
    from natter.state import starting_zoom
    assert starting_zoom(WindowState(), 768) == 0.85
    assert starting_zoom(WindowState(), 1080) == 1.0
    assert starting_zoom(WindowState(), None) == 1.0
    assert starting_zoom(WindowState(zoom=1.2, zoom_chosen=True), 768) == 1.2
    assert starting_zoom(WindowState(zoom=1.0, zoom_chosen=True), 768) == 1.0
