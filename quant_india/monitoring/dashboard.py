from __future__ import annotations

import streamlit as st


def render_dashboard() -> None:
    st.set_page_config(page_title="Quant India Monitoring", layout="wide")
    st.title("Quant India Monitoring Dashboard")
    st.write("Placeholder Streamlit dashboard. Connect to Parquet metrics and feature store for live monitoring.")
    uploaded_file = st.file_uploader("Upload backtest results (Parquet)", type=["parquet"])
    if uploaded_file:
        import pandas as pd

        df = pd.read_parquet(uploaded_file)
        st.line_chart(df.set_index("timestamp")["net_pnl"].cumsum(), height=300)
