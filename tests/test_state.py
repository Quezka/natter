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
