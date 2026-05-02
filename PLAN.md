# EarningsEdgeBot MVP Plan

## Context

Build a minimal CLI trading bot that consumes stdout from EarningsEdgeDetection (run with `--iron-fly`) and executes iron fly options trades via Alpaca paper trading. Two manual commands: one to open trades (~3:30pm EDT before earnings), one to close all positions (~9:45am EDT next morning).

No modifications to EarningsEdgeDetection. The `--iron-fly` flag already outputs all needed strike data.

---

## Daily Workflow

**~3:30pm EDT — open trades:**
```bash
# In EarningsEdgeDetection repo
python run.py --iron-fly > /tmp/scan.txt

# In EarningsEdgeBot repo
python open_trades.py /tmp/scan.txt
```

**~9:45am EDT next morning — close trades:**
```bash
python close_trades.py
```

---

## Project Structure

```
EarningsEdgeBot/
├── open_trades.py        # CLI: parse scan output, confirm, submit iron fly orders
├── close_trades.py       # CLI: confirm, close all open legs
├── positions.json        # Written by open_trades.py, cleared by close_trades.py (gitignored)
├── bot/
│   ├── parser.py         # Parse --iron-fly stdout → IronFlyTrade dataclasses
│   ├── alpaca_client.py  # Alpaca paper trading HTTP client
│   └── positions.py      # Read/write positions.json
├── .env                  # ALPACA_API_KEY, ALPACA_SECRET_KEY (gitignored)
├── .env.example          # Template for credentials
├── requirements.txt      # requests, python-dotenv
└── PLAN.md               # This file
```

---

## Components

### Input: EarningsEdgeDetection scanner output

The scanner is run separately with `--iron-fly`. Its stdout is redirected to a file and passed to `open_trades.py`. Only **Tier 1** trades are executed.

Relevant section of scanner output:
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

Note: short put and call strikes can differ (e.g. CC has `$26.0P/$27.5C`).

### bot/parser.py

Regex-parses the Tier 1 section. Extracts per ticker:
- `expiration` (YYYY-MM-DD)
- `short_put`, `short_call` strikes
- `long_put`, `long_call` strikes
- `net_credit` = credit − debit

Returns a list of `IronFlyTrade` dataclasses.

### bot/alpaca_client.py

Alpaca paper trading base URL: `https://paper-api.alpaca.markets`

Credentials loaded from `.env` via `python-dotenv`:
- `ALPACA_API_KEY`
- `ALPACA_SECRET_KEY`

Each iron fly = 4 separate market orders (1 contract each):

| # | Side | Leg |
|---|------|-----|
| 1 | SELL | short put  — `{TICKER}{YYMMDD}P{strike}` |
| 2 | SELL | short call — `{TICKER}{YYMMDD}C{strike}` |
| 3 | BUY  | long put   — `{TICKER}{YYMMDD}P{strike}` |
| 4 | BUY  | long call  — `{TICKER}{YYMMDD}C{strike}` |

OCC symbol format: ticker left-padded to 6 chars + YYMMDD + P/C + 8-digit strike (×1000).
Example: `ANET  260508P00172500`

### bot/positions.py

Persists opened trades to `positions.json`:
```json
[
  {
    "ticker": "ANET",
    "expiration": "2026-05-08",
    "legs": ["ANET  260508P00172500", "ANET  260508C00172500", "..."],
    "opened_at": "2026-05-05T19:30:00+00:00"
  }
]
```

### open_trades.py

1. Read scan file passed as CLI arg
2. Parse Tier 1 trades
3. Print summary of all trades to be submitted
4. Ask for `[y/N]` confirmation
5. For each trade: submit 4 legs via Alpaca, save to `positions.json`
6. Report success/failure per ticker

### close_trades.py

1. Read `positions.json`
2. Print summary of positions to close
3. Ask for `[y/N]` confirmation
4. Call `DELETE /v2/positions/{symbol}` for each leg
5. On full success: clear `positions.json`
6. On any failure: leave `positions.json` intact and report which legs failed

---

## Setup

```bash
cp .env.example .env
# fill in ALPACA_API_KEY and ALPACA_SECRET_KEY from paper.alpaca.markets

pip install -r requirements.txt
```

---

## Verification

1. Run EarningsEdgeDetection with `--iron-fly` for a date with known Tier 1 trades, save to file
2. Run `python open_trades.py <file>` — confirm trades look correct before entering `y`
3. Check Alpaca paper portfolio — verify 4 option legs per ticker appear
4. Run `python close_trades.py` — verify positions are closed in Alpaca and `positions.json` is cleared

> **OCC symbol format caveat**: Alpaca paper trading may have minor variations in how it expects option symbols (spacing, padding). Verify the first real submission against the Alpaca paper UI and adjust `_occ_symbol()` in `bot/alpaca_client.py` if needed.

---

## Future: Calendar Spread Bot (not in this MVP)

Sell near-expiry ATM put or call, buy same strike 30 days out. Likely a separate script (`open_calendars.py`) reusing the same `alpaca_client.py` and `positions.py` infrastructure.
