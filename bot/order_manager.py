import time
from bot import alpaca_client
from bot.parser import IronFlyTrade

REPRICE_INTERVAL = 10  # seconds between reprice attempts
REPRICE_STEP = 0.05    # dollars to walk per interval


def open_iron_fly(trade: IronFlyTrade) -> dict:
    """
    Submit iron fly as a single mleg limit order at current mid credit.
    Reprices every REPRICE_INTERVAL seconds until filled or credit reaches $0.
    Returns the filled order dict.
    """
    legs = _build_open_legs(trade)
    limit_price = -_net_open_mid(trade)  # negative = credit received

    while True:
        order = alpaca_client.submit_mleg_order(legs, limit_price)
        print(f"    limit ${-limit_price:.2f} credit", end="", flush=True)

        if _poll(order["id"], timeout=REPRICE_INTERVAL):
            print(" → filled")
            return alpaca_client.get_order(order["id"])

        alpaca_client.cancel_order(order["id"])
        limit_price = round(limit_price + REPRICE_STEP, 2)
        if limit_price >= 0:
            raise RuntimeError(f"{trade.ticker}: could not fill — limit reached $0 credit")
        print(" → repricing", end="", flush=True)


def close_iron_fly(position: dict) -> dict:
    """
    Close an iron fly as a single mleg limit order at current mid debit.
    Reprices every REPRICE_INTERVAL seconds, willing to pay more each time.
    Returns the filled order dict.
    """
    legs = _build_close_legs(position)
    limit_price = _net_close_mid(position)  # positive = debit paid

    while True:
        order = alpaca_client.submit_mleg_order(legs, limit_price)
        print(f"    limit ${limit_price:.2f} debit", end="", flush=True)

        if _poll(order["id"], timeout=REPRICE_INTERVAL):
            print(" → filled")
            return alpaca_client.get_order(order["id"])

        alpaca_client.cancel_order(order["id"])
        limit_price = round(limit_price + REPRICE_STEP, 2)
        print(" → repricing", end="", flush=True)


def _build_open_legs(trade: IronFlyTrade) -> list[dict]:
    return [
        {"symbol": _sym(trade, "P", trade.long_put),   "side": "buy",  "ratio_qty": "1", "position_intent": "buy_to_open"},
        {"symbol": _sym(trade, "C", trade.long_call),  "side": "buy",  "ratio_qty": "1", "position_intent": "buy_to_open"},
        {"symbol": _sym(trade, "P", trade.short_put),  "side": "sell", "ratio_qty": "1", "position_intent": "sell_to_open"},
        {"symbol": _sym(trade, "C", trade.short_call), "side": "sell", "ratio_qty": "1", "position_intent": "sell_to_open"},
    ]


def _build_close_legs(position: dict) -> list[dict]:
    close_intent = {"sell_to_open": "buy_to_close",  "buy_to_open": "sell_to_close"}
    close_side   = {"sell_to_open": "buy",           "buy_to_open": "sell"}
    return [
        {
            "symbol": leg["symbol"],
            "side": close_side[leg["position_intent"]],
            "ratio_qty": "1",
            "position_intent": close_intent[leg["position_intent"]],
        }
        for leg in position["legs"]
    ]


def _net_open_mid(trade: IronFlyTrade) -> float:
    """Net credit at mid for all 4 legs (positive = we receive)."""
    sell_syms = [_sym(trade, "P", trade.short_put), _sym(trade, "C", trade.short_call)]
    buy_syms  = [_sym(trade, "P", trade.long_put),  _sym(trade, "C", trade.long_call)]
    credit = sum(_mid(s) for s in sell_syms) - sum(_mid(s) for s in buy_syms)
    return round(credit, 2)


def _net_close_mid(position: dict) -> float:
    """Net debit at mid to close (positive = we pay)."""
    debit = 0.0
    for leg in position["legs"]:
        bid, ask = alpaca_client.get_option_quote(leg["symbol"])
        mid = (bid + ask) / 2
        if leg["position_intent"] == "sell_to_open":  # closing = buy_to_close
            debit += mid
        else:                                          # closing = sell_to_close
            debit -= mid
    return round(max(debit, 0.01), 2)


def _mid(symbol: str) -> float:
    bid, ask = alpaca_client.get_option_quote(symbol)
    return round((bid + ask) / 2, 2)


def _sym(trade: IronFlyTrade, option_type: str, strike: float) -> str:
    return alpaca_client._occ_symbol(trade.ticker, trade.expiration, option_type, strike)


def _poll(order_id: str, timeout: int) -> bool:
    """Returns True if order fills within timeout seconds, False otherwise."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        status = alpaca_client.get_order(order_id)["status"]
        if status == "filled":
            return True
        if status in ("canceled", "expired", "rejected"):
            return False
        time.sleep(2)
    return False
