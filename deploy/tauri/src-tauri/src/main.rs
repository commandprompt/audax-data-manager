//! Audax Data Manager desktop shell.
//!
//! Starts the Django backend as a child process, shows a splash screen while it boots, then
//! opens the app in a system webview. Replaces the NW.js host page (deploy/app/index.html).

#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::{
    collections::HashSet,
    io::{BufRead, BufReader, Read, Write},
    path::{Path, PathBuf},
    process::{Child, Command, Stdio},
    sync::{
        atomic::{AtomicBool, Ordering},
        Mutex,
    },
    time::Duration,
};

use tauri::{
    webview::{NewWindowResponse, PageLoadEvent},
    AppHandle, CloseRequestApi, DragDropEvent, Emitter, Manager, PhysicalPosition, RunEvent, State,
    Url, WebviewUrl, WebviewWindow, WebviewWindowBuilder, Window, WindowEvent, Wry,
};
use tauri_plugin_clipboard_manager::ClipboardExt;
use tauri_plugin_dialog::{DialogExt, FileDialogBuilder};
use tauri_plugin_opener::OpenerExt;
use tauri_plugin_window_state::StateFlags;

const MAIN_WINDOW: &str = "main";
const SPLASH_WINDOW: &str = "splash";

/// How long to wait for the page to report ready before showing the window anyway.
const REVEAL_FALLBACK: Duration = Duration::from_secs(30);
const SIGNAL_POLL_INTERVAL: Duration = Duration::from_millis(200);

const MAX_DROPPED_FILE_BYTES: u64 = 50 * 1024 * 1024;
const MAX_SAVED_FILE_BYTES: usize = 200 * 1024 * 1024;
const PART_SUFFIX: &str = ".audaxdm-part";

/// Header carrying the percent-encoded suggested file name of a `save_file` call.
/// Keep in sync with `saveBlobAs` in the frontend's utils/native_dialog.js.
const FILE_NAME_HEADER: &str = "x-file-name";

/// The host side of the page's pgmanage:* message protocol, injected into the main window.
const HOST_SHIM: &str = include_str!("shim.js");

// ---------------------------------------------------------------------------------------------
// Shared state and small helpers
// ---------------------------------------------------------------------------------------------

/// One line of backend output: (index, "stdout" | "stderr", text).
type LogLine = (usize, String, String);

#[derive(Default)]
struct Shared {
    /// The backend server process.
    child: Mutex<Option<Child>>,
    /// Backend output so far, replayed to the splash screen when it loads late.
    log: Mutex<Vec<LogLine>>,
    /// The main window has been shown (and the splash closed). Set once.
    main_revealed: AtomicBool,
    /// The "reveal anyway" fallback timer has been started.
    reveal_fallback_armed: AtomicBool,
    /// The page confirmed the close (no unsaved tabs, or the user chose to discard them).
    close_confirmed: AtomicBool,
    /// Paths of the most recent native file drop. `read_dropped_file` serves only these.
    dropped: Mutex<HashSet<PathBuf>>,
}

impl Shared {
    fn kill_server(&self) {
        if let Some(mut child) = self.child.lock().unwrap().take() {
            let _ = child.kill();
            let _ = child.wait();
        }
    }
}

fn main_window(app: &AppHandle) -> Option<WebviewWindow> {
    app.get_webview_window(MAIN_WINDOW)
}

/// Converts any error into the plain string tauri commands return to the page.
fn to_msg(e: impl ToString) -> String {
    e.to_string()
}

// ---------------------------------------------------------------------------------------------
// Backend server process
// ---------------------------------------------------------------------------------------------

/// Replays the backend output so far, for a splash screen that loaded after some of it.
#[tauri::command]
fn splash_log(state: State<'_, Shared>) -> Vec<LogLine> {
    state.log.lock().unwrap().clone()
}

/// Path of the backend executable: `AUDAXDM_SERVER` if set (development), otherwise the
/// `audaxdm-server` folder next to the app executable (deb/rpm install), or else in the bundle
/// resources (AppImage).
fn server_path(app: &AppHandle) -> PathBuf {
    if let Ok(path) = std::env::var("AUDAXDM_SERVER") {
        return PathBuf::from(path);
    }
    let exe = if cfg!(windows) { "audaxdm-server.exe" } else { "audaxdm-server" };
    let server = Path::new("audaxdm-server").join(exe);

    let beside_app = std::env::current_exe()
        .ok()
        .and_then(|app_exe| app_exe.parent().map(|dir| dir.join(&server)));
    match beside_app {
        Some(path) if path.exists() => path,
        _ => app.path().resource_dir().unwrap_or_default().join(server),
    }
}

