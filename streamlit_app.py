import datetime
import time
import numpy as np
import pandas as pd
import requests
import streamlit as st

# ---------------------------------------------------------
# CONFIGURACIÓN DE PÁGINA Y MEMORIA PERSISTENTE DE TRADING
# ---------------------------------------------------------
st.set_page_config(
    page_title="Crypto Predictor Pro - Auto SL/TP Engine",
    page_icon="⚡",
    layout="wide",
)

st.title("⚡ Crypto Predictor Pro — Trading 100% Automático (Auto SL/TP)")

# Memoria de sesión para balance, posiciones fijas e historial
if "paper_balance" not in st.session_state:
  st.session_state.paper_balance = 10000.0
if "active_trade" not in st.session_state:
  st.session_state.active_trade = None
if "trade_history" not in st.session_state:
  st.session_state.trade_history = []
if "last_close_event" not in st.session_state:
  st.session_state.last_close_event = None

# ---------------------------------------------------------
# 1. BARRA LATERAL: CONFIGURACIÓN Y AUTO-TRADING
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

st.sidebar.header("🤖 Piloto Automático")
auto_execute = st.sidebar.toggle(
    "Activar Apertura y Cierre 100% Automático", value=True
)
signal_threshold = st.sidebar.slider(
    "Umbral Mínimo de Confianza para Entrar (%)",
    min_value=70,
    max_value=90,
    value=80,
    step=1,
)

st.sidebar.header("🛡️ Parámetros de Salida (SL / TP)")
risk_reward_ratio = st.sidebar.slider(
    "Ratio Riesgo / Beneficio (R:R)",
    min_value=1.0,
    max_value=3.5,
    value=2.5,
    step=0.1,
)
trade_amount_usd = st.sidebar.number_input(
    "Monto por Operación ($)", min_value=100, max_value=5000, value=1000
)
min_whale_usd = st.sidebar.slider(
    "Filtro de Ballenas (USD)",
    min_value=5000,
    max_value=100000,
    value=10000,
    step=5000,
)

auto_refresh = st.sidebar.checkbox("Activar Auto-Refresco (1s)", value=True)
candle_limit = 150

# ---------------------------------------------------------
# 2. CONEXIÓN API EN TIEMPO REAL (OKX)
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


def fetch_live_order_flow(symbol: str, min_usd: float):
  url = f"https://www.okx.com/api/v5/market/trades?instId={symbol}&limit=300"
  try:
    response = requests.get(url, headers=HEADERS, timeout=3)
    if response.status_code == 200:
      trades_data = response.json().get("data", [])
      if trades_data:
        df_trades = pd.DataFrame(trades_data)
        if "px" in df_trades.columns and "sz" in df_trades.columns:
          df_trades["Price"] = df_trades["px"].astype(float)
          df_trades["Size"] = df_trades["sz"].astype(float)
          df_trades["Side"] = df_trades["side"]
          df_trades["Total_USD"] = df_trades["Price"] * df_trades["Size"]
          df_trades["Hora"] = pd.to_datetime(
              df_trades["ts"].astype(int), unit="ms"
          ).dt.strftime("%H:%M:%S")

          total_buy_vol = df_trades[df_trades["Side"] == "buy"][
              "Total_USD"
          ].sum()
          total_sell_vol = df_trades[df_trades["Side"] == "sell"][
              "Total_USD"
          ].sum()
          whales = df_trades[df_trades["Total_USD"] >= min_usd]
          return df_trades, whales, total_buy_vol, total_sell_vol
  except Exception:
    pass
  return pd.DataFrame(), pd.DataFrame(), 0.0, 0.0


@st.cache_data(ttl=1, show_spinner=False)
def get_crypto_candles(symbol: str, interval: str):
  return fetch_from_okx(symbol, interval, candle_limit)


data = get_crypto_candles(symbol, interval)
df_trades, whale_df, live_buy_vol, live_sell_vol = fetch_live_order_flow(
    symbol, min_whale_usd
)

if data.empty or len(data) < 50:
  st.error("Estableciendo conexión con el servidor de datos...")
  time.sleep(1)
  st.rerun()


