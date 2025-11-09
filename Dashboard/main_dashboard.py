# Dashboard/main_dashboard.py
import streamlit as st
import pandas as pd
import os
import matplotlib.pyplot as plt


st.set_page_config(page_title="ORACLE Dashboard", layout="wide")

st.title("🧠 ORACLE Adaptive Trading Engine Dashboard")

data_path = "data/metrics/equity_curve.csv"

if os.path.exists(data_path):
    df = pd.read_csv(data_path)
    st.subheader("📈 Equity Curve")
    st.line_chart(df["equity"], use_container_width=True)

    st.subheader("📊 Recent Metrics")
    st.dataframe(df.tail(10))
else:
    st.warning("No equity curve data found. Run a backtest first.")
import streamlit as st
    