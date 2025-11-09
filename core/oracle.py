"""
ORACLE Engine Core

High-level responsibilities:
- Enforce config/sizing integrity (Kelly, CVaR, max position caps).
- Use MetaModel to gate low-quality signals.
- Use Strategy Registry to restrict allowed structures by equity tier.
- Use options_gater to select structures (spreads, condors, etc.).
- Size positions via tempered Kelly + CVaR cap (+ Black-Litterman multiplier hook).
- Provide a single approve(snapshot) entrypoint for backtests and live trading.
"""

import time
import json

def load_allowed_strategies(equity: float, registry_path="./core/strategy_registry.json"):
    with open(registry_path) as f:
        reg = json.load(f)
    tiers = sorted(reg["capital_tiers"], key=lambda x: x["min_equity"])
    allowed = []
    for tier in tiers:
        if equity >= tier["min_equity"]:
            allowed = tier["strategies"]
        else:
            break
    return allowed
if __name__ == "__main__":
    print("ORACLE Engine initialized and ready.")
