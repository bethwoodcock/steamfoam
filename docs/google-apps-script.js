// SteamFoam — Google Apps Script Web App
// Paste this into Extensions > Apps Script in your Google Sheet
// Then: Deploy > New deployment > Web app > Anyone > Deploy

function doGet() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const ws = ss.getSheetByName("Games");
  const rows = ws.getDataRange().getValues();
  const headers = rows[0];
  const games = rows.slice(1).map(row => {
    const obj = {};
    headers.forEach((h, i) => obj[h] = row[i]);
    return obj;
  });
  const html = HtmlService.createHtmlOutput(buildPage(games))
    .setTitle("SteamFoam")
    .setXFrameOptionsMode(HtmlService.XFrameOptionsMode.ALLOWALL);
  return html;
}

function buildPage(games) {
  const rows = games.map(g => `
    <tr class="row" data-status="${g.status || ''}" onclick="window.open('${g.url}','_blank')">
      <td>${g.title}</td>
      <td>£${parseFloat(g.price_gbp).toFixed(2)}</td>
      <td><span class="badge ${badgeClass(g.status)}">${g.status || '—'}</span></td>
      <td>${g.price_change || '—'}</td>
      <td>${g.first_seen || ''}</td>
    </tr>`).join('');

  return `<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>SteamFoam</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #0f0f1a; color: #e0e0e0; min-height: 100vh; }
  header { background: #1a1a2e; padding: 20px 32px; border-bottom: 1px solid #2a2a3e; display: flex; align-items: center; gap: 16px; }
  header h1 { font-size: 1.4rem; font-weight: 700; color: #fff; }
  header span { font-size: 0.85rem; color: #888; }
  .controls { padding: 20px 32px; display: flex; flex-wrap: wrap; gap: 12px; align-items: center; background: #13131f; border-bottom: 1px solid #2a2a3e; }
  input[type=search] { flex: 1; min-width: 200px; padding: 8px 14px; border-radius: 8px; border: 1px solid #2a2a3e; background: #1a1a2e; color: #e0e0e0; font-size: 0.9rem; outline: none; }
  input[type=search]:focus { border-color: #5c6bc0; }
  .filters { display: flex; gap: 8px; flex-wrap: wrap; }
  button { padding: 7px 16px; border-radius: 8px; border: 1px solid #2a2a3e; background: #1a1a2e; color: #aaa; font-size: 0.85rem; cursor: pointer; transition: all 0.15s; }
  button:hover { border-color: #5c6bc0; color: #fff; }
  button.active { background: #5c6bc0; border-color: #5c6bc0; color: #fff; }
  .count { font-size: 0.85rem; color: #666; margin-left: auto; }
  .table-wrap { overflow-x: auto; padding: 0 32px 32px; }
  table { width: 100%; border-collapse: collapse; margin-top: 16px; font-size: 0.9rem; }
  th { text-align: left; padding: 10px 14px; color: #666; font-weight: 600; font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.05em; border-bottom: 1px solid #2a2a3e; }
  td { padding: 10px 14px; border-bottom: 1px solid #1e1e30; }
  tr.row { cursor: pointer; transition: background 0.1s; }
  tr.row:hover td { background: #1a1a2e; }
  .badge { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 0.75rem; font-weight: 600; }
  .badge-new { background: #1b3a2e; color: #4caf82; }
  .badge-down { background: #1a2e3a; color: #4ca8cf; }
  .badge-up { background: #3a2a1a; color: #cf8c4c; }
  .badge-none { background: transparent; color: #555; }
  tr.hidden { display: none; }
  @media (max-width: 600px) { .controls, .table-wrap { padding-left: 16px; padding-right: 16px; } }
</style>
</head>
<body>
<header>
  <h1>☕ SteamFoam</h1>
  <span>Steam games under £3 · tracked weekly</span>
</header>
<div class="controls">
  <input type="search" id="search" placeholder="Search games…" oninput="filter()">
  <div class="filters">
    <button class="active" onclick="setFilter('all', this)">All</button>
    <button onclick="setFilter('NEW', this)">New</button>
    <button onclick="setFilter('PRICE_DOWN', this)">Price Drop</button>
    <button onclick="setFilter('PRICE_UP', this)">Price Up</button>
  </div>
  <span class="count" id="count"></span>
</div>
<div class="table-wrap">
  <table>
    <thead><tr>
      <th>Game</th><th>Price</th><th>Status</th><th>Change</th><th>First Seen</th>
    </tr></thead>
    <tbody id="tbody">${rows}</tbody>
  </table>
</div>
<script>
  let activeFilter = 'all';
  function setFilter(f, btn) {
    activeFilter = f;
    document.querySelectorAll('button').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    filter();
  }
  function filter() {
    const q = document.getElementById('search').value.toLowerCase();
    const tbody = document.getElementById('tbody');
    let visible = 0;
    tbody.querySelectorAll('tr').forEach(row => {
      const status = row.dataset.status;
      const matchFilter = activeFilter === 'all' || status === activeFilter;
      const matchSearch = !q || row.textContent.toLowerCase().includes(q);
      const show = matchFilter && matchSearch;
      row.classList.toggle('hidden', !show);
      if (show) visible++;
    });
    document.getElementById('count').textContent = visible + ' games';
  }
  filter();
</script>
</body>
</html>`;
}

function badgeClass(status) {
  if (status === 'NEW') return 'badge-new';
  if (status === 'PRICE_DOWN') return 'badge-down';
  if (status === 'PRICE_UP') return 'badge-up';
  return 'badge-none';
}
