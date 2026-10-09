import datetime
import hashlib
import hmac
import time
import numpy as np
import pandas as pd
import requests
import streamlit as st

# ---------------------------------------------------------
# CONFIGURACIÓN DE PÁGINA
# ---------------------------------------------------------
st.set_page_config(
    page_title="Crypto Predictor Pro - Engine Estable",
    page_icon="⚡",
    layout="wide",
)

st.title("⚡ Crypto Predictor Pro — Panel de Control Estable")

# Inicialización segura de variables de sesión
if "paper_balance" not in st.session_state:
  st.session_state.paper_balance = 10000.0
if "active_trade" not in st.session_state:
  st.session_state.active_trade = None
if "trade_history" not in st.session_state:
  st.session_state.trade_history = []
if "last_close_event" not in st.session_state:
  st.session_state.last_close_event = None

# ---------------------------------------------------------
# 1. BARRA LATERAL
# ---------------------------------------------------------
st.sidebar.header("⚙️ Configuración del Sistema")

trading_mode = st.sidebar.radio(
    "Modo de Operación",
    ["Simulación (Paper)", "Binance Testnet", "Binance REAL"],
    index=0,
)

binance_api_key = st.sidebar.text_input(
    "Binance API Key",
    type="password",
    value=st.secrets.get("binance", {}).get("api_key", ""),
)
binance_api_secret = st.sidebar.text_input(
    "Binance API Secret",
    type="password",
    value=st.secrets.get("binance", {}).get("api_secret", ""),
)

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
    "Umbral de Confianza (%)", min_value=70, max_value=90, value=80
)

st.sidebar.header("🛡️ Gestión de Riesgo")
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
    "Filtro Ballenas (USD)",
    min_value=5000,
    max_value=100000,
    value=10000,
    step=5000,
)

# Intervalo seguro de refresco para evitar pantalla negra
refresh_seconds = st.sidebar.slider(
    "Intervalo de Refresco (segundos)",
    min_value=2,
    max_value=10,
    value=3,
    help="Valores muy bajos (1s) pueden congelar la interfaz.",
)
auto_refresh = st.sidebar.checkbox("Activar Auto-Refresco Seguro", value=True)