/// Records one line of backend output and forwards it to the splash screen. The backend prints
/// the app URL as an `http...` line on stdout once it is ready; that starts the main window.
fn push_line(app: &AppHandle, stream: &str, line: String) {
    let state = app.state::<Shared>();
    let entry: LogLine = {
        let mut log = state.log.lock().unwrap();
        let entry = (log.len(), stream.to_string(), line);
        log.push(entry.clone());
        entry
    };
    let _ = app.emit("server-line", &entry);

    let (_, stream, line) = &entry;
    if stream == "stdout" && line.starts_with("http") {
        if let Ok(url) = line.trim().parse::<Url>() {
            let handle = app.clone();
            let _ = app.run_on_main_thread(move || open_main_window(&handle, url));
        }
    }
}

/// Forwards each line of `reader` to `push_line`.
fn pump_output<R: Read + Send + 'static>(app: AppHandle, reader: R, stream: &'static str) {
    std::thread::spawn(move || {
        for raw in BufReader::new(reader).split(b'\n') {
            let Ok(raw) = raw else { break };
            let line = String::from_utf8_lossy(&raw).trim_end_matches('\r').to_string();
            if !line.is_empty() {
                push_line(&app, stream, line);
            }
        }
    });
}

fn spawn_server(app: &AppHandle) {
    let path = server_path(app);
    let mut cmd = Command::new(&path);
    cmd.arg("-A").stdout(Stdio::piped()).stderr(Stdio::piped());
    clean_appimage_env(&mut cmd);

    if cfg!(target_os = "macos") {
        // GUI apps on macOS do not inherit the shell PATH (Homebrew tools live in /usr/local/bin).
        let old = std::env::var("PATH").unwrap_or_default();
        cmd.env("PATH", format!("/usr/local/bin:{old}"));
    }
    #[cfg(target_os = "linux")]
    {
        use std::os::unix::process::CommandExt;
        // Kill the backend if the shell dies without running its exit hook (SIGKILL, crash).
        // Safe: the closure only calls prctl, which is async-signal-safe.
        unsafe {
            cmd.pre_exec(|| {
                libc::prctl(libc::PR_SET_PDEATHSIG, libc::SIGKILL);
                Ok(())
            });
        }
    }
    #[cfg(windows)]
    {
        use std::os::windows::process::CommandExt;
        cmd.creation_flags(0x0800_0000); // CREATE_NO_WINDOW
    }

    let mut child = match cmd.spawn() {
        Ok(child) => child,
        Err(e) => {
            push_line(app, "stderr", format!("Could not start {}: {e}", path.display()));
            return;
        }
    };
    if let Some(stdout) = child.stdout.take() {
        pump_output(app.clone(), stdout, "stdout");
    }
    if let Some(stderr) = child.stderr.take() {
        pump_output(app.clone(), stderr, "stderr");
    }
    *app.state::<Shared>().child.lock().unwrap() = Some(child);
}

// SIGTERM / SIGINT / SIGHUP take the normal exit path (kills the backend, saves window state),
// so a plain `kill` or Ctrl-C does not leave the backend behind.
#[cfg(unix)]
static TERM_REQUESTED: AtomicBool = AtomicBool::new(false);

// A signal handler may only do async-signal-safe work, so it just raises a flag.
#[cfg(unix)]
extern "C" fn on_term_signal(_: libc::c_int) {
    TERM_REQUESTED.store(true, Ordering::SeqCst);
}

#[cfg(unix)]
fn handle_term_signals(app: AppHandle) {
    for signal in [libc::SIGTERM, libc::SIGINT, libc::SIGHUP] {
        // Safety: the handler only stores to an atomic.
        unsafe {
            libc::signal(signal, on_term_signal as extern "C" fn(libc::c_int) as libc::sighandler_t);
        }
    }
    std::thread::spawn(move || {
        while !TERM_REQUESTED.load(Ordering::SeqCst) {
            std::thread::sleep(SIGNAL_POLL_INTERVAL);
        }
        app.exit(0);
    });
}

