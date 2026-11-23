use serde::Serialize;
use tauri::AppHandle;
use tauri_plugin_updater::UpdaterExt;

const REPO_URL: &str = "https://github.com/dr-week/STOCK-MARKET-KA-DON";

#[derive(Serialize)]
pub struct AppInfo {
    pub name: String,
    pub version: String,
    pub identifier: String,
    pub install_dir: String,
    pub repo_url: String,
}

#[derive(Serialize)]
pub struct UpdateCheckResult {
    pub available: bool,
    pub current_version: String,
    pub latest_version: Option<String>,
    pub notes: Option<String>,
    pub signed_updater: bool,
}

#[tauri::command]
pub fn get_app_info(app: AppHandle) -> AppInfo {
    let pkg = app.package_info();
    let install_dir = std::env::current_exe()
        .ok()
        .and_then(|p| p.parent().map(|d| d.display().to_string()))
        .unwrap_or_else(|| "Unknown".to_string());

    AppInfo {
        name: pkg.name.clone(),
        version: pkg.version.to_string(),
        identifier: app.config().identifier.clone(),
        install_dir,
        repo_url: REPO_URL.to_string(),
    }
}

#[tauri::command]
pub async fn check_for_update(app: AppHandle) -> Result<UpdateCheckResult, String> {
    let current = app.package_info().version.to_string();
    let updater = app
        .updater()
        .map_err(|e| format!("Updater unavailable (configure signing key): {e}"))?;

    match updater.check().await {
        Ok(Some(update)) => Ok(UpdateCheckResult {
            available: true,
            current_version: current,
            latest_version: Some(update.version.clone()),
            notes: update.body.clone(),
            signed_updater: true,
        }),
        Ok(None) => Ok(UpdateCheckResult {
            available: false,
            current_version: current,
            latest_version: None,
            notes: None,
            signed_updater: true,
        }),
        Err(e) => Err(format!("Signed update check failed: {e}")),
    }
}

#[tauri::command]
pub async fn install_update(app: AppHandle) -> Result<String, String> {
    let updater = app
        .updater()
        .map_err(|e| format!("Updater unavailable: {e}"))?;

    let update = updater
        .check()
        .await
        .map_err(|e| format!("Update check failed: {e}"))?
        .ok_or_else(|| "Already on the latest version.".to_string())?;

    update
        .download_and_install(|_, _| {}, || {})
        .await
        .map_err(|e| format!("Failed to download/install update: {e}"))?;

    app.restart();
}
