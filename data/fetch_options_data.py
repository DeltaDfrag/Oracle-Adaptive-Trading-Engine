import os
import datetime
import time
import logging
import numpy as np
import pandas as pd
import yfinance as yf

# --- Define all paths (auto-create if missing) ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RAW_DIR = os.path.join(BASE_DIR, "raw", "options")
PROC_DIR = os.path.join(BASE_DIR, "processed")
LOG_DIR = os.path.join(BASE_DIR, "logs")

for p in [RAW_DIR, PROC_DIR, LOG_DIR]:
    os.makedirs(p, exist_ok=True)

LOG_FILE = os.path.join(LOG_DIR, "data_fetch.log")
logging.basicConfig(filename=LOG_FILE, level=logging.INFO,
                    format="%(asctime)s - %(levelname)s - %(message)s")

SYMBOLS = ["SPY", "QQQ", "AAPL", "TSLA", "NVDA"]

def fetch_chain(symbol: str) -> pd.DataFrame:
    """Download the entire options chain for a ticker."""
    try:
        ticker = yf.Ticker(symbol)
        expiries = ticker.options
        all_frames = []
        for exp in expiries:
            try:
                opt = ticker.option_chain(exp)
                calls, puts = opt.calls, opt.puts
                calls["type"], puts["type"] = "call", "put"
                df = pd.concat([calls, puts])
                df["symbol"], df["expiry"] = symbol, exp
                all_frames.append(df)
                time.sleep(0.2)
            except Exception as e:
                logging.warning(f"{symbol} {exp} failed: {e}")
        return pd.concat(all_frames, ignore_index=True) if all_frames else pd.DataFrame()
    except Exception as e:
        logging.error(f"{symbol} fetch error: {e}")
        return pd.DataFrame()

def main():
    logging.info("Starting options data fetch…")
    all_data = []
    for sym in SYMBOLS:
        df = fetch_chain(sym)
        if not df.empty:
            raw_path = os.path.join(RAW_DIR, f"{sym}_{datetime.date.today()}.csv")
            df.to_csv(raw_path, index=False)
            logging.info(f"{sym}: {len(df)} rows saved.")
            all_data.append(df)
    if not all_data:
        print("⚠️ No data downloaded.")
        return

    combined = pd.concat(all_data, ignore_index=True)
    combined = combined.rename(columns={
        "lastPrice": "last", "impliedVolatility": "IV",
        "bid": "bid", "ask": "ask", "strike": "strike"
    })
    combined.dropna(subset=["IV", "bid", "ask"], inplace=True)
    combined["mid"] = (combined["bid"] + combined["ask"]) / 2
    combined["spread_pct"] = np.where(combined["bid"] > 0,
                                      (combined["ask"] - combined["bid"]) / combined["bid"], np.nan)
    combined["IV"] = combined["IV"].clip(0, 5)
    proc_path = os.path.join(PROC_DIR, "options_cleaned.parquet")
    combined.to_parquet(proc_path)
    print(f"Done - normalized file written to:\n{proc_path}")

if __name__ == "__main__":
    main()