// ---------------------------------------------------------------------------------------------
// Main window and the hand-over from the splash screen
// ---------------------------------------------------------------------------------------------

/// Shows the main window and closes the splash. Runs once; later calls do nothing.
fn reveal_main(app: &AppHandle) {
    let state = app.state::<Shared>();
    if state.main_revealed.swap(true, Ordering::SeqCst) {
        return;
    }
    if let Some(window) = main_window(app) {
        let _ = window.show();
        let _ = window.set_focus();
    }
    if let Some(splash) = app.get_webview_window(SPLASH_WINDOW) {
        let _ = splash.close();
    }
}

/// The page calls this once the app is mounted, so the splash stays up until the UI is ready.
#[tauri::command]
fn app_ready(app: AppHandle) {
    reveal_main(&app);
}

/// Creates the main window, hidden, and starts loading `url` in it while the splash is shown.
fn open_main_window(app: &AppHandle, url: Url) {
    if main_window(app).is_some() {
        return;
    }
    let nav_app = app.clone();
    let new_window_app = app.clone();

    let result = WebviewWindowBuilder::new(app, MAIN_WINDOW, WebviewUrl::External(url))
        .title("Audax Data Manager")
        .inner_size(1024.0, 768.0)
        .min_inner_size(1024.0, 768.0)
        .center()
        .visible(false)
        .initialization_script(HOST_SHIM)
        .on_page_load(|window, payload| {
            if payload.event() != PageLoadEvent::Finished {
                return;
            }
            // The window is normally revealed by `app_ready`. If the page never reports ready
            // (script error, server problem), reveal it anyway after a while so the failure is
            // visible.
            let app = window.app_handle().clone();
            if app.state::<Shared>().reveal_fallback_armed.swap(true, Ordering::SeqCst) {
                return;
            }
            std::thread::spawn(move || {
                std::thread::sleep(REVEAL_FALLBACK);
                reveal_main(&app);
            });
        })
        .on_navigation(move |url| allow_navigation(&nav_app, url))
        .on_new_window(move |url, _features| {
            open_external(&new_window_app, &url);
            NewWindowResponse::Deny
        })
        .build();

    if let Err(e) = result {
        push_line(app, "stderr", format!("Could not open the main window: {e}"));
    }
}

/// The page confirmed that the window may close (no unsaved tabs, or the user discarded them).
#[tauri::command]
fn confirm_close(app: AppHandle, state: State<'_, Shared>) {
    state.close_confirmed.store(true, Ordering::SeqCst);
    if let Some(window) = main_window(&app) {
        let _ = window.close();
    }
}

fn on_close_requested(window: &Window, api: &CloseRequestApi) {
    let app = window.app_handle();
    let state = app.state::<Shared>();
    let revealed = state.main_revealed.load(Ordering::SeqCst);

    match window.label() {
        // Closing the splash while the app is still starting means the user gave up.
        SPLASH_WINDOW if !revealed => {
            state.kill_server();
            app.exit(0);
        }
        MAIN_WINDOW if revealed && !state.close_confirmed.load(Ordering::SeqCst) => {
            // Let the page check for unsaved tabs first (pgmanage:request-close).
            api.prevent_close();
            if let Some(main) = main_window(app) {
                let _ = main.eval("window.postMessage({ type: 'pgmanage:request-close' }, '*');");
            }
        }
        _ => {}
    }
}

fn on_window_event(window: &Window, event: &WindowEvent) {
    match event {
        WindowEvent::DragDrop(DragDropEvent::Drop { paths, position }) => {
            on_file_drop(window, paths, position)
        }
        WindowEvent::CloseRequested { api, .. } => on_close_requested(window, api),
        _ => {}
    }
}

// ---------------------------------------------------------------------------------------------
// System integration: system browser, link policy, clipboard
// ---------------------------------------------------------------------------------------------

fn is_local(url: &Url) -> bool {
    matches!(url.host_str(), Some("localhost") | Some("127.0.0.1"))
}

/// Removes the parts of an environment value that point into the AppImage mount (`appdir`).
/// Returns None if nothing is left, so the variable should be removed altogether.
fn without_appdir(value: &str, appdir: &str) -> Option<String> {
    if !value.contains(appdir) {
        return Some(value.to_string());
    }
    let kept: Vec<&str> = value.split(':').filter(|part| !part.starts_with(appdir)).collect();
    if kept.iter().all(|part| part.is_empty()) {
        None
    } else {
        Some(kept.join(":"))
    }
}

