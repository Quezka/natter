import sys
import threading

import pytest

from natter import single_instance


@pytest.fixture
def address(tmp_path):
    if sys.platform == "win32":
        return rf"\\.\pipe\natter-test-{tmp_path.name}", "AF_PIPE"
    return str(tmp_path / "natter.sock"), "AF_UNIX"


def test_first_launch_claims_and_second_launch_shows_the_first(address):
    shown = threading.Event()
    assert single_instance.claim(shown.set, address) is True
    assert single_instance.claim(lambda: pytest.fail("second must not listen"), address) is False
    assert shown.wait(5)


@pytest.mark.skipif(sys.platform == "win32", reason="unix sockets only")
def test_stale_socket_from_a_crash_is_replaced(address):
    path, _family = address
    open(path, "w").close()  # a leftover file nobody listens on
    assert single_instance.claim(lambda: None, address) is True
