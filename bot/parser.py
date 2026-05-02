import re
from dataclasses import dataclass


@dataclass
class IronFlyTrade:
    ticker: str
    expiration: str      # "YYYY-MM-DD"
    short_put: float
    short_call: float
    long_put: float
    long_call: float
    net_credit: float    # credit - debit


def parse_scan_output(text: str) -> list[IronFlyTrade]:
    """Parse EarningsEdgeDetection --iron-fly stdout, returning Tier 1 trades only."""
    tier1_match = re.search(
        r"TIER 1 RECOMMENDED TRADES:(.*?)(?=TIER 2 RECOMMENDED TRADES:|NEAR MISSES:|SKIPPING:|$)",
        text,
        re.DOTALL,
    )
    if not tier1_match:
        return []

    section = tier1_match.group(1)
    trades = []

    # Split on ticker blocks: lines that start with exactly 2 spaces + WORD + colon
    ticker_pattern = re.compile(r"^\s{2}(\w+):", re.MULTILINE)
    ticker_positions = [(m.group(1), m.start()) for m in ticker_pattern.finditer(section)]

    for i, (ticker, start) in enumerate(ticker_positions):
        end = ticker_positions[i + 1][1] if i + 1 < len(ticker_positions) else len(section)
        block = section[start:end]

        expiry = _extract(r"Expiration:\s+(\d{4}-\d{2}-\d{2})", block)
        short_raw = _extract(r"SHORT:\s+\$([0-9.]+)P/\$([0-9.]+)C\s+for\s+\$([0-9.]+)\s+credit", block, groups=3)
        long_raw = _extract(r"LONG:\s+\$([0-9.]+)P/\$([0-9.]+)C\s+for\s+\$([0-9.]+)\s+debit", block, groups=3)

        if not all([expiry, short_raw, long_raw]):
            continue

        trades.append(IronFlyTrade(
            ticker=ticker,
            expiration=expiry,
            short_put=float(short_raw[0]),
            short_call=float(short_raw[1]),
            long_put=float(long_raw[0]),
            long_call=float(long_raw[1]),
            net_credit=round(float(short_raw[2]) - float(long_raw[2]), 4),
        ))

    return trades


def _extract(pattern: str, text: str, groups: int = 1):
    m = re.search(pattern, text)
    if not m:
        return None
    return m.group(1) if groups == 1 else tuple(m.group(i + 1) for i in range(groups))
