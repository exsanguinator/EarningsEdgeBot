# EarningsEdgeBot

A minimal CLI trading bot that executes iron fly options trades via Alpaca paper trading. Consumes scanner output from [EarningsEdgeDetection](https://github.com/exsanguinator/EarningsEdgeDetection) (run with `--iron-fly`) and exposes two manual commands: one to open trades before earnings, one to close all positions the next morning.

## Setup

```bash
cp .env.example .env
# fill in ALPACA_API_KEY and ALPACA_SECRET_KEY from paper.alpaca.markets
pip install -r requirements.txt
```

## Daily workflow

```bash
# ~3:30pm EDT — run scanner in EarningsEdgeDetection repo, pipe output here
python run.py --iron-fly > /tmp/scan.txt   # in EarningsEdgeDetection repo
python open_trades.py /tmp/scan.txt        # in this repo

# anytime — publish positions report to GitHub Pages
./publish_report.sh

# ~9:45am EDT next morning — close all positions after market open
python close_trades.py
python close_trades.py positions-260511.json   # optional: specify a different positions file
```

Both `open_trades.py` and `close_trades.py` prompt `[y/N]` before submitting anything.

## Architecture

```
EarningsEdgeDetection stdout
        ↓
  bot/parser.py          regex-parses TIER 1 RECOMMENDED TRADES section
        ↓
  IronFlyTrade           dataclass: ticker, expiration, strikes, net credit
        ↓
  bot/order_manager.py   single mleg limit order; reprices every 10s until filled
        ↓
  bot/alpaca_client.py   REST calls to Alpaca paper API
        ↓
  positions.json         persisted leg symbols + order ID for close_trades.py
```

**`bot/parser.py`** — Parses the `TIER 1 RECOMMENDED TRADES:` section only. Extracts expiration, strikes, and credit/debit via regex. Short put and call strikes can differ (e.g. CC's `$26.0P/$27.5C`).

**`bot/alpaca_client.py`** — Wraps the Alpaca paper trading REST API (`https://paper-api.alpaca.markets`). OCC symbol format: ticker + YYMMDD + P/C + 8-digit strike ×1000. Example: `ANET260508P00172500`. Also fetches live option snapshots from `data.alpaca.markets` for mid pricing.

**`bot/order_manager.py`** — Submits iron flies as a single mleg limit order at the current mid credit. Reprices by $0.05 every 10 seconds until filled or credit reaches $0. When closing, long wings with a 0 bid are skipped and left to expire worthless.

**`bot/positions.py`** — Reads/writes `positions.json` at repo root. `save_positions` appends after each successful open; `clear_positions` is only called on full success in `close_trades.py` (partial failures leave the file intact for manual resolution). Closed positions are appended to `closed_positions.json` with fills, PnL, and leg details.

**`bot/quotes.py`** — Fetches live bid/ask/mid quotes and opening fill prices for all legs of a position. Computes per-leg and net PnL. Credits are positive, debits are negative.

**`generate_report.py`** — Writes `docs/index.html` with a live dashboard: open positions (quotes, fills, per-leg and net PnL) and a Closed Position Summary table with total PnL. Published via `publish_report.sh`.

## Positions report (GitHub Pages)

`publish_report.sh` generates a live HTML dashboard and pushes it to GitHub Pages:

```bash
./publish_report.sh
```

To enable: go to repo **Settings → Pages**, set source to `main` branch, `/docs` folder. The report will be available at:

```
https://<your-github-username>.github.io/<repo-name>/
```

## Scanner output format

The bot expects the output format produced by `EarningsEdgeDetection --iron-fly`. Only `TIER 1 RECOMMENDED TRADES` entries are executed; Tier 2 and lower are ignored. Example input:

```
TIER 1 RECOMMENDED TRADES:

  ANET:
    Price: $172.70
    ...
    IRON FLY STRATEGY:
      Expiration: 2026-05-08
      SHORT: $172.5P/$172.5C for $17.1 credit
      LONG:  $121.0P/$225.0C for $0.4 debit
      Break-evens: 155.8-189.2, Risk/Reward: 1:2.1
```

## Notes

- **Paper trading only** — uses `paper-api.alpaca.markets`. Switch `BASE_URL` in `bot/alpaca_client.py` to go live.
- `positions.json` is gitignored. If it gets out of sync with actual positions, edit or delete it manually before re-running. An alternate file can be passed to `close_trades.py` as a positional argument.
- `closed_positions.json` is gitignored. It accumulates a record of every closed trade and is read by `generate_report.py` for the dashboard summary.
- Each iron fly is submitted as a single multi-leg (mleg) limit order. If it can't fill, it reprices toward zero credit and raises if credit would go negative.
- Long wings that expire worthless (0 bid) are excluded from the close order automatically.
