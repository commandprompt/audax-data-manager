# Neutralino shell (prototype)

Replacement for the Tauri shell that uses whatever WebKitGTK the system has (4.0 or 4.1), so a
single AppImage can run on RHEL/Rocky 9 and on newer distributions. Linux only so far.

## Layout

- `app/neutralino.config.json`: window defaults, native API allow list, injected scripts.
- `app/resources/index.html`: launcher. The Tauri splash page plus the logic that starts the
  backend and, when the backend prints its URL, the main window.
- `app/resources/shim.js`: host shim injected into the main window (clipboard, external links,
  file drops, file dialogs and saves, saved window geometry, close handshake).

## How it works

Neutralino has one window per process, so the shell is two processes of the same binary:

1. The launcher shows the splash and starts the backend (`audaxdm-server -A`).
2. When the backend prints its URL, the launcher starts the main window process, hidden.
3. When the page reports it is mounted, the main window shows itself at its saved size and
   position and prints `mainReady` on its standard output; the launcher hides the splash.
4. When the main window process exits, the launcher exits and the backend stops with it.

Notes from testing: `spawnProcess` with `envs` replaces the whole environment (pass
`os.getEnvs()` plus overrides), and `app.broadcast` does not cross processes.

## Assembling an AppImage (manual)

AppDir contents:

- `usr/bin/neutralino`: `neutralino-linux_x64` from the Neutralino v6.9.0 framework release.
- `usr/share/neuapp/`: `neutralino.config.json` and `resources/` from `app/`, plus
  `resources/js/neutralino.js` (the v6.9.0 client library release asset, not in the framework zip).
- `usr/share/neuapp/.tmp`: symlink to a writable directory that `AppRun` creates (Neutralino
  creates `.tmp` inside its app path, which is read-only in an AppImage).
- `usr/lib/audaxdm-server/`: the PyInstaller backend.
- `AppRun`: exports `APPDIR` and runs
  `neutralino --load-dir-res --path="$APPDIR/usr/share/neuapp"`.
- A `.desktop` file and icon, then pack with `appimagetool`.

## Known gaps

- `tokenSecurity` is `none`, so any local process that finds the port can call the native API.
- Not tested: file dialogs and last-directory memory, saving files and exports, clipboard,
  external links, the unsaved-changes close prompt, SIGTERM handling.
- The frontend's file dialogs call `window.__TAURI__.core.invoke`, so the shim fakes that shape.
- No Docker, deb or rpm packaging, and no Windows or macOS support.
