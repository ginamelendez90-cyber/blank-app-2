import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score
import plotly.graph_objects as go

# Configuración de página
st.set_page_config(page_title="Crypto Predictor Bot", layout="wide")
st.title("🤖 Predictor Automático de Tendencia Cripto")

# 1. Parámetros en barra lateral
st.sidebar.header("Configuración del Par")
ticker = st.sidebar.selectbox("Criptomoneda Base", ["BTC-USD", "ETH-USD", "SOL-USD", "BNB-USD", "XRP-USD"])
interval = st.sidebar.selectbox("Temporalidad de Velas", ["5m", "15m", "1h", "1d"], index=1)
period = st.sidebar.selectbox("Historial de Entrenamiento", ["7d", "30d", "60d"], index=1)

# 2. Descarga automática de datos con caché dinámico (300 segundos)
@st.cache_data(ttl=300)
def load_crypto_data(symbol, p, i):
    df = yf.download(symbol, period=p, interval=i)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df

with st.spinner("Obteniendo datos de mercado..."):
    data = load_crypto_data(ticker, period, interval)

if data.empty or len(data) < 50:
    st.error("No hay suficientes datos disponibles para este intervalo.")
    st.stop()

# 3. Ingeniería de Características (Indicadores Técnicos)
def build_features(df):
    df = df.copy()
    # Rendimiento porcentual y volatilidad
    df['Returns'] = df['Close'].pct_change()
    df['Volatility'] = df['Returns'].rolling(window=10).std()
    
    # Medias Móviles Simples (SMA)
    df['SMA_10'] = df['Close'].rolling(window=10).mean()
    df['SMA_30'] = df['Close'].rolling(window=30).mean()
    df['SMA_Ratio'] = df['SMA_10'] / df['SMA_30']
    
    # RSI (Relative Strength Index)
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / (loss + 1e-9)
    df['RSI'] = 100 - (100 / (1 + rs))
    
    # Variable Objetivo: 1 si la siguiente vela cierra al alza, 0 si baja
    df['Target'] = (df['Close'].shift(-1) > df['Close']).astype(int)
    
    return df.dropna()

df_processed = build_features(data)

# 4. Entrenamiento del Modelo sin Fuga Temporal (Time-Series Split)
feature_cols = ['Returns', 'Volatility', 'SMA_Ratio', 'RSI']
X = df_processed[feature_cols]
y = df_processed['Target']

# Corte secuencial (80% entrenamiento, 20% prueba)
train_size = int(len(X) * 0.8)
X_train, X_test = X.iloc[:train_size], X.iloc[train_size:-1]
y_train, y_test = y.iloc[:train_size], y.iloc[train_size:-1]

# Entrenamiento
model = RandomForestClassifier(n_estimators=100, max_depth=5, random_state=42)
model.fit(X_train, y_train)

# Evaluación
y_pred = model.predict(X_test)
acc = accuracy_score(y_test, y_pred)

# 5. Predicción en Tiempo Real (Última vela no cerrada)
latest_features = X.iloc[[-1]]
prediction = model.predict(latest_features)[0]
probabilities = model.predict_proba(latest_features)[0]

# --- INTERFAZ GRÁFICA ---
current_price = float(data['Close'].iloc[-1])
prob_up = probabilities[1] * 100
prob_down = probabilities[0] * 100

col1, col2, col3, col4 = st.columns(4)
col1.metric("Precio Actual", f"${current_price:,.2f}")
col2.metric("Predicción Próxima Vela", "🟢 SUBIDA" if prediction == 1 else "🔴 BAJADA")
col3.metric("Confianza de Subida", f"{prob_up:.1f}%")
col4.metric("Precisión del Modelo (Test)", f"{acc * 100:.1f}%")

st.markdown("---")

# Gráfico interactivo con Plotly
fig = go.Figure()
fig.add_trace(go.Candlestick(
    x=data.index,
    open=data['Open'], high=data['High'],
    low=data['Low'], close=data['Close'],
    name="Precio"
))
fig.update_layout(title=f"Evolución de Precio - {ticker}", xaxis_rangeslider_visible=False, height=500)
st.plotly_chart(fig, use_container_width=True)

# Importancia de Variables
st.subheader("Importancia de Indicadores en la Predicción")
importance_df = pd.DataFrame({
    'Indicador': feature_cols,
    'Importancia': model.feature_importances_
}).sort_values('Importancia', ascending=False)

st.bar_chart(importance_df.set_index('Indicador'))
