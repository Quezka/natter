# Changelog

All notable changes to Natter. Versions follow [Semantic Versioning](https://semver.org):
patch for fixes, minor for new features, major for breaking changes (while below 1.0,
breaking changes bump the minor version).

## [0.1.3] - 2026-09-23

### Changed
- New green app icon, so Natter is easy to spot as your messaging app.

## [0.1.2] - 2026-09-23

### Fixed
- Maintainer and contact email in the packages is now arsdom15@gmail.com.

## [0.1.1] - 2026-09-23

### Added
- Developer and publisher info in every build: the Windows `.exe` shows Quezka as the
  company, with copyright and version on the file's Details tab; the `.deb` lists Quezka as
  maintainer; app stores (GNOME Software, Ubuntu App Center) show Quezka as the developer
  with links to the homepage and issue tracker. `natter --version` names the developer too.

## [0.1.0] - 2026-09-23

### Added
- WhatsApp Web in a native window using the system webview: WebKitGTK on Linux, WebView2
  on Windows. No bundled browser.
- Stays logged in between runs; remembers window size and zoom.
- Desktop notifications (click one to bring the window back), unread count in the window
  title, and taskbar attention when a message arrives in the background.
- Links open in your default browser; downloads go to your Downloads folder without
  overwriting existing files.
- Voice notes, camera and pasting images work; right-click menu with spell-check.
- Linux: closing the window keeps Natter running for notifications. Launch it again to
  bring it back, or press Ctrl+Q to quit. Ctrl+R reloads, Ctrl+plus/minus/0 zoom.
