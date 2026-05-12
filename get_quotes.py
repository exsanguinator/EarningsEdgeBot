#!/usr/bin/env python3
"""Print midpoint quotes and PnL for all open positions."""

import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv

load_dotenv()

from bot.quotes import fetch_position_data
from bot.positions import load_positions


def main():
    positions = load_positions()
    if not positions:
        print("No open positions found in positions.json.")
        return

    total_pnl = 0.0
    for position in load_positions():
        data = fetch_position_data(position)
        ticker, expiration = data["ticker"], data["expiration"]
        print(f"{ticker} (exp {expiration}):")

        if data["quotes_error"]:
            print(f"  Warning: could not fetch fill prices: {data['quotes_error']}")

        for leg in data["legs"]:
            if leg["error"]:
                print(f"  {'- ' if leg['is_short'] else '+ '}{leg['symbol']}  ERROR: {leg['error']}")
                continue
            sign = "-" if leg["is_short"] else "+"
            fill_str = f"fill={leg['fill']:.2f}  " if leg["fill"] is not None else ""
            pnl_str = f"  pnl={leg['pnl']:+.2f}" if leg["pnl"] is not None else ""
            print(f"  {sign} {leg['symbol']}  {fill_str}bid={leg['bid']:.2f} ask={leg['ask']:.2f} mid={leg['mid']:.2f}{pnl_str}")

        net_mid = data["net_mid"]
        print(f"  net mid: ${net_mid:.2f}  ({'debit' if net_mid > 0 else 'credit'})", end="")
        if data["net_pnl"] is not None:
            print(f"   net PnL: ${data['net_pnl']:+.2f}", end="")
            total_pnl += data["net_pnl"]
        print()
        print()

    if len(positions) > 1:
        print(f"Total PnL: ${total_pnl:+.2f}")


if __name__ == "__main__":
    main()