# ---------------------------------------------------------
# 3. TEMPORIZADOR Y CÁLCULO ALGORÍTMICO DE NIVELES
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

entry_price = float(last_row["Close"])
atr_val = float(last_row["ATR"])

score = 0
reasons = []

if last_row["EMA_20"] > last_row["EMA_50"]:
  score += 35
  reasons.append("EMA 20 por encima de EMA 50 (Estructura Alcista).")
else:
  score -= 35
  reasons.append("EMA 20 por debajo de EMA 50 (Estructura Bajista).")

if last_row["Close"] > last_row["EMA_200"]:
  score += 25
  reasons.append("Precio cotizando sobre la EMA 200 Macro.")
else:
  score -= 25
  reasons.append("Precio cotizando bajo la EMA 200 Macro.")

if last_row["RSI"] < 35:
  score += 30
  reasons.append("RSI en sobreventa (<35): Zona de rebote.")
elif last_row["RSI"] > 65:
  score -= 30
  reasons.append("RSI en sobrecompra (>65): Zona de caída.")
else:
  if last_row["RSI"] > prev_row["RSI"]:
    score += 10
    reasons.append("Impulso ascendente en oscilador RSI.")
  else:
    score -= 10
    reasons.append("Pérdida de momentum en oscilador RSI.")

total_vol = live_buy_vol + live_sell_vol
buy_pct = (live_buy_vol / total_vol * 100) if total_vol > 0 else 50.0

if buy_pct > 55:
  score += 10
  reasons.append(f"Order Flow Alcista: Compras en {buy_pct:.1f}% en vivo.")
elif buy_pct < 45:
  score -= 10
  reasons.append(f"Order Flow Bajista: Ventas en {100-buy_pct:.1f}% en vivo.")

confidence = min(abs(score) + 35, 96.0)
is_up = True if score >= 0 else False
candle_prediction = "🟢 SUBIDA" if is_up else "🔴 BAJADA"

expected_range_usd = atr_val * risk_reward_ratio

if is_up:
  take_profit = entry_price + expected_range_usd
  stop_loss = entry_price - (atr_val * 1.0)
  type_str = "LONG (COMPRA)"
else:
  take_profit = entry_price - expected_range_usd
  stop_loss = entry_price + (atr_val * 1.0)
  type_str = "SHORT (VENTA)"

should_open_trade = confidence >= signal_threshold

# ---------------------------------------------------------
# 4. MOTOR DE TRADING AUTOMÁTICO (MONITOREO FIJO SL/TP)
# ---------------------------------------------------------

# A) Monitoreo de posición activa -> Cierre automático cuando toca TP o SL
if st.session_state.active_trade:
  act = st.session_state.active_trade
  closed_reason = None
  pnl_usd = 0.0

  if act["type"] == "LONG (COMPRA)":
    if entry_price >= act["tp"]:
      closed_reason = "TAKE PROFIT (ALCANZADO 🎯)"
      pnl_usd = (act["tp"] - act["entry"]) * act["size"]
    elif entry_price <= act["sl"]:
      closed_reason = "STOP LOSS (EJECUTADO 🛡️)"
      pnl_usd = (act["sl"] - act["entry"]) * act["size"]
  else:  # SHORT
    if entry_price <= act["tp"]:
      closed_reason = "TAKE PROFIT (ALCANZADO 🎯)"
      pnl_usd = (act["entry"] - act["tp"]) * act["size"]
    elif entry_price >= act["sl"]:
      closed_reason = "STOP LOSS (EJECUTADO 🛡️)"
      pnl_usd = (act["entry"] - act["sl"]) * act["size"]

  # Si el precio tocó alguno de los límites fijados, se cierra la orden automáticamente
  if closed_reason:
    st.session_state.paper_balance += pnl_usd
    close_event = {
        "Fecha": datetime.datetime.now().strftime("%H:%M:%S"),
        "Par": act["symbol"],
        "Tipo": act["type"],
        "Entrada": act["entry"],
        "Cierre": entry_price,
        "Resultado": closed_reason,
        "PnL ($)": round(pnl_usd, 2),
    }
    st.session_state.trade_history.append(close_event)
    st.session_state.last_close_event = close_event
    st.session_state.active_trade = None

