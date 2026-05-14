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
  <title>Clearpath Paid Lead Analytics</title>
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
      --ink: #0f172a;
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
      display: grid;
      grid-template-columns: 1fr auto;
      gap: 16px;
      padding: 18px 24px;
      background: var(--ink);
      color: white;
      border-bottom: 1px solid #111827;
    }
    h1 { margin: 0; font-size: 20px; font-weight: 800; letter-spacing: 0; }
    h2 { margin: 0 0 12px; font-size: 15px; font-weight: 800; letter-spacing: 0; }
    .subtitle { margin-top: 4px; color: #cbd5e1; max-width: 760px; line-height: 1.4; }
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
    .toolbar { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; justify-content: flex-end; }
    input, select {
      height: 36px;
      border: 1px solid #475467;
      border-radius: 6px;
      padding: 0 10px;
      min-width: 160px;
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
      font-weight: 800;
      cursor: pointer;
    }
    .filters {
      display: flex;
      align-items: center;
      gap: 8px;
      flex-wrap: wrap;
      margin: 0 0 14px;
    }
    .filters input, .filters select {
      background: white;
      color: var(--text);
      border-color: var(--line);
    }
    .import-panel {
      display: grid;
      grid-template-columns: minmax(180px, 1fr) minmax(140px, 0.5fr) minmax(220px, 1.2fr) auto;
      gap: 8px;
      align-items: center;
    }
    .import-panel input {
      background: white;
      color: var(--text);
      border-color: var(--line);
      min-width: 0;
    }
    .grid {
      display: grid;
      grid-template-columns: repeat(5, minmax(0, 1fr));
      gap: 12px;
      margin-bottom: 14px;
    }
    .panel {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 14px;
    }
    .kpi-label { color: var(--muted); font-size: 12px; font-weight: 800; text-transform: uppercase; }
    .kpi-value { font-size: 26px; font-weight: 900; margin-top: 6px; letter-spacing: 0; }
    .layout {
      display: grid;
      grid-template-columns: 1.35fr 0.85fr;
      gap: 14px;
      align-items: start;
    }
    table { width: 100%; border-collapse: collapse; }
    th, td { padding: 10px 8px; border-bottom: 1px solid var(--line); text-align: left; vertical-align: top; }
    th { color: var(--muted); font-size: 12px; font-weight: 900; text-transform: uppercase; }
    tbody tr:hover { background: #f8fafc; }
    .stack { display: grid; gap: 14px; }
    .stage-grid { display: grid; grid-template-columns: repeat(7, minmax(0, 1fr)); gap: 8px; }
    .stage {
      min-height: 78px;
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 10px;
      background: #fbfdff;
    }
    .stage strong { display: block; font-size: 22px; margin-bottom: 4px; }
    .stage span { color: var(--muted); font-size: 12px; font-weight: 800; text-transform: uppercase; }
    .stale-list { display: grid; gap: 8px; }
    .stale-card {
      display: grid;
      gap: 4px;
      padding: 10px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #fffdf8;
    }
    .muted { color: var(--muted); }
    .money { font-weight: 900; color: var(--ok); }
    .pill {
      display: inline-flex;
      align-items: center;
      min-height: 24px;
      padding: 2px 8px;
      border-radius: 999px;
      font-size: 12px;
      font-weight: 900;
      background: #eef2f6;
      color: #344054;
      white-space: nowrap;
    }
    .pill.closed { background: #ecfdf3; color: var(--ok); }
    .pill.dead { background: #fef3f2; color: var(--danger); }
    .pill.contract, .pill.offer, .pill.appointment { background: #eaf1ff; color: #0b4fd8; }
    .pill.received, .pill.contacted { background: #fffaeb; color: var(--warn); }
    .status { min-height: 24px; color: var(--muted); }
    @media (max-width: 1100px) {
      header { grid-template-columns: 1fr; }
      .toolbar { justify-content: flex-start; }
      .grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
      .layout { grid-template-columns: 1fr; }
      .stage-grid { grid-template-columns: repeat(3, minmax(0, 1fr)); }
      .import-panel { grid-template-columns: repeat(2, minmax(0, 1fr)); }
    }
    @media (max-width: 620px) {
      main { padding: 14px; }
      .site-footer { padding: 0 14px 18px; }
      .grid, .stage-grid { grid-template-columns: 1fr; }
      .import-panel { grid-template-columns: 1fr; }
      input, select, button { width: 100%; }
      .toolbar, .filters { width: 100%; }
      .table-wrap { overflow-x: auto; }
      table { min-width: 760px; }
    }
  </style>
</head>
<body>
  <header>
    <div>
      <h1>Clearpath Paid Lead Analytics</h1>
      <div class="subtitle">GHL-connected reporting for paid seller leads: source ROI, funnel outcomes, stale leads, and normalized provider fields.</div>
    </div>
    <div class="toolbar">
      <input id="apiKey" type="password" placeholder="X-Clearpath-API-Key">
      <button id="refresh">Refresh</button>
    </div>
  </header>
  <main>
    <div class="filters">
      <input id="sourceFilter" placeholder="Source">
      <input id="countyFilter" placeholder="County">
      <select id="stageFilter">
        <option value="">All lifecycle stages</option>
        <option value="received">Received</option>
        <option value="contacted">Contacted</option>
        <option value="appointment">Appointment</option>
        <option value="offer">Offer</option>
        <option value="contract">Contract</option>
        <option value="closed">Closed</option>
        <option value="dead">Dead</option>
      </select>
      <input id="motivationFilter" placeholder="Motivation contains">
    </div>
    <div id="status" class="status"></div>
    <section class="panel" style="margin-bottom:14px">
      <h2>CSV Backfill</h2>
      <div class="import-panel">
        <input id="csvSource" placeholder="Default source/provider">
        <input id="csvCost" type="number" min="0" step="0.01" placeholder="Cost per lead">
        <input id="csvFile" type="file" accept=".csv,text/csv">
        <button id="importCsv" type="button">Import CSV</button>
      </div>
      <div id="importStatus" class="muted" style="margin-top:8px">Use CSV for historical backfill; GHL webhooks keep new leads current.</div>
    </section>
    <section class="grid" id="kpis"></section>
    <section class="panel">
      <h2>Acquisition Funnel</h2>
      <div id="funnel" class="stage-grid"></div>
    </section>
    <section class="layout" style="margin-top:14px">
      <div class="stack">
        <section class="panel">
          <h2>Source ROI Scorecard</h2>
          <div id="sourceRoi" class="table-wrap"></div>
        </section>
        <section class="panel">
          <h2>All Leads</h2>
          <div id="leadsTable" class="table-wrap"></div>
        </section>
      </div>
      <div class="stack">
        <section class="panel">
          <h2>Stale Lead Queue</h2>
          <div id="staleLeads" class="stale-list"></div>
        </section>
        <section class="panel">
          <h2>Market Context</h2>
          <div id="countyPerformance" class="table-wrap"></div>
        </section>
      </div>
    </section>
  </main>
  <footer class="site-footer">©2026 SUPREME AI VENTURES LLC</footer>
  <script>
    const apiKeyInput = document.getElementById("apiKey");
    const statusNode = document.getElementById("status");
    const importStatus = document.getElementById("importStatus");
    const filterIds = ["sourceFilter", "countyFilter", "stageFilter", "motivationFilter"];
    apiKeyInput.value = localStorage.getItem("clearpathApiKey") || "";

    const esc = (value) => String(value ?? "").replace(/[&<>"']/g, (char) => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
    })[char]);
    const dollars = (value) => value == null ? "n/a" : `$${Number(value).toLocaleString(undefined, { maximumFractionDigits: 2 })}`;
    const percent = (value) => value == null ? "n/a" : `${value}%`;

    function apiHeaders(extra = {}) {
      const headers = {};
      const key = apiKeyInput.value.trim();
      if (key) headers["X-Clearpath-API-Key"] = key;
      return { ...headers, ...extra };
    }

    async function fetchJson(path) {
      const headers = apiHeaders();
      const response = await fetch(path, { headers });
      if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
      return response.json();
    }

    function analyticsQuery() {
      const params = new URLSearchParams({ limit: "100", sort: "created_at", direction: "desc" });
      const source = document.getElementById("sourceFilter").value.trim();
      const county = document.getElementById("countyFilter").value.trim();
      const stage = document.getElementById("stageFilter").value.trim();
      const motivation = document.getElementById("motivationFilter").value.trim();
      if (source) params.set("source", source);
      if (county) params.set("county", county);
      if (stage) params.set("lifecycle_stage", stage);
      if (motivation) params.set("motivation", motivation);
      return params.toString();
    }

    function renderKpis(summary, roi, funnel, stale) {
      const spend = roi.reduce((total, row) => total + (Number(row.estimated_spend_dollars) || 0), 0);
      const stages = Object.fromEntries(funnel.stages.map((stage) => [stage.stage, stage.count]));
      const kpis = [
        ["Total leads", summary.total_leads],
        ["Tracked spend", dollars(spend)],
        ["Appointments", stages.appointment || 0],
        ["Closed deals", stages.closed || 0],
        ["Stale leads", stale.length],
      ];
      document.getElementById("kpis").innerHTML = kpis.map(([label, value]) => `
        <div class="panel">
          <div class="kpi-label">${esc(label)}</div>
          <div class="kpi-value">${esc(value)}</div>
        </div>
      `).join("");
    }

    function renderFunnel(funnel) {
      document.getElementById("funnel").innerHTML = funnel.stages.map((stage) => `
        <div class="stage">
          <strong>${esc(stage.count)}</strong>
          <span>${esc(stage.stage.replace("_", " "))}</span>
          <div class="muted">${percent(stage.conversion_rate)}</div>
        </div>
      `).join("");
    }

    function renderSourceRoi(rows) {
      document.getElementById("sourceRoi").innerHTML = `
        <table>
          <thead><tr><th>Source</th><th>Leads</th><th>Spend</th><th>Appt</th><th>Contract</th><th>Closed</th><th>Close Rate</th><th>Cost/Close</th></tr></thead>
          <tbody>
            ${rows.map((row) => `
              <tr>
                <td><strong>${esc(row.source)}</strong><br><span class="muted">${esc(row.vendor_name || row.channel || "")}</span></td>
                <td>${esc(row.total_leads)}</td>
                <td class="money">${dollars(row.estimated_spend_dollars)}</td>
                <td>${esc(row.appointment_count)} <span class="muted">(${percent(row.appointment_rate)})</span></td>
                <td>${esc(row.contract_count)} <span class="muted">${dollars(row.cost_per_contract_dollars)}</span></td>
                <td>${esc(row.closed_count)}</td>
                <td>${percent(row.close_rate)}</td>
                <td class="money">${dollars(row.cost_per_close_dollars)}</td>
              </tr>
            `).join("")}
          </tbody>
        </table>`;
    }

    function renderStaleLeads(rows) {
      document.getElementById("staleLeads").innerHTML = rows.map((row) => `
        <div class="stale-card">
          <strong>${esc(row.lead_name)}</strong>
          <div><span class="pill ${esc(row.lifecycle_stage)}">${esc(row.lifecycle_stage)}</span> <span class="muted">${esc(row.stale_days)} days stale</span></div>
          <div class="muted">${esc(row.source || "unknown")} / ${esc(row.property_address || "no address")}</div>
        </div>
      `).join("") || '<span class="muted">No stale leads for the current window.</span>';
    }

    function renderLeads(page) {
      document.getElementById("leadsTable").innerHTML = `
        <table>
          <thead><tr><th>Lead</th><th>Source</th><th>Lifecycle</th><th>Motivation</th><th>Urgency</th><th>Market</th><th>Property</th></tr></thead>
          <tbody>
            ${page.leads.map((row) => `
              <tr>
                <td><strong>${esc(row.lead_name)}</strong><br><span class="muted">${esc(row.ghl_id)}</span></td>
                <td>${esc(row.source || "unknown")}<br><span class="muted">${esc(row.vendor_name || "")}</span></td>
                <td><span class="pill ${esc(row.lifecycle_stage)}">${esc(row.lifecycle_stage)}</span><br><span class="muted">${esc(row.status)}</span></td>
                <td>${esc(row.motivation || "n/a")}</td>
                <td>${esc(row.urgency || "n/a")}</td>
                <td>${esc(row.county || "unknown")}, ${esc(row.state || "")}</td>
                <td>${esc(row.property_address || "n/a")}</td>
              </tr>
            `).join("")}
          </tbody>
        </table>`;
    }

    function renderCountyPerformance(rows) {
      document.getElementById("countyPerformance").innerHTML = `
        <table>
          <thead><tr><th>County</th><th>Leads</th><th>Median</th><th>DOM</th></tr></thead>
          <tbody>
            ${rows.slice(0, 5).map((row) => `
              <tr>
                <td><strong>${esc(row.county)}</strong><br><span class="muted">${esc(row.state)}</span></td>
                <td>${esc(row.total_leads)}</td>
                <td>${row.median_price == null ? "n/a" : "$" + esc(row.median_price.toLocaleString())}</td>
                <td>${esc(row.avg_dom ?? "n/a")}</td>
              </tr>
            `).join("")}
          </tbody>
        </table>`;
    }

    async function refreshDashboard() {
      localStorage.setItem("clearpathApiKey", apiKeyInput.value.trim());
      statusNode.textContent = "Loading...";
      try {
        const query = analyticsQuery();
        const [summary, roi, funnel, stale, leads, counties] = await Promise.all([
          fetchJson("/api/intelligence/summary"),
          fetchJson("/api/analytics/source-roi"),
          fetchJson("/api/analytics/funnel"),
          fetchJson("/api/analytics/stale-leads?days=7"),
          fetchJson(`/api/analytics/leads?${query}`),
          fetchJson("/api/intelligence/county-performance"),
        ]);
        renderKpis(summary, roi, funnel, stale);
        renderFunnel(funnel);
        renderSourceRoi(roi);
        renderStaleLeads(stale);
        renderLeads(leads);
        renderCountyPerformance(counties);
        statusNode.textContent = `Updated ${new Date().toLocaleTimeString()} / showing ${leads.count} leads`;
      } catch (error) {
        statusNode.textContent = `Unable to load dashboard: ${error.message}`;
      }
    }

    async function importCsv() {
      localStorage.setItem("clearpathApiKey", apiKeyInput.value.trim());
      const file = document.getElementById("csvFile").files[0];
      if (!file) {
        importStatus.textContent = "Choose a CSV file first.";
        return;
      }

      const params = new URLSearchParams();
      const source = document.getElementById("csvSource").value.trim();
      const cost = document.getElementById("csvCost").value.trim();
      if (source) params.set("source", source);
      if (cost) params.set("cost_per_lead_dollars", cost);

      importStatus.textContent = "Importing CSV...";
      try {
        const body = await file.text();
        const response = await fetch(`/api/imports/leads/csv?${params.toString()}`, {
          method: "POST",
          headers: apiHeaders({ "Content-Type": "text/csv" }),
          body,
        });
        const result = await response.json();
        if (!response.ok) throw new Error(result.detail || `${response.status} ${response.statusText}`);
        importStatus.textContent = `Imported ${result.imported}/${result.rows_received} rows from CSV. Failed: ${result.failed}.`;
        await refreshDashboard();
      } catch (error) {
        importStatus.textContent = `CSV import failed: ${error.message}`;
      }
    }

    document.getElementById("refresh").addEventListener("click", refreshDashboard);
    document.getElementById("importCsv").addEventListener("click", importCsv);
    filterIds.forEach((id) => document.getElementById(id).addEventListener("change", refreshDashboard));
    filterIds.forEach((id) => document.getElementById(id).addEventListener("keydown", (event) => {
      if (event.key === "Enter") refreshDashboard();
    }));
    refreshDashboard();
  </script>
</body>
</html>
"""
