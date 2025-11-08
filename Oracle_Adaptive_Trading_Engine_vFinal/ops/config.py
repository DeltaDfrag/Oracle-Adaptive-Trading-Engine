
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
