import numpy as np
import pandas as pd
import requests
import streamlit as st

st.set_page_config(
    page_title="Crypto Predictor Bot", page_icon="🤖", layout="wide"
)
st.title("🤖 Predictor Automático Cripto (Algoritmo Cuantitativo)")

# 1. PARÁMETROS EN LA BARRA LATERAL
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


# 2. EXTRACCIÓN DE DATOS
@st.cache_data(ttl=120, show_spinner=False)
def get_binance_klines(symbol: str, interval: str, limit: int = 300):
  url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
  try:
    response = requests.get(url, timeout=10)
    if response.status_code != 200:
      return pd.DataFrame()
    cols = [
        "Open_time",
        "Open",
        "High",
        "Low",
        "Close",
        "Volume",
        "Close_time",
        "Quote_volume",
        "Trades",
        "Taker_buy_base",
        "Taker_buy_quote",
        "Ignore",
    ]
    df = pd.DataFrame(response.json(), columns=cols)
    df["Date"] = pd.to_datetime(df["Open_time"], unit="ms")
    df.set_index("Date", inplace=True)
    for col in ["Open", "High", "Low", "Close", "Volume"]:
      df[col] = df[col].astype(float)
    return df[["Open", "High", "Low", "Close", "Volume"]]
  except Exception:
    return pd.DataFrame()


with st.spinner("Cargando datos desde Binance..."):
  data = get_binance_klines(symbol, interval)

if data.empty:
  st.warning("No se pudieron obtener los datos de la API.")
  st.stop()

# 3. INDICADORES Y PREDICCIÓN ALGORÍTMICA (SIN SKLEARN)
df = data.copy()
df["SMA_10"] = df["Close"].rolling(window=10).mean()
df["SMA_30"] = df["Close"].rolling(window=30).mean()

delta = df["Close"].diff()
gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
rs = gain / (loss + 1e-9)
df["RSI"] = 100 - (100 / (1 + rs))

# Cálculo de Puntuación Cuantitativa (-100 a +100)
last_row = df.iloc[-1]
score = 0

# Regla 1: Tendencia por Medias Móviles
if last_row["SMA_10"] > last_row["SMA_30"]:
  score += 50
else:
  score -= 50

# Regla 2: Momentum por RSI
if last_row["RSI"] < 30:
  score += 40  # Sobrevendido (Probable rebote al alza)
elif last_row["RSI"] > 70:
  score -= 40  # Sobrecomprado (Probable corrección a la baja)

# Predicción final
prediction = 1 if score >= 0 else 0
confidence = min(abs(score) + 50, 95)

# 4. INTERFAZ GRÁFICA
col1, col2, col3 = st.columns(3)
col1.metric("Precio Actual", f"${last_row['Close']:,.2f}")
col2.metric(
    "Predicción Próxima Vela", "🟢 SUBIDA" if prediction == 1 else "🔴 BAJADA"
)
col3.metric("Confianza del Algoritmo", f"{confidence:.1f}%")

st.markdown("---")
st.subheader(f"Evolución de Precio — {symbol}")
st.line_chart(df[["Close", "SMA_10", "SMA_30"]])
