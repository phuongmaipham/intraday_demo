import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import requests
import xml.etree.ElementTree as ET

# --- Configuration ---
ENTSOE_API_KEY = "PASTE_YOUR_ENTSOE_API_KEY_HERE"
ENTSOE_AREA_CODE = "10YCH-SWISSGRID"

st.set_page_config(page_title="CH ID Live Dashboard", layout="wide")

# Style for blinking text
st.markdown("""
<style>
@keyframes blinker {
  50% {
    opacity: 0;
  }
}
.blink-red {
  animation: blinker 1s linear infinite;
  color: red;
  font-weight: bold;
}
.blink-yellow {
  animation: blinker 1s linear infinite;
  color: orange;
  font-weight: bold;
}
</style>
""", unsafe_allow_html=True)

@st.cache_data(ttl=3600) # Cache for 1 hour
def fetch_historical_prices(api_key, area_code, end_date, days_to_fetch):
    if not api_key or api_key == "PASTE_YOUR_ENTSOE_API_KEY_HERE":
        st.error("Using random data.")
        return pd.DataFrame()
    start_date = end_date - timedelta(days=days_to_fetch)
    params = {
        'securityToken': api_key, 'documentType': 'A44', 'in_Domain': area_code,
        'out_Domain': area_code, 'periodStart': start_date.strftime('%Y%m%d%H%M'),
        'periodEnd': end_date.strftime('%Y%m%d%H%M'),
    }
    try:
        response = requests.get("https://web-api.tp.entsoe.eu/api", params=params)
        response.raise_for_status()
        root = ET.fromstring(response.content)
        namespace = {'ns': 'urn:iec62325.351:tc57wg16:451-3:publicationdocument:7:0'}
        points = []
        for ts in root.findall('ns:TimeSeries', namespace):
            series_start_str = ts.find('.//ns:start', namespace).text
            series_start = datetime.fromisoformat(series_start_str.replace('Z', '+00:00'))
            for p in ts.findall('.//ns:Point', namespace):
                pos = int(p.find('ns:position', namespace).text)
                price = float(p.find('ns:price.amount', namespace).text)
                point_time = series_start + timedelta(hours=pos-1)
                points.append({'time': point_time, 'price': price})
        if not points: return pd.DataFrame()
        df = pd.DataFrame(points).set_index('time')
        df['hour'] = df.index.hour
        df['day'] = df.index.date
        price_df = df.pivot(index='day', columns='hour', values='price')
        return price_df
    except (requests.exceptions.RequestException, ET.ParseError) as e:
        st.error(f"API error: {e}. Could not fetch historical prices.")
        return pd.DataFrame()