# ---------------------------------------------------------
# 2. CONECTOR DIRECTO A BINANCE (SIN LIBRERÍAS EXTERNAS)
# ---------------------------------------------------------
def binance_native_trade(
    symbol_raw, side_type, amount_usd, api_key, api_secret, is_testnet=True
):
  """Ejecuta orden en Binance directamente vía HTTP HMAC SHA256."""
  if not api_key or not api_secret:
    return None, "Faltan las credenciales API Key / Secret."

  base_url = (
      "https://testnet.binance.vision"
      if is_testnet
      else "https://api.binance.com"
  )
  binance_symbol = symbol_raw.replace("-", "")

  try:
    # Obtener precio de mercado
    p_res = requests.get(
        f"{base_url}/api/v3/ticker/price?symbol={binance_symbol}", timeout=4
    ).json()
    if "price" not in p_res:
      return None, f"Error obteniendo precio: {p_res}"

    curr_price = float(p_res["price"])
    qty_precision = 5 if "BTC" in symbol_raw else 2
    quantity = round(amount_usd / curr_price, qty_precision)
    side = "BUY" if "LONG" in side_type else "SELL"

    # Preparar parámetros para firma
    params = {
        "symbol": binance_symbol,
        "side": side,
        "type": "MARKET",
        "quantity": quantity,
        "timestamp": int(time.time() * 1000),
        "recvWindow": 5000,
    }

    query_string = "&".join([f"{k}={v}" for k, v in params.items()])
    signature = hmac.new(
        api_secret.encode("utf-8"),
        query_string.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    full_url = f"{base_url}/api/v3/order?{query_string}&signature={signature}"
    headers = {"X-MBX-APIKEY": api_key}

    res = requests.post(full_url, headers=headers, timeout=5).json()

    if "orderId" in res:
      return res, "OK"
    else:
      return None, res.get("msg", str(res))
  except Exception as e:
    return None, f"Excepción de red: {e}"


# ---------------------------------------------------------
# 3. EXTRACCIÓN PROTEGIDA DE DATOS
# ---------------------------------------------------------
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
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
  url = f"https://www.okx.com/api/v5/market/trades?instId={symbol}&limit=200"
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


# Carga de datos con mecanismo de fallback seguro
data = fetch_from_okx(symbol, interval)
df_trades, whale_df, live_buy_vol, live_sell_vol = fetch_live_order_flow(
    symbol, min_whale_usd
)

if data.empty or len(data) < 30:
  st.warning(
      "⚠️ Conectando con los servidores de datos... Reintentando de forma"
      " segura."
  )
  time.sleep(2)
  st.rerun()

# ---------------------------------------------------------
# 4. CÁLCULOS TÉCNICOS Y SEÑALES
# ---------------------------------------------------------
df_processed = data.copy()
df_processed["EMA_20"] = df_processed["Close"].ewm(span=20, adjust=False).mean()
df_processed["EMA_50"] = df_processed["Close"].ewm(span=50, adjust=False).mean()
df_processed["EMA_200"] = (
    df_processed["Close"].ewm(span=200, adjust=False).mean()
)

delta = df_processed["Close"].diff()
gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
rs = gain / (loss + 1e-9)
df_processed["RSI"] = 100 - (100 / (1 + rs))

high_low = df_processed["High"] - df_processed["Low"]
high_close = np.abs(df_processed["High"] - df_processed["Close"].shift())
low_close = np.abs(df_processed["Low"] - df_processed["Close"].shift())
true_range = np.max(
    pd.concat([high_low, high_close, low_close], axis=1), axis=1
)
df_processed["ATR"] = true_range.rolling(14).mean()

last_row = df_processed.iloc[-1]
prev_row = df_processed.iloc[-2]
entry_price = float(last_row["Close"])
atr_val = float(last_row["ATR"])

score = 0
reasons = []

if last_row["EMA_20"] > last_row["EMA_50"]:
  score += 35
  reasons.append("EMA 20 sobre EMA 50 (Estructura Alcista).")
else:
  score -= 35
  reasons.append("EMA 20 bajo EMA 50 (Estructura Bajista).")

if last_row["Close"] > last_row["EMA_200"]:
  score += 25
  reasons.append("Precio sobre EMA 200 Macro.")
else:
  score -= 25
  reasons.append("Precio bajo EMA 200 Macro.")

if last_row["RSI"] < 35:
  score += 30
  reasons.append("RSI en Sobreventa (<35).")
elif last_row["RSI"] > 65:
  score -= 30
  reasons.append("RSI en Sobrecompra (>65).")

total_vol = live_buy_vol + live_sell_vol
buy_pct = (live_buy_vol / total_vol * 100) if total_vol > 0 else 50.0

confidence = min(abs(score) + 35, 96.0)
is_up = score >= 0
candle_prediction = "🟢 SUBIDA" if is_up else "🔴 BAJADA"

expected_range_usd = atr_val * risk_reward_ratio
if is_up:
  take_profit = entry_price + expected_range_usd
  stop_loss = entry_price - atr_val
  type_str = "LONG (COMPRA)"
else:
  take_profit = entry_price - expected_range_usd
  stop_loss = entry_price + atr_val
  type_str = "SHORT (VENTA)"

should_open_trade = confidence >= signal_threshold

# ---------------------------------------------------------
# 5. MONITOREO DE SL / TP Y AUTO-EJECUCIÓN
# ---------------------------------------------------------
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
    st.session_state.trade_history.append({
        "Fecha": datetime.datetime.now().strftime("%H:%M:%S"),
        "Par": act.get("symbol", symbol),
        "Tipo": act_type,
        "Entrada": act_entry,
        "Cierre": entry_price,
        "Resultado": closed_reason,
        "PnL ($)": round(pnl_usd, 2),
    })
    st.session_state.active_trade = None

# Disparo de orden
if auto_execute and should_open_trade and st.session_state.active_trade is None:
  exec_ok = True
  if trading_mode != "Simulación (Paper)":
    is_tn = trading_mode == "Binance Testnet"
    _, res_msg = binance_native_trade(
        symbol,
        type_str,
        trade_amount_usd,
        binance_api_key,
        binance_api_secret,
        is_testnet=is_tn,
    )
    if res_msg != "OK":
      exec_ok = False
      st.error(f"❌ Error en Binance: {res_msg}")

  if exec_ok:
    pos_size = trade_amount_usd / entry_price
    st.session_state.active_trade = {
        "symbol": symbol,
        "type": type_str,
        "entry": entry_price,
        "tp": take_profit,
        "sl": stop_loss,
        "size": pos_size,
        "mode": trading_mode,
        "time": datetime.datetime.now().strftime("%H:%M:%S"),
    }
    st.toast(f"🚀 Orden Abierta: {type_str} en {symbol}")

# ---------------------------------------------------------
# 6. INTERFAZ GRÁFICA Y RENDIMIENTO
# ---------------------------------------------------------
m1, m2, m3, m4 = st.columns(4)
m1.metric("Precio Mercado", f"${entry_price:,.2f}")
m2.metric("Predicción Vela", candle_prediction)
m3.metric("Confianza", f"{confidence:.1f}%")
m4.metric("Balance Simulado", f"${st.session_state.paper_balance:,.2f} USDT")

st.markdown("---")

st.subheader("⚖️ Presión de Mercado en Vivo (Compras vs Ventas)")
col_p1, col_p2 = st.columns(2)
col_p1.metric(
    "🟢 Compras", f"${live_buy_vol:,.2f}", f"{buy_pct:.1f}% del Mercado"
)
col_p2.metric(
    "🔴 Ventas", f"${live_sell_vol:,.2f}", f"{100-buy_pct:.1f}% del Mercado"
)
st.progress(int(buy_pct))

st.markdown("---")

st.subheader("🎮 Estado de Posición Activa")
if st.session_state.active_trade:
  act = st.session_state.active_trade
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

  st.warning(
      f"**POSICIÓN ACTIVA ({act.get('mode', trading_mode)}):** {act_type}"
  )
  st.write(
      f"• **Entrada:** `${act_entry:,.2f}` | **TP:** `${act_tp:,.2f}` | **SL:**"
      f" `${act_sl:,.2f}`"
  )
  st.write(f"• **PnL Flotante:** `${floating_pnl:+,.2f} USDT`")

  if st.button("❌ Cerrar Posición Manualmente"):
    st.session_state.paper_balance += floating_pnl
    st.session_state.active_trade = None
    st.rerun()
else:
  st.info("🤖 **Piloto Automático:** En búsqueda de señales...")

if st.session_state.trade_history:
  st.markdown("##### 📜 Historial de Operaciones")
  st.dataframe(
      pd.DataFrame(st.session_state.trade_history), use_container_width=True
  )

st.markdown("---")

st.subheader(f"🎯 Análisis Técnico — {symbol}")
st.line_chart(df_processed[["Close", "EMA_20", "EMA_50", "EMA_200"]])

# ---------------------------------------------------------
# 7. CICLO DE AUTO-REFRESCO SEGURO (SIN PANTALLA NEGRA)
# ---------------------------------------------------------
if auto_refresh:
  time.sleep(refresh_seconds)
  st.rerun()
