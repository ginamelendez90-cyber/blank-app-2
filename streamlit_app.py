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

st.title("🤖 Predictor Automático Cripto (Vía KuCoin API)")

# ---------------------------------------------------------
# 1. PARÁMETROS EN LA BARRA LATERAL
# ---------------------------------------------------------
st.sidebar.header("⚙️ Configuración del Par")

# Pares compatibles con KuCoin (formato BASE-QUOTE)
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

candle_limit = st.sidebar.slider(
    "Cantidad de Velas Históricas",
    min_value=100,
    max_value=500,
    value=300,
    step=50,
)


# ---------------------------------------------------------
# 2. EXTRACCIÓN DE DATOS DESDE KUCOIN (SIN GEOBLOQUEO)
# ---------------------------------------------------------
@st.cache_data(ttl=120, show_spinner=False)
def get_kucoin_klines(symbol: str, interval: str, limit: int = 300):
  """Obtiene datos históricos desde la API pública de KuCoin (Sin geobloqueo de AWS/Streamlit Cloud)."""
  # Mapeo de temporalidades de KuCoin
  kline_map = {
      "5m": "5min",
      "15m": "15min",
      "1h": "1hour",
      "4h": "4hour",
      "1d": "1day",
  }
  kc_interval = kline_map.get(interval, "15min")

  url = f"https://api.kucoin.com/api/1/market/candles?symbol={symbol}&type={kc_interval}"

  try:
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers, timeout=10)

    if response.status_code != 200:
      st.error(f"Error {response.status_code} al consultar la API de KuCoin.")
      return pd.DataFrame()

    raw_data = response.json().get("data", [])
    if not raw_data:
      return pd.DataFrame()

    # Formato devuelto por KuCoin: [time, open, close, high, low, volume, turnover]
    cols = ["time", "Open", "Close", "High", "Low", "Volume", "Turnover"]
    df = pd.DataFrame(raw_data, columns=cols)

    # Convertir tiempo UNIX a fechas
    df["Date"] = pd.to_datetime(df["time"].astype(int), unit="s")
    df.set_index("Date", inplace=True)
    df.sort_index(inplace=True)

    # Convertir valores a float
    for col in ["Open", "High", "Low", "Close", "Volume"]:
      df[col] = df[col].astype(float)

    return df[["Open", "High", "Low", "Close", "Volume"]].tail(limit)

  except Exception as e:
    st.error(f"Error de conexión con la API: {e}")
    return pd.DataFrame()


with st.spinner(f"Cargando velas de {symbol} desde KuCoin..."):
  data = get_kucoin_klines(symbol, interval, candle_limit)

if data.empty or len(data) < 40:
  st.warning(
      "No se pudieron obtener suficientes datos de la API. Intenta de nuevo en"
      " unos instantes."
  )
  st.stop()


# ---------------------------------------------------------
# 3. INDICADORES TÉCNICOS Y ESTRATEGIA CUANTITATIVA
# ---------------------------------------------------------
def build_analysis(df_in):
  df = df_in.copy()

  # Medias Móviles Simples (SMA)
  df["SMA_10"] = df["Close"].rolling(window=10).mean()
  df["SMA_30"] = df["Close"].rolling(window=30).mean()

  # Índice de Fuerza Relativa (RSI 14)
  delta = df["Close"].diff()
  gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
  loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
  rs = gain / (loss + 1e-9)
  df["RSI"] = 100 - (100 / (1 + rs))

  # Volatilidad
  df["Returns"] = df["Close"].pct_change()
  df["Volatility"] = df["Returns"].rolling(window=10).std()

  return df.dropna()


df_processed = build_analysis(data)

# ---------------------------------------------------------
# 4. MOTOR DE PREDICCIÓN ALGORÍTMICA
# ---------------------------------------------------------
last_row = df_processed.iloc[-1]
prev_row = df_processed.iloc[-2]

score = 0

# Regla 1: Cruce de Medias Móviles (Tendencia)
if last_row["SMA_10"] > last_row["SMA_30"]:
  score += 40
else:
  score -= 40

# Regla 2: Niveles de Momentum RSI
if last_row["RSI"] < 35:
  score += 35  # Sobrevendido -> Probable alza
elif last_row["RSI"] > 65:
  score -= 3