# B) Apertura automática cuando el algoritmo genera la señal
if (
    should_open_trade
    and auto_execute
    and st.session_state.active_trade is None
):
  pos_size = trade_amount_usd / entry_price
  # SE FIJAN PERMANENTEMENTE LOS NIVELES DE SL Y TP PARA ESTA OPERACIÓN
  st.session_state.active_trade = {
      "symbol": symbol,
      "type": type_str,
      "entry": entry_price,
      "tp": take_profit,
      "sl": stop_loss,
      "size": pos_size,
      "amount_usd": trade_amount_usd,
      "reasons": reasons,
      "time": datetime.datetime.now().strftime("%H:%M:%S"),
  }

# ---------------------------------------------------------
# 5. INTERFAZ Y REPORTE DE ESTADO
# ---------------------------------------------------------
m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("Precio Mercado", f"${entry_price:,.2f}")
m2.metric("Predicción Vela Actual", candle_prediction)
m3.metric("⏳ Cierre de Vela en", candle_countdown)
m4.metric("Rango Proyectado", f"±${expected_range_usd:,.2f}")
m5.metric("Balance Simulado", f"${st.session_state.paper_balance:,.2f} USDT")

st.markdown("---")

# NOTIFICACIÓN DE CIERRE RECIENTE POR SL O TP
if st.session_state.last_close_event:
  evt = st.session_state.last_close_event
  pnl_color = "🟢" if evt["PnL ($)"] >= 0 else "🔴"
  st.toast(
      f"Operación Auto-Cerrada por {evt['Resultado']}: PnL"
      f" ${evt['PnL ($)']:+,.2f}"
  )
  st.success(
      f"🤖 **AUTOMÁTICO:** Última posición en **{evt['Par']} ({evt['Tipo']})**"
      f" cerrada por **{evt['Resultado']}** a las {evt['Fecha']}. Resultado:"
      f" {pnl_color} **${evt['PnL ($)']:+,.2f} USDT**"
  )

# BANNER DE SEÑAL
if should_open_trade:
  st.error(
      f"🚨 **SEÑAL ACTIVA DE ENTRADA AUTOMÁTICA** — Tipo: **{type_str}** en"
      f" **{symbol}**"
  )
  c1, c2, c3, c4 = st.columns(4)
  c1.metric("Punto Entrada Fijo", f"${entry_price:,.2f}")
  c2.metric("Take Profit Fijo (TP)", f"${take_profit:,.2f}")
  c3.metric("Stop Loss Fijo (SL)", f"${stop_loss:,.2f}")
  c4.metric("Confianza Algorítmica", f"{confidence:.1f}%")

st.markdown("---")

# ---------------------------------------------------------
# 6. COMPRAS Y VENTAS EN VIVO Y RASTREADOR DE BALLENAS
# ---------------------------------------------------------
st.subheader("⚖️ Presión Interna de Compra y Venta (Vela Actual en Vivo)")

col_p1, col_p2 = st.columns(2)
with col_p1:
  st.metric(
      "🟢 Volumen de Compras (En Vivo)",
      f"${live_buy_vol:,.2f}",
      f"{buy_pct:.1f}% del Mercado",
  )
with col_p2:
  st.metric(
      "🔴 Volumen de Ventas (En Vivo)",
      f"${live_sell_vol:,.2f}",
      f"{100-buy_pct:.1f}% del Mercado",
  )

st.progress(
    int(buy_pct),
    text=(
        f"Dominio de Compras: {buy_pct:.1f}%  |  Dominio de Ventas:"
        f" {100-buy_pct:.1f}%"
    ),
)

st.markdown("---")

st.subheader(
    f"🐋 RASTREADOR DE BALLENAS (Órdenes > ${min_whale_usd:,.0f} USD)"
)

