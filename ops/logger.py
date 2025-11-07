"""
ORACLE Adaptive Trading Engine — MLflow Logger
------------------------------------------------
Lightweight experiment logger for ORACLE.

Usage:
    from ops.logger import OracleLogger
    log = OracleLogger(run_name="Backtest_2025_11_07")
    log.log_param("policy", "CVaR-PPO")
    log.log_metric("sharpe", 1.87)
    log.end_run()

View runs:
    mlflow ui --port 5000
    then open http://localhost:5000
"""

import os
import mlflow
from datetime import datetime
from typing import Any, Dict

# ------------------------------------------------------------
# CORE LOGGER CLASS
# ------------------------------------------------------------

class OracleLogger:
    """
    Simple wrapper around MLflow for consistent logging across
    SMITH, ORACLE, LUCID, and RL modules.
    """

    def __init__(self, run_name: str = None):
        os.makedirs("./mlruns", exist_ok=True)
        mlflow.set_tracking_uri("file:./mlruns")

        if run_name is None:
            run_name = f"Run_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        self.run = mlflow.start_run(run_name=run_name)
        mlflow.set_tag("system", "ORACLE_Adaptive_Trading_Engine")

    # -----------------------------
    # PARAMETER / METRIC LOGGING
    # -----------------------------
    def log_param(self, key: str, value: Any):
        mlflow.log_param(key, value)

    def log_params(self, params: Dict[str, Any]):
        for k, v in params.items():
            mlflow.log_param(k, v)

    def log_metric(self, key: str, value: float, step: int = None):
        mlflow.log_metric(key, value, step=step)

    def log_metrics(self, metrics: Dict[str, float], step: int = None):
        for k, v in metrics.items():
            mlflow.log_metric(k, v, step=step)

    # -----------------------------
    # ARTIFACT LOGGING
    # -----------------------------
    def log_artifact(self, path: str):
        if os.path.exists(path):
            mlflow.log_artifact(path)

    # -----------------------------
    # END RUN
    # -----------------------------
    def end_run(self):
        mlflow.end_run()


# ------------------------------------------------------------
# QUICK TEST
# ------------------------------------------------------------

if __name__ == "__main__":
    log = OracleLogger("smoke_test")
    log.log_param("example_param", "test_value")
    log.log_metric("dummy_sharpe", 1.23)
    log.end_run()
    print("Logged example run to ./mlruns/")