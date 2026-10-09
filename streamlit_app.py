import time
import numpy as np
import pandas as pd
import requests
import streamlit as st

# Configuración de página
st.set_page_config(
    page_title="Crypto Predictor Bot",
    page_icon="🤖",
    layout="wide",
)

st.title("🤖 Predictor Automático Cripto (En Tiempo Real - 1s)")

# ---------------------------------------------------------
# 1. PARÁMETROS EN LA BARRA LATERAL
# ---------------------------------------------------------
st.sidebar.header("⚙️ Configuración del Par")

pair_options = {
    "Bitcoin (BTC/USDT)": "BTC-USDT",
    "Ethereum (ETH/USDT)": "ETH-USDT",
    "Solana (SOL/USDT)": "SOL-USDT",
    "BNB (BNB/USDT)": "BNB-USDT",
    "Ripple (XRP/USDT)": "XRP-USDT",
}

selected_label = st.sidebar.selectbox(
    "Criptomoneda Base", list(pair_options.keys())
)
symbol = pair_options[selected_label]

interval = st.sidebar.selectbox(
    "Temporalidad de Velas", ["5m", "15m", "1h", "4h", "1d"], index=1
)

auto_refresh = st.sidebar.checkbox("Activar auto-refresco (1s)", value=True)

candle_limit = 150

# ---------------------------------------------------------
# 2. SISTEMA DE EXTRACCIÓN CON CACHÉ DE 1 SEGUNDO
# ---------------------------------------------------------
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML,"
        " like Gecko) Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
}


def fetch_from_okx(symbol: str, interval: str, limit: int):
  interval_map = {"5m": "5m", "15m": "15m", "1h": "1H", "4h": "4H", "1d": "1Dutc"}
  bar = interval_map.get(interval, "15m")

  url = f"https://www.okx.com/api/v5/market/candles?instId={symbol}&bar={bar}&limit={limit}"
  try:
    response = requests.get(url, headers=HEADERS, timeout=3)
    if response.status_code == 200:
      data = response.json().get("data", [])
      if data:
        cols = [
            "time",
            "Open",
            "High",
            "Low",
            "Close",
            "Volume",
            "v2",
            "v3",
            "c",
        ]
        df = pd.DataFrame(data, columns=cols)
        df["Date"] = pd.to_datetime(df["time"].astype(int), unit="ms")
        df.set_index("Date", inplace=True)
        df.sort_index(inplace=True)
        for col in ["Open", "High", "Low", "Close", "Volume"]:
          df[col] = df[col].astype(float)
        return df[["Open", "High", "Low", "Close", "Volume"]], "OKX"
  except Exception:
    pass
  return pd.DataFrame(), None


# Caché ajustado a 1 segundo para refrescar precios al instante
@st.cache_data(ttl=1, show_spinner=False)
def get_crypto_candles(symbol: str, interval: str, limit: int = 150):
  df, source = fetch_from_okx(symbol, interval, limit)
  return df, source


data, active_source = get_crypto_candles(symbol, interval, candle_limit)

if data.empty or len(data) < 20:
  st.error("Conectando con la API...")
  time.sleep(1)
  st.rerun()


# ---------------------------------------------------------
# 3. INDICADORES Y PREDICCIÓN ALGORÍTMICA
# ---------------------------------------------------------
def build_analysis(df_in):
  df = df_in.copy()
  df["SMA_10"] = df["Close"].rolling(window=10).mean()
  df["SMA_30"] = df["Close"].rolling(window=30).mean()

  delta = df["Close"].diff()
  gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
  loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
  rs = gain / (loss + 1e-9)
  df["RSI"] = 100 - (100 / (1 + rs))
  return df.dropna()


df_processed = build_analysis(data)

last_row = df_processed.iloc[-1]
prev_row = df_processed.iloc[-2]

score = 0
if last_row["SMA_10"] > last_row["SMA_30"]:
  score += 40
else:
  score -= 40

if last_row["RSI"] < 35:
  score += 35
elif last_row["RSI"] > 65:
  score -= 35
else:
  if last_row["RSI"] > prev_row["RSI"]:
    score += 15
  else:
    score -= 15

prediction = 1 if score >= 0 else 0
confidence = min(abs(score) + 40, 95.0)

# ---------------------------------------------------------
# 4. DASHBOARD E INTERFAZ
# ---------------------------------------------------------
current_price = float(last_row["Close"])

col1, col2, col3, col4 = st.columns(4)
col1.metric("Precio Actual", f"${current_price:,.2f}")
col2.metric(
    "Predicción Próxima Vela", "🟢 SUBIDA" if prediction == 1 else "🔴 BAJADA"
)
col3.metric("Confianza de Señal", f"{confidence:.1f}%")
col4.metric("Última Actualización", time.strftime("%H:%M:%S"))

st.markdown("---")

st.subheader(f"📈 Tendencia en Tiempo Real — {symbol}")
st.line_chart(df_processed[["Close", "SMA_10", "SMA_30"]])

st.subheader("📊 Indicador RSI")
st.line_chart(df_processed["RSI"])

# ---------------------------------------------------------
# 5. REFRESEO AUTOMÁTICO CADA 1 SEGUNDO
# ---------------------------------------------------------
if auto_refresh:
  time.sleep(1)
  st.rerun()
