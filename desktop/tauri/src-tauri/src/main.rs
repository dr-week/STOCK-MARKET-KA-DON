#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::fs::{self, File, OpenOptions};
use std::io::{Read, Write};
use std::net::{SocketAddr, TcpStream};
use std::path::{Path, PathBuf};
use std::process::{Child, Command, Stdio};
use std::sync::Mutex;
use std::thread;
use std::time::{Duration, Instant};
use tauri::{AppHandle, Manager, RunEvent};

#[cfg(windows)]
use std::os::windows::process::CommandExt;

#[cfg(windows)]
const CREATE_NO_WINDOW: u32 = 0x08000000;

struct BackendProcess(Mutex<Option<Child>>);

fn development_root() -> PathBuf {
    let source_root = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../../..");
    source_root.canonicalize().unwrap_or(source_root)
}

fn service_is_ready() -> bool {
    let address: SocketAddr = "127.0.0.1:8000".parse().expect("valid backend address");
    let Ok(mut stream) = TcpStream::connect_timeout(&address, Duration::from_millis(500)) else {
        return false;
    };
    let _ = stream.set_read_timeout(Some(Duration::from_secs(1)));
    if stream.write_all(b"GET /health HTTP/1.1\r\nHost: 127.0.0.1\r\nConnection: close\r\n\r\n").is_err() {
        return false;
    }
    let mut response = String::new();
    stream.read_to_string(&mut response).is_ok()
        && response.contains("200 OK")
        && response.contains("NSE Signal Engine")
}

fn first_existing(candidates: &[PathBuf]) -> Option<PathBuf> {
    candidates.iter().find(|path| path.is_file()).cloned()
}

fn log_file(path: &Path) -> std::io::Result<File> {
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent)?;
    }
    OpenOptions::new().create(true).append(true).open(path)
}

fn hidden_command(command: &mut Command) {
    #[cfg(windows)]
    command.creation_flags(CREATE_NO_WINDOW);
}

#[cfg(windows)]
fn ensure_webview_runtime() -> Result<(), String> {
    let executable = std::env::current_exe()
        .map_err(|error| format!("Could not locate the launcher: {error}"))?;
    let executable_dir = executable
        .parent()
        .ok_or_else(|| "Could not locate the launcher folder.".to_string())?;
    let bootstrap_script = executable_dir.join("bootstrap/ensure_webview.ps1");
    if !bootstrap_script.is_file() {
        if cfg!(debug_assertions) {
            return Ok(());
        }
        return Err("The portable package is missing its WebView2 setup script.".to_string());
    }

    let local_app_data = std::env::var_os("LOCALAPPDATA")
        .map(PathBuf::from)
        .ok_or_else(|| "Windows did not provide a local app-data directory.".to_string())?;
    let log_path = local_app_data
        .join("com.dangerlabs.smkd")
        .join("logs/webview-bootstrap.log");
    let output = log_file(&log_path)
        .map_err(|error| format!("Could not open WebView2 setup log: {error}"))?;
    let error_output = output
        .try_clone()
        .map_err(|error| format!("Could not prepare WebView2 setup log: {error}"))?;
    let mut command = Command::new("powershell.exe");
    command
        .args([
            "-NoLogo",
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
        ])
        .arg(bootstrap_script)
        .stdin(Stdio::null())
        .stdout(Stdio::from(output))
        .stderr(Stdio::from(error_output));
    hidden_command(&mut command);
    let status = command
        .status()
        .map_err(|error| format!("Could not check WebView2: {error}"))?;
    if !status.success() {
        return Err(format!(
            "WebView2 setup failed. Check {} for details.",
            log_path.display()
        ));
    }
    Ok(())
}

#[cfg(not(windows))]
fn ensure_webview_runtime() -> Result<(), String> {
    Ok(())
}

fn run_backend_setup(
    resource_dir: &Path,
    data_dir: &Path,
) -> Result<PathBuf, String> {
    let runtime_dir = data_dir.join("runtime");
    let backend_source = resource_dir.join("backend");
    let bundled_script = resource_dir.join("bootstrap/prepare_backend.ps1");
    let script = first_existing(&[bundled_script])
        .ok_or_else(|| "The backend setup script is missing from the app.".to_string())?;
    if !backend_source.join("requirements-lock.txt").is_file() {
        return Err("The backend runtime files are missing from the app package.".to_string());
    }

    let log_path = data_dir.join("logs/bootstrap.log");
    let output = log_file(&log_path).map_err(|error| format!("Could not open setup log: {error}"))?;
    let error_output = output
        .try_clone()
        .map_err(|error| format!("Could not prepare setup log: {error}"))?;
    let mut command = Command::new("powershell.exe");
    command
        .args([
            "-NoLogo",
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
        ])
        .arg(script)
        .arg("-BackendSource")
        .arg(&backend_source)
        .arg("-RuntimeDir")
        .arg(&runtime_dir)
        .arg("-AppVersion")
        .arg(env!("CARGO_PKG_VERSION"))
        .stdin(Stdio::null())
        .stdout(Stdio::from(output))
        .stderr(Stdio::from(error_output));
    hidden_command(&mut command);
    let status = command
        .status()
        .map_err(|error| format!("Could not prepare the private Python environment: {error}"))?;
    if !status.success() {
        return Err(format!(
            "Backend setup failed. Check {} for details.",
            log_path.display()
        ));
    }

    let python = runtime_dir.join("venv/Scripts/python.exe");
    if !python.is_file() {
        return Err(format!(
            "Backend setup completed without a Python executable. Check {}.",
            log_path.display()
        ));
    }
    Ok(backend_source)
}

