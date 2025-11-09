import os
import time
import numpy as np
import pandas as pd
import os, sys
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)
from core.oracle import approve
import os, sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))


DATA_PATH = "data/processed/options_cleaned.parquet"
OUTPUT_PATH = "data/metrics/backtest_results.csv"

os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)

def run_backtest():
    if not os.path.exists(DATA_PATH):
        print("Error: processed options data not found.")
        return

    df = pd.read_parquet(DATA_PATH)
    total_rows = len(df)
    print(f"Loaded {total_rows} option records.")

    if total_rows == 0:
        print("No data found in parquet file.")
        return

    results = []
    portfolio_equity = 10_000.0
    processed_count = 0

    print("Starting backtest...")

    for i, row in df.iterrows():
        snapshot = {
            "price": float(row.get("mid", 0.0)),
            "bias": float(np.sign(np.random.randn())),
            "confidence": float(np.random.uniform(0.6, 0.95)),
            "trade_prob": float(np.random.uniform(0.5, 0.9)),
            "dispersion": float(np.random.uniform(0.0, 0.02))
        }

        try:
            decision = approve(snapshot)
            processed_count += 1

            # Basic data sanity
            if decision.get("approve", False):
                results.append({
                    "timestamp": time.time(),
                    "symbol": row.get("symbol", "N/A"),
                    "expiry": row.get("expiry", "N/A"),
                    "decision": decision.get("approve", False),
                    "strategy": decision.get("strategy", "None"),
                    "allocation": decision.get("allocation_fraction", 0.0),
                    "confidence": snapshot["confidence"],
                    "price": snapshot["price"],
                    "side": decision.get("side", "N/A"),
                    "asset_type": decision.get("asset_type", "N/A")
                })

        except Exception as e:
            print(f"Error at row {i}: {e}")

        # Progress logging every 500 rows
        if i % 500 == 0 and i > 0:
            print(f"Processed {i}/{total_rows} rows...")

        # Limit the test run to 5,000 rows for speed during first pass
        if processed_count >= 5000:
            break

    print(f"Finished processing {processed_count} rows.")

    if results:
        results_df = pd.DataFrame(results)
        results_df.to_csv(OUTPUT_PATH, index=False)
        print(f"Backtest complete. Results written to {OUTPUT_PATH}")
    else:
        print("No trade decisions were approved or logged.")

if __name__ == "__main__":
    run_backtest()
