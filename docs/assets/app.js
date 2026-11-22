const STORAGE_KEY = "smkd_backend_url";
const apiInput = document.getElementById("apiUrl");
const statusEl = document.getElementById("healthOut");
const scanBody = document.getElementById("scanBody");
const paperOut = document.getElementById("paperOut");

const savedUrl = localStorage.getItem(STORAGE_KEY);
if (savedUrl) apiInput.value = savedUrl;

function getBaseUrl() {
  const base = apiInput.value.trim().replace(/\/+$/, "");
  if (base) localStorage.setItem(STORAGE_KEY, base);
  return base;
}

function esc(v) {
  return String(v ?? "—")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

function setMetric(id, val, sub) {
  const el = document.getElementById(id);
  if (el) el.textContent = val;
  const subEl = document.getElementById(id + "Sub");
  if (subEl && sub !== undefined) subEl.textContent = sub;
}

async function fetchJson(base, path) {
  const res = await fetch(base + path, { mode: "cors" });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

function renderOverview(ov) {
  const sess = ov.session || {};
  setMetric("mSession", sess.phase || "UNAVAILABLE", `IST ${sess.ist_time || "—"}`);
  const nifty = ov.nifty_50 || {};
  const nVal = nifty.price != null ? `₹${nifty.price}` : "Unavailable";
  const nSub = nifty.change_pct != null ? `${nifty.change_pct >= 0 ? "+" : ""}${nifty.change_pct}% (${nifty.trend})` : "Provider unavailable";
  setMetric("mNifty", nVal, nSub);
  const vix = ov.india_vix || {};
  setMetric("mVix", vix.level != null ? String(vix.level) : "Unavailable", vix.regime || "UNAVAILABLE");
  setMetric("mBias", ov.macro_bias || "NEUTRAL", `Sectors: ${Object.keys(ov.sector_strengths || {}).length}`);
}

function renderScan(scan) {
  const rows = scan.results || [];
  if (!rows.length) {
    scanBody.innerHTML = '<tr><td colspan="7" class="warn">No scan results returned by backend.</td></tr>';
    return;
  }
  scanBody.innerHTML = rows.map((r) => {
    const dec = r.signal_decision || {};
    const sig = String(dec.signal || "WAIT");
    const cls = sig.includes("BUY") ? "pill-buy" : sig.includes("SELL") ? "pill-sell" : "pill-wait";
    const chg = r.change_pct != null ? `${r.change_pct >= 0 ? "+" : ""}${r.change_pct}%` : "—";
    const score = dec.confluence_score != null ? `${dec.confluence_score}/${dec.max_score || 11}` : "—";
    const levels = dec.target_1 != null && dec.stop_loss != null ? `T1 ₹${dec.target_1} / SL ₹${dec.stop_loss}` : "—";
    const via = dec.risk_sizing?.viability_status || "—";
    return `<tr>
      <td><strong>${esc(r.symbol)}</strong></td>
      <td>₹${esc(r.current_price)}</td>
      <td class="${(r.change_pct || 0) >= 0 ? "ok" : "err"}">${esc(chg)}</td>
      <td><span class="pill ${cls}">${esc(sig)}</span></td>
      <td>${esc(score)}</td>
      <td>${esc(levels)}</td>
      <td>${esc(via)}</td>
    </tr>`;
  }).join("");
}

function renderPaper(pnl, pos) {
  const openCount = (pos.positions || []).length;
  paperOut.innerHTML = `Open Positions: <strong>${openCount}</strong> | Closed Trades: <strong>${esc(pnl.trade_count)}</strong> | Realized P&amp;L: <strong>₹${esc(pnl.total_realized)}</strong> | Unrealized: <strong>₹${esc(pnl.total_unrealized)}</strong> | Win Rate: <strong>${esc(pnl.win_rate)}%</strong>`;
}

async function connectAndLoad() {
  const base = getBaseUrl();
  if (!base) {
    statusEl.innerHTML = '<span class="warn">Enter your backend API URL first.</span>';
    return;
  }
  statusEl.textContent = `Connecting to ${base}/health ...`;
  try {
    const h = await fetchJson(base, "/health");
    statusEl.innerHTML = `<span class="ok">ONLINE</span> — ${esc(h.service)} v${esc(h.version)} (${esc(base)})`;
  } catch (err) {
    statusEl.innerHTML = `<span class="err">UNREACHABLE</span> — ${esc(err.message)} (verify backend is running and SMKD_ALLOWED_ORIGINS allows this origin)`;
    return;
  }

  scanBody.innerHTML = '<tr><td colspan="7">Loading live scan from backend...</td></tr>';
  try {
    const [ov, scan, pnl, pos] = await Promise.all([
      fetchJson(base, "/api/overview"),
      fetchJson(base, "/api/scan"),
      fetchJson(base, "/api/paper/pnl"),
      fetchJson(base, "/api/paper/positions"),
    ]);
    renderOverview(ov);
    renderScan(scan);
    renderPaper(pnl, pos);
  } catch (err) {
    scanBody.innerHTML = `<tr><td colspan="7" class="err">Failed to load live data: ${esc(err.message)}</td></tr>`;
  }
}

document.getElementById("checkBtn").addEventListener("click", connectAndLoad);
