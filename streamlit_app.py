import numpy as np
import pandas as pd
import requests
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score
import streamlit as st

st.set_page_config(
    page_title="Crypto Predictor Bot", page_icon="🤖", layout="wide"
)
st.title("🤖 Predictor Automático Cripto (Vía Binance API)")

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
candle_limit = st.sidebar.slider(
    "Velas Históricas", min_value=200, max_value=1000, value=500, step=100
)


# 2. EXTRACCIÓN DE DATOS
@st.cache_data(ttl=120, show_spinner=False)
def get_binance_klines(symbol: str, interval: str, limit: int = 500):
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
  data = get_binance_klines(symbol, interval, candle_limit)

if data.empty or len(data) < 60:
  st.warning("Sin datos suficientes de la API.")
  st.stop()


# 3. INDICADORES
def build_features(df_in):
  df = df_in.copy()
  df["Returns"] = df["Close"].pct_change()
  df["Volatility"] = df["Returns"].rolling(window=10).std()
  df["SMA_10"] = df["Close"].rolling(window=10).mean()
  df["SMA_30"] = df["Close"].rolling(window=30).mean()
  df["SMA_Ratio"] = df["SMA_10"] / df["SMA_30"]

  delta = df["Close"].diff()
  gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
  loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
  rs = gain / (loss + 1e-9)
  df["RSI"] = 100 - (100 / (1 + rs))
  df["Target"] = (df["Close"].shift(-1) > df["Close"]).astype(int)
  return df.dropna()


df_processed = build_features(data)

# 4. ENTRENAMIENTO
feature_cols = ["Returns", "Volatility", "SMA_Ratio", "RSI"]
X = df_processed[feature_cols]
y = df_processed["Target"]

train_size = int(len(X) * 0.8)
X_train, X_test = X.iloc[:train_size], X.iloc[train_size:-1]
y_train, y_test = y.iloc[:train_size], y.iloc[train_size:-1]

model = RandomForestClassifier(n_estimators=100, max_depth=5, random_state=42)
model.fit(X_train, y_train)

acc = accuracy_score(y_test, model.predict(X_test)) if len(y_test) > 0 else 0.0
latest_features = X.iloc[[-1]]
prediction = model.predict(latest_features)[0]
probabilities = model.predict_proba(latest_features)[0]

# 5. INTERFAZ
col1, col2, col3, col4 = st.columns(4)
col1.metric("Precio Actual", f"${data['Close'].iloc[-1]:,.2f}")
col2.metric(
    "Predicción Próxima Vela", "🟢 SUBIDA" if prediction == 1 else "🔴 BAJADA"
)
col3.metric("Confianza Subida", f"{probabilities[1]*100:.1f}%")
col4.metric("Precisión (Test)", f"{acc * 100:.1f}%")

st.markdown("---")

# Gráfico nativo de Streamlit (sin Plotly)
st.subheader(f"Evolución de Precio — {symbol}")
st.line_chart(data["Close"])

st.subheader("📊 Peso de cada Indicador")
importance_df = pd.DataFrame({
    "Indicador": feature_cols,
    "Importancia": model.feature_importances_,
}).sort_values("Importancia", ascending=False)
st.bar_chart(importance_df.set_index("Indicador"))
