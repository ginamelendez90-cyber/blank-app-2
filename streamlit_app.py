import datetime
import time
import numpy as np
import pandas as pd
import requests
import streamlit as st

# ---------------------------------------------------------
# CONFIGURACIÓN DE PÁGINA
# ---------------------------------------------------------
st.set_page_config(
    page_title="Crypto Predictor Pro Engine - Whale Tracker",
    page_icon="🐋",
    layout="wide",
)

st.title("🐋 Crypto Predictor & Detector de Ballenas (Optimizado)")

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
    "Temporalidad de Velas", ["5m", "15m", "1h", "4h"], index=1
)

st.sidebar.header("🛡️ Filtros de Ballenas & Riesgo")
min_whale_usd = st.sidebar.slider(
    "Tamaño Mínimo de Ballena (USD)",
    min_value=5000,
    max_value=100000,
    value=10000,
    step=5000,
)
risk_reward_ratio = st.sidebar.slider(
    "Ratio Riesgo / Beneficio (R:R)",
    min_value=1.0,
    max_value=3.5,
    value=2.5,
    step=0.1,
)

auto_refresh = st.sidebar.checkbox("Activar Auto-Refresco (1s)", value=True)
candle_limit = 150

# ---------------------------------------------------------
# 2. CONEXIÓN API Y EXTRACCIÓN DE DATOS DE MERCADO
# ---------------------------------------------------------
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML,"
        " like Gecko) Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
}


def fetch_from_okx(symbol: str, interval: str, limit: int = 150):
  interval_map = {"5m": "5m", "15m": "15m", "1h": "1H", "4h": "4H"}
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


def fetch_whale_trades(symbol: str, min_usd: float):
  # Aumentamos el límite a 300 para capturar más historial de transacciones en vivo
  url = f"https://www.okx.com/api/v5/market/trades?instId={symbol}&limit=300"
  try:
    response = requests.get(url, headers=HEADERS, timeout=3)
    if response.status_code == 200:
      trades_data = response.json().get("data", [])
      if trades_data:
        df_trades = pd.DataFrame(
            trades_data, columns=["tradeId", "Price", "Size", "Side", "Time"]
        )
        df_trades["Price"] = df_trades["Price"].astype(float)
        df_trades["Size"] = df_trades["Size"].astype(float)
        df_trades["Total_USD"] = df_trades["Price"] * df_trades["Size"]
        df_trades["Hora"] = pd.to_datetime(
            df_trades["Time"].astype(int), unit="ms"
        ).dt.strftime("%H:%M:%S")

        whales = df_trades[df_trades["Total_USD"] >= min_usd]
        return whales[["Hora", "Side", "Price", "Size", "Total_USD"]]
  except Exception:
    pass
  return pd.DataFrame()


@st.cache_data(ttl=1, show_spinner=False)
def get_crypto_candles(symbol: str, interval: str):
  return fetch_from_okx(symbol, interval, candle_limit)


data = get_crypto_candles(symbol, interval)
whale_df = fetch_whale_trades(symbol, min_whale_usd)

if data.empty or len(data) < 50:
  st.error("Estableciendo conexión con el servidor de datos...")
  time.sleep(1)
  st.rerun()


# ---------------------------------------------------------
# 3. CÁLCULO DE TIEMPO RESTANTE DE LA VELA ACTUAL
# ---------------------------------------------------------
def get_candle_countdown(interval_str):
  interval_minutes = {"5m": 5, "15m": 15, "1h": 60, "4h": 240}
  duration_mins = interval_minutes.get(interval_str, 15)
  duration_seconds = duration_mins * 60

  now = datetime.datetime.now(datetime.timezone.utc)
  epoch_seconds = now.timestamp()
  seconds_into_candle = epoch_seconds % duration_seconds
  seconds_remaining = int(duration_seconds - seconds_into_candle)

  hours_left = seconds_remaining // 3600
  mins_left = (seconds_remaining % 3600) // 60
  secs_left = seconds_remaining % 60

  if hours_left > 0:
    return f"{hours_left:02d}:{mins_left:02d}:{secs_left:02d}"
  return f"{mins_left:02d}:{secs_left:02d}"


