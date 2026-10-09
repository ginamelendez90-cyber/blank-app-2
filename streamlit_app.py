import time
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st

# ---------------------------------------------------------
# CONFIGURACIÓN DE PÁGINA
# ---------------------------------------------------------
st.set_page_config(
    page_title="Crypto Predictor Pro Engine",
    page_icon="⚡",
    layout="wide",
)

st.title("⚡ Crypto Predictor & Quantitative Engine — Modo Pro")

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
    max_value=3.5,
    value=2.0,
    step=0.1,
)

auto_refresh = st.sidebar.checkbox("Activar Auto-Refresco (1s)", value=True)

candle_limit = 150

# ---------------------------------------------------------
# 2. CONEXIÓN API Y EXTRACCIÓN DE DATOS
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
  return fetch_from_okx(symbol, interval, candle_limit)


data = get_crypto_candles(symbol, interval)

if data.empty or len(data) < 50:
  st.error("Estableciendo conexión con el servidor de datos...")
  time.sleep(1)
  st.rerun()


# ---------------------------------------------------------
# 3. MOTOR DE CÁLCULO TÉCNICO Y FUNDAMENTAL
# ---------------------------------------------------------
def build_pro_indicators(df_in):
  df = df_in.copy()

  # Medias Móviles Exponenciales (EMA)
  df["EMA_20"] = df["Close"].ewm(span=20, adjust=False).mean()
  df["EMA_50"] = df["Close"].ewm(span=50, adjust=False).mean()
  df["EMA_200"] = df["Close"].ewm(span=200, adjust=False).mean()

  # RSI (14)
  delta = df["Close"].diff()
  gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
  loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
  rs = gain / (loss + 1e-9)
  df["RSI"] = 100 - (100 / (1 + rs))

  # ATR (Average True Range)
  high_low = df["High"] - df["Low"]
  high_close = np.abs(df["High"] - df["Close"].shift())
  low_close = np.abs(df["Low"] - df["Close"].shift())
  ranges = pd.concat([high_low, high_close, low_close], axis=1)
  true_range = np.max(ranges, axis=1)
  df["ATR"] = true_range.rolling(14).mean()

  return df.dropna()


df_processed = build_pro_indicators(data)

last_row = df_processed.iloc[-1]
prev_row = df_processed.iloc[-2]

# CÁLCULO DE NIVELES TÉCNICOS AUTOMÁTICOS
max_price = df_processed["High"].max()
min_price = df_processed["Low"].min()
price_range = max_price - min_price

# Retrocesos de Fibonacci
fib_382 = max_price - (price_range * 0.382)
fib_500 = max_price - (price_range * 0.500)
fib_618 = max_price - (price_range * 0.618)

# Pivot Points Diarios
pivot = (last_row["High"] + last_row["Low"] + last_row["Close"]) / 3
r1_level = (2 * pivot) - last_row["Low"]
s1_level = (2 * pivot) - last_row["High"]

# ESTRUCTURA Y ALGORITMO DE PREDICCIÓN
score = 0

# Tendencia por EMA
if last_row["EMA_20"] > last_row["EMA_50"]:
  score += 35
else:
  score -= 35

# Filtro Macro EMA 200
if last_row["Close"] > last_row["EMA_200"]:
  score += 25
else:
  score -= 25

# Momentum RSI
if last_row["RSI"] < 35:
  score += 30
elif last_row["RSI"] > 65:
  score -= 30
else:
  if last_row["RSI"] > prev_row["RSI"]:
    score += 10
  else:
    score -= 10

# Predicción de la vela siguiente
if score >= 0:
  candle_prediction = "🟢 SUBIDA"
  is_up = True
else:
  candle_prediction = "🔴 BAJADA"
  is_up = False

entry_price = float(last_row["Close"])
atr_val = float(last_row["ATR"])

# Proyección de Volatilidad (Rango Estimado en USD y %)
expected_range_usd = atr_val * risk_reward_ratio
expected_range_pct = (expected_range_usd / entry_price) * 100

if is_up:
  take_profit = entry_price + expected_range_usd
  stop_loss = entry_price - (atr_val * 1.2)
else:
  take_profit = entry_price - expected_range_usd
  stop_loss = entry_price + (atr_val * 1.2)

confidence = min(abs(score) + 35, 96.0)

# ---------------------------------------------------------
# 4. INTERFAZ PRINCIPAL - MÉTRICAS Y FICHA OPERATIVA
# ---------------------------------------------------------
m1, m2, m3, m4 = st.columns(4)
m1.metric("Precio Mercado", f"${entry_price:,.2f}")
m2.metric("Predicción Próxima Vela", candle_prediction)
m3.metric("Rango Proyectado (ATR)", f"±${expected_range_usd:,.2f}")
m4.metric("Movimiento Estimado", f"{expected_range_pct:.2f}%")

