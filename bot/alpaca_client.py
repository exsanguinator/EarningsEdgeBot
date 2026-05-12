import os
import requests
from datetime import datetime


BASE_URL = "https://paper-api.alpaca.markets"
DATA_URL = "https://data.alpaca.markets"


def _headers() -> dict:
    return {
        "APCA-API-KEY-ID": os.environ["ALPACA_API_KEY"],
        "APCA-API-SECRET-KEY": os.environ["ALPACA_SECRET_KEY"],
        "Content-Type": "application/json",
    }


def _occ_symbol(ticker: str, expiration: str, option_type: str, strike: float) -> str:
    exp = datetime.strptime(expiration, "%Y-%m-%d").strftime("%y%m%d")
    strike_int = round(strike * 1000)
    return f"{ticker}{exp}{option_type}{strike_int:08d}"


def get_option_quote(symbol: str) -> tuple[float, float]:
    """Returns (bid, ask) for an option symbol."""
    resp = requests.get(
        f"{DATA_URL}/v1beta1/options/snapshots",
        params={"symbols": symbol},
        headers=_headers(),
    )
    resp.raise_for_status()
    snap = resp.json()["snapshots"].get(symbol)
    if not snap:
        raise ValueError(f"No snapshot data for {symbol}")
    quote = snap["latestQuote"]
    return quote["bp"], quote["ap"]


def submit_mleg_order(legs: list[dict], limit_price: float, qty: int = 1) -> dict:
    payload = {
        "order_class": "mleg",
        "type": "limit",
        "time_in_force": "day",
        "qty": str(qty),
        "limit_price": str(round(limit_price, 2)),
        "legs": legs,
    }
    resp = requests.post(f"{BASE_URL}/v2/orders", json=payload, headers=_headers())
    if not resp.ok:
        raise requests.HTTPError(f"{resp.status_code} {resp.reason}: {resp.text}", response=resp)
    return resp.json()


def get_order(order_id: str) -> dict:
    resp = requests.get(
        f"{BASE_URL}/v2/orders/{order_id}",
        params={"nested": "true"},
        headers=_headers(),
    )
    resp.raise_for_status()
    return resp.json()


def cancel_order(order_id: str) -> None:
    resp = requests.delete(f"{BASE_URL}/v2/orders/{order_id}", headers=_headers())
    if not resp.ok and resp.status_code != 422:  # 422 = already filled/canceled
        resp.raise_for_status()


def get_open_positions() -> list[dict]:
    resp = requests.get(f"{BASE_URL}/v2/positions", headers=_headers())
    resp.raise_for_status()
    return resp.json()
