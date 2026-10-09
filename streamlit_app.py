import datetime
import time
import numpy as np
import pandas as pd
import requests
import streamlit as st

# Intentar importar python-binance para ejecución real
try:
  from binance.client import Client
  from binance.enums import *

  BINANCE_AVAILABLE = True
except ImportError:
  BINANCE_AVAILABLE = False

# ---------------------------------------------------------
# CONFIGURACIÓN DE PÁGINA Y MEMORIA DEL BOT
# ---------------------------------------------------------
st.set_page_config(
    page_title="Crypto Predictor Pro - Binance Live Engine",
    page_icon="⚡",
    layout="wide",
)

st.title("⚡ Crypto Predictor Pro — Sistema Autónomo Binance & Order Flow")

# Variables de sesión persistentes
if "paper_balance" not in st.session_state:
  st.session_state.paper_balance = 10000.0
if "active_trade" not in st.session_state:
  st.session_state.active_trade = None
if "trade_history" not in st.session_state:
  st.session_state.trade_history = []
if "last_close_event" not in st.session_state:
  st.session_state.last_close_event = None
if "is_executing" not in st.session_state:
  st.session_state.is_executing = False  # Bloqueo anti-duplicación

# ---------------------------------------------------------
# 1. BARRA LATERAL: ENTORNO Y SALVAGUARDAS DE SEGURIDAD
# ---------------------------------------------------------
st.sidebar.header("🛡️ Entorno y Claves Binance")

trading_mode = st.sidebar.radio(
    "Modo de Operación",
    ["Simulación (Paper)", "Binance Testnet (Pruebas)", "Binance REAL (Live)"],
    index=0,
)

# Carga de credenciales desde st.secrets o Sidebar
binance_api_key = ""
binance_api_secret = ""

if trading_mode != "Simulación (Paper)":
  if not BINANCE_AVAILABLE:
    st.sidebar.error("❌ Instala 'python-binance' en requirements.txt")
  else:
    try:
      binance_api_key = st.secrets["binance"]["api_key"]
      binance_api_secret = st.secrets["binance"]["api_secret"]
      st.sidebar.success("🔑 Claves cargadas desde Secrets")
    except Exception:
      binance_api_key = st.sidebar.text_input(
          "Binance API Key", type="password"
      )
      binance_api_secret = st.sidebar.text_input(
          "Binance API Secret", type="password"
      )

live_confirm = False
if trading_mode == "Binance REAL (Live)":
  live_confirm = st.sidebar.checkbox(
      "⚠️ Acepto el riesgo de operar con CAPITAL REAL"
  )
  if not live_confirm:
    st.sidebar.warning(
        "Debes confirmar la casilla para habilitar órdenes reales."
    )

emergency_stop = st.sidebar.button("🚨 BOTÓN DE PÁNICO: DETENER BOT")
if emergency_stop:
  st.session_state.is_executing = False
  st.sidebar.error("🛑 Bot congelado por orden del usuario.")

# Botón adicional para limpiar sesión si hay conflictos
if st.sidebar.button("🧹 Limpiar Estado de Posiciones"):
  st.session_state.active_trade = None
  st.session_state.is_executing = False
  st.success("Estado limpiado correctamente.")

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
auto_execute = st.sidebar.toggle("Activar Auto-Trading", value=False)
signal_threshold = st.sidebar.slider(
    "Umbral de Confianza para Entrar (%)",
    min_value=70,
    max_value=90,
    value=80,
    step=1,
)

