from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()


@router.get("/dashboard", response_class=HTMLResponse, include_in_schema=False)
async def dashboard():
    return """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Clearpath Lead Intelligence</title>
  <style>
    :root {
      color-scheme: light;
      --bg: #f6f8fb;
      --panel: #ffffff;
      --text: #17202a;
      --muted: #667085;
      --line: #d9e0ea;
      --accent: #1463ff;
      --danger: #b42318;
      --ok: #027a48;
      --warn: #b54708;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      background: var(--bg);
      color: var(--text);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      font-size: 14px;
    }
    header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      padding: 18px 24px;
      background: #0f172a;
      color: white;
      border-bottom: 1px solid #111827;
    }
    h1 { margin: 0; font-size: 20px; font-weight: 700; letter-spacing: 0; }
    h2 { margin: 0 0 12px; font-size: 15px; font-weight: 700; letter-spacing: 0; }
    main { padding: 20px 24px 28px; max-width: 1440px; margin: 0 auto; }
    .site-footer {
      max-width: 1440px;
      margin: 0 auto;
      padding: 0 24px 22px;
      color: var(--muted);
      font-size: 12px;
      font-weight: 700;
      letter-spacing: 0;
    }
    .toolbar { display: flex; align-items: center; gap: 8px; }
    input {
      height: 36px;
      border: 1px solid #475467;
      border-radius: 6px;
      padding: 0 10px;
      min-width: 240px;
      background: #111827;
      color: white;
    }
    button {
      height: 36px;
      border: 1px solid transparent;
      border-radius: 6px;
      padding: 0 12px;
      background: var(--accent);
      color: white;
      font-weight: 700;
      cursor: pointer;
    }
    .grid {
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 12px;
      margin-bottom: 14px;
    }
    .panel {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 14px;
    }
    .kpi-label { color: var(--muted); font-size: 12px; font-weight: 700; text-transform: uppercase; }
    .kpi-value { font-size: 28px; font-weight: 800; margin-top: 6px; letter-spacing: 0; }
    .layout {
      display: grid;
      grid-template-columns: 1.2fr 1fr;
      gap: 14px;
      align-items: start;
    }
    table { width: 100%; border-collapse: collapse; }
    th, td { padding: 10px 8px; border-bottom: 1px solid var(--line); text-align: left; vertical-align: top; }
    th { color: var(--muted); font-size: 12px; font-weight: 800; text-transform: uppercase; }
    .stack { display: grid; gap: 14px; }
    .score-list { display: grid; gap: 8px; }
    .score-card {
      display: grid;
      grid-template-columns: 56px 1fr auto;
      gap: 10px;
      align-items: start;
      padding: 10px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #fbfdff;
    }
    .score {
      display: grid;
      place-items: center;
      width: 48px;
      height: 48px;
      border-radius: 999px;
      background: #eaf1ff;
      color: #0b4fd8;
      font-weight: 800;
    }
    .muted { color: var(--muted); }
    .pill {
      display: inline-flex;
      align-items: center;
      min-height: 24px;
      padding: 2px 8px;
      border-radius: 999px;
      font-size: 12px;
      font-weight: 800;
      background: #eef2f6;
      color: #344054;
    }
    .pill.high { background: #ecfdf3; color: var(--ok); }
    .pill.medium { background: #fffaeb; color: var(--warn); }
    .pill.review { background: #fef3f2; color: var(--danger); }
    .status { min-height: 24px; color: var(--muted); }
    @media (max-width: 980px) {
      header { align-items: flex-start; flex-direction: column; }
      .toolbar { width: 100%; }
      input { min-width: 0; flex: 1; }
      .grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
      .layout { grid-template-columns: 1fr; }
    }
    @media (max-width: 560px) {
      main { padding: 14px; }
      .site-footer { padding: 0 14px 18px; }
      .grid { grid-template-columns: 1fr; }
      .score-card { grid-template-columns: 48px 1fr; }
      .score-card .pill { grid-column: 2; width: max-content; }
    }
  </style>
</head>
<body>
  <header>
    <h1>Clearpath Lead Intelligence</h1>
    <div class="toolbar">
      <input id="apiKey" type="password" placeholder="X-Clearpath-API-Key">
      <button id="refresh">Refresh</button>
    </div>
  </header>
  <main>
    <div id="status" class="status"></div>
    <section class="grid" id="kpis"></section>
    <section class="layout">
      <div class="stack">
        <section class="panel">
          <h2>Lead Source Scorecard</h2>
          <div id="sourcePerformance"></div>
        </section>
        <section class="panel">
          <h2>County Performance</h2>
          <div id="countyPerformance"></div>
        </section>
      </div>
      <div class="stack">
        <section class="panel">
          <h2>Needs Review Queue</h2>
          <div id="leadScores" class="score-list"></div>
        </section>
        <section class="panel">
          <h2>Provider Quality Signals</h2>
          <div id="qualitySignals"></div>
        </section>
      </div>
    </section>
  </main>
  <footer class="site-footer">©2026 SUPREME AI VENTURES LLC</footer>
  <script>
    const apiKeyInput = document.getElementById("apiKey");
    const statusNode = document.getElementById("status");
    apiKeyInput.value = localStorage.getItem("clearpathApiKey") || "";

    const esc = (value) => String(value ?? "").replace(/[&<>"']/g, (char) => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
    })[char]);

    async function fetchJson(path) {
      const headers = {};
      const key = apiKeyInput.value.trim();
      if (key) headers["X-Clearpath-API-Key"] = key;
      const response = await fetch(path, { headers });
      if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
      return response.json();
    }

    function renderKpis(summary) {
      const kpis = [
        ["Total leads", summary.total_leads],
        ["Needs review", summary.needs_review_count],
        ["Lead sources", summary.total_sources],
        ["Avg score", summary.average_score ?? "n/a"],
      ];
      document.getElementById("kpis").innerHTML = kpis.map(([label, value]) => `
        <div class="panel">
          <div class="kpi-label">${esc(label)}</div>
          <div class="kpi-value">${esc(value)}</div>
        </div>
      `).join("");
    }

    function renderSourcePerformance(rows) {
      document.getElementById("sourcePerformance").innerHTML = `
        <table>
          <thead><tr><th>Source</th><th>Leads</th><th>Avg Score</th><th>Review</th><th>Hot/Warm</th><th>Spend</th></tr></thead>
          <tbody>
            ${rows.map((row) => `
              <tr>
                <td><strong>${esc(row.source)}</strong><br><span class="muted">${esc(row.channel || row.vendor_name || "")}</span></td>
                <td>${esc(row.total_leads)}</td>
                <td>${esc(row.average_score ?? "n/a")}</td>
                <td>${esc(row.needs_review_count)}</td>
                <td>${esc(row.hot_leads)} / ${esc(row.warm_leads)}</td>
                <td>${row.estimated_spend_dollars == null ? "n/a" : "$" + esc(row.estimated_spend_dollars)}</td>
              </tr>
            `).join("")}
          </tbody>
        </table>`;
    }

    function renderCountyPerformance(rows) {
      document.getElementById("countyPerformance").innerHTML = `
        <table>
          <thead><tr><th>County</th><th>Leads</th><th>Hot/Warm</th><th>Avg Score</th><th>Median</th><th>DOM</th></tr></thead>
          <tbody>
            ${rows.map((row) => `
              <tr>
                <td><strong>${esc(row.county)}</strong><br><span class="muted">${esc(row.state)}</span></td>
                <td>${esc(row.total_leads)}</td>
                <td>${esc(row.hot_leads)} / ${esc(row.warm_leads)}</td>
                <td>${esc(row.average_score ?? "n/a")}</td>
                <td>${row.median_price == null ? "n/a" : "$" + esc(row.median_price.toLocaleString())}</td>
                <td>${esc(row.avg_dom ?? "n/a")}</td>
              </tr>
            `).join("")}
          </tbody>
        </table>`;
    }

    function renderLeadScores(rows) {
      document.getElementById("leadScores").innerHTML = rows.map((row) => `
        <div class="score-card">
          <div class="score">${esc(row.score)}</div>
          <div>
            <strong>${esc(row.lead_name)}</strong>
            <div class="muted">${esc(row.source || "unknown")} / ${esc(row.county || "unknown")} / ${esc(row.status)}</div>
            <div class="muted">${esc(row.reasons.slice(0, 3).join(" | "))}</div>
          </div>
          <span class="pill ${esc(row.priority)}">${esc(row.priority)}</span>
        </div>
      `).join("") || '<span class="muted">No leads require review.</span>';
    }

    function renderQualitySignals(sources, counties, summary) {
      const rankedSources = [...sources].filter((row) => row.average_score !== null && row.average_score !== undefined);
      const bestSource = rankedSources.sort((a, b) => b.average_score - a.average_score)[0];
      const reviewSource = [...sources].sort((a, b) => b.needs_review_count - a.needs_review_count)[0];
      const bestCounty = [...counties]
        .filter((row) => row.average_score !== null && row.average_score !== undefined)
        .sort((a, b) => b.average_score - a.average_score)[0];
      document.getElementById("qualitySignals").innerHTML = `
        <table>
          <thead><tr><th>Signal</th><th>Current Read</th></tr></thead>
          <tbody>
            <tr>
              <td>Best source by score</td>
              <td>${bestSource ? `${esc(bestSource.source)} (${esc(bestSource.average_score)})` : "n/a"}</td>
            </tr>
            <tr>
              <td>Source needing review</td>
              <td>${reviewSource ? `${esc(reviewSource.source)} (${esc(reviewSource.needs_review_count)} leads)` : "n/a"}</td>
            </tr>
            <tr>
              <td>Best county by score</td>
              <td>${bestCounty ? `${esc(bestCounty.county)} (${esc(bestCounty.average_score)})` : "n/a"}</td>
            </tr>
            <tr>
              <td>Recent GHL events</td>
              <td>${esc(summary.recent_webhook_events)}</td>
            </tr>
          </tbody>
        </table>`;
    }

    async function refreshDashboard() {
      localStorage.setItem("clearpathApiKey", apiKeyInput.value.trim());
      statusNode.textContent = "Loading...";
      try {
        const [summary, sources, counties, scores] = await Promise.all([
          fetchJson("/api/intelligence/summary"),
          fetchJson("/api/intelligence/source-performance"),
          fetchJson("/api/intelligence/county-performance"),
          fetchJson("/api/intelligence/lead-scores?needs_review=true&limit=8"),
        ]);
        renderKpis(summary);
        renderSourcePerformance(sources);
        renderCountyPerformance(counties);
        renderLeadScores(scores);
        renderQualitySignals(sources, counties, summary);
        statusNode.textContent = `Updated ${new Date().toLocaleTimeString()}`;
      } catch (error) {
        statusNode.textContent = `Unable to load dashboard: ${error.message}`;
      }
    }

    document.getElementById("refresh").addEventListener("click", refreshDashboard);
    refreshDashboard();
  </script>
</body>
</html>
"""
