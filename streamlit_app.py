import datetime
from io import BytesIO
import pandas as pd
import streamlit as st

# Configuración de la Página
st.set_page_config(
    page_title="ControlCobro PRO - Sistema de Préstamos",
    page_icon="💸",
    layout="wide",
)

# Inicializar Base de Datos en Session State (Simulando Supabase o CSV)
if "clientes" not in st.session_state:
  st.session_state.clientes = pd.DataFrame(columns=["id", "nombre", "telefono", "direccion", "score"])

if "prestamos" not in st.session_state:
  st.session_state.prestamos = pd.DataFrame(
      columns=[
          "id_prestamo",
          "cliente",
          "monto_prestado",
          "interes",
          "monto_total",
          "cuotas",
          "frecuencia",
          "saldo_pendiente",
          "estado",
      ]
  )

if "pagos" not in st.session_state:
  st.session_state.pagos = pd.DataFrame(columns=["id_pago", "fecha", "cliente", "monto_abono", "saldo_restante", "recibo_n"])

# Título Principal
st.title("💸 ControlCobro PRO: Tu Sistema de Préstamos y Cobranza")
st.markdown("---")

# Menú Lateral
menu = st.sidebar.selectbox("Menú Principal", ["📊 Dashboard General", "👥 Clientes", "📝 Otorgar Préstamo", "💳 Registrar Cobro / Abono", "⚙️ Exportar / Ajustes"])

# ==========================================
# 1. DASHBOARD GENERAL
# ==========================================
if menu == "📊 Dashboard General":
  st.subheader("Resumen Financiero de la Ruta")

  col1, col2, col3, col4 = st.columns(4)

  total_prestado = (
      st.session_state.prestamos["monto_total"].sum() if not st.session_state.prestamos.empty else 0
  )
  total_cobrado = st.session_state.pagos["monto_abono"].sum() if not st.session_state.pagos.empty else 0
  total_cartera = (
      st.session_state.prestamos["saldo_pendiente"].sum() if not st.session_state.prestamos.empty else 0
  )

  col1.metric("Capital Cartera Activa", f"${total_cartera:,.2f}")
  col2.metric("Total Cobrado", f"${total_cobrado:,.2f}")
  col3.metric("Total Prestado", f"${total_prestado:,.2f}")
  col4.metric("Clientes Registrados", len(st.session_state.clientes))

  st.markdown("### Últimos Pagos Registrados")
  if not st.session_state.pagos.empty:
    st.dataframe(st.session_state.pagos.tail(10), use_container_width=True)
  else:
    st.info("No hay pagos registrados todavía.")

# ==========================================
# 2. GESTIÓN DE CLIENTES
# ==========================================
elif menu == "👥 Clientes":
  st.subheader("Gestión de Prestatarios")

  with st.form("form_cliente"):
    col1, col2 = st.columns(2)
    with col1:
      nombre = st.text_input("Nombre y Apellido del Cliente")
      telefono = st.text_input("Teléfono (con código país, ej: 584120000000)")
    with col2:
      direccion = st.text_input("Dirección / Zona de Cobro")
      score = st.slider("Calificación (Score de Confianza)", 1, 5, 3)

    submitted = st.form_submit_button("Registrar Cliente")
    if submitted and nombre:
      nuevo_id = len(st.session_state.clientes) + 1
      nuevo_cliente = pd.DataFrame(
          [{"id": nuevo_id, "nombre": nombre, "telefono": telefono, "direccion": direccion, "score": score}]
      )
      st.session_state.clientes = pd.concat([st.session_state.clientes, nuevo_cliente], ignore_index=True)
      st.success(f"¡Cliente {nombre} registrado con éxito!")

  st.markdown("### Listado de Clientes")
  if not st.session_state.clientes.empty:
    st.dataframe(st.session_state.clientes, use_container_width=True)
  else:
    st.info("Aún no hay clientes registrados.")

# ==========================================
# 3. OTORGAR PRÉSTAMO
# ==========================================
elif menu == "📝 Otorgar Préstamo":
  st.subheader("Crear Nuevo Crédito")

  if st.session_state.clientes.empty:
    st.warning("Debes registrar al menos un cliente antes de otorgar un préstamo.")
  else:
    with st.form("form_prestamo"):
      cliente_seleccionado = st.selectbox("Seleccionar Cliente", st.session_state.clientes["nombre"].tolist())
      col1, col2 = st.columns(2)
      with col1:
        monto = st.number_input("Monto a Prestar ($)", min_value=10.0, step=10.0)
        interes_pct = st.number_input("Porcentaje de Interés (%)", min_value=0.0, value=20.0, step=5.0)
      with col2:
        cuotas = st.number_input("Número de Cuotas", min_value=1, value=10, step=1)
        frecuencia = st.selectbox("Frecuencia de Pago", ["Diario", "Semanal", "Quincenal", "Mensual"])

      submitted_p = st.form_submit_button("Aprobar y Emitir Préstamo")
      if submitted_p:
        total_con_interes = monto * (1 + interes_pct / 100)
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
        st.success(f"¡Préstamo {id_p} creado exitosamente por un total de ${total_con_interes:,.2f}!")

  st.markdown("### Préstamos Activos")
  if not st.session_state.prestamos.empty:
    st.dataframe(st.session_state.prestamos, use_container_width=True)