st.sidebar.header("🛡️ Parámetros de Riesgo")
trade_amount_usd = st.sidebar.number_input(
    "Monto por Operación ($)", min_value=10, max_value=5000, value=100
)
risk_reward_ratio = st.sidebar.slider(
    "Ratio Riesgo / Beneficio (R:R)",
    min_value=1.0,
    max_value=3.5,
    value=2.5,
    step=0.1,
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
# 2. CLIENTE BINANCE Y FUNCIONES DE EJECUCIÓN
# ---------------------------------------------------------
binance_client = None

if (
    trading_mode != "Simulación (Paper)"
    and BINANCE_AVAILABLE
    and binance_api_key
):
  try:
    is_testnet = trading_mode == "Binance Testnet (Pruebas)"
    binance_client = Client(
        binance_api_key, binance_api_secret, testnet=is_testnet
    )
  except Exception as e:
    st.sidebar.error(f"Error conexión Binance: {e}")


def execute_binance_trade(symbol_raw, side_type, amount_usd, entry, tp, sl):
  if not binance_client:
    return None, "Cliente de Binance no configurado correctamente."

  try:
    binance_symbol = symbol_raw.replace("-", "")
    account = binance_client.get_account()
    usdt_balance = sum(
        float(b["free"]) for b in account["balances"] if b["asset"] == "USDT"
    )

    if "LONG" in side_type and usdt_balance < amount_usd:
      return (
          None,
          f"Saldo insuficiente en Binance USDT (${usdt_balance:.2f} <"
          f" ${amount_usd})",
      )

    ticker = binance_client.get_symbol_ticker(symbol=binance_symbol)
    curr_price = float(ticker["price"])
    raw_qty = amount_usd / curr_price

    qty_precision = 5 if "BTC" in symbol_raw else 2
    quantity = round(raw_qty, qty_precision)

    order_side = SIDE_BUY if "LONG" in side_type else SIDE_SELL

    main_order = binance_client.create_order(
        symbol=binance_symbol,
        side=order_side,
        type=ORDER_TYPE_MARKET,
        quantity=quantity,
    )

    return main_order, "OK"
  except Exception as e:
    return None, str(e)


# ---------------------------------------------------------
# 3. EXTRAER DATOS EN VIVO (OKX PUBLIC API + ORDER FLOW)
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
  st.error("Conectando con el servidor de datos...")
  time.sleep(1)
  st.rerun()


# ---------------------------------------------------------
# 4. TEMPORIZADOR Y MOTOR TÉCNICO ALGORÍTMICO
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
# 5. EJECUCIÓN Y GESTIÓN AUTOMÁTICA DE POSICIONES
# ---------------------------------------------------------

# Monitoreo de posición abierta -> Cierre por SL o TP
if st.session_state.active_trade:
  act = st.session_state.active_trade
  closed_reason = None
  pnl_usd = 0.0

  act_type = act.get("type", "LONG (COMPRA)")
  act_tp = act.get("tp", take_profit)
  act_sl = act.get("sl", stop_loss)
  act_entry = act.get("entry", entry_price)
  act_size = act.get("size", 1.0)

  if act_type == "LONG (COMPRA)":
    if entry_price >= act_tp:
      closed_reason = "TAKE PROFIT (ALCANZADO 🎯)"
      pnl_usd = (act_tp - act_entry) * act_size
    elif entry_price <= act_sl:
      closed_reason = "STOP LOSS (EJECUTADO 🛡️)"
      pnl_usd = (act_sl - act_entry) * act_size
  else:
    if entry_price <= act_tp:
      closed_reason = "TAKE PROFIT (ALCANZADO 🎯)"
      pnl_usd = (act_entry - act_tp) * act_size
    elif entry_price >= act_sl:
      closed_reason = "STOP LOSS (EJECUTADO 🛡️)"
      pnl_usd = (act_entry - act_sl) * act_size

  if closed_reason:
    st.session_state.paper_balance += pnl_usd
    close_event = {
        "Fecha": datetime.datetime.now().strftime("%H:%M:%S"),
        "Par": act.get("symbol", symbol),
        "Tipo": act_type,
        "Entrada": act_entry,
        "Cierre": entry_price,
        "Resultado": closed_reason,
        "PnL ($)": round(pnl_usd, 2),
    }
    st.session_state.trade_history.append(close_event)
    st.session_state.last_close_event = close_event
    st.session_state.active_trade = None
    st.session_state.is_executing = False

# Disparo de Orden con Cerrojo Anti-Duplicación
if (
    should_open_trade
    and auto_execute
    and st.session_state.active_trade is None
    and not st.session_state.is_executing
    and not emergency_stop
):

  can_proceed = True
  if trading_mode == "Binance REAL (Live)" and not live_confirm:
    can_proceed = False

  if can_proceed:
    st.session_state.is_executing = True

    binance_res = "OK"
    if trading_mode != "Simulación (Paper)":
      _, binance_res = execute_binance_trade(
          symbol, type_str, trade_amount_usd, entry_price, take_profit, stop_loss
      )

    if binance_res == "OK":
      pos_size = trade_amount_usd / entry_price
      st.session_state.active_trade = {
          "symbol": symbol,
          "type": type_str,
          "entry": entry_price,
          "tp": take_profit,
          "sl": stop_loss,
          "size": pos_size,
          "amount_usd": trade_amount_usd,
          "reasons": reasons,
          "mode": trading_mode,
          "time": datetime.datetime.now().strftime("%H:%M:%S"),
      }
      st.toast(f"🚀 Orden Ejecutada ({trading_mode}): {type_str} en {symbol}")
    else:
      st.error(f"❌ Fallo al emitir orden en Binance: {binance_res}")
      st.session_state.is_executing = False

# ---------------------------------------------------------
# 6. INTERFAZ GRÁFICA Y DASHBOARD PRINCIPAL
# ---------------------------------------------------------
m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("Precio Mercado", f"${entry_price:,.2f}")
m2.metric("Predicción Vela Actual", candle_prediction)
m3.metric("⏳ Cierre de Vela en", candle_countdown)
m4.metric("Rango Proyectado", f"±${expected_range_usd:,.2f}")
m5.metric("Modo Activo", trading_mode.split()[0])

st.markdown("---")

if st.session_state.last_close_event:
  evt = st.session_state.last_close_event
  pnl_color = "🟢" if evt["PnL ($)"] >= 0 else "🔴"
  st.success(
      f"🤖 Última posición en **{evt['Par']} ({evt['Tipo']})** cerrada por"
      f" **{evt['Resultado']}**. Resultado: {pnl_color}"
      f" **${evt['PnL ($)']:+,.2f} USDT**"
  )

if should_open_trade:
  st.error(
      f"🚨 **SEÑAL ACTIVA DE ENTRADA AUTOMÁTICA** — Tipo: **{type_str}** en"
      f" **{symbol}**"
  )
  c1, c2, c3, c4 = st.columns(4)
  c1.metric("Punto Entrada", f"${entry_price:,.2f}")
  c2.metric("Take Profit Fijo (TP)", f"${take_profit:,.2f}")
  c3.metric("Stop Loss Fijo (SL)", f"${stop_loss:,.2f}")
  c4.metric("Confianza Algorítmica", f"{confidence:.1f}%")

st.markdown("---")

# ---------------------------------------------------------
# 7. ORDER FLOW & RASTREADOR DE BALLENAS
# ---------------------------------------------------------
st.subheader("⚖️ Presión Interna de Compra y Venta (Vela Actual en Vivo)")

col_p1, col_p2 = st.columns(2)
col_p1.metric(
    "🟢 Volumen Compras (En Vivo)",
    f"${live_buy_vol:,.2f}",
    f"{buy_pct:.1f}% del Mercado",
)
col_p2.metric(
    "🔴 Volumen Ventas (En Vivo)",
    f"${live_sell_vol:,.2f}",
    f"{100-buy_pct:.1f}% del Mercado",
)

st.progress(
    int(buy_pct),
    text=(
        f"Dominio Compras: {buy_pct:.1f}%  |  Dominio Ventas: {100-buy_pct:.1f}%"
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
      .head(8)
      .style.format(
          {"Price": "${:,.2f}", "Size": "{:,.4f}", "Total_USD": "${:,.2f}"}
      ),
      use_container_width=True,
      height=160,
  )
else:
  st.info("Escaneando órdenes institucionales...")

st.markdown("---")

# ---------------------------------------------------------
# 8. PANEL DE CONTROL DE POSICIÓN Y HISTORIAL
# ---------------------------------------------------------
st.subheader("🎮 Estado de Posición y Monitor de Cierre Automático")
col_sim1, col_sim2 = st.columns([1, 2])

with col_sim1:
  if st.session_state.active_trade:
    act = st.session_state.active_trade
    act_mode = act.get("mode", trading_mode)
    act_type = act.get("type", type_str)
    act_entry = act.get("entry", entry_price)
    act_tp = act.get("tp", take_profit)
    act_sl = act.get("sl", stop_loss)
    act_size = act.get("size", 1.0)

    floating_pnl = (
        (entry_price - act_entry) * act_size
        if act_type == "LONG (COMPRA)"
        else (act_entry - entry_price) * act_size
    )
    pnl_symbol = "🟢" if floating_pnl >= 0 else "🔴"

    st.warning(f"**POSICIÓN ABIERTA ({act_mode}):** {act_type}")
    st.write(f"• **Entrada:** `${act_entry:,.2f}`")
    st.write(f"• **Take Profit Fijo:** `${act_tp:,.2f}`")
    st.write(f"• **Stop Loss Fijo:** `${act_sl:,.2f}`")
    st.write(f"• **PnL Flotante:** {pnl_symbol} `${floating_pnl:+,.2f} USDT`")

    if st.button("❌ Cierre Manual de Emergencia"):
      st.session_state.paper_balance += floating_pnl
      st.session_state.trade_history.append({
          "Fecha": datetime.datetime.now().strftime("%H:%M:%S"),
          "Par": symbol,
          "Tipo": act_type,
          "Entrada": act_entry,
          "Cierre": entry_price,
          "Resultado": "CIERRE_MANUAL",
          "PnL ($)": round(floating_pnl, 2),
      })
      st.session_state.active_trade = None
      st.session_state.is_executing = False
      st.rerun()
  else:
    st.info("🤖 **Piloto Automático:** Monitorizando entradas...")
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
# 9. GRÁFICOS TÉCNICOS
# ---------------------------------------------------------
st.subheader(
    f"🎯 Análisis Técnico Profesional ({interval}) — {symbol}"
)
st.line_chart(df_processed[["Close", "EMA_20", "EMA_50", "EMA_200"]])

st.subheader("📊 Indicador RSI")
st.line_chart(df_processed["RSI"])

# ---------------------------------------------------------
# 10. REFRESO AUTOMÁTICO CADA 1 SEGUNDO
# ---------------------------------------------------------
if auto_refresh:
  time.sleep(1)
  st.rerun()
