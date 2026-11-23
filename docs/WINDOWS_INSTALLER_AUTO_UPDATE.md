# Windows Lightweight Installer & GitHub Auto-Update Guide

SMKD ships a lightweight **Tauri v2 NSIS Windows installer** (`~4–8 MB`, using the built-in Windows WebView2 runtime instead of bundling Chromium).

## Key Capabilities
1. **Install Anywhere (`installMode: "both"`):** During setup, choose either per-user or per-machine installation and pick **any destination directory** (`C:\`, `D:\Apps\SMKD`, etc.).
2. **Run Directly After Installing:** The NSIS Finish screen launches Stock Market Ka Don immediately; first launch automatically sets up the isolated local Python backend (`%LOCALAPPDATA%\com.dangerlabs.smkd\runtime`) with zero manual Python/Node setup required.
3. **Automatic & Manual Updates from GitHub Releases:**
   - Open **Settings → About Software** inside the app.
   - Toggle **Automatically check for GitHub updates on startup** (enabled by default).
   - Click **Check for Updates** anytime to check `https://github.com/dr-week/STOCK-MARKET-KA-DON/releases/latest`.
   - When signed release artifacts (`latest.json` + `.sig`) are published, click **Download & Install Update** to download, cryptographically verify, install, and restart automatically.

## Publishing a New Windows Release
Push a version tag (or run **Actions → Build & Release Windows Installer → Run workflow**):

```bash
git tag v2.0.0
git push origin v2.0.0
```

[.github/workflows/release-windows.yml](../.github/workflows/release-windows.yml) builds the `.exe` NSIS installer on `windows-latest` and publishes it to GitHub Releases.

## Enabling 1-Click Signed In-App Auto-Updates (One-Time Setup)
Tauri v2 requires an Ed25519 signature before installing updates in-app:

1. Generate a signing keypair locally (never commit the private key):
   ```bash
   cd desktop/tauri
   npx tauri signer generate -w ~/.tauri/smkd.key
   ```
2. Add the **private key** content to GitHub **Settings → Secrets and variables → Actions → Secrets**:
   - `TAURI_SIGNING_PRIVATE_KEY`
   - `TAURI_SIGNING_PRIVATE_KEY_PASSWORD` (if you set a password)
3. Add the **public key** (`~/.tauri/smkd.key.pub`) to GitHub **Settings → Secrets and variables → Actions → Variables**:
   - `TAURI_SIGNING_PUBLIC_KEY`

Once configured, every `v*` release automatically signs the `.exe` installer, publishes `latest.json`, and enables 1-click in-app updates in **Settings → About Software**.
