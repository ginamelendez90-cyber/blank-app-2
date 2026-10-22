import datetime
import pandas as pd
import streamlit as st

# Configuración de la Página
st.set_page_config(
    page_title="ControlCobro PRO - Sistema Financiero",
    page_icon="💸",
    layout="wide",
)

# ==========================================
# ESTILOS CSS PERSONALIZADOS (Estilo Moderno Web)
# ==========================================
st.markdown("""
    <style>
    /* Ocultar elementos por defecto de Streamlit para limpieza visual */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Contenedores de Tarjetas Modernas */
    .metric-card {
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
        border: 1px solid #334155;
        padding: 20px;
        border-radius: 12px;
        color: white;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
        margin-bottom: 15px;
    }
    .metric-title {
        font-size: 14px;
        color: #94a3b8;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .metric-value {
        font-size: 26px;
        color: #f8fafc;
        font-weight: 700;
        margin-top: 5px;
    }
    
    /* Botones y Enlaces Estilizados */
    .whatsapp-btn {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        background-color: #25D366;
        color: white !important;
        padding: 12px 24px;
        border-radius: 8px;
        font-weight: 600;
        text-decoration: none;
        width: 100%;
        box-shadow: 0 4px 12px rgba(37, 211, 102, 0.3);
        transition: all 0.3s ease;
    }
    .whatsapp-btn:hover {
        background-color: #22bf5b;
        box-shadow: 0 6px 15px rgba(37, 211, 102, 0.4);
    }
    </style>
""", unsafe_allow_html=True)

# Inicializar Base de Datos en Session State
if "clientes" not in st.session_state:
    st.session_state.clientes = pd.DataFrame(columns=["id", "nombre", "telefono", "direccion", "score"])

if "prestamos" not in st.session_state:
    st.session_state.prestamos = pd.DataFrame(columns=[
        "id_prestamo", "cliente", "monto_prestado", "interes", "monto_total", "cuotas", "frecuencia", "saldo_pendiente", "estado"
    ])

if "pagos" not in st.session_state:
    st.session_state.pagos = pd.DataFrame(columns=["id_pago", "fecha", "cliente", "monto_abono", "saldo_restante", "recibo_n"])

# ==========================================
# ENCABEZADO Y MENÚ LATERAL
# ==========================================
st.markdown("<h1 style='color: #0f172a; font-weight: 800;'>💸 ControlCobro <span style='color: #2563eb;'>PRO</span></h1>", unsafe_allow_html=True)
st.markdown("<p style='color: #64748b; margin-top: -15px;'>Sistema inteligente de préstamos, cobranza en ruta y comprobantes por WhatsApp.</p>", unsafe_allow_html=True)
st.markdown("---")

menu = st.sidebar.selectbox("📂 Menú Principal", [
    "📊 Dashboard General", 
    "👥 Clientes", 
    "📝 Otorgar Préstamo", 
    "💳 Registrar Cobro / Abono", 
    "⚙️ Exportar Datos"
])

