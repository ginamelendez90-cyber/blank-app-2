import streamlit as st

st.set_page_config(page_title="AI Video Automation Hub", page_icon="🚀", layout="wide")

st.title("🚀 Central de Automatización de Videos y Nichos")

# Sidebar con claves únicas para evitar conflictos en el DOM
st.sidebar.header("Panel de Control A.X.I.S.")
niche_option = st.sidebar.selectbox(
    "Selecciona el Nicho de Alto RPM",
    ["Inteligencia Artificial y Futuro", "Psicología Oscura y Poder Mental", "Finanzas y Libertad Financiera"],
    key="select_niche_main"
)

action_mode = st.sidebar.radio(
    "Fase de Operación",
    ["1. Escanear Tendencias", "2. Generar Guion Viral", "3. Renderizar Video Automático"],
    key="radio_action_mode"
)

if action_mode == "1. Escanear Tendencias":
    st.subheader(f"📊 Análisis de Tendencias para: {niche_option}")
    if st.button("Ejecutar Escaneo Algorítmico", key="btn_scan_trends"):
        st.success("¡Tendencias analizadas con éxito!")
        st.metric(label="RPM Estimado Promedio", value="$14.50 USD / 1k vistas", delta="+2.3%")

elif action_mode == "2. Generar Guion Viral":
    st.subheader("✍️ Generador de Guiones de Alta Retención")
    topic_input = st.text_input("Ingresa el tema específico:", "El error mental que te impide acumular capital", key="input_topic_script")
    if st.button("Crear Guion Optimizado", key="btn_create_script"):
        st.info("Estructurando ganchos y patrones de interrupción...")

elif action_mode == "3. Renderizar Video Automático":
    st.subheader("🎬 Ensamblaje y Producción")
    if st.button("Iniciar Producción Masiva", key="btn_render_video"):
        with st.spinner("Procesando audio, subtítulos y secuencias visuales..."):
            import time
            time.sleep(2)
        st.success("¡Video renderizado con éxito!")
