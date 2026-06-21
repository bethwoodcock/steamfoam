import asyncio
from crawler import fetch_all_games
from sheets import get_client, read_existing_games, write_games, append_history, prune_history
from diff import compute_diff


async def main():
    print("=== SteamFoam — starting crawl ===\n")

    print("Step 1: Crawling loaded.com...")
    current_games = await fetch_all_games()
    if not current_games:
        print("ERROR: No games returned. Check selectors in extractor.py.")
        return

    print("\nStep 2: Reading existing Games sheet...")
    client = get_client()
    existing_games = read_existing_games(client)
    print(f"  Found {len(existing_games)} existing games in sheet.")

    print("\nStep 3: Computing diff...")
    games_to_write, history_events = compute_diff(current_games, existing_games)
    new_count = sum(1 for g in games_to_write if g["status"] == "NEW")
    changed_count = sum(1 for g in games_to_write if g["status"] in ("PRICE_DOWN", "PRICE_UP"))
    print(f"  {new_count} new, {changed_count} price changes, {len(games_to_write)} total.")

    print("\nStep 4: Writing to Google Sheets...")
    write_games(client, games_to_write)
    append_history(client, history_events)
    prune_history(client)

    print("\n=== SteamFoam done ===")
    print(f"  {new_count} new | {changed_count} price changes | {len(games_to_write)} total tracked")


if __name__ == "__main__":
    asyncio.run(main())
