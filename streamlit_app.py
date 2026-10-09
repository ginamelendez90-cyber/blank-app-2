import hashlib
import hmac
import time
import requests


def binance_api_request(
    endpoint: str,
    method: str = "GET",
    params: dict = None,
    api_key: str = "",
    api_secret: str = "",
    testnet: bool = True,
):
  """Conector nativo ultra-ligero para Binance API (sin librerías externas)."""
  base_url = (
      "https://testnet.binance.vision" if testnet else "https://api.binance.com"
  )
  url = f"{base_url}{endpoint}"

  if params is None:
    params = {}

  # Agregar timestamp obligatorio para la firma HMAC
  params["timestamp"] = int(time.time() * 1000)
  params["recvWindow"] = 5000

  # Crear cadena de consulta y firma digital HMAC SHA256
  query_string = "&".join([f"{k}={v}" for k, v in params.items()])
  signature = hmac.new(
      api_secret.encode("utf-8"),
      query_string.encode("utf-8"),
      hashlib.sha256,
  ).hexdigest()

  full_url = f"{url}?{query_string}&signature={signature}"
  headers = {"X-MBX-APIKEY": api_key}

  try:
    if method == "POST":
      response = requests.post(full_url, headers=headers, timeout=5)
    elif method == "DELETE":
      response = requests.delete(full_url, headers=headers, timeout=5)
    else:
      response = requests.get(full_url, headers=headers, timeout=5)

    return response.json()
  except Exception as e:
    return {"error": str(e)}


def execute_native_binance_trade(
    symbol_raw, side_type, amount_usd, api_key, api_secret, testnet=True
):
  """Envía una orden SPOT a Binance usando el conector nativo."""
  binance_symbol = symbol_raw.replace("-", "")

  # 1. Obtener precio actual del par
  ticker_res = requests.get(
      f'https://api.binance.com/api/v3/ticker/price?symbol={binance_symbol}'
  ).json()
  if "price" not in ticker_res:
    return None, f"Error obteniendo precio: {ticker_res}"

  curr_price = float(ticker_res["price"])
  qty_precision = 5 if "BTC" in symbol_raw else 2
  quantity = round(amount_usd / curr_price, qty_precision)

  side = "BUY" if "LONG" in side_type else "SELL"

  # 2. Enviar orden a la API
  order_params = {
      "symbol": binance_symbol,
      "side": side,
      "type": "MARKET",
      "quantity": quantity,
  }

  res = binance_api_request(
      endpoint="/api/v3/order",
      method="POST",
      params=order_params,
      api_key=api_key,
      api_secret=api_secret,
      testnet=testnet,
  )

  if "orderId" in res:
    return res, "OK"
  else:
    return None, res.get("msg", str(res))
