# Android Mobile Setup for SMKD

This project already includes Capacitor-based Android wiring. Use the commands below to build and open the native Android app.

## Prerequisites

- Android Studio installed
- Android SDK configured locally
- Node.js and pnpm installed
- Python backend environment ready

## Run locally

1. Start the backend:
   ```bash
   npm run dev:backend
   ```

2. Start the frontend dev server:
   ```bash
   npm run dev:ui
   ```

3. Sync the web app to the Android wrapper:
   ```bash
   npm run android:sync
   ```

4. Open Android Studio:
   ```bash
   npm run android:open
   ```

## Production native build

```bash
npm run android:sync
```

Then open the Android project in Android Studio and build the APK/AAB from there.

## Notes

- The web app is served from `fast-framework/packages/stock-bot-ui/dist` for Capacitor packaging.
- The native shell is designed to keep the same dark trading-terminal UI and a chart-first mobile layout.
- The terminal uses its in-repository SVG candlestick renderer; no TradingView chart engine or widget is embedded. The shell remains compatible with Android packaging and responsive mobile surfaces.
