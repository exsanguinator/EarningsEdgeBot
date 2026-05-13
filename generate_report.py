#!/usr/bin/env python3
"""Generate docs/index.html — open positions with live quotes and PnL."""

import os
import re
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv

load_dotenv()

from bot.quotes import fetch_position_data
from bot.positions import load_positions, load_closed_positions

DOCS_DIR = os.path.join(os.path.dirname(__file__), "docs")
OUT_FILE = os.path.join(DOCS_DIR, "index.html")


def _parse_symbol(symbol: str) -> tuple[str, str]:
    """Returns (type, strike) parsed from an OCC symbol, e.g. ('Call', '$83.00')."""
    m = re.search(r"\d{6}([PC])(\d{8})$", symbol)
    if not m:
        return ("—", "—")
    opt_type = "Call" if m.group(1) == "C" else "Put"
    strike = int(m.group(2)) / 1000
    return (opt_type, f"${strike:.2f}")


def _pnl_class(val):
    if val is None:
        return ""
    return "pos" if val >= 0 else "neg"


def _fmt_pnl(val):
    if val is None:
        return "—"
    return f"${val:+.2f}"


def _render_closed(closed: list[dict]) -> str:
    if not closed:
        return ""
    rows = ""
    total = 0.0
    for c in sorted(closed, key=lambda x: x["closed_at"], reverse=True):
        close_date = c["closed_at"][:10]
        ticker = c["ticker"]
        pnl = c["total_pnl"]
        if pnl is not None:
            total += pnl
        rows += f"""
              <tr>
                <td>{close_date}</td>
                <td>{ticker}</td>
                <td class="{_pnl_class(pnl)}">{_fmt_pnl(pnl)}</td>
              </tr>"""
    total_html = f'<span class="{_pnl_class(total)}">{_fmt_pnl(total)}</span>'
    return f"""
        <section>
          <h2>Closed Position Summary</h2>
          <table>
            <thead>
              <tr><th>Close Date</th><th>Ticker</th><th>PnL</th></tr>
            </thead>
            <tbody>{rows}
            </tbody>
          </table>
          <p class="total">Total PnL: <strong>{total_html}</strong></p>
        </section>"""


def _render(positions_data: list[dict], closed: list[dict]) -> str:
    updated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    total_pnl = sum(d["net_pnl"] for d in positions_data if d["net_pnl"] is not None)
    total_pnl_html = f'<span class="{_pnl_class(total_pnl)}">{_fmt_pnl(total_pnl)}</span>'

    position_blocks = ""
    for data in positions_data:
        ticker = data["ticker"]
        expiration = data["expiration"]
        opened_at = data.get("opened_at", "")[:10]
        net_mid = data["net_mid"]
        net_pnl = data["net_pnl"]
        mleg_fill = data.get("mleg_fill")
        net_mid_label = "credit" if net_mid > 0 else "debit"

        rows = ""
        for leg in data["legs"]:
            opt_type, strike = _parse_symbol(leg["symbol"])
            if leg["error"]:
                rows += f"""
                <tr>
                  <td>{"Short" if leg["is_short"] else "Long"}</td>
                  <td>{opt_type}</td>
                  <td>{strike}</td>
                  <td colspan="5" class="neg">Error: {leg["error"]}</td>
                </tr>"""
                continue
            fill_cell = f"${leg['fill']:.2f}" if leg["fill"] is not None else "—"
            pnl_cell = f'<span class="{_pnl_class(leg["pnl"])}">{_fmt_pnl(leg["pnl"])}</span>'
            rows += f"""
                <tr>
                  <td>{"Short" if leg["is_short"] else "Long"}</td>
                  <td>{opt_type}</td>
                  <td>{strike}</td>
                  <td>{fill_cell}</td>
                  <td>${leg["bid"]:.2f}</td>
                  <td>${leg["ask"]:.2f}</td>
                  <td>${leg["mid"]:.2f}</td>
                  <td>{pnl_cell}</td>
                </tr>"""

        position_blocks += f"""
        <section>
          <h2>{ticker} <span class="sub">exp {expiration} &nbsp;·&nbsp; opened {opened_at}</span></h2>
          <table>
            <thead>
              <tr>
                <th>Side</th><th>Type</th><th>Strike</th><th>Fill</th>
                <th>Bid</th><th>Ask</th><th>Mid</th><th>PnL</th>
              </tr>
            </thead>
            <tbody>{rows}
            </tbody>
          </table>
          <p class="net">
            Fill: <strong>{"$" + f"{mleg_fill:.2f}" if mleg_fill is not None else "—"}</strong>
            &nbsp;&nbsp;
            Net mid: <strong>${net_mid:.2f}</strong> ({net_mid_label})
            &nbsp;&nbsp;
            Net PnL: <strong class="{_pnl_class(net_pnl)}">{_fmt_pnl(net_pnl)}</strong>
          </p>
        </section>"""

    no_positions = "" if positions_data else "<p class='empty'>No open positions.</p>"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>EarningsEdgeBot — Open Positions</title>
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ font-family: system-ui, sans-serif; background: #0f1117; color: #e2e8f0; padding: 2rem; }}
    h1 {{ font-size: 1.4rem; font-weight: 600; margin-bottom: 0.25rem; }}
    .updated {{ color: #64748b; font-size: 0.85rem; margin-bottom: 2rem; }}
    section {{ margin-bottom: 2.5rem; }}
    h2 {{ font-size: 1.1rem; font-weight: 600; margin-bottom: 0.75rem; }}
    h2 .sub {{ font-weight: 400; color: #94a3b8; font-size: 0.9rem; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 0.875rem; }}
    th {{ text-align: left; padding: 0.4rem 0.75rem; color: #94a3b8;
          border-bottom: 1px solid #1e293b; font-weight: 500; }}
    td {{ padding: 0.4rem 0.75rem; border-bottom: 1px solid #1a2234; }}
    tr:last-child td {{ border-bottom: none; }}
    .mono {{ font-family: monospace; font-size: 0.8rem; }}
    .net {{ margin-top: 0.75rem; color: #94a3b8; font-size: 0.875rem; }}
    .net strong {{ color: #e2e8f0; }}
    .pos {{ color: #4ade80; }}
    .neg {{ color: #f87171; }}
    .total {{ font-size: 1rem; margin-top: 1rem; padding-top: 1rem;
              border-top: 1px solid #1e293b; color: #94a3b8; }}
    .total strong {{ font-size: 1.1rem; }}
    .empty {{ color: #64748b; }}
  </style>
</head>
<body>
  <h1>EarningsEdgeBot — Open Positions</h1>
  <p class="updated">Updated {updated}</p>
  {no_positions}
  {position_blocks}
  {f'<p class="total">Total PnL: <strong>{total_pnl_html}</strong></p>' if positions_data else ''}
  {_render_closed(closed)}
</body>
</html>"""


def main():
    positions = load_positions()
    print(f"Fetching quotes for {len(positions)} position(s)...")

    positions_data = []
    for position in positions:
        print(f"  {position['ticker']}...", end=" ", flush=True)
        data = fetch_position_data(position)
        positions_data.append(data)
        print("OK" if not data["quotes_error"] else f"WARN: {data['quotes_error']}")

    closed = load_closed_positions()

    os.makedirs(DOCS_DIR, exist_ok=True)
    with open(OUT_FILE, "w") as f:
        f.write(_render(positions_data, closed))

    print(f"\nWrote {OUT_FILE}")


if __name__ == "__main__":
    main()
