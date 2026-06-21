from flask import Flask, render_template_string
from sheets import get_client, read_existing_games

app = Flask(__name__)

PAGE = """<!DOCTYPE html>
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
  th { text-align: left; padding: 10px 14px; color: #666; font-weight: 600; font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.05em; border-bottom: 1px solid #2a2a3e; cursor: pointer; user-select: none; }
  th:hover { color: #aaa; }
  td { padding: 10px 14px; border-bottom: 1px solid #1e1e30; }
  tr.row { cursor: pointer; transition: background 0.1s; }
  tr.row:hover td { background: #1a1a2e; }
  .badge { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 0.75rem; font-weight: 600; }
  .badge-new { background: #1b3a2e; color: #4caf82; }
  .badge-down { background: #1a2e3a; color: #4ca8cf; }
  .badge-up { background: #3a2a1a; color: #cf8c4c; }
  .badge-none { color: #555; }
  tr.hidden { display: none; }
  @media (max-width: 600px) { .controls, .table-wrap { padding-left: 16px; padding-right: 16px; } }
</style>
</head>
<body>
<header>
  <h1>☕ SteamFoam</h1>
  <span>Steam games under £3 · {{ total }} games tracked</span>
</header>
<div class="controls">
  <input type="search" id="search" placeholder="Search games…" oninput="filter()">
  <div class="filters">
    <button class="active" onclick="setFilter('all', this)">All</button>
    <button onclick="setFilter('NEW', this)">🟢 New</button>
    <button onclick="setFilter('PRICE_DOWN', this)">🔵 Price Drop</button>
    <button onclick="setFilter('PRICE_UP', this)">🟠 Price Up</button>
  </div>
  <span class="count" id="count"></span>
  <button id="dlcBtn" onclick="toggleDlc(this)">DLC: Hidden</button>
  <button id="stockBtn" onclick="toggleStock(this)">Out of Stock: Hidden</button>
</div>
<div class="table-wrap">
  <table id="tbl">
    <thead><tr>
      <th onclick="sortBy('title')">Game ↕</th>
      <th onclick="sortBy('price')">Price ↕</th>
      <th>Status</th>
      <th>Change</th>
      <th onclick="sortBy('first_seen')">First Seen ↕</th>
    </tr></thead>
    <tbody id="tbody">
    {% for g in games %}
    <tr class="row" data-status="{{ g.status }}" data-title="{{ g.title|lower }}" data-price="{{ g.price_gbp }}" data-first="{{ g.first_seen }}" data-instock="{{ 'true' if g.in_stock else 'false' }}" onclick="window.open('{{ g.url }}','_blank')">
      <td>{{ g.title }}</td>
      <td>£{{ "%.2f"|format(g.price_gbp|float) }}</td>
      <td>
        {% if g.status == 'NEW' %}<span class="badge badge-new">NEW</span>
        {% elif g.status == 'PRICE_DOWN' %}<span class="badge badge-down">PRICE DROP</span>
        {% elif g.status == 'PRICE_UP' %}<span class="badge badge-up">PRICE UP</span>
        {% else %}<span class="badge-none">—</span>{% endif %}
      </td>
      <td>{{ g.price_change or '—' }}</td>
      <td>{{ g.first_seen or '' }}</td>
    </tr>
    {% endfor %}
    </tbody>
  </table>
</div>
<script>
  let activeFilter = 'all';
  let sortCol = null, sortAsc = true;
  let showDlc = false;
  let showOutOfStock = false;

  function setFilter(f, btn) {
    activeFilter = f;
    document.querySelectorAll('.filters button').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    filter();
  }

  function toggleDlc(btn) {
    showDlc = !showDlc;
    btn.textContent = showDlc ? 'DLC: Shown' : 'DLC: Hidden';
    btn.classList.toggle('active', showDlc);
    filter();
  }

  function toggleStock(btn) {
    showOutOfStock = !showOutOfStock;
    btn.textContent = showOutOfStock ? 'Out of Stock: Shown' : 'Out of Stock: Hidden';
    btn.classList.toggle('active', showOutOfStock);
    filter();
  }

  function filter() {
    const q = document.getElementById('search').value.toLowerCase();
    let visible = 0;
    document.querySelectorAll('#tbody tr').forEach(row => {
      const status = row.dataset.status;
      const title = row.dataset.title;
      const inStock = row.dataset.instock === 'true';
      const isDlc = title.includes('dlc');
      const matchFilter = activeFilter === 'all' || status === activeFilter;
      const matchSearch = !q || row.textContent.toLowerCase().includes(q);
      const matchDlc = showDlc || !isDlc;
      const matchStock = showOutOfStock || inStock;
      const show = matchFilter && matchSearch && matchDlc && matchStock;
      row.classList.toggle('hidden', !show);
      if (show) visible++;
    });
    document.getElementById('count').textContent = visible.toLocaleString() + ' games';
  }

  function sortBy(col) {
    const tbody = document.getElementById('tbody');
    const rows = Array.from(tbody.querySelectorAll('tr'));
    if (sortCol === col) sortAsc = !sortAsc; else { sortCol = col; sortAsc = true; }
    rows.sort((a, b) => {
      let av = a.dataset[col === 'price' ? 'price' : col === 'first_seen' ? 'first' : 'title'];
      let bv = b.dataset[col === 'price' ? 'price' : col === 'first_seen' ? 'first' : 'title'];
      if (col === 'price') { av = parseFloat(av); bv = parseFloat(bv); }
      return sortAsc ? (av > bv ? 1 : -1) : (av < bv ? 1 : -1);
    });
    rows.forEach(r => tbody.appendChild(r));
  }

  filter();
</script>
</body>
</html>"""

@app.route("/")
def index():
    client = get_client()
    games_dict = read_existing_games(client)
    games = sorted(games_dict.values(), key=lambda g: (
        {"NEW": 0, "PRICE_DOWN": 1, "PRICE_UP": 2, "": 3}.get(g.get("status", ""), 3),
        g.get("title", "").lower()
    ))
    return render_template_string(PAGE, games=games, total=len(games))

if __name__ == "__main__":
    app.run(debug=False)
