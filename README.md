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

# ~9:45am EDT next morning — close all positions after market open
python close_trades.py
```

Both commands prompt `[y/N]` before submitting anything.

## Architecture

```
EarningsEdgeDetection stdout
        ↓
  bot/parser.py          regex-parses TIER 1 RECOMMENDED TRADES section
        ↓
  IronFlyTrade           dataclass: ticker, expiration, strikes, net credit
        ↓
  bot/alpaca_client.py   4 individual market orders per iron fly → Alpaca paper API
        ↓
  positions.json         persisted leg symbols for close_trades.py
```

**`bot/parser.py`** — Parses the `TIER 1 RECOMMENDED TRADES:` section only. Extracts expiration, strikes, and credit/debit via regex. Short put and call strikes can differ (e.g. CC's `$26.0P/$27.5C`).

**`bot/alpaca_client.py`** — Wraps the Alpaca paper trading REST API (`https://paper-api.alpaca.markets`). OCC symbol format: ticker left-padded to 6 chars + YYMMDD + P/C + 8-digit strike ×1000. Example: `ANET  260508P00172500`. Adjust `_occ_symbol()` if Alpaca rejects symbols.

**`bot/positions.py`** — Reads/writes `positions.json` at repo root. `save_positions` appends after each successful open; `clear_positions` is only called on full success in `close_trades.py` (partial failures leave the file intact for manual resolution).

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
- `positions.json` is gitignored. If it gets out of sync with actual positions, edit or delete it manually before re-running.
- Each iron fly is submitted as 4 separate market orders (sell short put, sell short call, buy long put, buy long call), not as a multi-leg combo order.
