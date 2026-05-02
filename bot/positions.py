import json
import os
from datetime import datetime, timezone

POSITIONS_FILE = os.path.join(os.path.dirname(__file__), "..", "positions.json")


def save_positions(ticker: str, expiration: str, order_responses: list[dict]) -> None:
    positions = _load()
    symbols = [o["symbol"] for o in order_responses if "symbol" in o]
    positions.append({
        "ticker": ticker,
        "expiration": expiration,
        "legs": symbols,
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
