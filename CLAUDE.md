# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A minimal CLI trading bot that executes iron fly options trades via Alpaca paper trading. It consumes output from a separate `EarningsEdgeDetection` scanner (run with `--iron-fly`) and exposes two manual commands: one to open trades (~3:30pm EDT before earnings), one to close all positions (~9:45am EDT next morning).

## Setup

```bash
cp .env.example .env
# fill in ALPACA_API_KEY and ALPACA_SECRET_KEY from paper.alpaca.markets
pip install -r requirements.txt
```

## Daily workflow

```bash
# ~3:30pm EDT — open trades
python run.py --iron-fly > /tmp/scan.txt   # run in EarningsEdgeDetection repo
python open_trades.py /tmp/scan.txt        # run here

# ~9:45am EDT next day — close trades
python close_trades.py
```

## Architecture

**Data flow:** EarningsEdgeDetection stdout → `bot/parser.py` → `IronFlyTrade` dataclasses → `bot/alpaca_client.py` → Alpaca paper API. Opened positions are persisted to `positions.json` (gitignored) so `close_trades.py` knows what to close.

**`bot/parser.py`** — Regex-parses the `TIER 1 RECOMMENDED TRADES:` section only. Splits on ticker blocks, extracts expiration/strikes/credit via regex. Short put and call strikes can differ (e.g. CC's `$26.0P/$27.5C`).

**`bot/alpaca_client.py`** — Wraps Alpaca paper trading REST API (`https://paper-api.alpaca.markets`). Each iron fly = 4 individual market orders. OCC symbol format: ticker left-padded to 6 chars + YYMMDD + P/C + 8-digit strike ×1000. Example: `ANET  260508P00172500`. If Alpaca rejects symbols, adjust `_occ_symbol()` here.

**`bot/positions.py`** — Reads/writes `positions.json` at repo root. `save_positions` appends; `clear_positions` only called on full success in `close_trades.py` (partial failures leave the file intact).

**`open_trades.py` / `close_trades.py`** — CLI entry points. Both prompt `[y/N]` before submitting anything.
