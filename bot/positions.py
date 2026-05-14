import json
import os
from datetime import datetime, timezone

from bot import alpaca_client
from bot.parser import IronFlyTrade

POSITIONS_FILE = os.path.join(os.path.dirname(__file__), "..", "positions.json")
CLOSED_POSITIONS_FILE = os.path.join(os.path.dirname(__file__), "..", "closed_positions.json")


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


def load_positions(path: str = POSITIONS_FILE) -> list[dict]:
    return _load(path)


def clear_positions(path: str = POSITIONS_FILE) -> None:
    _write([], path)


def append_closed_position(open_position: dict, open_order: dict, close_order: dict) -> None:
    open_fill = -float(open_order["filled_avg_price"]) if open_order.get("filled_avg_price") else None
    close_fill = -float(close_order["filled_avg_price"]) if close_order.get("filled_avg_price") else None
    # open_fill is positive (credit received); close_fill is negative (debit paid)
    total_pnl = round(open_fill + close_fill, 2) if (open_fill is not None and close_fill is not None) else None
    closed = _load_closed()
    closed.append({
        "ticker": open_position["ticker"],
        "expiration": open_position["expiration"],
        "open_order_id": open_position["order_id"],
        "close_order_id": close_order["id"],
        "opened_at": open_position["opened_at"],
        "closed_at": datetime.now(timezone.utc).isoformat(),
        "open_fill": open_fill,
        "close_fill": close_fill,
        "total_pnl": total_pnl,
        "legs": [{"symbol": leg["symbol"], "position_intent": leg["position_intent"]} for leg in open_position["legs"]],
    })
    _write_closed(closed)


def load_closed_positions() -> list[dict]:
    return _load_closed()


def _load(path: str = POSITIONS_FILE) -> list:
    if not os.path.exists(path):
        return []
    with open(path) as f:
        return json.load(f)


def _write(data: list, path: str = POSITIONS_FILE) -> None:
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def _load_closed() -> list:
    if not os.path.exists(CLOSED_POSITIONS_FILE):
        return []
    with open(CLOSED_POSITIONS_FILE) as f:
        return json.load(f)


def _write_closed(data: list) -> None:
    with open(CLOSED_POSITIONS_FILE, "w") as f:
        json.dump(data, f, indent=2)
