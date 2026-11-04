//! Unit tests for the file-handling and drop-safety code in main.rs.

use super::*;
use std::net::TcpListener;

/// A fresh, uniquely named directory under the system temp dir.
fn scratch(tag: &str) -> PathBuf {
    let dir = std::env::temp_dir().join(format!("audaxdm-test-{}-{tag}", std::process::id()));
    std::fs::create_dir(&dir).unwrap();
    dir
}

/// Serves one canned HTTP response on a loopback port; returns the port.
fn serve_once(response: Vec<u8>) -> u16 {
    let listener = TcpListener::bind("127.0.0.1:0").unwrap();
    let port = listener.local_addr().unwrap().port();
    std::thread::spawn(move || {
        let (mut conn, _) = listener.accept().unwrap();
        // Read the whole request header first: closing with unread data would reset the connection.
        let mut request = Vec::new();
        let mut buf = [0u8; 256];
        while !request.windows(4).any(|w| w == b"\r\n\r\n") {
            let n = conn.read(&mut buf).unwrap();
            if n == 0 {
                break;
            }
            request.extend_from_slice(&buf[..n]);
        }
        conn.write_all(&response).unwrap();
    });
    port
}

// --- names and urls ---

#[test]
fn export_filename_accepts_only_the_temp_export_folder() {
    assert_eq!(export_filename("/static/temp/$1_2.csv"), Some("$1_2.csv"));
    assert_eq!(export_filename("/pgmanage/static/temp/a.xlsx"), Some("a.xlsx"));
    assert_eq!(export_filename("/static/temp/"), None);
    assert_eq!(export_filename("/static/temp/.."), None);
    assert_eq!(export_filename("/static/temp/a/b.csv"), None);
    assert_eq!(export_filename("/static/temp/a\\b.csv"), None);
    assert_eq!(export_filename("/file_manager/download/"), None);
    assert_eq!(export_filename("/static/other/a.csv"), None);
}

#[test]
fn same_server_requires_matching_scheme_host_and_port() {
    let own: Url = "http://localhost:8000/workspace/".parse().unwrap();
    assert!(is_same_server(&"http://localhost:8000/static/temp/a.csv".parse().unwrap(), &own));
    assert!(!is_same_server(&"http://localhost:8001/static/temp/a.csv".parse().unwrap(), &own));
    assert!(!is_same_server(&"http://127.0.0.1:8000/static/temp/a.csv".parse().unwrap(), &own));
    assert!(!is_same_server(&"https://localhost:8000/static/temp/a.csv".parse().unwrap(), &own));
}

#[test]
fn only_loopback_hosts_are_local() {
    assert!(is_local(&"http://localhost:8000/".parse().unwrap()));
    assert!(is_local(&"http://127.0.0.1:8000/".parse().unwrap()));
    assert!(!is_local(&"https://github.com/".parse().unwrap()));
    assert!(!is_local(&"http://localhost.evil.com/".parse().unwrap()));
}

#[test]
fn sanitize_file_name_strips_directories() {
    assert_eq!(sanitize_file_name("a.sql").as_deref(), Some("a.sql"));
    assert_eq!(sanitize_file_name("../../evil.csv").as_deref(), Some("evil.csv"));
    assert_eq!(sanitize_file_name("/etc/passwd").as_deref(), Some("passwd"));
    assert_eq!(sanitize_file_name(""), None);
    assert_eq!(sanitize_file_name(".."), None);
}

#[test]
fn percent_decode_handles_utf8_and_malformed_input() {
    assert_eq!(percent_decode("a%20b.sql"), "a b.sql");
    assert_eq!(percent_decode("%D1%82%D0%B5%D1%81%D1%82.sql"), "тест.sql");
    assert_eq!(percent_decode("100%"), "100%");
    assert_eq!(percent_decode("%zz"), "%zz");
    assert_eq!(percent_decode("%é"), "%é");
    assert_eq!(percent_decode("%"), "%");
}

#[test]
fn js_string_escapes_quotes_backslashes_and_newlines() {
    assert_eq!(js_string("a\"b\\c\nd"), "\"a\\\"b\\\\c\\nd\"");
    assert_eq!(js_string("plain"), "\"plain\"");
    assert_eq!(js_string("\u{1}"), "\"\\u0001\"");
}

// --- writing files ---

#[test]
fn write_via_part_writes_and_replaces_atomically() {
    let dir = scratch("wvp");
    let dest = dir.join("out.sql");
    std::fs::write(&dest, b"old").unwrap();
    write_via_part(&dest, |f| f.write_all(b"new").map_err(to_msg)).unwrap();
    assert_eq!(std::fs::read(&dest).unwrap(), b"new");
    assert_eq!(std::fs::read_dir(&dir).unwrap().count(), 1, "no part file left");
    std::fs::remove_file(&dest).unwrap();
    std::fs::remove_dir(&dir).unwrap();
}

#[test]
fn write_via_part_failure_keeps_the_existing_file() {
    let dir = scratch("wvpf");
    let dest = dir.join("out.sql");
    std::fs::write(&dest, b"keep").unwrap();
    assert!(write_via_part(&dest, |_| Err("boom".to_string())).is_err());
    assert_eq!(std::fs::read(&dest).unwrap(), b"keep");
    assert_eq!(std::fs::read_dir(&dir).unwrap().count(), 1, "no part file left");
    std::fs::remove_file(&dest).unwrap();
    std::fs::remove_dir(&dir).unwrap();
}