/// Inside an AppImage the launcher points many variables (LD_LIBRARY_PATH, PYTHONHOME, GTK_PATH,
/// PATH, ...) into its mount, for the bundled WebKitGTK only. The backend and the system tools it
/// starts (pg_dump, xdg-open) must not see them, or they load the bundled libraries and Python.
fn clean_appimage_env(cmd: &mut Command) {
    let Ok(appdir) = std::env::var("APPDIR") else { return };
    for (key, value) in std::env::vars_os() {
        let (Some(key), Some(value)) = (key.to_str(), value.to_str()) else { continue };
        match without_appdir(value, &appdir) {
            None => {
                cmd.env_remove(key);
            }
            Some(cleaned) if cleaned != value => {
                cmd.env(key, cleaned);
            }
            Some(_) => {}
        }
    }
    for key in ["APPIMAGE", "ARGV0", "OWD"] {
        cmd.env_remove(key);
    }
}

/// Opens an http(s) URL in the system browser. Other schemes are ignored.
fn open_external(app: &AppHandle, url: &Url) {
    if !matches!(url.scheme(), "http" | "https") {
        return;
    }
    if std::env::var_os("APPDIR").is_some() {
        // xdg-open would start the browser with the AppImage's libraries
        let mut cmd = Command::new("xdg-open");
        cmd.arg(url.as_str());
        clean_appimage_env(&mut cmd);
        std::thread::spawn(move || {
            let _ = cmd.status();
        });
        return;
    }
    let _ = app.opener().open_url(url.as_str(), None::<&str>);
}

#[tauri::command]
fn open_external_url(app: AppHandle, url: String) {
    if let Ok(url) = url.parse::<Url>() {
        open_external(&app, &url);
    }
}

/// Decides whether the app window may navigate to `url`.
/// Remote http(s) pages open in the system browser instead of replacing the app.
fn allow_navigation(app: &AppHandle, url: &Url) -> bool {
    match url.scheme() {
        // Never navigate to local files (e.g. an uncancelled file drop would show the file).
        "file" => false,
        "http" | "https" if !is_local(url) => {
            open_external(app, url);
            false
        }
        _ => true,
    }
}

#[tauri::command]
fn read_clipboard(app: AppHandle) -> String {
    app.clipboard().read_text().unwrap_or_default()
}

// ---------------------------------------------------------------------------------------------
// File dialogs
//
// The destination of every save is chosen by the user in a native dialog, never by the page.
// ---------------------------------------------------------------------------------------------

/// Where the last-used dialog directory is remembered (survives restarts, like the old NW.js dialogs).
fn last_dir_file(app: &AppHandle) -> Option<PathBuf> {
    app.path().app_config_dir().ok().map(|d| d.join("last-dialog-dir"))
}

fn read_last_dir(file: &Path) -> Option<PathBuf> {
    let dir = PathBuf::from(std::fs::read_to_string(file).ok()?.trim());
    dir.is_dir().then_some(dir)
}

fn write_last_dir(file: &Path, dir: &Path) {
    if let Some(parent) = file.parent() {
        let _ = std::fs::create_dir_all(parent);
    }
    let _ = std::fs::write(file, dir.to_string_lossy().as_bytes());
}

/// Remembers the directory the user just picked in (the folder itself for folder picks).
fn remember_dir(app: &AppHandle, chosen: &Path, is_folder: bool) {
    let dir = if is_folder { Some(chosen) } else { chosen.parent() };
    if let (Some(file), Some(dir)) = (last_dir_file(app), dir) {
        write_last_dir(&file, dir);
    }
}

/// A dialog attached to `window` that starts in the last used directory.
fn dialog_in_last_dir(window: &WebviewWindow) -> FileDialogBuilder<Wry> {
    let app = window.app_handle();
    let dialog = app.dialog().file().set_parent(window);
    match last_dir_file(app).and_then(|f| read_last_dir(&f)) {
        Some(dir) => dialog.set_directory(dir),
        None => dialog,
    }
}

