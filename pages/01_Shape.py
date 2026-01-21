import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import time

st.markdown("# 📈 **ID vs DA Curve - 24H Comparison**")

# Base shape for a typical daily power price curve
peak_shape = np.array([
    35, 30, 28, 25, 28, 32, # H1-H6: Overnight low
    55, 65, 70, 60, # H7-H10: Morning peak
    50, 45, 42, 40, 43, 48, # H11-H16: Mid-day solar dip
    65, 75, 80, 72, 68, # H17-H21: Evening peak
    55, 45, 40 # H22-H24: Late night decline
])

@st.cache_data
def generate_initial_data():
    """Fake DA/ID curves with realistic spreads for the first 24 hours"""
    # Use the peak_shape and add some noise for DA prices
    da_base = peak_shape + np.random.uniform(-3, 3, 24)
    id_spread = np.random.uniform(-2.0, 3.0, 24)
    id_prices = da_base + id_spread
    
    data = pd.DataFrame({
        'DA €/MWh': np.round(da_base, 2),
        'ID €/MWh': np.round(id_prices, 2),
        'Spread €': np.round(id_spread, 2),
        'Spread %': np.round((id_spread / da_base) * 100, 1)
    })
    return data

# Initialize or update data in session state - KEEP LAST 24 ROWS ONLY
if 'curve_data' not in st.session_state:
    st.session_state.curve_data = generate_initial_data()
else:
    # Shift: remove oldest row, add new data
    df = st.session_state.curve_data.iloc[1:].copy()
    
    new_da = peak_shape[0] + np.random.uniform(-3, 3)  # Use peak_shape for new "H1"
    new_spread = np.random.uniform(-2.0, 3.0)
    new_id = new_da + new_spread
    
    new_row = pd.DataFrame({
        'DA €/MWh': [np.round(new_da, 2)],
        'ID €/MWh': [np.round(new_id, 2)],
        'Spread €': [np.round(new_spread, 2)],
        'Spread %': [np.round((new_spread / new_da) * 100, 1)]
    })
    
    st.session_state.curve_data = pd.concat([df, new_row], ignore_index=True)
    
    # TRIM TO EXACTLY 24 ROWS to prevent unlimited growth
    st.session_state.curve_data = st.session_state.curve_data.tail(24).reset_index(drop=True)

# Always create fresh display DataFrame with fixed Hour labels
df_display = st.session_state.curve_data.tail(24).copy().reset_index(drop=True)
df_display.insert(0, 'Hour', [f'H{i+1}' for i in range(len(df_display))])

df = df_display  # Use this for metrics and display

# METRICS FRONT AND CENTER (always visible)
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Max Spread", f"{df['Spread €'].max():.1f}€")
with col2:
    st.metric("Avg Spread", f"{df['Spread €'].mean():.1f}€")
with col3:
    st.metric("Volatility", f"{df['Spread €'].std():.1f}€")

def color_spread(val):
    if isinstance(val, (int, float)):
        return 'background-color: #90EE90' if val < 0 else 'background-color: #FFB6C1'
    return ''

# FIXED ORDER: Make Hour categorical so it can't be sorted out of order
hour_order = [f'H{i}' for i in range(1, 25)]
df_display['Hour'] = pd.Categorical(df_display['Hour'], categories=hour_order, ordered=True)

styled_df = df_display.style.format({
    'DA €/MWh': '{:.2f}',
    'ID €/MWh': '{:.2f}',
    'Spread €': '{:.2f}',
    'Spread %': '{:.1f}%'
}).applymap(color_spread, subset=['Spread €', 'Spread %'])

st.dataframe(styled_df, use_container_width=True, height=600, hide_index=True)


time.sleep(1)
st.rerun()
