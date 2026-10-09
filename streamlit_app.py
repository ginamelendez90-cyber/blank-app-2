import time
import numpy as np
import pandas as pd
import requests
import streamlit as st

# Configuración de página
st.set_page_config(
    page_title="Crypto Signal & Candle Predictor",
    page_icon="🎯",
    layout="wide",
)

st.title("🎯 Predictor de Próxima Vela y Ficha de Operación (1s)")

# ---------------------------------------------------------
# 1. BARRA LATERAL: PARÁMETROS Y GESTIÓN DE RIESGO
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

st.sidebar.header("🛡️ Gestión de Riesgo (ATR)")
risk_reward_ratio = st.sidebar.slider(
    "Ratio Riesgo / Beneficio (R:R)",
    min_value=1.0,
    max_value=3.0,
    value=1.5,
    step=0.1,
)

auto_refresh = st.sidebar.checkbox("Activar auto-refresco (1s)", value=True)

# ---------------------------------------------------------
# 2. EXTRACCIÓN DE DATOS DE MERCADO
# ---------------------------------------------------------
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML,"
        " like Gecko) Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
}


def fetch_from_okx(symbol: str, interval: str, limit: int = 150):
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
        return df[["Open", "High", "Low", "Close", "Volume"]]
  except Exception:
    pass
  return pd.DataFrame()


@st.cache_data(ttl=1, show_spinner=False)
def get_crypto_candles(symbol: str, interval: str):
  return fetch_from_okx(symbol, interval)


data = get_crypto_candles(symbol, interval)

if data.empty or len(data) < 30:
  st.error("Conectando con la API de mercado...")
  time.sleep(1)
  st.rerun()


# ---------------------------------------------------------
# 3. INDICADORES, PREDICCIÓN DE VELA Y ATR
# ---------------------------------------------------------
def build_indicators(df_in):
  df = df_in.copy()

  # Medias Móviles
  df["SMA_10"] = df["Close"].rolling(window=10).mean()
  df["SMA_30"] = df["Close"].rolling(window=30).mean()

  # RSI (14)
  delta = df["Close"].diff()
  gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
  loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
  rs = gain / (loss + 1e-9)
  df["RSI"] = 100 - (100 / (1 + rs))

  # ATR (Volatilidad real en USD)
  high_low = df["High"] - df["Low"]
  high_close = np.abs(df["High"] - df["Close"].shift())
  low_close = np.abs(df["Low"] - df["Close"].shift())
  ranges = pd.concat([high_low, high_close, low_close], axis=1)
  true_range = np.max(ranges, axis=1)
  df["ATR"] = true_range.rolling(14).mean()

  return df.dropna()


df_processed = build_indicators(data)

last_row = df_processed.iloc[-1]
prev_row = df_processed.iloc[-2]

# Criterio de Puntuación
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

# --- PREDICCIÓN DE LA PRÓXIMA VELA ---
if score >= 0:
  candle_prediction = "🟢 SUBIDA"
  is_up = True
else:
  candle_prediction = "🔴 BAJADA"
  is_up = False

entry_price = float(last_row["Close"])
atr_val = float(last_row["ATR"])

# Rango estimado que subirá o bajará la vela según volatilidad (ATR)
expected_range_usd = atr_val * risk_reward_ratio
expected_range_pct = (expected_range_usd / entry_price) * 100

# Cálculo de Stop Loss y Take Profit
if is_up:
  take_profit = entry_price + expected_range_usd
  stop_loss = entry_price - atr_val
else:
  take_profit = entry_price - expected_range_usd
  stop_loss = entry_price + atr_val

confidence = min(abs(score) + 40, 95.0)

# ---------------------------------------------------------
# 4. DASHBOARD DE PREDICCIÓN Y OPERACIÓN
# ---------------------------------------------------------
m1, m2, m3, m4 = st.columns(4)
m1.metric("Precio Actual", f"${entry_price:,.2f}")
m2.metric("Predicción Próxima Vela", candle_prediction)
m3.metric("Rango Estimado del Movimiento", f"±${expected_range_usd:,.2f}")
m4.metric("Porcentaje Estimado", f"{expected_range_pct:.2f}%")

st.markdown("---")

st.subheader("📋 Parámetros Exactos para Entrar a Operar")

t1, t2, t3, t4 = st.columns(4)

with t1:
  st.info(f"**Punto de Entrada (EP):**\n### ${entry_price:,.2f}")

with t2:
  st.success(f"**Take Profit (TP / Objetivo):**\n### ${take_profit:,.2f}")

with t3:
  st.error(f"**Stop Loss (SL / Límite):**\n### ${stop_loss:,.2f}")

with t4:
  st.warning(f"**Confianza de la Señal:**\n### {confidence:.1f}%")

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
