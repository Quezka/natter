from pathlib import Path

from natter import drop


def test_only_local_files_are_taken(tmp_path):
    f = tmp_path / "a b.pdf"
    f.write_bytes(b"x")
    uris = [f.as_uri(), "# comment", tmp_path.as_uri(), "https://example.com/x.png", "file://otherhost/etc/passwd", ""]
    got = drop.files_from_uris(uris)
    assert [(d.name, d.mime) for d in got] == [("a b.pdf", "application/pdf")]


def test_shelf_serves_only_the_latest_drop(tmp_path):
    f = tmp_path / "x.txt"
    f.write_text("hi")
    shelf = drop.DropShelf()
    assert shelf.take("natter-file://anything/0") is None
    first = shelf.put(drop.files_from_uris([f.as_uri()]))
    assert shelf.take(f"natter-file://{first}/0").path == f
    assert shelf.take(f"natter-file://{first}/1") is None
    assert shelf.take(f"natter-file://{first}/x") is None
    second = shelf.put([])
    assert second != first
    assert shelf.take(f"natter-file://{first}/0") is None


def test_script_drops_at_the_pointer():
    script = drop.drop_script("tok", [drop.Dropped(Path("/a"), 'q"uote.png', "image/png")], 12.5, 40)
    assert "natter-file://tok/" in script
    assert 'q\\"uote.png' in script  # names are JSON-escaped
    assert "elementFromPoint(12.5, 40)" in script
