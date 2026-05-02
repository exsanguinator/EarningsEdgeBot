#!/usr/bin/env python3
"""
Open iron fly positions for all Tier 1 trades in a scanner output file.

Usage:
    python open_trades.py <scan_output_file>

Run ~3:30pm EDT before market close and before earnings announcement.
"""
import sys
from dotenv import load_dotenv

load_dotenv()

from bot.parser import parse_scan_output
from bot.alpaca_client import submit_iron_fly
from bot.positions import save_positions


def main():
    if len(sys.argv) != 2:
        print("Usage: python open_trades.py <scan_output_file>")
        sys.exit(1)

    scan_file = sys.argv[1]
    with open(scan_file) as f:
        text = f.read()

    trades = parse_scan_output(text)
    if not trades:
        print("No Tier 1 trades found in scan output.")
        sys.exit(0)

    print(f"Found {len(trades)} Tier 1 trade(s):\n")

    for trade in trades:
        print(f"  {trade.ticker}: SHORT {trade.short_put}P/{trade.short_call}C | "
              f"LONG {trade.long_put}P/{trade.long_call}C | "
              f"Exp {trade.expiration} | Net credit ${trade.net_credit:.2f}")

    print()
    confirm = input("Submit all trades? [y/N] ").strip().lower()
    if confirm != "y":
        print("Aborted.")
        sys.exit(0)

    print()
    for trade in trades:
        print(f"Submitting {trade.ticker}...", end=" ", flush=True)
        try:
            orders = submit_iron_fly(trade)
            save_positions(trade.ticker, trade.expiration, orders)
            print(f"OK ({len(orders)} legs)")
        except Exception as e:
            print(f"FAILED: {e}")

    print("\nDone. Positions saved to positions.json.")


if __name__ == "__main__":
    main()
