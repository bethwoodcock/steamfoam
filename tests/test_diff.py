from diff import compute_diff

EXISTING = {
    "Half-Life 2": {"price_gbp": 1.99, "url": "https://www.loaded.com/hl2", "first_seen": "2026-01-01"},
    "Portal": {"price_gbp": 3.99, "url": "https://www.loaded.com/portal", "first_seen": "2026-01-01"},
}

CURRENT = [
    {"title": "Half-Life 2", "price_gbp": 1.99, "url": "https://www.loaded.com/hl2"},   # unchanged
    {"title": "Portal", "price_gbp": 2.49, "url": "https://www.loaded.com/portal"},     # price drop
    {"title": "Team Fortress 2", "price_gbp": 0.99, "url": "https://www.loaded.com/tf2"}, # new
]


def test_new_game_gets_NEW_status():
    games, _ = compute_diff(CURRENT, EXISTING)
    tf2 = next(g for g in games if g["title"] == "Team Fortress 2")
    assert tf2["status"] == "NEW"


def test_new_game_in_history():
    _, history = compute_diff(CURRENT, EXISTING)
    events = [e for e in history if e["title"] == "Team Fortress 2"]
    assert len(events) == 1
    assert events[0]["event"] == "new"
    assert events[0]["new_price"] == 0.99


def test_price_drop_status():
    games, _ = compute_diff(CURRENT, EXISTING)
    portal = next(g for g in games if g["title"] == "Portal")
    assert portal["status"] == "PRICE_DOWN"


def test_price_drop_in_history():
    _, history = compute_diff(CURRENT, EXISTING)
    events = [e for e in history if e["title"] == "Portal"]
    assert len(events) == 1
    assert events[0]["event"] == "price_down"
    assert events[0]["old_price"] == 3.99
    assert events[0]["new_price"] == 2.49


def test_unchanged_no_history():
    _, history = compute_diff(CURRENT, EXISTING)
    events = [e for e in history if e["title"] == "Half-Life 2"]
    assert len(events) == 0


def test_unchanged_empty_status():
    games, _ = compute_diff(CURRENT, EXISTING)
    hl2 = next(g for g in games if g["title"] == "Half-Life 2")
    assert hl2["status"] == ""


def test_first_seen_preserved():
    games, _ = compute_diff(CURRENT, EXISTING)
    hl2 = next(g for g in games if g["title"] == "Half-Life 2")
    assert hl2["first_seen"] == "2026-01-01"


def test_sort_order():
    games, _ = compute_diff(CURRENT, EXISTING)
    statuses = [g["status"] for g in games]
    assert statuses.index("NEW") < statuses.index("PRICE_DOWN")
    assert statuses.index("PRICE_DOWN") < statuses.index("")
