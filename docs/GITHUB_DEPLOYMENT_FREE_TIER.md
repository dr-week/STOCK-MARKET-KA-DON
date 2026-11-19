# GitHub Deployment & Free-Tier Backend Blueprint for SMKD

**Status:** Implementation Blueprint & Evaluated Free-Tier Architecture  
**Scope:** Deploying SMKD backend API, database, and web dashboard with zero cloud hosting cost using proven open platforms.

---

## 1. Executive Summary

SMKD is engineered as a lightweight modular monolith. While designed primarily for local intraday analysis and research, it can be deployed to reliable free-tier cloud infrastructure directly from GitHub with zero hosting expenses:

- **Frontend & Docs:** Hosted on **GitHub Pages** (100% free, automatic SSL, CDN).
- **Backend API:** Containerized via Docker and deployed to **Render** (750 free hrs/mo), **Koyeb** (always-on nano instance), or **Hugging Face Spaces** (16 GB RAM free).
- **Artifact Packaging:** Automated via **GitHub Actions** pushing multi-arch images to **GitHub Container Registry (GHCR)**.
- **Database:** **Turso (LibSQL/SQLite)** for zero-schema-rewrite persistence (9 GB free, 1B reads/mo) or **Neon/Supabase (Serverless PostgreSQL)**.
- **Zero-Port Tunneling:** **Cloudflare Tunnel (`cloudflared`)** for exposing a local workstation instance to a secure public HTTPS endpoint for free.

---

## 2. Free-Tier Backend Hosting Comparison

| Provider | Free Specs | Sleep / Inactivity Policy | Outbound Traffic & Quotas | Best Use Case for SMKD |
|:---|:---|:---|:---|:---|
| **Render** | 512 MB RAM, 0.1 CPU | Spins down after 15m inactivity (50s cold start) | 750 free instance hrs/month, 100 GB egress | Default backend API via `render.yaml` Blueprint. Single service runs 24/7. |
| **Koyeb** | 512 MB RAM, 0.1 vCPU, 2 GB SSD | **Does NOT spin down** on active free tier | 55 free service hours monthly credit pool; global edge | Production-like latency without cold starts. |
| **Hugging Face Spaces** | **2 vCPU, 16 GB RAM** | Sleeps after 48h idle unless pinged | High compute, direct Docker support | Ideal when running heavier Python quant models or memory-heavy historical backtests. |
| **Fly.io** | 256 MB RAM micro-VMs | Scale-to-zero | Credit-based; requires credit card verification | Backup container runtime. |
| **Vercel** | Serverless Python (`/api`) | Ephemeral (execution per request) | 10-15s timeout limit, no resident background workers | Lightweight webhook or gateway endpoints; **unsuitable** for paper-trade auto workers. |

> [!IMPORTANT]
> **Automatic Paper Runner Constraint:**  
> The SMKD automatic paper trading runner (`AutomaticPaperRunner`) is a persistent background worker designed to run during NSE market hours (9:15 AM – 3:30 PM IST). Serverless platforms with 15s execution limits (Vercel, AWS Lambda) terminate background workers. Choose a persistent container runtime (Render, Koyeb, Hugging Face, or a long-running dev VM) for automatic paper execution.

---

## 3. Free-Tier Database Solutions

| Database Engine | Provider | Free Tier Allowance | Strengths | Caveats & Gotchas |
|:---|:---|:---|:---|:---|
| **LibSQL / SQLite** | **Turso** | **9 GB storage**, 1 billion row reads/month | 100% SQLite compatible, native edge replication | Exact drop-in match for SMKD's SQLite databases (`paper_trades.db`, `signals_tree.db`). |
| **Serverless Postgres** | **Neon.tech** | **0.5 GB storage**, branchable databases | Autoscaling, instant branch creation, wakes up in <500ms | Generous free compute hours; does not pause after 7 days if queried. |
| **Managed Postgres** | **Supabase** | **500 MB database**, 5 GB egress, 2 active projects | Row-Level Security (RLS), auto REST API, PgBouncer | **Pauses after 7 days of inactivity** on Free plan. Requires periodic ping or upgrade. |

