const AUTO_UPDATE_KEY = "smkd_auto_update";
const REPO_RELEASES_API = "https://api.github.com/repos/dr-week/STOCK-MARKET-KA-DON/releases/latest";
const REPO_RELEASES_WEB = "https://github.com/dr-week/STOCK-MARKET-KA-DON/releases/latest";

const modal = document.getElementById("aboutModal");
const banner = document.getElementById("updateBanner");
const statusBox = document.getElementById("aboutUpdateStatus");
const installBtn = document.getElementById("installUpdateBtn");
const downloadLink = document.getElementById("downloadReleaseLink");
const autoToggle = document.getElementById("autoUpdateToggle");

let currentVersion = "2.0.0";
let signedUpdateReady = false;

function tauriInvoke(cmd, args) {
  const inv = window.__TAURI__?.core?.invoke;
  return typeof inv === "function" ? inv(cmd, args) : null;
}

function cmpSemver(a, b) {
  const pa = String(a || "0").replace(/^v/i, "").split(".").map((n) => parseInt(n, 10) || 0);
  const pb = String(b || "0").replace(/^v/i, "").split(".").map((n) => parseInt(n, 10) || 0);
  for (let i = 0; i < 3; i++) {
    if ((pa[i] || 0) !== (pb[i] || 0)) return (pa[i] || 0) - (pb[i] || 0);
  }
  return 0;
}

async function initAppInfo() {
  const info = await tauriInvoke("get_app_info")?.catch(() => null);
  const envEl = document.getElementById("aboutRuntime");
  const verEl = document.getElementById("aboutVersion");
  const dirEl = document.getElementById("aboutInstallDir");
  if (info) {
    currentVersion = info.version || currentVersion;
    if (verEl) verEl.textContent = `v${currentVersion}`;
    if (envEl) envEl.textContent = "Windows Desktop App (Tauri v2)";
    if (dirEl) dirEl.textContent = info.install_dir || "Custom Install Path";
  } else {
    if (verEl) verEl.textContent = `v${currentVersion}`;
    if (envEl) envEl.textContent = "Web Console (GitHub Pages)";
    if (dirEl) dirEl.textContent = "Browser (install Windows .exe for local mode)";
  }
}

function showUpdateAvailable(latest, notes, signed, exeUrl) {
  signedUpdateReady = signed;
  if (statusBox) {
    const mode = signed ? "Signed in-app update ready." : "New GitHub release available.";
    statusBox.innerHTML = `<span class="ok">Update available: v${latest}</span> (current v${currentVersion}). ${mode}${notes ? "<br/>" + notes.slice(0, 220) : ""}`;
  }
  if (installBtn) installBtn.style.display = signed ? "inline-block" : "none";
  if (downloadLink) {
    downloadLink.href = exeUrl || REPO_RELEASES_WEB;
    downloadLink.style.display = "inline-block";
  }
  if (banner) {
    banner.style.display = "flex";
    document.getElementById("bannerText").textContent = `New SMKD version v${latest} is available on GitHub Releases.`;
  }
}

async function checkUpdates(silent = false) {
  if (statusBox && !silent) statusBox.textContent = "Checking GitHub Releases for updates...";
  if (installBtn) installBtn.style.display = "none";
  if (downloadLink) downloadLink.style.display = "none";

  const signedRes = await tauriInvoke("check_for_update")?.catch(() => null);
  if (signedRes && signedRes.signed_updater) {
    if (signedRes.available) {
      showUpdateAvailable(signedRes.latest_version, signedRes.notes, true, REPO_RELEASES_WEB);
    } else if (statusBox && !silent) {
      statusBox.innerHTML = `<span class="ok">Up to date</span> — running latest signed version v${currentVersion}.`;
    }
    return;
  }

  try {
    const res = await fetch(REPO_RELEASES_API, { headers: { Accept: "application/vnd.github+json" } });
    if (res.status === 404) {
      if (statusBox && !silent) statusBox.textContent = `Current version v${currentVersion}. No GitHub Releases published yet (tag v2.0.0 to publish first installer).`;
      return;
    }
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const rel = await res.json();
    const tag = String(rel.tag_name || "").replace(/^v/i, "");
    const exeAsset = (rel.assets || []).find((a) => String(a.name || "").endsWith(".exe"));
    if (tag && cmpSemver(tag, currentVersion) > 0) {
      showUpdateAvailable(tag, rel.body || "", false, exeAsset?.browser_download_url || rel.html_url);
    } else if (statusBox && !silent) {
      statusBox.innerHTML = `<span class="ok">Up to date</span> — running v${currentVersion} (latest GitHub release: v${tag || currentVersion}).`;
    }
  } catch (err) {
    if (statusBox && !silent) statusBox.innerHTML = `<span class="warn">Update check failed:</span> ${err.message}`;
  }
}

async function runSignedInstall() {
  if (!signedUpdateReady) return;
  if (statusBox) statusBox.textContent = "Downloading, verifying signature, and installing update...";
  try {
    await tauriInvoke("install_update");
  } catch (err) {
    if (statusBox) statusBox.innerHTML = `<span class="err">Install failed:</span> ${err}`;
  }
}

const savedAuto = localStorage.getItem(AUTO_UPDATE_KEY);
if (autoToggle) {
  autoToggle.checked = savedAuto !== "false";
  autoToggle.addEventListener("change", () => {
    localStorage.setItem(AUTO_UPDATE_KEY, autoToggle.checked ? "true" : "false");
  });
}

document.getElementById("openAboutBtn")?.addEventListener("click", () => { if (modal) modal.style.display = "grid"; });
document.getElementById("bannerOpenBtn")?.addEventListener("click", () => { if (modal) modal.style.display = "grid"; });
document.getElementById("closeAboutBtn")?.addEventListener("click", () => { if (modal) modal.style.display = "none"; });
document.getElementById("manualCheckBtn")?.addEventListener("click", () => checkUpdates(false));
installBtn?.addEventListener("click", runSignedInstall);

window.addEventListener("DOMContentLoaded", async () => {
  await initAppInfo();
  if (!autoToggle || autoToggle.checked) checkUpdates(true);
});