candle_countdown = get_candle_countdown(interval)


# ---------------------------------------------------------
# 4. MOTOR TÉCNICO, FUNDAMENTAL Y DETECTOR DE OPORTUNIDADES
# ---------------------------------------------------------
def build_pro_indicators(df_in):
  df = df_in.copy()

  df["EMA_20"] = df["Close"].ewm(span=20, adjust=False).mean()
  df["EMA_50"] = df["Close"].ewm(span=50, adjust=False).mean()
  df["EMA_200"] = df["Close"].ewm(span=200, adjust=False).mean()

  delta = df["Close"].diff()
  gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
  loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
  rs = gain / (loss + 1e-9)
  df["RSI"] = 100 - (100 / (1 + rs))

  high_low = df["High"] - df["Low"]
  high_close = np.abs(df["High"] - df["Close"].shift())
  low_close = np.abs(df["Low"] - df["Close"].shift())
  ranges = pd.concat([high_low, high_close, low_close], axis=1)
  true_range = np.max(ranges, axis=1)
  df["ATR"] = true_range.rolling(14).mean()

  df["Vol_SMA"] = df["Volume"].rolling(window=20).mean()
  df["Volume_Surge"] = df["Volume"] > (df["Vol_SMA"] * 1.5)

  return df.dropna()


df_processed = build_pro_indicators(data)
last_row = df_processed.iloc[-1]
prev_row = df_processed.iloc[-2]

max_price = df_processed["High"].max()
min_price = df_processed["Low"].min()
price_range = max_price - min_price
fib_618 = max_price - (price_range * 0.618)

score = 0
if last_row["EMA_20"] > last_row["EMA_50"]:
  score += 35
else:
  score -= 35

if last_row["Close"] > last_row["EMA_200"]:
  score += 25
else:
  score -= 25

if last_row["RSI"] < 35:
  score += 30
elif last_row["RSI"] > 65:
  score -= 30
else:
  if last_row["RSI"] > prev_row["RSI"]:
    score += 10
  else:
    score -= 10

candle_prediction = "🟢 SUBIDA" if score >= 0 else "🔴 BAJADA"
is_up = True if score >= 0 else False

entry_price = float(last_row["Close"])
atr_val = float(last_row["ATR"])

expected_range_usd = atr_val * risk_reward_ratio
expected_range_pct = (expected_range_usd / entry_price) * 100

if is_up:
  take_profit = entry_price + expected_range_usd
  stop_loss = entry_price - (atr_val * 1.0)
else:
  take_profit = entry_price - expected_range_usd
  stop_loss = entry_price + (atr_val * 1.0)

confidence = min(abs(score) + 35, 96.0)

is_high_expansion_setup = (
    confidence >= 78
    and last_row["Volume_Surge"]
    and (atr_val > df_processed["ATR"].mean())
)

# ---------------------------------------------------------
# 5. INTERFAZ PRINCIPAL Y PANEL DE BALLENAS (CON RESPALDO)
# ---------------------------------------------------------
m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("Precio Mercado", f"${entry_price:,.2f}")
m2.metric("Predicción Vela Actual", candle_prediction)
m3.metric("⏳ Cierre de Vela en", candle_countdown)
m4.metric("Rango Proyectado", f"±${expected_range_usd:,.2f}")
m5.metric("Movimiento Est.", f"{expected_range_pct:.2f}%")

st.markdown("##### 📈 Comportamiento Reciente (Mini Tendencia)")
st.line_chart(df_processed["Close"].tail(25), height=120)

st.markdown("---")

# APARTADO DE RASTEO DE BALLENAS
st.subheader(
    f"🐋 RASTREADOR DE BALLENAS (Órdenes > ${min_whale_usd:,.0f} USD)"
)

