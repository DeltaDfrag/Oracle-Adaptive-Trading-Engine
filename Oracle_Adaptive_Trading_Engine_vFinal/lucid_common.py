
import random
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict

def clamp(value, min_val, max_val):
    return max(min_val, min(value, max_val))

@dataclass
class OptionsMetrics:
    iv_rank: float = 0.0
    theta_per_day: float = 0.0
    bid_ask_spread_pct: float = 0.0

@dataclass
class OptionsTradeDetails:
    asset_type: str = 'none'
    strategy: str = 'none'
    side: str = 'none'
    contracts_qty: int = 0
    max_risk_dollars: float = 0.0
    entry_price_px: float = 0.0
    expiry_date: str = ""
    entry_dte: int = 0

def compute_options_metrics() -> OptionsMetrics:
    return OptionsMetrics(
        iv_rank=random.uniform(0.1, 0.9),
        theta_per_day=random.uniform(-0.1, 0.1),
        bid_ask_spread_pct=random.uniform(0.005, 0.05),
    )

def select_expiry_date(min_days: int, max_days: int):
    today = datetime.utcnow()
    dte = random.randint(min_days, max_days)
    return (today + timedelta(days=dte)).strftime("%Y-%m-%d"), dte

def log(src: str, msg: str):
    print(f"[{src}] {msg}")

def bus_write(name: str, payload: Dict[str, Any]):
    pass

def bus_read(name: str, default):
    return default