st.markdown("---")

# Ficha de Orden Cuantitativa
t1, t2, t3, t4 = st.columns(4)
with t1:
  st.info(f"**Punto de Entrada (EP):**\n### ${entry_price:,.2f}")
with t2:
  st.success(f"**Take Profit (TP):**\n### ${take_profit:,.2f}")
with t3:
  st.error(f"**Stop Loss (SL):**\n### ${stop_loss:,.2f}")
with t4:
  st.warning(f"**Confianza Algorítmica:**\n### {confidence:.1f}%")

st.markdown("---")

# ---------------------------------------------------------
# 5. APARTADO PROFESIONAL: GRÁFICO AUTOMÁTICO DE VELAS Y LÍNEAS
# ---------------------------------------------------------
st.subheader("🎯 Análisis Técnico Profesional (Líneas e Indicadores Trazados)")

fig = go.Figure()

# Velas Japonesas
fig.add_trace(
    go.Candlestick(
        x=df_processed.index,
        open=df_processed["Open"],
        high=df_processed["High"],
        low=df_processed["Low"],
        close=df_processed["Close"],
        name="Precio OHLC",
    )
)

# Trazado de Medias Móviles Exponenciales (EMAs)
fig.add_trace(
    go.Scatter(
        x=df_processed.index,
        y=df_processed["EMA_20"],
        line=dict(color="yellow", width=1.2),
        name="EMA 20",
    )
)
fig.add_trace(
    go.Scatter(
        x=df_processed.index,
        y=df_processed["EMA_50"],
        line=dict(color="orange", width=1.2),
        name="EMA 50",
    )
)
fig.add_trace(
    go.Scatter(
        x=df_processed.index,
        y=df_processed["EMA_200"],
        line=dict(color="purple", width=1.5),
        name="EMA 200 (Macro)",
    )
)

# Líneas automáticas de Niveles Clave (Soporte, Resistencia y Fib 61.8%)
fig.add_hline(
    y=max_price,
    line_dash="dash",
    line_color="red",
    annotation_text=f"Resistencia Max: ${max_price:,.2f}",
)
fig.add_hline(
    y=min_price,
    line_dash="dash",
    line_color="green",
    annotation_text=f"Soporte Min: ${min_price:,.2f}",
)
fig.add_hline(
    y=fib_618,
    line_dash="dot",
    line_color="cyan",
    annotation_text=f"Fibonacci 61.8%: ${fib_618:,.2f}",
)

# Líneas dinámicas de la Operación (TP y SL)
fig.add_hline(
    y=take_profit,
    line_color="#00FF00",
    line_width=2,
    annotation_text=f"TARGET TP: ${take_profit:,.2f}",
)
fig.add_hline(
    y=stop_loss,
    line_color="#FF0000",
    line_width=2,
    annotation_text=f"STOP SL: ${stop_loss:,.2f}",
)

fig.update_layout(
    template="plotly_dark",
    xaxis_rangeslider_visible=False,
    height=550,
    margin=dict(l=10, r=10, t=30, b=10),
)

st.plotly_chart(fig, use_container_width=True)

# ---------------------------------------------------------
# 6. APARTADO FUNDAMENTAL & ESTRUCTURAL AUTOMÁTICO
# ---------------------------------------------------------
st.subheader("🏛️ Módulo de Análisis Fundamental y Contexto Macro")

col_f1, col_f2, col_f3 = st.columns(3)

with col_f1:
  macro_bias = (
      "BULLISH (ALCISTA)"
      if entry_price > last_row["EMA_200"]
      else "BEARISH (BAJISTA)"
  )
  st.markdown(f"**Sesgo Macro (EMA 200):**\n#### {macro_bias}")
  st.caption("Determina la tendencia dominante de fondo en el mercado.")

with col_f2:
  volatility_status = (
      "ALTA VOLATILIDAD"
      if atr_val > df_processed["ATR"].mean()
      else "BAJA VOLATILIDAD / CONSOLIDACIÓN"
  )
  st.markdown(f"**Estado de Volatilidad (ATR):**\n#### {volatility_status}")
  st.caption("Evalúa si hay expansión o contracción de rango de precio.")

with col_f3:
  fib_zone = (
      "Cerca de Zona de Reacción Fib 61.8%"
      if abs(entry_price - fib_618) < (atr_val * 2)
      else "Sin nivel Fibonacci Inmediato"
  )
  st.markdown(f"**Estructura Fibonacci:**\n#### {fib_zone}")
  st.caption("Identifica si el precio cotiza en niveles de retroceso institucional.")

# ---------------------------------------------------------
# 7. CICLO DE AUTO-REFRESCO
# ---------------------------------------------------------
if auto_refresh:
  time.sleep(1)
  st.rerun()
