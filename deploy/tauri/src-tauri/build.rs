fn main() {
    tauri_build::try_build(
        tauri_build::Attributes::new().app_manifest(
            tauri_build::AppManifest::new().commands(&["splash_log", "confirm_close", "read_clipboard", "pick_path", "open_external_url", "save_export", "save_file", "read_dropped_file", "app_ready"]),
        ),
    )
    .expect("failed to run tauri-build");
}
