import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import time

st.markdown("# 📈 **CH vs FR Curve - 24H Comparison**")

tab1_inter, tab2_inter = st.tabs(["60 Mins", "15 Mins"])
with tab1_inter:
    # Base shape for a typical daily power price curve
    peak_shape_interconnection = np.array([
        35, 30, 28, 25, 28, 32, # H1-H6: Overnight low
        55, 65, 70, 60, # H7-H10: Morning peak
        50, 45, 42, 40, 43, 48, # H11-H16: Mid-day solar dip
        65, 75, 80, 72, 68, # H17-H21: Evening peak
        55, 45, 40 # H22-H24: Late night decline
    ])

    @st.cache_data
    def generate_initial_data_interconnection():
        """Fake DA/ID curves with realistic spreads for the first 24 hours"""
        # Use the peak_shape and add some noise for DA prices
        da_base_interconnection = peak_shape_interconnection + np.random.uniform(-3, 3, 24)
        id_spread_interconnection = np.random.uniform(-2.0, 3.0, 24)
        id_prices_interconnection = da_base_interconnection + id_spread_interconnection
        
        data_interconnection = pd.DataFrame({
            'CH €/MWh': np.round(da_base_interconnection, 2),
            'FR €/MWh': np.round(id_prices_interconnection, 2),
            'Spread €': np.round(id_spread_interconnection, 2),
            'Spread %': np.round((id_spread_interconnection / da_base_interconnection) * 100, 1)
        })
        return data_interconnection

    # Initialize or update data in session state - KEEP LAST 24 ROWS ONLY
    if 'curve_data_inter' not in st.session_state:
        st.session_state.curve_data_inter = generate_initial_data_interconnection()
    else:
        # Shift: remove oldest row, add new data
        df_interconnection = st.session_state.curve_data_inter.iloc[1:].copy()
        
        new_da_interconnection = peak_shape_interconnection[0] + np.random.uniform(-3, 3)  # Use peak_shape for new "H1"
        new_spread_interconnection = np.random.uniform(-2.0, 3.0)
        new_id_interconnection = new_da_interconnection + new_spread_interconnection
        
        new_row_interconnection = pd.DataFrame({
            'CH €/MWh': [np.round(new_da_interconnection, 2)],
            'FR €/MWh': [np.round(new_id_interconnection, 2)],
            'Spread €': [np.round(new_spread_interconnection, 2)],
            'Spread %': [np.round((new_spread_interconnection / new_da_interconnection) * 100, 1)]
        })
        
        st.session_state.curve_data_inter = pd.concat([df_interconnection, new_row_interconnection], ignore_index=True)
        
        # TRIM TO EXACTLY 24 ROWS to prevent unlimited growth
        st.session_state.curve_data_inter = st.session_state.curve_data_inter.tail(24).reset_index(drop=True)

    # Always create fresh display DataFrame with fixed Hour labels
    df_display_inter = st.session_state.curve_data_inter.tail(24).copy().reset_index(drop=True)
    df_display_inter.insert(0, 'Hour', [f'H{i+1}' for i in range(len(df_display_inter))])

    df = df_display_inter  # Use this for metrics and display

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
    hour_order_inter = [f'H{i}' for i in range(1, 25)]
    df_display_inter['Hour'] = pd.Categorical(df_display_inter['Hour'], categories=hour_order_inter, ordered=True)

    styled_df_inter = df_display_inter.style.format({
        'CH €/MWh': '{:.2f}',
        'FR €/MWh': '{:.2f}',
        'Spread €': '{:.2f}',
        'Spread %': '{:.1f}%'
    }).applymap(color_spread, subset=['Spread €', 'Spread %'])

    st.dataframe(styled_df_inter, use_container_width=True, height=600, hide_index=True)
with tab2_inter:
     # =========================
    # BASE HOURLY SHAPE (24 HOURS)
    # =========================
    peak_shape_hourly_inter = np.array([
        35, 35.2, 35.1, 33, 30, 29, 29, 27, 28, 28, 29, 31,
        25, 25, 25, 23, 28, 28, 27, 29, 32, 35, 35, 35
    ])

    # =========================
    # EXPAND TO 15-MIN (96 QH)
    # =========================
    peak_shape_15m_inter = np.repeat(peak_shape_hourly_inter, 4)

    # =========================
    # DATA GENERATOR (CACHE VERSIONED)
    # =========================
    @st.cache_data(show_spinner=False)
    def generate_initial_data_v2_inter():  # <-- version bump fixes cache
        da_base = peak_shape_15m_inter + np.random.uniform(-3, 3, 96)
        id_spread = np.random.uniform(-2.0, 3.0, 96)
        id_prices = da_base + id_spread

        return pd.DataFrame({
            'CH €/MWh': np.round(da_base, 2),
            'FR €/MWh': np.round(id_prices, 2),
            'Spread €': np.round(id_spread, 2),
            'Spread %': np.round((id_spread / da_base) * 100, 1)
        })

    # =========================
    # SESSION STATE
    # =========================
    if 'curve_data_inter' not in st.session_state:
        st.session_state.curve_data_inter = generate_initial_data_v2_inter()
    else:
        df_inter = st.session_state.curve_data_inter.iloc[1:].copy()

        new_da_interconnection = peak_shape_15m_inter[0] + np.random.uniform(-3, 3)
        new_spread_interconnection = np.random.uniform(-2.0, 3.0)
        new_id_interconnection = new_da_interconnection + new_spread_interconnection

        new_row_interconnection = pd.DataFrame({
            'CH €/MWh': [round(new_da_interconnection, 2)],
            'FR €/MWh': [round(new_id_interconnection, 2)],
            'Spread €': [round(new_spread_interconnection, 2)],
            'Spread %': [round((new_spread_interconnection / new_da_interconnection) * 100, 1)]
        })

        st.session_state.curve_data_inter = pd.concat([df_inter, new_row_interconnection], ignore_index=True)
        st.session_state.curve_data_inter = (
            st.session_state.curve_data_inter.tail(96).reset_index(drop=True)
        )

    # =========================
    # DISPLAY DATA
    # =========================
    df_display_inter = st.session_state.curve_data_inter.copy()

    quarter_labels = [
        f'H{h}-Q{q}'
        for h in range(1, 25)
        for q in range(1, 5)
    ]

    # ✅ SAFE: slice labels to df length
    df_display_inter.insert(0, 'Hour', quarter_labels[:len(df_display_inter)])

    df_display_inter['Hour'] = pd.Categorical(
        df_display_inter['Hour'],
        categories=quarter_labels,
        ordered=True
    )

    # =========================
    # METRICS
    # =========================
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Max Spread", f"{df_display_inter['Spread €'].max():.1f}€")
    with col2:
        st.metric("Avg Spread", f"{df_display_inter['Spread €'].mean():.1f}€")
    with col3:
        st.metric("Volatility", f"{df_display_inter['Spread €'].std():.1f}€")

    # =========================
    # STYLING
    # =========================
    def color_spread(val):
        if isinstance(val, (int, float)):
            return 'background-color: #90EE90' if val < 0 else 'background-color: #FFB6C1'
        return ''

    styled_df_inter = (
        df_display_inter.style
        .format({
            'CH €/MWh': '{:.2f}',
            'FR €/MWh': '{:.2f}',
            'Spread €': '{:.2f}',
            'Spread %': '{:.1f}%'
        })
        .applymap(color_spread, subset=['Spread €', 'Spread %'])
    )

    st.dataframe(styled_df_inter, use_container_width=True, height=600, hide_index=True)

time.sleep(1)
st.rerun()