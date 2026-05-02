#!/usr/bin/env python3
"""
Close all iron fly positions opened by open_trades.py.

Usage:
    python close_trades.py

Run ~9:45am EDT the morning after earnings, after market has opened.
"""
from dotenv import load_dotenv

load_dotenv()

from bot.alpaca_client import close_position
from bot.positions import load_positions, clear_positions


def main():
    positions = load_positions()
    if not positions:
        print("No open positions found in positions.json.")
        return

    total_legs = sum(len(p["legs"]) for p in positions)
    print(f"Found {len(positions)} trade(s), {total_legs} leg(s) to close:\n")
    for p in positions:
        print(f"  {p['ticker']} exp {p['expiration']} — {len(p['legs'])} legs")

    print()
    confirm = input("Close all positions? [y/N] ").strip().lower()
    if confirm != "y":
        print("Aborted.")
        return

    print()
    failed = []
    for position in positions:
        for symbol in position["legs"]:
            print(f"  Closing {symbol}...", end=" ", flush=True)
            try:
                close_position(symbol)
                print("OK")
            except Exception as e:
                print(f"FAILED: {e}")
                failed.append(symbol)

    if failed:
        print(f"\nWarning: {len(failed)} leg(s) failed to close: {failed}")
        print("positions.json NOT cleared — resolve manually and re-run.")
    else:
        clear_positions()
        print("\nAll positions closed. positions.json cleared.")


if __name__ == "__main__":
    main()
