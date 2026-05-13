#!/usr/bin/env python3
"""
Close all iron fly positions opened by open_trades.py.

Usage:
    python close_trades.py

Run ~9:45am EDT the morning after earnings, after market has opened.
"""
from dotenv import load_dotenv

load_dotenv()

from bot.alpaca_client import get_order
from bot.order_manager import close_iron_fly
from bot.positions import load_positions, clear_positions, append_closed_position


def main():
    positions = load_positions()
    if not positions:
        print("No open positions found in positions.json.")
        return

    print(f"Found {len(positions)} trade(s) to close:\n")
    for p in positions:
        print(f"  {p['ticker']} exp {p['expiration']}")

    print()
    confirm = input("Close all positions? [y/N] ").strip().lower()
    if confirm != "y":
        print("Aborted.")
        return

    print()
    failed = []
    for position in positions:
        print(f"Closing {position['ticker']}...")
        try:
            close_order = close_iron_fly(position)
            open_order = get_order(position["order_id"])
            append_closed_position(position, open_order, close_order)
            print(f"  {position['ticker']} OK")
        except Exception as e:
            print(f"  {position['ticker']} FAILED: {e}")
            failed.append(position["ticker"])

    if failed:
        print(f"\nWarning: {len(failed)} trade(s) failed to close: {failed}")
        print("positions.json NOT cleared — resolve manually and re-run.")
    else:
        clear_positions()
        print("\nAll positions closed. positions.json cleared.")


if __name__ == "__main__":
    main()
