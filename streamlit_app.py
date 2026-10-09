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

st.title("🤖 Predictor Automático Cripto (Vía Bybit API)")

# ---------------------------------------------------------
# 1. PARÁMETROS EN LA BARRA LATERAL
# ---------------------------------------------------------
st.sidebar.header("⚙️ Configuración del Par")

pair_options = {
    "Bitcoin (BTC/USDT)": "BTCUSDT",
    "Ethereum (ETH/USDT)": "ETHUSDT",
    "Solana (SOL/USDT)": "SOLUSDT",
    "BNB (BNB/USDT)": "BNBUSDT",
    "Ripple (XRP/USDT)": "XRPUSDT",
}

selected_label = st.sidebar.selectbox(
    "Criptomoneda Base", list(pair_options.keys())
)
symbol = pair_options[selected_label]

interval = st.sidebar.selectbox(
    "Temporalidad de Velas", ["5m", "15m", "1h", "4h", "1d"], index=1
)

candle_limit = st.sidebar.slider(
    "Cantidad de Velas Históricas",
    min_value=100,
    max_value=500,
    value=200,
    step=50,
)


# ---------------------------------------------------------
# 2. EXTRACCIÓN DE DATOS DESDE BYBIT (API V5 NATIVA)
# ---------------------------------------------------------
@st.cache_data(ttl=120, show_spinner=False)
def get_bybit_klines(symbol: str, interval: str, limit: int = 200):
  """Obtiene datos OHLCV desde el endpoint v5 público de Bybit."""
  # Mapeo de intervalos Bybit v5: 5, 15, 60, 240, D
  interval_map = {"5m": "5", "15m": "15", "1h": "60", "4h": "240", "1d": "D"}
  bybit_interval = interval_map.get(interval, "15")

  url = f"https://api.bybit.com/v5/market/kline?category=spot&symbol={symbol}&interval={bybit_interval}&limit={limit}"

  try:
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers, timeout=10)

    if response.status_code != 200:
      st.error(f"Error {response.status_code} al consultar Bybit API.")
      return pd.DataFrame()

    json_data = response.json()
    raw_list = json_data.get("result", {}).get("list", [])

    if not raw_list:
      st.error("No se encontraron velas para este par.")
      return pd.DataFrame()

    # Formato Bybit v5: [startTime, openPrice, highPrice, lowPrice, closePrice, volume, turnover]
    cols = ["time", "Open", "High", "Low", "Close", "Volume", "Turnover"]
    df = pd.DataFrame(raw_list, columns=cols)

    # Convertir tiempo UNIX (ms) a fechas
    df["Date"] = pd.to_datetime(df["time"].astype(int), unit="ms")
    df.set_index("Date", inplace=True)
    df.sort_index(inplace=True)

    # Convertir a flotantes
    for col in ["Open", "High", "Low", "Close", "Volume"]:
      df[col] = df[col].astype(float)

    return df[["Open", "High", "Low", "Close", "Volume"]]

  except Exception as e:
    st.error(f"Error de conexión con la API: {e}")
    return pd.DataFrame()


with st.spinner(f"Cargando datos de {symbol} desde Bybit..."):
  data = get_bybit_klines(symbol, interval, candle_limit)

if data.empty or len(data) < 30:
  st.warning("No se pudieron obtener suficientes datos de la API.")
  st.stop()


# ---------------------------------------------------------
# 3. INDICADORES TÉCNICOS Y ANÁLISIS
# ---------------------------------------------------------
def build_analysis(df_in):
  df = df_in.copy()

  # Medias Móviles Simples (SMA)
  df["SMA_10"] = df["Close"].rolling(window=10).mean()
  df["SMA_30"] = df["Close"].rolling(window=30).mean()

  # RSI (14 periodos)
  delta = df["Close"].diff()
  gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
  loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
  rs = gain / (loss + 1e-9)
  df["RSI"] = 100 - (100 / (1 + rs))

  return df.dropna()


df_processed = build_analysis(data)

# ---------------------------------------------------------
# 4. PREDICCIÓN ALGORÍTMICA
# ---------------------------------------------------------
last_row = df_processed.iloc[-1]
prev_row = df_processed.iloc[-2]

score = 0

# Criterio 1: Tendencia por Medias Móviles
if last_row["SMA_10"] > last_row["SMA_30"]:
  score += 40
else:
  score -= 40

# Criterio 2: Momentum por RSI
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
# 5. DASHBOARD E INTERFAZ
# ---------------------------------------------------------
current_price = float(last_row["Close"])

col1, col2, col3, col4 = st.columns(4)
col1.metric("Precio Actual", f"${current_price:,.2f}")
col2.metric(
    "Predicción Próxima Vela", "🟢 SUBIDA" if prediction == 1 else "🔴 BAJADA"
)
col3.metric("Confianza de Señal", f"{confidence:.1f}%")
col4.metric("RSI Actual", f"{last_row['RSI']:.1f}")

st.markdown("---")

st.subheader(f"📈 Tendencia del Precio y Medias Móviles — {symbol}")
st.line_chart(df_processed[["Close", "SMA_10", "SMA_30"]])

st.subheader("📊 Indicador RSI")
st.line_chart(df_processed["RSI"])