# ==========================================
# 1. DASHBOARD GENERAL
# ==========================================
if menu == "📊 Dashboard General":
    st.subheader("Resumen de Cartera")

    total_prestado = st.session_state.prestamos["monto_total"].sum() if not st.session_state.prestamos.empty else 0
    total_cobrado = st.session_state.pagos["monto_abono"].sum() if not st.session_state.pagos.empty else 0
    total_cartera = st.session_state.prestamos["saldo_pendiente"].sum() if not st.session_state.prestamos.empty else 0
    total_clientes = len(st.session_state.clientes)

    # Tarjetas Métricas Modernas con HTML/CSS
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
            <div class="metric-card">
                <div class="metric-title">Cartera Activa</div>
                <div class="metric-value">${total_cartera:,.2f}</div>
            </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
            <div class="metric-card">
                <div class="metric-title">Total Cobrado</div>
                <div class="metric-value" style="color: #4ade80;">${total_cobrado:,.2f}</div>
            </div>
        """, unsafe_allow_html=True)
    with col3:
        st.markdown(f"""
            <div class="metric-card">
                <div class="metric-title">Capital Prestado</div>
                <div class="metric-value">${total_prestado:,.2f}</div>
            </div>
        """, unsafe_allow_html=True)
    with col4:
        st.markdown(f"""
            <div class="metric-card">
                <div class="metric-title">Clientes Totales</div>
                <div class="metric-value">{total_clientes}</div>
            </div>
        """, unsafe_allow_html=True)

    st.markdown("### 📋 Historial de Últimos Pagos")
    if not st.session_state.pagos.empty:
        st.dataframe(st.session_state.pagos.tail(10), use_container_width=True)
    else:
        st.info("No hay pagos registrados todavía en el sistema.")

# ==========================================
# 2. GESTIÓN DE CLIENTES
# ==========================================
elif menu == "👥 Clientes":
    st.subheader("Registro y Control de Prestatarios")

    with st.form("form_cliente"):
        col1, col2 = st.columns(2)
        with col1:
            nombre = st.text_input("Nombre y Apellido del Cliente")
            telefono = st.text_input("Teléfono (ej: 584120000000 - con código de país)")
        with col2:
            direccion = st.text_input("Dirección / Zona o Localidad")
            score = st.slider("Scoring de Confianza", 1, 5, 3)

        submitted = st.form_submit_button("Guardar Cliente")
        if submitted and nombre:
            nuevo_id = len(st.session_state.clientes) + 1
            nuevo_cliente = pd.DataFrame([{
                "id": nuevo_id, "nombre": nombre, "telefono": telefono, "direccion": direccion, "score": score
            }])
            st.session_state.clientes = pd.concat([st.session_state.clientes, nuevo_cliente], ignore_index=True)
            st.success(f"¡Cliente {nombre} registrado exitosamente!")

    st.markdown("### Directorio de Clientes")
    if not st.session_state.clientes.empty:
        st.dataframe(st.session_state.clientes, use_container_width=True)
    else:
        st.info("Aún no tienes clientes registrados.")

# ==========================================
# 3. OTORGAR PRÉSTAMO
# ==========================================
elif menu == "📝 Otorgar Préstamo":
    st.subheader("Otorgar Nuevo Crédito")

    if st.session_state.clientes.empty:
        st.warning("⚠️ Debes registrar al menos un cliente antes de otorgar un préstamo.")
    else:
        with st.form("form_prestamo"):
            cliente_seleccionado = st.selectbox("Seleccionar Cliente", st.session_state.clientes["nombre"].tolist())
            col1, col2 = st.columns(2)
            with col1:
                monto = st.number_input("Monto del Préstamo ($)", min_value=10.0, step=10.0)
                interes_pct = st.number_input("Porcentaje de Interés (%)", min_value=0.0, value=20.0, step=5.0)
            with col2:
                cuotas = st.number_input("Número de Cuotas", min_value=1, value=10, step=1)
                frecuencia = st.selectbox("Frecuencia de Pago", ["Diario", "Semanal", "Quincenal", "Mensual"])

            submitted_p = st.form_submit_button("Aprobar y Emitir Crédito")
            if submitted_p:
                total_con_interes = monto * (1 + (interes_pct / 100))
                id_p = f"PRE-{len(st.session_state.prestamos)+1:03d}"
                
                nuevo_p = pd.DataFrame([{
                    "id_prestamo": id_p,
                    "cliente": cliente_seleccionado,
                    "monto_prestado": monto,
                    "interes": interes_pct,
                    "monto_total": total_con_interes,
                    "cuotas": cuotas,
                    "frecuencia": frecuencia,
                    "saldo_pendiente": total_con_interes,
                    "estado": "Activo"
                }])
                st.session_state.prestamos = pd.concat([st.session_state.prestamos, nuevo_p], ignore_index=True)
                st.success(f"¡Préstamo {id_p} emitido por un total de ${total_con_interes:,.2f}!")

    st.markdown("### Créditos Activos")
    if not st.session_state.prestamos.empty:
        st.dataframe(st.session_state.prestamos, use_container_width=True)

# ==========================================
# 4. REGISTRAR COBRO Y WHATSAPP
# ==========================================
elif menu == "💳 Registrar Cobro / Abono":
    st.subheader("Cobranza y Envío de Comprobante")

    prestamos_activos = st.session_state.prestamos[st.session_state.prestamos["estado"] == "Activo"]

    if prestamos_activos.empty:
        st.info("No hay préstamos activos para cobrar en este momento.")
    else:
        prestamo_id = st.selectbox("Seleccionar Crédito", prestamos_activos["id_prestamo"].tolist())
        
        p_info = prestamos_activos[prestamos_activos["id_prestamo"] == prestamo_id].iloc[0]
        cliente_nombre = p_info["cliente"]
        saldo_actual = p_info["saldo_pendiente"]
        
        c_info = st.session_state.clientes[st.session_state.clientes["nombre"] == cliente_nombre]
        telefono_cliente = c_info["telefono"].values[0] if not c_info.empty else ""

        st.markdown(f"**Cliente Asignado:** `{cliente_nombre}` | **Saldo Pendiente:** `${saldo_actual:,.2f}`")

        with st.form("form_cobro"):
            monto_abono = st.number_input("Monto del Abono ($)", min_value=1.0, max_value=float(saldo_actual), step=1.0)
            metodo_pago = st.selectbox("Método de Abono", ["Efectivo", "Pago Móvil", "Transferencia", "Zelle"])
            
            submitted_cobro = st.form_submit_button("Registrar Cobro")

            if submitted_cobro:
                nuevo_saldo = saldo_actual - monto_abono
                nro_recibo = f"REC-2026-{len(st.session_state.pagos)+1:04d}"
                fecha_str = datetime.datetime.now().strftime("%d/%m/%Y %I:%M %p")

                st.session_state.prestamos.loc[st.session_state.prestamos["id_prestamo"] == prestamo_id, "saldo_pendiente"] = nuevo_saldo
                if nuevo_saldo <= 0:
                    st.session_state.prestamos.loc[st.session_state.prestamos["id_prestamo"] == prestamo_id, "estado"] = "Cancelado"

                nuevo_pago = pd.DataFrame([{
                    "id_pago": nro_recibo,
                    "fecha": fecha_str,
                    "cliente": cliente_nombre,
                    "monto_abono": monto_abono,
                    "saldo_restante": nuevo_saldo,
                    "recibo_n": nro_recibo
                }])
                st.session_state.pagos = pd.concat([st.session_state.pagos, nuevo_pago], ignore_index=True)
                st.success(f"¡Cobro registrado! Recibo N° {nro_recibo}")

                # Plantilla de Comprobante WhatsApp
                mensaje_w = f"""🧾 *COMPROBANTE DE ABONO* 🧾