/// Asks where to save a file. Blocks: only call from async commands, never the UI thread.
fn ask_save_path(window: &WebviewWindow, suggested: String) -> Result<Option<PathBuf>, String> {
    let picked = dialog_in_last_dir(window).set_file_name(suggested).blocking_save_file();
    let Some(chosen) = picked else { return Ok(None) };
    let dest = chosen.into_path().map_err(to_msg)?;
    remember_dir(window.app_handle(), &dest, false);
    Ok(Some(dest))
}

/// The last path component of `name`, if there is a usable one (drops directories and "..").
fn sanitize_file_name(name: &str) -> Option<String> {
    Path::new(name)
        .file_name()
        .map(|n| n.to_string_lossy().into_owned())
        .filter(|n| !n.is_empty())
}

// kind: "select_file" | "select_folder" | "create_file". Returns None when cancelled.
#[tauri::command]
async fn pick_path(
    window: WebviewWindow,
    kind: String,
    title: Option<String>,
) -> Result<Option<String>, String> {
    let mut dialog = dialog_in_last_dir(&window);
    if let Some(title) = title {
        dialog = dialog.set_title(title);
    }
    let picked = match kind.as_str() {
        "select_folder" => dialog.blocking_pick_folder(),
        "create_file" => dialog.blocking_save_file(),
        "select_file" => dialog.blocking_pick_file(),
        other => return Err(format!("unknown dialog kind: {other}")),
    };
    let Some(picked) = picked else { return Ok(None) };
    let path = picked.into_path().map_err(to_msg)?;
    remember_dir(window.app_handle(), &path, kind == "select_folder");
    Ok(Some(path.to_string_lossy().into_owned()))
}

// ---------------------------------------------------------------------------------------------
// Saving files
//
// Files are written through a sibling ".audaxdm-part" file and renamed into place only after a
// complete transfer, so a failure can never damage an existing file.
// ---------------------------------------------------------------------------------------------

/// Writes a file through a brand-new sibling ".audaxdm-part" file (create_new never overwrites
/// anything) and renames it over `dest` only after `fill` succeeded. The caller has already had
/// the user confirm overwriting `dest` in the save dialog. On failure only the part file this
/// call created is removed, and `dest` is left exactly as it was.
fn write_via_part(
    dest: &Path,
    fill: impl FnOnce(&mut std::fs::File) -> Result<(), String>,
) -> Result<(), String> {
    let file_name = dest.file_name().ok_or("invalid destination")?.to_string_lossy().into_owned();

    let mut part = None;
    for n in 0..100 {
        let suffix = if n == 0 { String::new() } else { format!("-{n}") };
        let candidate = dest.with_file_name(format!("{file_name}{PART_SUFFIX}{suffix}"));
        match std::fs::OpenOptions::new().write(true).create_new(true).open(&candidate) {
            Ok(file) => {
                part = Some((candidate, file));
                break;
            }
            Err(e) if e.kind() == std::io::ErrorKind::AlreadyExists => continue,
            Err(e) => return Err(format!("cannot write to the chosen location: {e}")),
        }
    }
    let (part_path, mut part_file) =
        part.ok_or("cannot create a temporary file next to the destination")?;

    let result = fill(&mut part_file).and_then(|()| part_file.flush().map_err(to_msg));
    drop(part_file);

    let result = result.and_then(|()| std::fs::rename(&part_path, dest).map_err(to_msg));
    if result.is_err() {
        let _ = std::fs::remove_file(&part_path);
    }
    result
}

/// Decodes %XX escapes (the page sends the file name percent-encoded in a header).
fn percent_decode(s: &str) -> String {
    let bytes = s.as_bytes();
    let mut out = Vec::with_capacity(bytes.len());
    let mut i = 0;
    while i < bytes.len() {
        if bytes[i] == b'%' {
            // get() returns None (instead of panicking) if the slice splits a multi-byte char.
            if let Some(v) = s.get(i + 1..i + 3).and_then(|h| u8::from_str_radix(h, 16).ok()) {
                out.push(v);
                i += 3;
                continue;
            }
        }
        out.push(bytes[i]);
        i += 1;
    }
    String::from_utf8_lossy(&out).into_owned()
}

