"""Natter's layers (Clean Architecture, as in every app of the suite): the rules (`config`, `state`, `look`,
`updates`, `i18n`, `autostart`) know nothing of GTK, WebKit or Windows; only the backends do."""
import ast
from pathlib import Path

PACKAGE = Path(__file__).resolve().parent.parent / "natter"
CORE = ("config", "state", "look", "updates", "i18n", "autostart", "single_instance", "webpage")
PLATFORM = ("gi", "webview", "pystray", "clr", "System", "natter.linux", "natter.windows", "natter.tray_linux",
            "natter.updates_gtk", "natter.updates_win", "natter.settings_gtk")


def imports(path: Path) -> set[str]:
    found = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            found |= {a.name for a in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module:
            found.add(node.module)
    return found


def test_the_core_knows_no_platform():
    for name in CORE:
        for module in imports(PACKAGE / f"{name}.py"):
            assert not any(module == p or module.startswith(p + ".") for p in PLATFORM), f"{name} imports {module}"