----------------------------------------
📌 *Recibo N°:* {nro_recibo}
📅 *Fecha:* {fecha_str}
👤 *Cliente:* {cliente_nombre}
----------------------------------------
💰 *Abono Recibido:* ${monto_abono:,.2f}
💳 *Método:* {metodo_pago}
----------------------------------------
📊 *Estado de Cuenta:*
• *Saldo Anterior:* ${saldo_actual:,.2f}
• *Nuevo Saldo Pendiente:* ${nuevo_saldo:,.2f}
----------------------------------------
¡Gracias por su puntualidad! 🙏"""

                st.markdown("### 📲 Enviar Comprobante Directo al WhatsApp")
                if telefono_cliente:
                    import urllib.parse
                    encoded_msg = urllib.parse.quote(mensaje_w)
                    whatsapp_url = f"https://wa.me/{telefono_cliente}?text={encoded_msg}"
                    st.markdown(f'<a href="{whatsapp_url}" target="_blank" class="whatsapp-btn">💬 Enviar Comprobante a WhatsApp</a>', unsafe_allow_html=True)
                else:
                    st.warning("⚠️ Este cliente no tiene número de teléfono registrado.")

                st.text_area("Vista previa del texto del recibo:", value=mensaje_w, height=180)

# ==========================================
# 5. EXPORTAR DATOS
# ==========================================
elif menu == "⚙️ Exportar Datos":
    st.subheader("Exportación de Historial")
    st.markdown("Descarga tu base de datos de pagos en formato CSV para respaldarla o sincronizarla con **Google Sheets**.")

    if not st.session_state.pagos.empty:
        csv = st.session_state.pagos.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="📥 Descargar Reporte en CSV",
            data=csv,
            file_name="reporte_cobranza.csv",
            mime="text/csv",
        )
    else:
        st.info("No hay registros de pagos para exportar.")