// Saves bytes generated by the page (blob/data downloads such as snippets and the ERD image).
// The raw request body is the file content and the file name header the suggested name.
// Returns Some(saved path), or None if the dialog was cancelled.
#[tauri::command]
async fn save_file(
    window: WebviewWindow,
    request: tauri::ipc::Request<'_>,
) -> Result<Option<String>, String> {
    let tauri::ipc::InvokeBody::Raw(bytes) = request.body() else {
        return Err("expected raw file data".into());
    };
    if bytes.len() > MAX_SAVED_FILE_BYTES {
        return Err("The file is too large to save.".into());
    }
    let name = request
        .headers()
        .get(FILE_NAME_HEADER)
        .and_then(|v| v.to_str().ok())
        .and_then(|v| sanitize_file_name(&percent_decode(v)))
        .unwrap_or_else(|| "download".into());

    let Some(dest) = ask_save_path(&window, name)? else { return Ok(None) };
    write_via_part(&dest, |f| f.write_all(bytes).map_err(to_msg))?;
    Ok(Some(dest.display().to_string()))
}

/// Returns the file name if `path` is `<prefix>/static/temp/<file>`, the folder the server
/// writes query exports to. Anything else (other folders, nested paths, "..") is rejected.
fn export_filename(path: &str) -> Option<&str> {
    let (_, file) = path.rsplit_once("/static/temp/")?;
    let valid = !matches!(file, "" | "." | "..") && !file.contains(['/', '\\']);
    valid.then_some(file)
}

/// True if `url` points at the same server as the app window (scheme, host and port).
fn is_same_server(url: &Url, own: &Url) -> bool {
    url.scheme() == "http"
        && url.host_str() == own.host_str()
        && url.port_or_known_default() == own.port_or_known_default()
}

/// Reads the HTTP status line and headers. Returns the Content-Length if the response is a
/// plain 200 whose body can simply be read to the end.
fn read_response_head(reader: &mut impl BufRead) -> Result<Option<u64>, String> {
    let mut status = String::new();
    reader.read_line(&mut status).map_err(to_msg)?;
    if status.split_whitespace().nth(1) != Some("200") {
        return Err(format!("the server answered: {}", status.trim()));
    }

    let mut content_length = None;
    loop {
        let mut line = String::new();
        if reader.read_line(&mut line).map_err(to_msg)? == 0 {
            return Err("incomplete response".into());
        }
        let line = line.trim_end().to_ascii_lowercase();
        if line.is_empty() {
            return Ok(content_length);
        }
        if let Some(v) = line.strip_prefix("content-length:") {
            content_length = v.trim().parse().ok();
        }
        if line.starts_with("transfer-encoding:") && line.contains("chunked") {
            return Err("chunked responses are not supported".into());
        }
    }
}

/// Fetches `target` from the local app server (plain HTTP/1.0 over loopback) and writes it to
/// `dest` via `write_via_part`.
fn fetch_to_file(host: &str, port: u16, target: &str, dest: &Path) -> Result<(), String> {
    write_via_part(dest, |part_file| {
        let mut stream = std::net::TcpStream::connect((host, port)).map_err(to_msg)?;
        write!(stream, "GET {target} HTTP/1.0\r\nHost: {host}:{port}\r\nConnection: close\r\n\r\n")
            .map_err(to_msg)?;

        let mut reader = BufReader::new(stream);
        let content_length = read_response_head(&mut reader)?;
        let written = std::io::copy(&mut reader, part_file).map_err(to_msg)?;
        match content_length {
            Some(len) if len != written => Err("the download was incomplete".into()),
            _ => Ok(()),
        }
    })
}

// Save link of a query export: ask where to save, then copy the server-side export file there.
// Returns Some(saved path), or None if the dialog was cancelled.
#[tauri::command]
async fn save_export(
    window: WebviewWindow,
    url: String,
    name: String,
) -> Result<Option<String>, String> {
    let url: Url = url.parse().map_err(|_| "invalid URL")?;
    // Only the app's own server may be contacted, never another local service.
    if !is_same_server(&url, &window.url().map_err(to_msg)?) {
        return Err("not the application server".into());
    }
    let server_file = export_filename(url.path()).ok_or("not an export file")?;
    let suggested = sanitize_file_name(&name).unwrap_or_else(|| server_file.to_string());

    let Some(dest) = ask_save_path(&window, suggested)? else { return Ok(None) };

    let target = match url.query() {
        Some(query) => format!("{}?{query}", url.path()),
        None => url.path().to_string(),
    };
    let host = url.host_str().ok_or("invalid URL")?;
    let port = url.port_or_known_default().ok_or("invalid URL")?;
    fetch_to_file(host, port, &target, &dest)?;
    Ok(Some(dest.display().to_string()))
}

