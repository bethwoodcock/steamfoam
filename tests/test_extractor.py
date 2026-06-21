import pytest
from extractor import extract_games_from_page, _parse_price

FIXTURE_HTML = """
<html><body>
  <ul>
    <li class="list-product-item">
      <a class="product-item-link" href="https://www.loaded.com/half-life-2-steam-pc">Half-Life 2</a>
      <span class="price">£1.99</span>
    </li>
    <li class="list-product-item">
      <a class="product-item-link" href="https://www.loaded.com/portal-steam-pc">Portal</a>
      <span class="price">£3.49</span>
    </li>
  </ul>
  <!-- Nav link — NOT a product-item-link, should be excluded -->
  <a href="https://www.loaded.com/pc/steam">All Steam Games</a>
</body></html>
"""

def test_extract_returns_two_games():
    games = extract_games_from_page(FIXTURE_HTML)
    assert len(games) == 2

def test_extract_title():
    games = extract_games_from_page(FIXTURE_HTML)
    assert games[0]["title"] == "Half-Life 2"

def test_extract_price():
    games = extract_games_from_page(FIXTURE_HTML)
    assert games[0]["price_gbp"] == 1.99

def test_extract_url_is_absolute():
    games = extract_games_from_page(FIXTURE_HTML)
    assert games[0]["url"].startswith("https://www.loaded.com")

def test_nav_link_excluded():
    games = extract_games_from_page(FIXTURE_HTML)
    titles = [g["title"] for g in games]
    assert "All Steam Games" not in titles

def test_parse_price_pound_sign():
    assert _parse_price("£1.99") == 1.99

def test_parse_price_plain():
    assert _parse_price("1.99") == 1.99

def test_parse_price_missing():
    assert _parse_price("Free") is None
