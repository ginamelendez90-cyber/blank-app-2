import feedparser
import pandas as pd
import streamlit as st

# Configuración de la página
st.set_page_config(
    page_title="Detector de Impacto Global",
    page_icon="🚨",
    layout="wide"
)

# Título y encabezado
st.title("🚨 Detector de Noticias e Impacto Global")
st.write(
    "Monitoreo en tiempo real con filtrado inteligente de noticias criticas y de alto impacto a nivel mundial."
)

# 1. Fuentes de Noticias RSS Internacionales
RSS_FEEDS = {
    "BBC Mundo": "https://feeds.bbci.co.uk/spanish/rss.xml",
    "CNN en Español": "https://cnnespanol.cnn.com/feed/",
    "El País - Internacional": "https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/section/internacional/index.xml",
    "DW (Español)": "https://rss.dw.com/xml/rss_es_noticias",
}

# 2. Diccionario de Palabras Clave de Alto Impacto
HIGH_IMPACT_KEYWORDS = [
    "urgente", "alerta", "última hora", "crisis", "guerra", "conflicto", 
    "elecciones", "presidente", "banco central", "inflación", "terremoto", 
    "sismo", "emergencia", "acuerdo", "sanciones", "cumbre", "tragedia", "petróleo"
]

def calcular_nivel_impacto(texto):
    """
    Función que analiza el texto y calcula un nivel de impacto 
    basado en la presencia de palabras clave críticas.
    """
    texto_lower = texto.lower()
    coincidencias = [kw for kw in HIGH_IMPACT_KEYWORDS if kw in texto_lower]
    
    # Retorna el conteo y la lista de palabras clave encontradas
    return len(coincidencias), coincidencias


@st.cache_data(ttl=300) # Actualiza los feeds cada 5 minutos
def cargar_y_analizar_noticias():
    todas_noticias = []
    
    for fuente, url in RSS_FEEDS.items():
        feed = feedparser.parse(url)
        for entry in feed.entries:
            titulo = entry.title
            link = entry.link
            resumen = getattr(entry, "summary", "Sin descripción disponible.")
            publicado = getattr(entry, "published", "Reciente")
            
            # Analizar impacto sumando título + resumen
            texto_completo = f"{titulo} {resumen}"
            score, palabras_detectadas = calcular_nivel_impacto(texto_completo)
            
            todas_noticias.append({
                "fuente": fuente,
                "titulo": titulo,
                "link": link,
                "resumen": resumen,
                "publicado": publicado,
                "impacto_score": score,
                "palabras_clave": palabras_detectadas
            })
            
    df = pd.DataFrame(todas_noticias)
    return df

# Cargar las noticias analizadas
with st.spinner("Analizando fuentes internacionales en tiempo real..."):
    df_noticias = cargar_y_analizar_noticias()

# --- PANEL LATERAL DE CONTROLES ---
st.sidebar.header("⚙️ Filtros de Detección")

# Filtro por fuente
fuentes_seleccionadas = st.sidebar.multiselect(
    "Filtrar por Fuentes:",
    options=list(RSS_FEEDS.keys()),
    default=list(RSS_FEEDS.keys())
)

# Filtro por Nivel de Impacto
solo_alto_impacto = st.sidebar.checkbox("🔥 Mostrar SOLO noticias de alto impacto", value=False)

# Búsqueda manual por palabra clave
busqueda_custom = st.sidebar.text_input("🔍 Buscar término específico:", "").lower()


# --- FILTRADO DE DATOS ---
df_filtrado = df_noticias[df_noticias["fuente"].isin(fuentes_seleccionadas)]

if solo_alto_impacto:
    df_filtrado = df_filtrado[df_filtrado["impacto_score"] > 0]

if busqueda_custom:
    df_filtrado = df_filtrado[
        df_filtrado["titulo"].str.lower().str.contains(busqueda_custom) | 
        df_filtrado["resumen"].str.lower().str.contains(busqueda_custom)
    ]

# Ordenar para mostrar las de mayor impacto primero
df_filtrado = df_filtrado.sort_values(by="impacto_score", ascending=False)


# --- VISTA PRINCIPAL DE LA APP ---

# Métricas rápidas arriba
col1, col2, col3 = st.columns(3)
col1.metric("Noticias Monitoreadas", len(df_noticias))
col2.metric("Alertas de Alto Impacto", len(df_noticias[df_noticias["impacto_score"] > 0]))
col3.metric("Fuentes Activas", len(fuentes_seleccionadas))

st.markdown("---")

# 1. SECCIÓN DE ALERTAS CRÍTICAS DE ÚLTIMA HORA (Top Impacto)
top_alertas = df_noticias[df_noticias["impacto_score"] >= 2]

if not top_alertas.empty and not solo_alto_impacto:
    st.error("🚨 **ALERTAS DESTACADAS DE ALTO IMPACTO GLOBAL**")
    for _, row in top_alertas.head(3).iterrows():
        with st.expander(f"🔴 [{row['fuente']}] {row['titulo']}", expanded=True):
            st.write(row['resumen'])
            st.caption(f"Palabras críticas detectadas: **{', '.join(row['palabras_clave'])}** | [Leer noticia completa]({row['link']})")
    st.markdown("---")

# 2. FEED GENERAL DE NOTICIAS FILTRADAS
st.subheader("📰 Feed de Noticias")

if df_filtrado.empty:
    st.info("No se encontraron noticias con los filtros seleccionados.")
else:
    for _, row in df_filtrado.iterrows():
        with st.container():
            # Encabezado visual según nivel de impacto
            if row["impacto_score"] > 0:
                badge = f"🔥 **IMPACTO DETECTADO** (Términos: *{', '.join(row['palabras_clave'])}*)"
            else:
                badge = "ℹ️ Noticia Estándar"
                
            st.markdown(f"#### [{row['titulo']}]({row['link']})")
            st.caption(f"📌 **Fuente:** {row['fuente']} | 📅 {row['publicado']} | {badge}")
            st.write(row['resumen'])
            st.markdown("---")
