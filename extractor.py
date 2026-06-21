import re
from bs4 import BeautifulSoup

CARD_SEL = "li.list-product-item"
TITLE_SEL = "a.product-item-link"
PRICE_SEL = "span.price"


def extract_games_from_page(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    games = []
    seen_urls = set()

    for card in soup.select(CARD_SEL):
        link = card.select_one(TITLE_SEL)
        if not link:
            continue

        href = link.get("href", "")
        if not href or href in seen_urls:
            continue
        seen_urls.add(href)

        title = link.get_text(strip=True)
        price = _extract_price(card)
        if not title or price is None:
            continue

        url = href if href.startswith("http") else "https://www.loaded.com" + href
        label = card.select_one("span.item-label")
        in_stock = not (label and label.get_text(strip=True).lower() == "sold out")
        games.append({"title": title, "price_gbp": price, "url": url, "in_stock": in_stock})

    return games


def _extract_price(card) -> float | None:
    el = card.select_one(PRICE_SEL)
    if el:
        result = _parse_price(el.get_text())
        if result is not None:
            return result
    # Fallback: scan all card text for £X.XX
    match = re.search(r'£(\d+\.\d{2})', card.get_text())
    if match:
        return float(match.group(1))
    return None


def _parse_price(text: str) -> float | None:
    match = re.search(r'(\d+\.\d{2})', text)
    return float(match.group(1)) if match else None