@st.cache_data(ttl=1)
def generate_live_hourly_data(fence_active, historical_prices):
    hours = [f'H{i}' for i in range(1, 25)]
    data = []
    real_prices = historical_prices.iloc[-1].to_dict() if not historical_prices.empty else {}
    for h_num in range(1, 25):
        h = f"H{h_num}"
        h_col_index = h_num - 1
        hourly_series = historical_prices[h_col_index].dropna() if h_col_index in historical_prices.columns else pd.Series()
        if len(hourly_series) > 5:
            hourly_vol = hourly_series.std()
            hourly_var = hourly_vol * 10 
        else:
            hourly_vol = np.random.uniform(4, 7)
            hourly_var = np.random.uniform(35, 80)
        
        hourly_imb_mw = np.random.uniform(-4, 4)
        da = real_prices.get(h_col_index, 50 + np.random.uniform(-6, 6))
        id_mid = da + np.random.uniform(-1.2, 1.2)
        lob_mw = np.random.uniform(8, 95)
        vwap_pct = np.random.uniform(-1.5, 2.0)
        bid_imb = 0.5 + np.random.uniform(-0.3, 0.4) if vwap_pct > 0 else 0.5 + np.random.uniform(-0.4, 0.3)
        offer_imb = 1 - bid_imb
        
        if lob_mw < 25: size_pct = 0.30
        elif 25 <= lob_mw <= 40: size_pct = 0.50
        elif 45 <= lob_mw <= 60: size_pct = 0.75
        elif lob_mw > 65: size_pct = 1.00
        elif 40 < lob_mw < 45: size_pct = 0.50
        else: size_pct = 0.75
        
        size_mw = lob_mw * size_pct
        direction_sign = "+" if (bid_imb > offer_imb) else "-"
        formatted_size = f"{direction_sign}{size_mw:.0f}MW@{id_mid:.2f}"
        
        ppa_pos, id_pos, da_pos = np.random.randint(-50, 50), np.random.randint(-20, 20), np.random.randint(-100, 100)
        hour_residual = ppa_pos + id_pos + da_pos
        lob_color = ""
        shape_color = "🟢" if abs(vwap_pct) > 1.0 else ""
        action, size = "", ""
        
        if fence_active:
            residual_direction_sign = "-" if (hour_residual > 0) else "+"
            action, size = "Collar", f"{residual_direction_sign}€{id_mid - 2:.0f}P/€{id_mid + 2:.0f}C"
        else:
            if hourly_var < 70 and abs(hourly_imb_mw) < 3 and hourly_vol < 6:
                if abs(vwap_pct) > 1.1: action, size = "Shape Arb", formatted_size
                elif abs(lob_mw) > 60: action, size = "Market", formatted_size
                elif 25 <= abs(lob_mw) <= 40 and max(bid_imb, offer_imb) > 0.7: action, size = "Iceberg", formatted_size
                elif abs(lob_mw) < 25: action, size = "Ladder", formatted_size
                elif 25 <= abs(lob_mw) <= 60: action, size = "Leer", formatted_size
            else:
                action, size = "Market", formatted_size

        data.append({
            'Hour': h, 'DA€': f"{da:.2f}", 'ID Bid€': f"{id_mid - 0.1:.2f}/{int(lob_mw * bid_imb):.0f}MW",
            'ID Offer€': f"{id_mid + 0.1:.2f}/{int(lob_mw * offer_imb):.0f}MW", 'Mid€': f"{id_mid:.2f}",
            'LOB MW': f"{int(lob_mw)} {lob_color}", 'Shape': f"{vwap_pct:+.2f}{shape_color}",
            'Hour Residual': f"{hour_residual} MW", 'Hourly VaR': f"€{hourly_var:.1f}k", 
            'Hourly Vol': f"€{hourly_vol:.2f}", 'Hourly Imb': f"{hourly_imb_mw:+.1f}MW",
            'Strategy': f"{action}", 'Size': size
        })
    df = pd.DataFrame(data)
    column_rename_map = {'Hourly VaR': 'Var', 'Hourly Imb': 'Imb', 'Hourly Vol': 'Vol', 'LOB MW': 'LOB', 'Hour Residual': 'Residual'}
    df = df.rename(columns=column_rename_map)
    desired_order = ['Hour', 'DA€', 'ID Bid€', 'ID Offer€', 'Mid€', 'Shape', 'Var', 'Imb', 'Vol', 'LOB', 'Residual', 'Size', 'Strategy']
    df = df[desired_order]
    return df


def get_ptf_summary(var, imb, vol, ptf_var=False, imb_breach=False, vol_breach=False):
    pnl_str, pos_str = f"**P&L: €{pnl}k** / €850k", f"Pos: {pos:+d}MW"
    var_str, vol_str, imb_str = f'**VaR:** €{var:.1f}k', f'**Vol:** €{vol:.2f}', f'**Imb:** {imb:+.1f}MW'
    if ptf_var: var_str = f'<span class="blink-yellow">{var_str}</span>'
    if imb_breach: imb_str = f'<span class="blink-yellow">{imb_str}</span>'
    if vol_breach: vol_str = f'<span class="blink-yellow">{vol_str}</span>'
    return pnl_str, pos_str, var_str, imb_str, vol_str