fn packaged_resource_dir(executable_dir: &Path) -> PathBuf {
    #[cfg(windows)]
    {
        // Tauri's Windows resource directory is the executable's directory.
        return executable_dir.to_path_buf();
    }
    #[cfg(not(windows))]
    {
        executable_dir.to_path_buf()
    }
}

fn spawn_backend(
    python: &Path,
    backend_dir: &Path,
    data_dir: &Path,
    log_path: &Path,
    use_app_data: bool,
) -> Result<Child, String> {
    let output = log_file(log_path).map_err(|error| format!("Could not open backend log: {error}"))?;
    let error_output = output
        .try_clone()
        .map_err(|error| format!("Could not prepare backend log: {error}"))?;
    let mut command = Command::new(python);
    command
        .args(["-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000"])
        .current_dir(backend_dir)
        .stdin(Stdio::null())
        .stdout(Stdio::from(output))
        .stderr(Stdio::from(error_output));
    if use_app_data {
        command.env("SMKD_DATA_DIR", data_dir.join("data"));
    }
    hidden_command(&mut command);
    command.spawn().map_err(|error| format!("Could not start the backend: {error}"))
}

fn wait_for_backend(child: &mut Child) -> bool {
    let deadline = Instant::now() + Duration::from_secs(45);
    while Instant::now() < deadline {
        if service_is_ready() {
            return true;
        }
        if child.try_wait().ok().flatten().is_some() {
            return false;
        }
        thread::sleep(Duration::from_millis(400));
    }
    service_is_ready()
}

fn start_backend(
    root: Option<&Path>,
    resource_dir: &Path,
    data_dir: &Path,
) -> Result<Option<Child>, String> {
    if service_is_ready() {
        return Ok(None);
    }

    if cfg!(debug_assertions) {
        let root = root.ok_or_else(|| "The development checkout could not be found.".to_string())?;
        let backend_dir = root.join("stock-signal-bot/backend");
        let python = first_existing(&[
            backend_dir.join(".venv/Scripts/python.exe"),
            root.join(".venv/Scripts/python.exe"),
        ])
        .ok_or_else(|| "The backend virtual environment is missing from this checkout.".to_string())?;
        let mut child = spawn_backend(
            &python,
            &backend_dir,
            data_dir,
            &root.join(".runtime/tauri/backend.log"),
            false,
        )?;
        if !wait_for_backend(&mut child) {
            let _ = child.kill();
            return Err(format!("The backend did not start. Check {}.", root.join(".runtime/tauri/backend.log").display()));
        }
        return Ok(Some(child));
    }

    let backend_dir = run_backend_setup(resource_dir, data_dir)?;
    let python = data_dir.join("runtime/venv/Scripts/python.exe");
    let mut child = spawn_backend(
        &python,
        &backend_dir,
        data_dir,
        &data_dir.join("logs/backend.log"),
        true,
    )?;
    if !wait_for_backend(&mut child) {
        let _ = child.kill();
        return Err(format!("The backend did not start. Check {}.", data_dir.join("logs/backend.log").display()));
    }
    Ok(Some(child))
}

#[cfg(windows)]
fn show_startup_error(message: &str) {
    use std::ffi::OsStr;
    use std::os::windows::ffi::OsStrExt;
    let text: Vec<u16> = OsStr::new(message).encode_wide().chain(Some(0)).collect();
    let title: Vec<u16> = OsStr::new("SMKD desktop app").encode_wide().chain(Some(0)).collect();
    unsafe extern "system" {
        fn MessageBoxW(hwnd: isize, text: *const u16, caption: *const u16, kind: u32) -> i32;
    }
    unsafe {
        MessageBoxW(0, text.as_ptr(), title.as_ptr(), 0x10);
    }
}

#[cfg(not(windows))]
fn show_startup_error(message: &str) {
    eprintln!("{message}");
}

fn reveal_dashboard(app: &AppHandle) {
    if let Some(window) = app.get_webview_window("main") {
        let _ = window.eval("window.location.replace('index.html')");
    }
}

fn main() {
    if let Err(error) = ensure_webview_runtime() {
        show_startup_error(&error);
        std::process::exit(1);
    }

    let app = tauri::Builder::default()
        .manage(BackendProcess(Mutex::new(None)))
        .setup(move |app| {
            let app_handle = app.handle().clone();
            let root = if cfg!(debug_assertions) {
                Some(development_root())
            } else {
                None
            };
            let executable_dir = std::env::current_exe()
                .ok()
                .and_then(|path| path.parent().map(Path::to_path_buf));
            let resource_dir = if cfg!(debug_assertions) {
                executable_dir
                    .as_deref()
                    .map(packaged_resource_dir)
                    .unwrap_or_default()
            } else {
                app.path().resource_dir().ok().or_else(|| {
                    executable_dir.as_deref().map(packaged_resource_dir)
                }).unwrap_or_default()
            };
            let data_dir = app
                .path()
                .app_local_data_dir()
                .map_err(|error| format!("Could not find the local app data directory: {error}"))?;

            thread::spawn(move || match start_backend(root.as_deref(), &resource_dir, &data_dir) {
                Ok(child) => {
                    if let Some(child) = child {
                        if let Some(state) = app_handle.try_state::<BackendProcess>() {
                            if let Ok(mut slot) = state.0.lock() {
                                *slot = Some(child);
                            }
                        }
                    }
                    reveal_dashboard(&app_handle);
                }
                Err(error) => {
                    show_startup_error(&error);
                    app_handle.exit(1);
                }
            });
            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("error while starting SMKD desktop app");

    app.run(|handle, event| {
        if matches!(event, RunEvent::Exit) {
            if let Some(state) = handle.try_state::<BackendProcess>() {
                if let Ok(mut child_slot) = state.0.lock() {
                    if let Some(child) = child_slot.as_mut() {
                        let _ = child.kill();
                    }
                }
            }
        }
    });
}
