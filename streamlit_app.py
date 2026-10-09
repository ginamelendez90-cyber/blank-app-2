import numpy as np
import pandas as pd
import plotly.graph_objects as go
import requests
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score
import streamlit as st

# Configuración de página
st.set_page_config(
    page_title="Crypto Predictor Bot (Binance)",
    page_icon="🤖",
    layout="wide",
)
st.title("🤖 Predictor Automático Cripto (Vía Binance API)")

# ---------------------------------------------------------
# 1. PARÁMETROS EN LA BARRA LATERAL
# ---------------------------------------------------------
st.sidebar.header("⚙️ Configuración del Par")

# Binance utiliza pares directos tipo BTCUSDT, ETHUSDT, etc.
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
    min_value=200,
    max_value=1000,
    value=500,
    step=100,
)


# ---------------------------------------------------------
# 2. EXTRACCIÓN DE DATOS DESDE BINANCE CON CACHÉ
# ---------------------------------------------------------
@st.cache_data(ttl=120, show_spinner=False)
def get_binance_klines(symbol: str, interval: str, limit: int = 500):
  """Obtiene datos OHLCV desde el endpoint público de Binance Klines."""
  url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"

  try:
    response = requests.get(url, timeout=10)
    if response.status_code != 200:
      st.error(
          f"Error {response.status_code} al conectar con Binance API:"
          f" {response.text}"
      )
      return pd.DataFrame()

    raw_data = response.json()

    # Columnas según la documentación oficial de la API de Binance
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

    df = pd.DataFrame(raw_data, columns=cols)

    # Convertir marcas de tiempo a fechas
    df["Date"] = pd.to_datetime(df["Open_time"], unit="ms")
    df.set_index("Date", inplace=True)

    # Convertir columnas numéricas de string a float
    numeric_cols = ["Open", "High", "Low", "Close", "Volume"]
    for col in numeric_cols:
      df[col] = df[col].astype(float)

    return df[numeric_cols]

  except Exception as e:
    st.error(f"Error de conexión: {e}")
    return pd.DataFrame()


with st.spinner(f"Cargando velas de {symbol} desde Binance..."):
  data = get_binance_klines(symbol, interval, candle_limit)

if data.empty or len(data) < 60:
  st.warning(
      "No hay suficientes datos disponibles para procesar los indicadores."
  )
  st.stop()


# ---------------------------------------------------------
# 3. INGENIERÍA DE CARACTERÍSTICAS (INDICADORES TÉCNICOS)
# ---------------------------------------------------------
def build_features(df_in):
  df = df_in.copy()

  # Rendimiento porcentual y volatilidad
  df["Returns"] = df["Close"].pct_change()
  df["Volatility"] = df["Returns"].rolling(window=10).std()

  # Medias Móviles Simples (SMA)
  df["SMA_10"] = df["Close"].rolling(window=10).mean()
  df["SMA_30"] = df["Close"].rolling(window=30).mean()
  df["SMA_Ratio"] = df["SMA_10"] / df["SMA_30"]

  # RSI (Relative Strength Index - 14 periodos)
  delta = df["Close"].diff()
  gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
  loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
  rs = gain / (loss + 1e-9)
  df["RSI"] = 100 - (100 / (1 + rs))

  # Variable Objetivo: 1 si la próxima vela cierra arriba, 0 si cierra abajo
  df["Target"] = (df["Close"].shift(-1) > df["Close"]).astype(int)

  return df.dropna()


df_processed = build_features(data)

# ---------------------------------------------------------
# 4. ENTRENAMIENTO DEL MODELO (SPLIT CRONOLÓGICO)
# ---------------------------------------------------------
feature_cols = ["Returns", "Volatility", "SMA_Ratio", "RSI"]
X = df_processed[feature_cols]
y = df_processed["Target"]

# División sin aleatoriedad (80% entrenamiento, 20% prueba)
train_size = int(len(X) * 0.8)
X_train, X_test = X.iloc[:train_size], X.iloc[train_size:-1]
y_train, y_test = y.iloc[:train_size], y.iloc[train_size:-1]

model = RandomForestClassifier(n_estimators=100, max_depth=5, random_state=42)
model.fit(X_train, y_train)

# Evaluación
y_pred = model.predict(X_test)
acc = accuracy_score(y_test, y_pred) if len(y_test) > 0 else 0.0

# Predicción para la vela actual (en tiempo real)
latest_features = X.iloc[[-1]]
prediction = model.predict(latest_features)[0]
probabilities = model.predict_proba(latest_features)[0]

# ---------------------------------------------------------
# 5. DASHBOARD E INTERFAZ GRÁFICA
# ---------------------------------------------------------
current_price = float(data["Close"].iloc[-1])
prob_up = probabilities[1] * 100
prob_down = probabilities[0] * 100

col1, col2, col3, col4 = st.columns(4)
col1.metric("Precio Actual", f"${current_price:,.2f}")
col2.metric(
    "Predicción Próxima Vela", "🟢 SUBIDA" if prediction == 1 else "🔴 BAJADA"
)
col3.metric("Confianza de Subida", f"{prob_up:.1f}%")
col4.metric("Precisión del Modelo (Test)", f"{acc * 100:.1f}%")

st.markdown("---")

# Gráfico interactivo con Plotly
fig = go.Figure()
fig.add_trace(
    go.Candlestick(
        x=data.index,
        open=data["Open"],
        high=data["High"],
        low=data["Low"],
        close=data["Close"],
        name=symbol,
    )
)
fig.update_layout(
    title=f"Gráfico de Velas Japonesas — {symbol} ({interval})",
    xaxis_rangeslider_visible=False,
    height=480,
    template="plotly_dark",
)
st.plotly_chart(fig, use_container_width=True)

# Importancia de las variables
st.subheader("📊 Peso de cada Indicador en la Predicción")
importance_df = pd.DataFrame({
    "Indicador": feature_cols,
    "Importancia": model.feature_importances_,
}).sort_values("Importancia", ascending=False)

st.bar_chart(importance_df.set_index("Indicador"))
