# Changelog

All notable changes to Natter. Versions follow [Semantic Versioning](https://semver.org):
patch for fixes, minor for new features, major for breaking changes (while below 1.0,
breaking changes bump the minor version).

## [0.5.0] - 2026-10-02

### Added
- Small screens: the window never opens bigger than the screen, and on a screen up to 800 pixels tall (like 1366x768) WhatsApp starts a little zoomed out (85%). Zoom as you like with Ctrl+plus, Ctrl+minus and Ctrl+0; once you do, your choice is kept.

## [0.4.1] - 2026-09-29

### Fixed
- The 0.4.0 downloads were never published: GitHub's build-file storage was full. Release
  builds now go straight into the release, so this can't happen again. The app is the same
  as 0.4.0 (Russian translation and a Language choice in the tray).

## [0.4.0] - 2026-09-29

### Added
- **Russian translation** of Natter's own text: the tray menu, the unread tooltip
  ("3 непрочитанных чата"), the login entry, `--help`, and the app's name and description in
  the app menu and software store.
- **Language** in the tray menu: System, English or Русский. It switches straight away, no
  restart needed. "System" picks Russian on a Russian desktop and English otherwise.
- WhatsApp itself isn't affected: it follows your system language, or the language you pick
  in WhatsApp's own settings.

## [0.3.2] - 2026-09-27

### Changed
- **Windows: a real installer** instead of a portable `.exe`.
  - `Natter-…-windows-x64-setup.exe` installs Natter for your user, with no admin needed.
  - It adds a Start menu entry, and a desktop shortcut if you want one.
  - Uninstall it from Settings → Apps; that also removes the "Start on login" entry.
  - Running a newer setup closes Natter, upgrades it in place without logging you out of
    WhatsApp, and starts it again.
  - It starts faster than the portable file did.

## [0.3.1] - 2026-09-25

### Fixed
- **Linux: slow startup and WhatsApp stuck loading.** The tray icon froze Natter for about
  a second every time the panel read it, about 12 seconds at startup, and again whenever
  the unread count changed. That held up WhatsApp, so it took ages to appear and could
  hang on "downloading messages". WhatsApp now starts loading in about 3 seconds.

## [0.3.0] - 2026-09-25

### Added
- **Runs in the background like Discord.**
  - A tray icon with Open, Start on login and Quit. It gets a red dot when chats are
    unread, and its tooltip shows how many.
  - Closing the window hides Natter to the tray, so WhatsApp keeps running and
    notifications keep coming. Quit from the tray menu (or Ctrl+Q on Linux).
  - Starts hidden in the tray when you log in. This is on by default; untick "Start on
    login" in the tray menu to turn it off.
  - Windows: launching Natter again shows the running window instead of opening a second
    copy (Linux already did this).
- Linux: the tray works on KDE, Ubuntu (AppIndicator extension), Cinnamon, XFCE and other
  StatusNotifier trays, without extra libraries. On GNOME without a tray extension there's
  no icon; launch Natter again to bring the window back.

## [0.2.1] - 2026-09-24

### Changed
- **Back to the WebKitGTK window on Linux**, as in 0.1.x.
  - Closing hides Natter in the background again, so notifications keep coming.
  - Your 0.1.x login is used again.
  - Calls stay unavailable on Linux; use WhatsApp Web in a Chromium browser for those.

## [0.2.0] - 2026-09-24

### Changed
- **Linux: voice and video calls work.** Natter now opens WhatsApp Web as an app window of
  a Chromium browser you already have, in its own profile so your everyday browser isn't
  touched. It picks the first installed of Chrome, Chromium, Edge and Brave.
  - Calls weren't possible before: WhatsApp only offers them in Chromium browsers, and
    WebKitGTK lacks the WebRTC pieces they need.
  - All video formats play and notifications work as in the browser.
  - The engine updates with your browser.
  - The first time, link your phone again: it's a new session.
  - Closing the window now quits WhatsApp; it no longer hides in the background.
  - No Chromium browser installed? Natter uses WebKitGTK as before (no calls).
  - Choose the browser with `NATTER_BROWSER=brave-browser`, or keep WebKitGTK with
    `NATTER_ENGINE=webkit`.

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
