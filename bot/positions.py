import json
import os
from datetime import datetime, timezone

from bot import alpaca_client
from bot.parser import IronFlyTrade

POSITIONS_FILE = os.path.join(os.path.dirname(__file__), "..", "positions.json")


def save_positions(trade: IronFlyTrade, order: dict) -> None:
    positions = _load()
    legs = [
        {"symbol": alpaca_client._occ_symbol(trade.ticker, trade.expiration, "P", trade.long_put),   "position_intent": "buy_to_open"},
        {"symbol": alpaca_client._occ_symbol(trade.ticker, trade.expiration, "C", trade.long_call),  "position_intent": "buy_to_open"},
        {"symbol": alpaca_client._occ_symbol(trade.ticker, trade.expiration, "P", trade.short_put),  "position_intent": "sell_to_open"},
        {"symbol": alpaca_client._occ_symbol(trade.ticker, trade.expiration, "C", trade.short_call), "position_intent": "sell_to_open"},
    ]
    positions.append({
        "ticker": trade.ticker,
        "expiration": trade.expiration,
        "legs": legs,
        "order_id": order["id"],
        "opened_at": datetime.now(timezone.utc).isoformat(),
    })
    _write(positions)


def load_positions() -> list[dict]:
    return _load()


def clear_positions() -> None:
    _write([])


def _load() -> list:
    if not os.path.exists(POSITIONS_FILE):
        return []
    with open(POSITIONS_FILE) as f:
        return json.load(f)


def _write(data: list) -> None:
    with open(POSITIONS_FILE, "w") as f:
        json.dump(data, f, indent=2)