if not whale_df.empty:
  buy_whales = whale_df[whale_df["Side"] == "buy"]["Total_USD"].sum()
  sell_whales = whale_df[whale_df["Side"] == "sell"]["Total_USD"].sum()

  col_w1, col_w2, col_w3 = st.columns(3)
  col_w1.metric("Compras de Ballenas", f"${buy_whales:,.2f}")
  col_w2.metric("Ventas de Ballenas", f"${sell_whales:,.2f}")

  pressure = (
      "🟢 COMPRAS INSTITUCIONALES DOMINANTES"
      if buy_whales >= sell_whales
      else "🔴 VENTAS INSTITUCIONALES DOMINANTES"
  )
  col_w3.metric("Flujo Institucional", pressure)

  st.dataframe(
      whale_df[["Hora", "Side", "Price", "Size", "Total_USD"]]
      .head(10)
      .style.format(
          {
              "Price": "${:,.2f}",
              "Size": "{:,.4f}",
              "Total_USD": "${:,.2f}",
          }
      ),
      use_container_width=True,
      height=180,
  )
else:
  st.info("Escaneando transacciones institucionales grandes...")

st.markdown("---")

# ---------------------------------------------------------
# 7. ESTADO DE POSICIÓN ACTIVA Y FIJACIÓN DE SL/TP
# ---------------------------------------------------------
st.subheader("🎮 Estado de Posición y Monitor de Cierre Automático")
col_sim1, col_sim2 = st.columns([1, 2])

with col_sim1:
  if st.session_state.active_trade:
    act = st.session_state.active_trade
    floating_pnl = (
        (entry_price - act["entry"]) * act["size"]
        if act["type"] == "LONG (COMPRA)"
        else (act["entry"] - entry_price) * act["size"]
    )
    pnl_symbol = "🟢" if floating_pnl >= 0 else "🔴"

    st.warning(f"**POSICIÓN ABIERTA:** {act['type']}")
    st.write(f"• **Entrada:** `${act['entry']:,.2f}`")
    st.write(f"• **Take Profit Fijo:** `${act['tp']:,.2f}`")
    st.write(f"• **Stop Loss Fijo:** `${act['sl']:,.2f}`")
    st.write(f"• **PnL Flotante:** {pnl_symbol} `${floating_pnl:+,.2f} USDT`")

    if st.button("❌ Cierre Manual de Emergencia"):
      st.session_state.paper_balance += floating_pnl
      st.session_state.trade_history.append({
          "Fecha": datetime.datetime.now().strftime("%H:%M:%S"),
          "Par": symbol,
          "Tipo": act["type"],
          "Entrada": act["entry"],
          "Cierre": entry_price,
          "Resultado": "CIERRE_MANUAL",
          "PnL ($)": round(floating_pnl, 2),
      })
      st.session_state.active_trade = None
      st.rerun()
  else:
    st.info("🤖 **Piloto Automático:** En espera de señal de entrada...")
    st.write(f"**Próximo TP Estimado:** `${take_profit:,.2f}`")
    st.write(f"**Próximo SL Estimado:** `${stop_loss:,.2f}`")

with col_sim2:
  st.markdown("##### 📝 Justificación Técnica de la Estrategia:")
  for idx, r in enumerate(reasons, 1):
    st.markdown(f"**{idx}.** {r}")

if st.session_state.trade_history:
  st.markdown("##### 📜 Historial de Operaciones Auto-Cerradas")
  st.dataframe(
      pd.DataFrame(st.session_state.trade_history),
      use_container_width=True,
      height=140,
  )

st.markdown("---")

# ---------------------------------------------------------
# 8. GRÁFICOS TÉCNICOS
# ---------------------------------------------------------
st.subheader(
    f"🎯 Análisis Técnico Profesional ({interval}) — {symbol}"
)
st.line_chart(df_processed[["Close", "EMA_20", "EMA_50", "EMA_200"]])

st.subheader("📊 Indicador RSI")
st.line_chart(df_processed["RSI"])

# ---------------------------------------------------------
# 9. AUTO-REFRESCO CADA 1 SEGUNDO
# ---------------------------------------------------------
if auto_refresh:
  time.sleep(1)
  st.rerun()
