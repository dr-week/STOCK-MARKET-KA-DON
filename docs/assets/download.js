const RELEASES_API = "https://api.github.com/repos/dr-week/STOCK-MARKET-KA-DON/releases/latest";

function fmtMb(bytes) {
  return bytes ? `${(bytes / (1024 * 1024)).toFixed(1)} MB` : "";
}

async function syncLatestDownloads() {
  try {
    const res = await fetch(RELEASES_API, { headers: { Accept: "application/vnd.github+json" } });
    if (!res.ok) return;
    const rel = await res.json();
    const tag = rel.tag_name || "v2.0.0";
    const pill = document.getElementById("releasePill");
    if (pill) pill.textContent = `Latest Release • ${tag}`;

    const assets = rel.assets || [];
    const win = assets.find((a) => String(a.name || "").endsWith(".exe"));
    const apk = assets.find((a) => String(a.name || "").endsWith(".apk"));

    if (win) {
      const btn = document.getElementById("winDownloadBtn");
      const sz = document.getElementById("winSize");
      if (btn) btn.href = win.browser_download_url;
      if (sz && win.size) sz.textContent = fmtMb(win.size);
    }
    if (apk) {
      const btn = document.getElementById("apkDownloadBtn");
      const sz = document.getElementById("apkSize");
      if (btn) btn.href = apk.browser_download_url;
      if (sz && apk.size) sz.textContent = fmtMb(apk.size);
    }
  } catch {
    // Keep static v2.0.0 release fallback links if GitHub API is rate-limited.
  }
}

window.addEventListener("DOMContentLoaded", syncLatestDownloads);
