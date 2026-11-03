# Changelog

All notable changes to **Stock Market Ka Don (SMKD)** will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added
- Automated CI pipeline (`.github/workflows/ci.yml`) covering backend test suites and Zuari frontend verification.
- Isolated live provider integration workflow (`.github/workflows/provider-integration.yml`) separating deterministic PR tests from live network dependencies.
- Dependabot configuration (`.github/dependabot.yml`) for weekly dependency checks across GitHub Actions, pip, and npm.
- Locked backend dependency manifests (`requirements.txt` and `requirements-lock.txt`).
- Unit and contract test suite for live provider integrity (`test_live_provider_integration.py`).

---

## [v1.0.0] - 2026-10-25

### Added
- Core quantitative trading engine for Indian Equities (NSE) with 5-minute Intraday (MIS) and Swing (CNC) scanners.
- Closed-candle indicator calculation engine: VWAP, Dual EMA (9/21), 14-period RSI, ATR dynamic boundaries.
- Fine-grained reactive UI built on Danger Labs `@zuari` signals system (`packages/stock-bot-ui`).
- Local dev transaction controller, feed integrity validation, and backup snapshot mechanisms.