if not whale_df.empty:
  buy_whales = whale_df[whale_df["Side"] == "buy"]["Total_USD"].sum()
  sell_whales = whale_df[whale_df["Side"] == "sell"]["Total_USD"].sum()

  col_w1, col_w2, col_w3 = st.columns(3)
  col_w1.metric("Volumen Compras Ballenas (Buy)", f"${buy_whales:,.2f}")
  col_w2.metric("Volumen Ventas Ballenas (Sell)", f"${sell_whales:,.2f}")

  pressure = (
      "🟢 COMPRAS INSTITUCIONALES DOMINANTES"
      if buy_whales >= sell_whales
      else "🔴 VENTAS INSTITUCIONALES / PRESIÓN BAJISTA"
  )
  col_w3.metric("Flujo Neto Institucional", pressure)

  st.dataframe(
      whale_df.style.format(
          {
              "Price": "${:,.2f}",
              "Size": "{:,.4f}",
              "Total_USD": "${:,.2f}",
          }
      ),
      use_container_width=True,
      height=200,
  )
else:
  # Sistema de respaldo heurístico si el endpoint de trades está saturado o vacío
  st.warning(
      "⚠️ Órdenes directas individuales no detectadas en este milisegundo."
      " Activando Estimación de Flujo Institucional por Volumen de Velas:"
  )

  est_volume = last_row["Volume"] * entry_price
  col_w1, col_w2, col_w3 = st.columns(3)
  col_w1.metric(
      "Volumen de la Vela Actual",
      f"${est_volume:,.2f}",
      delta="Expan. Institucional"
      if last_row["Volume_Surge"]
      else "Normal",
  )
  col_w2.metric(
      "Intensidad de Compra/Venta",
      "🟢 Fuerte Acumulación" if is_up else "🔴 Fuerte Distribución",
  )
  col_w3.metric(
      "Estado de Ballenas",
      "Activas en el rango"
      if last_row["Volume_Surge"]
      else "En espera de ruptura",
  )

st.markdown("---")

if is_high_expansion_setup:
  st.error(
      f"🚀 **¡ALERTA PRO: OPORTUNIDAD X5/X10 EN TEMPORALIDAD DE {interval}!**"
  )
  st.markdown(
      "Se detectó un **impulso de volumen institucional** y acumulación de"
      f" ballenas en **{symbol}** para la temporalidad de **{interval}**."
  )
else:
  st.info(
      f"⏳ **Estado de Mercado ({interval}):** Analizando flujos de volumen y"
      " acumulación..."
  )

st.markdown("---")

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
# 6. GRÁFICOS Y ANÁLISIS TÉCNICO / FUNDAMENTAL
# ---------------------------------------------------------
st.subheader(
    f"🎯 Análisis Técnico Profesional ({interval}) — {symbol}"
)
st.line_chart(df_processed[["Close", "EMA_20", "EMA_50", "EMA_200"]])

st.subheader("📊 Indicador RSI")
st.line_chart(df_processed["RSI"])

st.subheader("🏛️ Módulo de Análisis Fundamental y Contexto Macro")
col_f1, col_f2, col_f3 = st.columns(3)

with col_f1:
  macro_bias = (
      "BULLISH (ALCISTA)"
      if entry_price > last_row["EMA_200"]
      else "BEARISH (BAJISTA)"
  )
  st.markdown(f"**Sesgo Macro (EMA 200):**\n#### {macro_bias}")

with col_f2:
  volatility_status = (
      "ALTA VOLATILIDAD (Expansión)"
      if atr_val > df_processed["ATR"].mean()
      else "CONSOLIDACIÓN"
  )
  st.markdown(f"**Estado de Volatilidad (ATR):**\n#### {volatility_status}")

with col_f3:
  fib_zone = (
      "Cerca de Zona de Reacción Fib 61.8%"
      if abs(entry_price - fib_618) < (atr_val * 2)
      else "Sin nivel Fibonacci Inmediato"
  )
  st.markdown(f"**Estructura Fibonacci:**\n#### {fib_zone}")

# ---------------------------------------------------------
# 7. CICLO DE AUTO-REFRESCO (1 SEGUNDO)
# ---------------------------------------------------------
if auto_refresh:
  time.sleep(1)
  st.rerun()
