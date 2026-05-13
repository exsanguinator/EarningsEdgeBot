from bot.alpaca_client import get_option_quote, get_order


def fetch_position_data(position: dict) -> dict:
    """
    Returns enriched position dict with per-leg quotes/PnL and net totals.

    Adds to each leg: bid, ask, mid, fill (float|None), pnl (float|None), error (str|None)
    Adds to position: net_mid, net_pnl (None if any fills missing), quotes_error (str|None)
    """
    fills = {}
    mleg_fill = None
    quotes_error = None
    try:
        order = get_order(position["order_id"])
        fills = {
            leg["symbol"]: float(leg["filled_avg_price"])
            for leg in order.get("legs", [])
            if leg.get("filled_avg_price")
        }
        if order.get("filled_avg_price"):
            mleg_fill = -float(order["filled_avg_price"])
    except Exception as e:
        quotes_error = str(e)

    net_mid = 0.0
    net_pnl = 0.0
    has_all_fills = bool(fills)

    enriched_legs = []
    for leg in position["legs"]:
        symbol = leg["symbol"]
        is_short = leg["position_intent"] == "sell_to_open"
        entry = {"symbol": symbol, "position_intent": leg["position_intent"],
                 "is_short": is_short, "bid": None, "ask": None, "mid": None,
                 "fill": None, "pnl": None, "error": None}
        try:
            bid, ask = get_option_quote(symbol)
            mid = round((bid + ask) / 2, 2)
            fill = fills.get(symbol)
            entry.update({"bid": bid, "ask": ask, "mid": mid, "fill": fill})
            net_mid += -mid if is_short else mid
            if fill is not None:
                leg_pnl = (fill - mid) if is_short else (mid - fill)
                entry["pnl"] = round(leg_pnl, 2)
                net_pnl += leg_pnl
            else:
                has_all_fills = False
        except Exception as e:
            entry["error"] = str(e)
            has_all_fills = False
        enriched_legs.append(entry)

    return {
        **position,
        "legs": enriched_legs,
        "mleg_fill": mleg_fill,
        "net_mid": round(net_mid, 2),
        "net_pnl": round(net_pnl, 2) if has_all_fills else None,
        "quotes_error": quotes_error,
    }