#[test]
fn existing_part_files_are_never_overwritten_or_deleted() {
    let dir = scratch("part");
    let dest = dir.join("out.csv");
    let stale = dir.join(format!("out.csv{PART_SUFFIX}"));
    std::fs::write(&stale, b"stale").unwrap();

    let port = serve_once(b"HTTP/1.0 200 OK\r\nContent-Length: 2\r\n\r\nhi".to_vec());
    fetch_to_file("127.0.0.1", port, "/static/temp/a.csv", &dest).unwrap();

    assert_eq!(std::fs::read(&stale).unwrap(), b"stale");
    assert_eq!(std::fs::read(&dest).unwrap(), b"hi");
    std::fs::remove_file(&stale).unwrap();
    std::fs::remove_file(&dest).unwrap();
    std::fs::remove_dir(&dir).unwrap();
}

// --- fetching exports ---

#[test]
fn fetch_writes_the_file_and_leaves_no_part_file() {
    let dir = scratch("ok");
    let port = serve_once(b"HTTP/1.0 200 OK\r\nContent-Length: 5\r\n\r\nhello".to_vec());
    let dest = dir.join("out.csv");
    fetch_to_file("127.0.0.1", port, "/static/temp/a.csv", &dest).unwrap();
    assert_eq!(std::fs::read(&dest).unwrap(), b"hello");
    assert_eq!(std::fs::read_dir(&dir).unwrap().count(), 1, "only the destination may remain");
    std::fs::remove_file(&dest).unwrap();
    std::fs::remove_dir(&dir).unwrap();
}

#[test]
fn fetch_failure_removes_only_its_own_part_file_and_keeps_existing_data() {
    let dir = scratch("fail");
    let dest = dir.join("out.csv");
    std::fs::write(&dest, b"existing").unwrap();
    let other = dir.join("other.txt");
    std::fs::write(&other, b"unrelated").unwrap();

    let port = serve_once(b"HTTP/1.0 404 Not Found\r\n\r\nnope".to_vec());
    assert!(fetch_to_file("127.0.0.1", port, "/static/temp/a.csv", &dest).is_err());

    assert_eq!(std::fs::read(&dest).unwrap(), b"existing", "destination untouched on failure");
    assert_eq!(std::fs::read(&other).unwrap(), b"unrelated");
    assert_eq!(std::fs::read_dir(&dir).unwrap().count(), 2, "no part file left behind");
    std::fs::remove_file(&dest).unwrap();
    std::fs::remove_file(&other).unwrap();
    std::fs::remove_dir(&dir).unwrap();
}

#[test]
fn truncated_transfer_is_rejected() {
    let dir = scratch("trunc");
    let dest = dir.join("out.csv");
    let port = serve_once(b"HTTP/1.0 200 OK\r\nContent-Length: 50\r\n\r\nshort".to_vec());
    assert!(fetch_to_file("127.0.0.1", port, "/static/temp/a.csv", &dest).is_err());
    assert!(!dest.exists());
    assert_eq!(std::fs::read_dir(&dir).unwrap().count(), 0);
    std::fs::remove_dir(&dir).unwrap();
}

#[test]
fn chunked_responses_are_rejected() {
    let dir = scratch("chunked");
    let dest = dir.join("out.csv");
    let port = serve_once(
        b"HTTP/1.1 200 OK\r\nTransfer-Encoding: chunked\r\n\r\n5\r\nhello\r\n0\r\n\r\n".to_vec(),
    );
    assert!(fetch_to_file("127.0.0.1", port, "/static/temp/a.csv", &dest).is_err());
    assert_eq!(std::fs::read_dir(&dir).unwrap().count(), 0);
    std::fs::remove_dir(&dir).unwrap();
}

// --- last directory ---

#[test]
fn last_dir_round_trips_and_ignores_missing_dirs() {
    let base = scratch("lastdir");
    let file = base.join("cfg").join("last-dialog-dir");
    assert_eq!(read_last_dir(&file), None);

    write_last_dir(&file, &base);
    assert_eq!(read_last_dir(&file), Some(base.clone()));

    write_last_dir(&file, &base.join("no-such-dir"));
    assert_eq!(read_last_dir(&file), None, "a directory that no longer exists is ignored");

    std::fs::remove_file(&file).unwrap();
    std::fs::remove_dir(base.join("cfg")).unwrap();
    std::fs::remove_dir(&base).unwrap();
}

// --- dropped files ---

#[test]
fn dropped_files_are_readable_only_if_registered() {
    let dir = scratch("drop");
    let file = dir.join("a.sql");
    std::fs::write(&file, "select 1;").unwrap();
    let other = dir.join("secret.txt");
    std::fs::write(&other, "no").unwrap();

    let shared = Shared::default();
    assert!(read_dropped(&shared, file.to_str().unwrap()).is_err());

    shared.dropped.lock().unwrap().insert(file.clone());
    assert_eq!(
        read_dropped(&shared, file.to_str().unwrap()).unwrap(),
        ("a.sql".to_string(), "select 1;".to_string())
    );
    assert!(read_dropped(&shared, other.to_str().unwrap()).is_err());
    assert!(read_dropped(&shared, dir.to_str().unwrap()).is_err());

    std::fs::remove_file(&file).unwrap();
    std::fs::remove_file(&other).unwrap();
    std::fs::remove_dir(&dir).unwrap();
}

#[test]
fn directories_are_refused_even_when_registered() {
    let dir = scratch("dropdir");
    let shared = Shared::default();
    shared.dropped.lock().unwrap().insert(dir.clone());
    assert!(read_dropped(&shared, dir.to_str().unwrap()).is_err());
    std::fs::remove_dir(&dir).unwrap();
}