---

## 4. Zero-Cost Self-Hosted & Tunnel Alternatives

When you want to keep sensitive broker credentials (e.g., Groww read-only tokens) strictly on your local PC while accessing your dashboard from anywhere:

### A. Cloudflare Tunnel (`cloudflared`)
- Exposes your local `http://127.0.0.1:8000` to a secure public URL (e.g. `https://smkd-api.yourdomain.com`).
- **Zero cost**, requires no open ports, no port forwarding on your home router, and no static IP.
- Cloudflare handles DDoS protection and TLS termination.

```bash
# Expose local SMKD backend in 1 command
cloudflared tunnel --url http://localhost:8000
```

### B. GitHub Codespaces
- GitHub provides **60 free core-hours per month** for every account.
- Launch the repository in Codespaces:
  1. Installs Python 3.11 and Node.js automatically.
  2. Runs backend and frontend with built-in port forwarding.
  3. Provides an authenticated browser-accessible development workstation.

---

## 5. Step-by-Step Deployment Instructions

### Option 1: Deploy Backend to Render (1-Click Blueprint)

1. Fork or push this repository to your GitHub account.
2. Sign in to [Render](https://render.com/) with GitHub.
3. Click **New +** $\rightarrow$ **Blueprint**.
4. Connect the `STOCK-MARKET-KA-DON` repository. Render automatically reads [`render.yaml`](../render.yaml).
5. Specify your environment variables:
   - `PORT`: `10000` (set automatically)
   - `SMKD_ALLOWED_ORIGINS`: `https://<your-username>.github.io`
6. Click **Apply**. Render will build the Docker container and deploy the service.
7. Your API will be live at `https://smkd-backend.onrender.com/api` (verify at `.../health`).

### Option 2: Deploy Container via GitHub Container Registry (GHCR) to Koyeb

1. When you push to `main`, `.github/workflows/deploy-backend.yml` automatically builds and publishes the container to:
   `ghcr.io/<your-username>/stock-market-ka-don/smkd-backend:latest`
2. In [Koyeb](https://www.koyeb.com/), click **Create App** $\rightarrow$ **Docker**.
3. Point to your GHCR image.
4. Set port to `8000` and deploy.

### Option 3: Deploy Frontend & Docs to GitHub Pages

1. Navigate to **Settings** $\rightarrow$ **Pages** in your GitHub repository.
2. Under **Build and deployment** $\rightarrow$ **Source**, select **GitHub Actions**.
3. Push to `main` branch. `.github/workflows/deploy-pages.yml` will automatically build the static bundle and deploy to:
   `https://<your-username>.github.io/STOCK-MARKET-KA-DON/`

---

## 6. Cold-Start Mitigation & Market Hours Keep-Alive

Render free web services sleep after 15 minutes of inactivity. To ensure the scanner is awake and warm before the NSE market opens at 9:15 AM IST:

Add a lightweight scheduled GitHub Actions workflow or external cron (e.g., [cron-job.org](https://cron-job.org/)):

```yaml
# .github/workflows/keep-alive.yml
name: Market Hours Warm-Up
on:
  schedule:
    # 3:30 AM UTC = 9:00 AM IST (Monday to Friday)
    - cron: '30 3 * * 1-5'
jobs:
  ping:
    runs-on: ubuntu-latest
    steps:
      - run: curl -s https://smkd-backend.onrender.com/health || true
```

---

## 7. Security & Market Data Integrity

- **Never Commit Secrets:** Never commit Groww tokens, broker passwords, or database passwords to git. Store them in GitHub Repository Secrets or Render/Koyeb Environment Variables.
- **CORS Protection:** By default, only local origins and explicitly configured domains in `SMKD_ALLOWED_ORIGINS` are accepted.
- **Fail-Closed Market Data:** If external market data endpoints are rate-limited or unavailable on cloud IPs, SMKD returns an explicit `unavailable` or `delayed` status. Synthetic candles must never be fabricated in cloud or live environments.
