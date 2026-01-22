import streamlit as st
import pandas as pd
import numpy as np
import time

st.markdown("# 📋 **EXECUTION LOG - Live Append**")
st.markdown("**_Strategies trigger → Real-time journal_**")

# Wide Bloomberg layout
st.set_page_config(layout="wide")

# Session state for persistent append
if 'logs' not in st.session_state:
    st.session_state.logs = pd.DataFrame(columns=[
        'Time', 'Hour', 'Trigger', 'EXEC PLAN', 'FENCE', 'Status', 'P&L €k', 'Notes'
    ])

# SLOWER Append: 20% chance (1 log every ~5 refreshes)
if np.random.random() < 2:
    new_log = {
        'Time': pd.Timestamp.now().strftime('%H:%M:%S'),
        'Hour': f'H{np.random.randint(1,25)}',
        'Trigger': np.random.choice(['MOM+1.2🔵', 'LOB60🔴', 'IMB82%', 'VAR120k', 'SHAPE-0.8']),
        'EXEC PLAN': np.random.choice([
            "2×BLOCK + 2×LARGE CLIP + 1×ICEBERG + 1×LADDER",
            "3×BLOCK + 1×CLIP + 2×ICEBERG",
            "1×BLOCK + 3×LARGE CLIP + 2×LADDER"
        ]),
        'FENCE': f"{np.random.randint(120,220)}MW €{np.random.randint(45,50)}P/€{np.random.randint(52,56)}C collar",
        'Status': np.random.choice(['✅ EXEC', '⏳ PENDING']),
        'P&L €k': np.random.randint(-30, 80),
        'Notes': np.random.choice(['Full fill', 'Partial 80%', 'Low slippage'])
    }
    st.session_state.logs = pd.concat([st.session_state.logs, pd.DataFrame([new_log])], ignore_index=True)
    
    # Cap at 30 logs for demo
    if len(st.session_state.logs) > 30:
        st.session_state.logs = st.session_state.logs.tail(30).reset_index(drop=True)

df_logs = st.session_state.logs

# Hour filter
selected_hour = st.selectbox("**Filter by Hour:**", ['All'] + sorted(df_logs['Hour'].unique().tolist()))

if selected_hour == 'All':
    filtered_logs = df_logs
else:
    filtered_logs = df_logs[df_logs['Hour'] == selected_hour]

# Bloomberg KPIs
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("**Total Logs**", len(df_logs))
with col2:
    avg_pnl = df_logs['P&L €k'].mean() if len(df_logs)>0 else 0
    st.metric("**Avg P&L**", f"€{avg_pnl:.0f}k")
with col3:
    fence_mws = df_logs['FENCE'].str.extract(r'(\d+)', expand=False).astype(float)
    avg_fence = fence_mws.mean() if len(fence_mws)>0 else 0
    st.metric("**Avg Fence**", f"{avg_fence:.0f}MW")

# Styled log table
def bloomberg_style(row):
    colors = [''] * len(row)
    if '✅ EXEC' in str(row['Status']):
        colors = ['background-color: #e1f5fe'] * len(row)
    if row.get('P&L €k', 0) > 30:
        colors[-2] = 'background-color: #d4edda'
    elif row.get('P&L €k', 0) < -15:
        colors[-2] = 'background-color: #f8d7da'
    return colors

styled_logs = filtered_logs[['Time','Trigger','EXEC PLAN','Status','P&L €k','Notes']].style.apply(bloomberg_style, axis=1).format({'P&L €k': '{:+.0f}'})

st.markdown("### **_LIVE EXECUTION JOURNAL_**")
st.dataframe(styled_logs, use_container_width=True, height=600, hide_index=True)

# Demo controls
with st.expander("⚙️ Demo Controls"):
    col1, col2 = st.columns(2)
    if col1.button("🧹 Clear Logs"):
        st.session_state.logs = pd.DataFrame(columns=df_logs.columns)
        st.rerun()
    if col2.button("➕ Force Append", type="secondary"):
        new_log = {
            'Time': pd.Timestamp.now().strftime('%H:%M:%S'),
            'Trigger': 'LOB45🟡',
            'EXEC PLAN': "2×BLOCK + 2×LEER + 1×ICEBERG",
            'FENCE': "148MW €47P/€54C collar",
            'Status': '✅ EXEC',
            'P&L €k': 42,
            'Notes': 'Full execution'
        }
        st.session_state.logs = pd.concat([st.session_state.logs, pd.DataFrame([new_log])], ignore_index=True)
        st.rerun()
    
    st.info("**Refresh 5-7x:** ~1 log every 5 refreshes (20% chance)")

# Smooth 3s refresh
time.sleep(3)
st.rerun()