def get_ptf_vol():
    return np.random.uniform(3, 7)

def style_dataframe(styler):
    styler.apply(lambda row: ['background-color: #0B4F6C; color: white' if '**' in str(val) else '' for val in row], subset=['Strategy'], axis=1)
    def blink_styler(row):
        styles = [''] * len(row)
        action = row['Strategy'].replace('**', '')
        if not action: return styles
        
        indices = {col: row.index.get_loc(col) for col in ['Var', 'Vol', 'Imb', 'LOB', 'Shape'] if col in row.index}
        blink_red, blink_yellow = 'color: red; font-weight: bold; animation: blinker 1s linear infinite;', 'color: yellow; font-weight: bold; animation: blinker 1s linear infinite;'
        blink_green = 'color: green; font-weight: bold; animation: blinker 1s linear infinite;'
        
        market_hour_rules = ["Shape Arb", "Iceberg", "Ladder", "Leer", "Market"]
        
        if action == "Shape Arb":
             styles[indices['Shape']] = blink_green
        elif action == "Iceberg":
            if 'Imb' in indices: styles[indices['Imb']] = blink_yellow
            if 'LOB' in indices: styles[indices['LOB']] = blink_yellow
        elif action == "Ladder":
            if 'LOB' in indices: styles[indices['LOB']] = blink_green
        elif action == "Market":
            if 'LOB' in indices: styles[indices['LOB']] = blink_red
        return styles
    styler.apply(blink_styler, axis=1)
    return styler

# === MAIN DASHBOARD ===
st.markdown("# 🏦 **Live PNL Trading Dashboard - CH ID**")
st.markdown(f"**🕐 Live Update:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S CET')} • Auto 1s refresh")

today = datetime.now()
historical_prices = fetch_historical_prices(ENTSOE_API_KEY, ENTSOE_AREA_CODE, today, days_to_fetch=30)
if historical_prices.empty and ENTSOE_API_KEY != "PASTE_YOUR_ENTSOE_API_KEY_HERE":
    st.error("Failed to fetch historical prices. The dashboard may not function correctly.")

pnl, pos, imb, ptf_var = np.random.randint(50, 120), np.random.randint(-10, 10), np.random.randint(-7, 7), np.random.uniform(35, 105)
ptf_vol = get_ptf_vol()
var_breach, imb_breach, vol_breach = ptf_var > 100, abs(imb) > 5, ptf_vol > 8
fence_active = var_breach or imb_breach or vol_breach
pnl_str, pos_str, var_str, vol_str, imb_str = get_ptf_summary(ptf_var, imb, ptf_vol, var_breach, imb_breach, vol_breach)

st.markdown("## 📈 **PTF Summary**")
cols = st.columns(6)
shape = np.random.randint(-10, 20)
leer = np.random.randint(10, 20)
ladder = np.random.randint(10, 20)
iceberg = np.random.randint(10, 20)
for col, metric in zip(cols, [pnl_str, f"MARKET €{pnl - shape - leer - ladder - iceberg}k", f"SHAPE €{shape}k", f"LEER €{leer}k", f"LADDER €{ladder}k", f"ICEBERG €{iceberg}k"]):
    col.markdown(metric, unsafe_allow_html=True)

cols = st.columns(4)
bess = np.random.randint(-10, 20)
wind = np.random.randint(-10, 20)
for col, metric in zip(cols, [pos_str, f"BESS {bess}MW", f"WIND €{wind}MW", f"SOLAR {pos - bess - wind}MW"]):
    col.markdown(metric, unsafe_allow_html=True)

cols = st.columns(3)
for col, metric in zip(cols, [var_str, vol_str, imb_str]):
    col.markdown(metric, unsafe_allow_html=True)

df = generate_live_hourly_data(fence_active, historical_prices)
st.dataframe(df.style.pipe(style_dataframe), use_container_width=True, hide_index=True, height=870)

time.sleep(1)
st.rerun()