// ---------------------------------------------------------------------------------------------
// Native file drops
//
// WebKitGTK gives the page no readable `File` for files dropped from the desktop, so the shell
// takes the native drop (which carries real paths) and hands it to the page (see shim.js).
// The page may then read exactly the files that were just dropped, and nothing else.
// ---------------------------------------------------------------------------------------------

/// Quotes a string as a JavaScript string literal.
fn js_string(s: &str) -> String {
    let mut out = String::from("\"");
    for c in s.chars() {
        match c {
            '"' => out.push_str("\\\""),
            '\\' => out.push_str("\\\\"),
            '\n' => out.push_str("\\n"),
            '\r' => out.push_str("\\r"),
            '\u{2028}' => out.push_str("\\u2028"),
            '\u{2029}' => out.push_str("\\u2029"),
            c if (c as u32) < 0x20 => out.push_str(&format!("\\u{:04x}", c as u32)),
            c => out.push(c),
        }
    }
    out.push('"');
    out
}

/// Remembers the dropped paths and reports the drop to the page as an `audax-native-drop` event.
fn on_file_drop(window: &Window, paths: &[PathBuf], position: &PhysicalPosition<f64>) {
    if window.label() != MAIN_WINDOW {
        return;
    }
    let app = window.app_handle();
    *app.state::<Shared>().dropped.lock().unwrap() = paths.iter().cloned().collect();

    // The page works in logical pixels (elementFromPoint), the event reports physical ones.
    let scale = window.scale_factor().unwrap_or(1.0);
    let list: Vec<String> = paths.iter().map(|p| js_string(&p.to_string_lossy())).collect();
    if let Some(main) = main_window(app) {
        let _ = main.eval(format!(
            "window.dispatchEvent(new CustomEvent('audax-native-drop', \
             {{ detail: {{ paths: [{}], x: {}, y: {} }} }}));",
            list.join(","),
            position.x / scale,
            position.y / scale
        ));
    }
}

/// Reads a file that was just dropped onto the window. Paths the user did not drop are refused,
/// so the page cannot use this to read arbitrary files. Returns (file name, text content).
fn read_dropped(shared: &Shared, path: &str) -> Result<(String, String), String> {
    let path = PathBuf::from(path);
    if !shared.dropped.lock().unwrap().contains(&path) {
        return Err("This file was not dropped onto the window.".into());
    }
    let meta = std::fs::metadata(&path).map_err(to_msg)?;
    if !meta.is_file() {
        return Err("Only files can be dropped.".into());
    }
    if meta.len() > MAX_DROPPED_FILE_BYTES {
        return Err("Please drop a file that is 50MB or less.".into());
    }
    let bytes = std::fs::read(&path).map_err(to_msg)?;
    let name = path
        .file_name()
        .map(|n| n.to_string_lossy().into_owned())
        .unwrap_or_else(|| "file".into());
    Ok((name, String::from_utf8_lossy(&bytes).into_owned()))
}

#[tauri::command]
fn read_dropped_file(state: State<'_, Shared>, path: String) -> Result<(String, String), String> {
    read_dropped(&state, &path)
}

// ---------------------------------------------------------------------------------------------

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .plugin(tauri_plugin_clipboard_manager::init())
        .plugin(tauri_plugin_dialog::init())
        .plugin(
            tauri_plugin_window_state::Builder::default()
                .with_denylist(&[SPLASH_WINDOW])
                // Never restore visibility: the plugin would show the blank main window right
                // after creation. It is revealed by reveal_main once the app is mounted.
                .with_state_flags(StateFlags::all() & !StateFlags::VISIBLE)
                .build(),
        )
        .manage(Shared::default())
        .invoke_handler(tauri::generate_handler![
            splash_log,
            app_ready,
            confirm_close,
            read_clipboard,
            open_external_url,
            pick_path,
            save_file,
            save_export,
            read_dropped_file,
        ])
        .on_window_event(on_window_event)
        .setup(|app| {
            #[cfg(unix)]
            handle_term_signals(app.handle().clone());
            spawn_server(app.handle());
            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("error while building the application")
        .run(|app, event| {
            if let RunEvent::Exit = event {
                app.state::<Shared>().kill_server();
            }
        });
}

#[cfg(test)]
mod tests;
