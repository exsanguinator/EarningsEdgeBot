import os
import requests
from datetime import datetime


BASE_URL = "https://paper-api.alpaca.markets"


def _headers() -> dict:
    return {
        "APCA-API-KEY-ID": os.environ["ALPACA_API_KEY"],
        "APCA-API-SECRET-KEY": os.environ["ALPACA_SECRET_KEY"],
        "Content-Type": "application/json",
    }


def _occ_symbol(ticker: str, expiration: str, option_type: str, strike: float) -> str:
    """Build OCC option symbol: e.g. ANET  260508C00172500"""
    exp = datetime.strptime(expiration, "%Y-%m-%d").strftime("%y%m%d")
    strike_int = round(strike * 1000)
    return f"{ticker:<6}{exp}{option_type}{strike_int:08d}"


def submit_iron_fly(trade) -> list[dict]:
    """Submit 4 legs of an iron fly as individual market orders. Returns list of order responses."""
    legs = [
        (_occ_symbol(trade.ticker, trade.expiration, "P", trade.short_put), "sell"),
        (_occ_symbol(trade.ticker, trade.expiration, "C", trade.short_call), "sell"),
        (_occ_symbol(trade.ticker, trade.expiration, "P", trade.long_put),  "buy"),
        (_occ_symbol(trade.ticker, trade.expiration, "C", trade.long_call), "buy"),
    ]

    results = []
    for symbol, side in legs:
        payload = {
            "symbol": symbol,
            "qty": "1",
            "side": side,
            "type": "market",
            "time_in_force": "day",
        }
        resp = requests.post(f"{BASE_URL}/v2/orders", json=payload, headers=_headers())
        resp.raise_for_status()
        results.append(resp.json())

    return results


def close_position(symbol: str) -> dict:
    resp = requests.delete(f"{BASE_URL}/v2/positions/{symbol}", headers=_headers())
    resp.raise_for_status()
    return resp.json()


def get_open_positions() -> list[dict]:
    resp = requests.get(f"{BASE_URL}/v2/positions", headers=_headers())
    resp.raise_for_status()
    return resp.json()