# ==========================================
# 4. REGISTRAR COBRO Y GENERAR WHATSAPP
# ==========================================
elif menu == "💳 Registrar Cobro / Abono":
  st.subheader("Registrar Abono y Enviar Comprobante")

  prestamos_activos = st.session_state.prestamos[st.session_state.prestamos["estado"] == "Activo"]

  if prestamos_activos.empty:
    st.info("No hay préstamos activos para cobrar.")
  else:
    prestamo_id = st.selectbox("Seleccionar Préstamo / Cliente", prestamos_activos["id_prestamo"].tolist())
    
    # Obtener datos del préstamo seleccionado
    p_info = prestamos_activos[prestamos_activos["id_prestamo"] == prestamo_id].iloc[0]
    cliente_nombre = p_info["cliente"]
    saldo_actual = p_info["saldo_pendiente"]
    
    # Buscar teléfono del cliente
    c_info = st.session_state.clientes[st.session_state.clientes["nombre"] == cliente_nombre]
    telefono_cliente = c_info["telefono"].values[0] if not c_info.empty else ""

    st.markdown(f"**Cliente:** {cliente_nombre} | **Saldo Pendiente Actual:** ${saldo_actual:,.2f}")

    with st.form("form_cobro"):
      monto_abono = st.number_input("Monto del Abono a Registrar ($)", min_value=1.0, max_value=float(saldo_actual), step=1.0)
      metodo_pago = st.selectbox("Método de Pago", ["Efectivo", "Pago Móvil", "Transferencia", "Zelle"])
      
      submitted_cobro = st.form_submit_button("Registrar Pago y Generar Comprobante")

      if submitted_cobro:
        nuevo_saldo = saldo_actual - monto_abono
        nro_recibo = f"REC-2026-{len(st.session_state.pagos)+1:04d}"
        fecha_str = datetime.datetime.now().strftime("%d/%m/%Y %I:%M %p")

        # Actualizar saldo en prestamos
        st.session_state.prestamos.loc[st.session_state.prestamos["id_prestamo"] == prestamo_id, "saldo_pendiente"] = nuevo_saldo
        if nuevo_saldo <= 0:
          st.session_state.prestamos.loc[st.session_state.prestamos["id_prestamo"] == prestamo_id, "estado"] = "Cancelado"

        # Registrar pago
        nuevo_pago = pd.DataFrame([{
            "id_pago": nro_recibo,
            "fecha": fecha_str,
            "cliente": cliente_nombre,
            "monto_abono": monto_abono,
            "saldo_restante": nuevo_saldo,
            "recibo_n": nro_recibo
        }])
        st.session_state.pagos = pd.concat([st.session_state.pagos, nuevo_pago], ignore_index=True)

        st.success(f"¡Abono registrado con éxito! Recibo N° {nro_recibo}")

        # Generar Mensaje para WhatsApp
        mensaje_w = f"""🧾 *COMPROBANTE DE PAGO* 🧾
----------------------------------------
📌 *Recibo:* {nro_recibo}
📅 *Fecha:* {fecha_str}
👤 *Cliente:* {cliente_nombre}
----------------------------------------
💰 *Abono realizado:* ${monto_abono:,.2f}
💳 *Método:* {metodo_pago}
----------------------------------------
📊 *Estado de Cuenta:*
• *Saldo Anterior:* ${saldo_actual:,.2f}
• *Nuevo Saldo:* ${nuevo_saldo:,.2f}
----------------------------------------
¡Gracias por su pago puntual! 🙏"""

        st.markdown("### 📲 Enviar Comprobante por WhatsApp al Cliente")
        if telefono_cliente:
          import urllib.parse
          encoded_msg = urllib.parse.quote(mensaje_w)
          whatsapp_url = f"https://wa.me/{telefono_cliente}?text={encoded_msg}"
          st.markdown(f'<a href="{whatsapp_url}" target="_blank"><button style="background-color:#25D366; color:white; padding:10px 20px; border:none; border-radius:5px; font-weight:bold; cursor:pointer;">🚀 Enviar Comprobante por WhatsApp</button></a>', unsafe_allow_html=True)
        else:
          st.warning("El cliente no tiene un número de teléfono registrado. Agrégalo en la sección de Clientes.")

        st.text_area("Texto del recibo generado:", value=mensaje_w, height=200)

# ==========================================
# 5. EXPORTAR Y AJUSTES
# ==========================================
elif menu == "⚙️ Exportar / Ajustes":
  st.subheader("Respaldo y Exportación de Datos")

  st.markdown("Puedes descargar toda la información de tus cobros y cartera en formato CSV para abrirlo directamente en **Google Sheets** o Excel.")

  if not st.session_state.pagos.empty:
    csv = st.session_state.pagos.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="📥 Descargar Reporte de Pagos (CSV)",
        data=csv,
        file_name="reporte_cobros.csv",
        mime="text/csv",
    )
  else:
    st.info("No hay pagos para exportar.")
