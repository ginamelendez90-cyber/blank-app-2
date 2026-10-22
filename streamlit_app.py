import time
from datetime import datetime
import streamlit as st

st.set_page_config(
    page_title="Sistema de Recuperación Anti-Apuestas",
    page_icon="🛡️",
    layout="wide",
)

# Menú lateral de navegación
st.sidebar.title("🛡️ Tu Escudo Personal")
opcion = st.sidebar.selectbox(
    "Selecciona una sección",
    [
        "Dashboard Principal",
        "🚨 Botón de Pánico",
        "📊 Diario de Detonantes",
        "💰 Control Financiero",
    ],
)

if opcion == "Dashboard Principal":
  st.title("Panel de Control de Recuperación")

  # Simulación de fecha de última recaída (idealmente guardada en Base de Datos o Session State)
  fecha_inicio = datetime(2026, 9, 1, 0, 0, 0)
  tiempo_transcurrido = datetime.now() - fecha_inicio

  dias = tiempo_transcurrido.days
  horas = int(tiempo_transcurrido.seconds / 3600)

  col1, col2, col3 = st.columns(3)
  col1.metric("Días sin apostar", f"{dias} días")
  col2.metric("Horas adicionales", f"{horas} hrs")
  col3.metric("Dinero Ahorrado Estimado", f"${dias * 20:,.2f}")  # Ejemplo base

  st.info(
      "💡 'El primer paso para salir del pozo es dejar de cavar. Cada día limpio"
      " es una victoria'."
  )

elif opcion == "🚨 Botón de Pánico":
  st.title("🚨 Zona de Interrupción de Urgencia")
  st.error("¡Alto! Detente un momento antes de tomar una decisión impulsiva.")

  if st.button("🆘 Activar Protocolo de Emergencia (15 minutos)"):
    with st.spinner(
        "Respirando hondo... Deja que pase la urgencia inicial..."
    ):
      progress_bar = st.progress(0)
      for i in range(100):
        time.sleep(0.1)  # Simulación de pausa táctica
        progress_bar.progress(i + 1)
    st.success(
        "Has superado el primer impulso crítico. El cerebro empieza a recuperar"
        " el control racional."
    )
    st.write(
        "👉 Llama ahora a tu persona de confianza o sal a caminar 10 minutos."
    )

elif opcion == "📊 Diario de Detonantes":
  st.title("Registro de Emociones y Detonantes")
  emocion = st.selectbox(
      "¿Qué emoción o situación gatilló la ansiedad?",
      ["Ansiedad", "Aburrimiento", "Problemas de dinero", "Estrés laboral", "Otro"],
  )
  nota = st.text_area("Describe brevemente qué estabas pensando:")
  if st.button("Guardar Registro"):
    st.success("Registro guardado. Tomar conciencia es vencer el patrón.")

elif opcion == "💰 Control Financiero":
  st.title("Estado de Deudas y Presupuesto")
  st.write(
      "Mantén el control estricto de tu dinero bloqueando cuentas y planificando"
      " tus pagos."
  )
  # Aquí puedes integrar tablas con Pandas y Supabase para almacenar las finanzas del usuario de forma segura.
