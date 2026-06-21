from datetime import datetime


def compute_diff(
    current_games: list[dict],
    existing_games: dict[str, dict],
) -> tuple[list[dict], list[dict]]:
    today = datetime.today().strftime("%Y-%m-%d")
    games_to_write = []
    history_events = []

    for game in current_games:
        title = game["title"]
        new_price = game["price_gbp"]
        url = game["url"]
        in_stock = game.get("in_stock", True)

        if title not in existing_games:
            games_to_write.append({
                "title": title,
                "price_gbp": new_price,
                "url": url,
                "status": "NEW",
                "price_change": "",
                "first_seen": today,
                "last_seen": today,
                "in_stock": in_stock,
            })
            history_events.append({
                "timestamp": today,
                "title": title,
                "event": "new",
                "old_price": "",
                "new_price": new_price,
                "url": url,
            })
        else:
            existing = existing_games[title]
            old_price = float(existing.get("price_gbp", 0) or 0)
            delta = round(new_price - old_price, 2)

            if delta != 0:
                status = "PRICE_DOWN" if delta < 0 else "PRICE_UP"
                price_change = f"{'+' if delta > 0 else ''}{delta:.2f}"
                history_events.append({
                    "timestamp": today,
                    "title": title,
                    "event": status.lower(),
                    "old_price": old_price,
                    "new_price": new_price,
                    "url": url,
                })
            else:
                status = ""
                price_change = ""

            games_to_write.append({
                "title": title,
                "price_gbp": new_price,
                "url": url,
                "status": status,
                "price_change": price_change,
                "first_seen": existing.get("first_seen", today),
                "last_seen": today,
                "in_stock": in_stock,
            })

    status_order = {"NEW": 0, "PRICE_DOWN": 1, "PRICE_UP": 2, "": 3}
    games_to_write.sort(key=lambda g: (status_order.get(g["status"], 3), g["title"].lower()))

    return games_to_write, history_events
