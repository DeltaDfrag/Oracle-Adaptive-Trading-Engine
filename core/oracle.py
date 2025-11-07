# ORACLE_ENGINE: Risk sizing, Kelly/CVaR governance, Black-Litterman integration
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
