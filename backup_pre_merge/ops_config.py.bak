from dataclasses import dataclass

@dataclass
class RiskConfig:
    portfolio_equity: float
    max_risk_per_trade: float
    max_positions: int
    portfolio_beta: float = 1.0

SMALL_ACCOUNT_RISK = RiskConfig(
    portfolio_equity=3250.0,
    max_risk_per_trade=32.50,
    max_positions=3,
)

META_THRESHOLD = 0.60
CVAR_CAP = 0.0125
MAX_POS_PCT = 0.10
DTE_STATE = {'count': 0}

# --- NEW GREEKS CONSTRAINTS ---
# Maximum Gamma allowed for any trade (especially sensitive near expiry)
MAX_GAMMA_LIMIT = 0.15 
# Minimum Theta (premium decay) required for short premium strategies
MIN_THETA_PREMIUM_SALE = 0.01 
# ORACLE_CONFIG: Central runtime configuration
