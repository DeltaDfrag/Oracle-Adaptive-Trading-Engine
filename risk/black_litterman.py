import numpy as np
from typing import Tuple

RISK_AVERSION = 2.5       # δ — risk-aversion parameter
TAU_CONFIDENCE = 0.02     # τ — prior covariance confidence

def calculate_implied_market_returns(
    w_market: np.ndarray,
    cov: np.ndarray,
    risk_aversion: float = RISK_AVERSION,
) -> np.ndarray:
    """Pi = δ * Σ * w_market"""
    return risk_aversion * cov @ w_market


def black_litterman_model(
    w_market: np.ndarray,
    cov: np.ndarray,
    P: np.ndarray,
    Q: np.ndarray,
    tau: float = TAU_CONFIDENCE,
    regularization: float = 1e-6,
) -> Tuple[np.ndarray, np.ndarray]:
    """Black–Litterman posterior expected returns (E[R]) and posterior covariance matrix (Σ_BL)."""
    pi = calculate_implied_market_returns(w_market, cov)
    tau_cov = tau * cov
    Omega = P @ tau_cov @ P.T
    try:
        Omega_inv = np.linalg.inv(Omega)
    except np.linalg.LinAlgError:
        reg_value = regularization * np.linalg.norm(Omega)
        Omega_inv = np.linalg.inv(Omega + np.eye(Omega.shape[0]) * reg_value)
    tau_cov_inv = np.linalg.inv(tau_cov)
    A = np.linalg.inv(tau_cov_inv + P.T @ Omega_inv @ P)
    B = tau_cov_inv @ pi + P.T @ Omega_inv @ Q
    er_bl = A @ B
    return er_bl, A
    B = tau_cov_inv @ pi + P.T @ Omega_inv @ Q
    er_bl = A @ B
    return er_bl, A


def black_litterman_weights(
    asset_returns: np.ndarray,
    market_weights: np.ndarray,
    views_P: np.ndarray,
    views_Q: np.ndarray,
    rf_rate: float = 0.02,
    risk_aversion: float = RISK_AVERSION,
) -> np.ndarray:
    """Optimal BL weights (un-normalized)"""
    if asset_returns.ndim != 2 or asset_returns.shape[1] < 2:
        return market_weights
    cov = np.cov(asset_returns.T)
    er_bl, cov_bl = black_litterman_model(market_weights, cov, views_P, views_Q)
    try:
        inv_cov = np.linalg.inv(cov_bl)
    except np.linalg.LinAlgError:
        inv_cov = np.linalg.inv(cov_bl + np.eye(cov_bl.shape[0]) * 1e-6)
    er_excess = er_bl - rf_rate
    w_opt = (inv_cov @ er_excess) / risk_aversion
    return w_opt
