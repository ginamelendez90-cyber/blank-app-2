import datetime
import sqlite3
import pandas as pd
import streamlit as st
import urllib.parse

# Configuración de la Página
st.set_page_config(
    page_title="ControlCobro PRO - Sistema Integral",
    page_icon="💸",
    layout="wide",
)

# ==========================================
# 🎨 ESTILOS CSS MODERNOS
# ==========================================
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    .metric-card {
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
        border: 1px solid #334155;
        padding: 18px;
        border-radius: 12px;
        color: white;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        margin-bottom: 10px;
    }
    .metric-title {
        font-size: 13px;
        color: #94a3b8;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .metric-value {
        font-size: 24px;
        color: #f8fafc;
        font-weight: 700;
        margin-top: 5px;
    }
    .whatsapp-btn {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        background-color: #25D366;
        color: white !important;
        padding: 10px 20px;
        border-radius: 8px;
        font-weight: 600;
        text-decoration: none;
        width: 100%;
        box-shadow: 0 4px 12px rgba(37, 211, 102, 0.3);
    }
    .whatsapp-btn:hover {
        background-color: #22bf5b;
    }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 🗄️ CONFIGURACIÓN DE BASE DE DATOS SQLITE
# ==========================================
def init_db():
    conn = sqlite3.connect("control_cobros.db", check_same_thread=False)
    cursor = conn.cursor()
    
    # Tabla Clientes
    cursor.execute('''CREATE TABLE IF NOT EXISTS clientes (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        nombre TEXT,
                        telefono TEXT,
                        direccion TEXT,
                        score INTEGER
                    )''')
    
    # Tabla Préstamos
    cursor.execute('''CREATE TABLE IF NOT EXISTS prestamos (
                        id_prestamo TEXT PRIMARY KEY,
                        cliente TEXT,
                        monto_prestado REAL,
                        interes REAL,
                        monto_total REAL,
                        cuotas INTEGER,
                        frecuencia TEXT,
                        saldo_pendiente REAL,
                        estado TEXT,
                        fecha_inicio TEXT
                    )''')

    # Tabla Cuotas del Préstamo (Plan de Pagos)
    cursor.execute('''CREATE TABLE IF NOT EXISTS cuotas_plan (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        id_prestamo TEXT,
                        nro_cuota INTEGER,
                        fecha_vencimiento TEXT,
                        monto_cuota REAL,
                        estado TEXT
                    )''')

    # Tabla Pagos / Abonos
    cursor.execute('''CREATE TABLE IF NOT EXISTS pagos (
                        id_pago TEXT PRIMARY KEY,
                        fecha TEXT,
                        cliente TEXT,
                        id_prestamo TEXT,
                        monto_abono REAL,
                        saldo_restante REAL,
                        metodo TEXT
                    )''')

    # Tabla Caja Chica / Gastos
    cursor.execute('''CREATE TABLE IF NOT EXISTS gastos (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        fecha TEXT,
                        descripcion TEXT,
                        monto REAL,
                        tipo TEXT
                    )''')
    conn.commit()
    conn.close()

init_db()

def run_query(query, params=(), fetch=True):
    conn = sqlite3.connect("control_cobros.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute(query, params)
    conn.commit()
    result = cursor.fetchall() if fetch else None
    conn.close()
    return result

# ==========================================
# 🧭 NAVEGACIÓN Y MENÚ PRINCIPAL
# ==========================================
st.markdown("<h1 style='color: #0f172a; font-weight: 800;'>💸 ControlCobro <span style='color: #2563eb;'>PRO</span></h1>", unsafe_allow_html=True)
st.markdown("<p style='color: #64748b; margin-top: -15px;'>Sistema gerencial y operativo para cobradores de calle.</p>", unsafe_allow_html=True)
st.markdown("---")

menu = st.sidebar.selectbox("📂 Módulos del Sistema", [
    "📊 Dashboard y Caja", 
    "🏍️ Ruta de Cobro de Hoy", 
    "👥 Clientes", 
    "📝 Otorgar Préstamo", 
    "💳 Registrar Abono", 
    "💸 Caja y Gastos",
    "⚙️ Ajustes / Base de Datos"
])

# ==========================================
# 1. DASHBOARD Y CAJA
# ==========================================
if menu == "📊 Dashboard y Caja":
    st.subheader("Indicadores Financieros de la Cartera")

    prestamos_df = pd.read_sql("SELECT * FROM prestamos", sqlite3.connect("control_cobros.db"))
    pagos_df = pd.read_sql("SELECT * FROM pagos", sqlite3.connect("control_cobros.db"))
    gastos_df = pd.read_sql("SELECT * FROM gastos", sqlite3.connect("control_cobros.db"))
    clientes_df = pd.read_sql("SELECT * FROM clientes", sqlite3.connect("control_cobros.db"))

    total_cartera = prestamos_df["saldo_pendiente"].sum() if not prestamos_df.empty else 0
    total_cobrado = pagos_df["monto_abono"].sum() if not pagos_df.empty else 0
    total_prestado = prestamos_df["monto_total"].sum() if not prestamos_df.empty else 0
    total_gastos = gastos_df["monto"].sum() if not gastos_df.empty else 0
    efectivo_caja = total_cobrado - total_gastos

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f'<div class="metric-card"><div class="metric-title">Cartera Activa</div><div class="metric-value">${total_cartera:,.2f}</div></div>', unsafe_allow_html=True)
    with col2:
        st.markdown(f'<div class="metric-card"><div class="metric-title">Total Cobrado</div><div class="metric-value" style="color: #4ade80;">${total_cobrado:,.2f}</div></div>', unsafe_allow_html=True)
    with col3:
        st.markdown(f'<div class="metric-card"><div class="metric-title">Efectivo en Caja</div><div class="metric-value" style="color: #38bdf8;">${efectivo_caja:,.2f}</div></div>', unsafe_allow_html=True)
    with col4:
        st.markdown(f'<div class="metric-card"><div class="metric-title">Clientes Totales</div><div class="metric-value">{len(clientes_df)}</div></div>', unsafe_allow_html=True)

    st.markdown("### 📈 Últimos Pagos Registrados")
    if not pagos_df.empty:
        st.dataframe(pagos_df.tail(10), use_container_width=True)
    else:
        st.info("No hay pagos registrados todavía.")

# ==========================================
# 2. RUTA DE COBRO DE HOY
# ==========================================
elif menu == "🏍️ Ruta de Cobro de Hoy":
    st.subheader("Cuotas Programadas para Cobro en Calle")
    
    hoy_str = datetime.date.today().strftime("%Y-%m-%d")
    cuotas_hoy = pd.read_sql(f"SELECT * FROM cuotas_plan WHERE fecha_vencimiento <= '{hoy_str}' AND estado = 'Pendiente'", sqlite3.connect("control_cobros.db"))

    if cuotas_hoy.empty:
        st.success("🎉 ¡Excelente! No hay cuotas pendientes vencidas o programadas para hoy.")
    else:
        st.warning(f"Tienes {len(cuotas_hoy)} cuotas pendientes por cobrar en la ruta.")
        
        # Enriquecer con datos del cliente
        for idx, row in cuotas_hoy.iterrows():
            prestamo_info = run_query("SELECT cliente FROM prestamos WHERE id_prestamo = ?", (row["id_prestamo"],))
            cliente_nombre = prestamo_info[0][0] if prestamo_info else "Desconocido"
            
            cliente_data = run_query("SELECT telefono, direccion FROM clientes WHERE nombre = ?", (cliente_nombre,))
            telefono, direccion = cliente_data[0] if cliente_data else ("", "")

            with st.expander(f"📌 Préstamo: {row['id_prestamo']} | Cliente: {cliente_nombre} | Cuota #{row['nro_cuota']} - ${row['monto_cuota']:,.2f}"):
                st.write(f"🏠 **Dirección:** {direccion}")
                st.write(f"📅 **Vencimiento:** {row['fecha_vencimiento']}")
                st.write(f"💰 **Monto de la Cuota:** ${row['monto_cuota']:,.2f}")

                if telefono:
                    msg = f"Hola {cliente_nombre}, le escribimos de ControlCobro para recordarle su cuota de ${row['monto_cuota']:,.2f} correspondiente al préstamo {row['id_prestamo']}. ¡Gracias por su puntualidad!"
                    wa_url = f"https://wa.me/{telefono}?text={urllib.parse.quote(msg)}"
                    st.markdown(f'<a href="{wa_url}" target="_blank" class="whatsapp-btn">💬 Enviar Recordatorio por WhatsApp</a>', unsafe_allow_html=True)
                else:
                    st.info("El cliente no tiene teléfono registrado.")

# ==========================================
# 3. GESTIÓN DE CLIENTES
# ==========================================
elif menu == "👥 Clientes":
    st.subheader("Directorio de Clientes")

    with st.form("form_cliente"):
        col1, col2 = st.columns(2)
        with col1:
            nombre = st.text_input("Nombre y Apellido")
            telefono = st.text_input("Teléfono (ej: 584120000000)")
        with col2:
            direccion = st.text_input("Dirección / Zona")
            score = st.slider("Score de Confiabilidad", 1, 5, 3)

        submitted = st.form_submit_button("Guardar Cliente")
        if submitted and nombre:
            run_query("INSERT INTO clientes (nombre, telefono, direccion, score) VALUES (?, ?, ?, ?)", (nombre, telefono, direccion, score), fetch=False)
            st.success(f"¡Cliente {nombre} guardado con éxito!")

    clientes_df = pd.read_sql("SELECT * FROM clientes", sqlite3.connect("control_cobros.db"))
    if not clientes_df.empty:
        st.dataframe(clientes_df, use_container_width=True)
    else:
        st.info("No hay clientes registrados.")

# ==========================================
# 4. OTORGAR PRÉSTAMO Y GENERAR CUOTAS
# ==========================================
elif menu == "📝 Otorgar Préstamo":
    st.subheader("Nuevo Crédito y Generador de Cuotas")

    clientes_df = pd.read_sql("SELECT nombre FROM clientes", sqlite3.connect("control_cobros.db"))
    if clientes_df.empty:
        st.warning("⚠️ Registra al menos un cliente antes de otorgar un préstamo.")
    else:
        with st.form("form_prestamo"):
            cliente_sel = st.selectbox("Cliente", clientes_df["nombre"].tolist())
            col1, col2 = st.columns(2)
            with col1:
                monto = st.number_input("Monto Prestado ($)", min_value=10.0, step=10.0)
                interes = st.number_input("Interés Total (%)", min_value=0.0, value=20.0, step=5.0)
            with col2:
                cuotas = st.number_input("Número de Cuotas", min_value=1, value=10, step=1)
                frecuencia = st.selectbox("Frecuencia", ["Diario", "Semanal", "Quincenal", "Mensual"])

            submitted_p = st.form_submit_button("Aprobar y Generar Plan de Pagos")
            if submitted_p:
                total_con_interes = monto * (1 + (interes / 100))
                id_p = f"PRE-{len(pd.read_sql('SELECT * FROM prestamos', sqlite3.connect('control_cobros.db')))+1:03d}"
                fecha_inicio = datetime.date.today().strftime("%Y-%m-%d")

                # Guardar préstamo
                run_query("""INSERT INTO prestamos VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", 
                          (id_p, cliente_sel, monto, interes, total_con_interes, cuotas, frecuencia, total_con_interes, "Activo", fecha_inicio), fetch=False)

                # Generar cuotas automáticas
                monto_por_cuota = total_con_interes / cuotas
                fecha_base = datetime.date.today()
                
                for i in range(1, int(cuotas) + 1):
                    if frecuencia == "Diario":
                        fecha_base += datetime.timedelta(days=1)
                    elif frecuencia == "Semanal":
                        fecha_base += datetime.timedelta(weeks=1)
                    elif frecuencia == "Quincenal":
                        fecha_base += datetime.timedelta(days=15)
                    elif frecuencia == "Mensual":
                        fecha_base += datetime.timedelta(days=30)

                    run_query("INSERT INTO cuotas_plan (id_prestamo, nro_cuota, fecha_vencimiento, monto_cuota, estado) VALUES (?, ?, ?, ?, ?)",
                              (id_p, i, fecha_base.strftime("%Y-%m-%d"), monto_por_cuota, "Pendiente"), fetch=False)

                st.success(f"¡Préstamo {id_p} aprobado y plan de {cuotas} cuotas generado con éxito!")

    prestamos_df = pd.read_sql("SELECT * FROM prestamos", sqlite3.connect("control_cobros.db"))
    if not prestamos_df.empty:
        st.dataframe(prestamos_df, use_container_width=True)

# ==========================================
# 5. REGISTRAR ABONO Y COMPROBANTE WHATSAPP
# ==========================================
elif menu == "💳 Registrar Abono":
    st.subheader("Cobro en Ruta y Comprobante")

    activos_df = pd.read_sql("SELECT * FROM prestamos WHERE estado = 'Activo'", sqlite3.connect("control_cobros.db"))
    if activos_df.empty:
        st.info("No hay préstamos activos.")
    else:
        prestamo_id = st.selectbox("Seleccionar Préstamo", activos_df["id_prestamo"].tolist())
        p_info = activos_df[activos_df["id_prestamo"] == prestamo_id].iloc[0]
        cliente_nombre = p_info["cliente"]
        saldo_actual = p_info["saldo_pendiente"]

        c_info = run_query("SELECT telefono FROM clientes WHERE nombre = ?", (cliente_nombre,))
        telefono_cliente = c_info[0][0] if c_info else ""

        st.markdown(f"**Cliente:** `{cliente_nombre}` | **Saldo Pendiente:** `${saldo_actual:,.2f}`")

        with st.form("form_abono"):
            monto_abono = st.number_input("Monto del Abono ($)", min_value=1.0, max_value=float(saldo_actual), step=1.0)
            metodo = st.selectbox("Método de Pago", ["Efectivo", "Pago Móvil", "Transferencia", "Zelle"])
            submitted_cobro = st.form_submit_button("Registrar Cobro")

            if submitted_cobro:
                nuevo_saldo = saldo_actual - monto_abono
                id_pago = f"REC-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
                fecha_str = datetime.datetime.now().strftime("%d/%m/%Y %I:%M %p")

                # Actualizar saldo préstamo
                nuevo_estado = "Cancelado" if nuevo_saldo <= 0 else "Activo"
                run_query("UPDATE prestamos SET saldo_pendiente = ?, estado = ? WHERE id_prestamo = ?", (nuevo_saldo, nuevo_estado, prestamo_id), fetch=False)

                # Registrar pago
                run_query("INSERT INTO pagos VALUES (?, ?, ?, ?, ?, ?, ?)", (id_pago, fecha_str, cliente_nombre, prestamo_id, monto_abono, nuevo_saldo, metodo), fetch=False)
                
                st.success(f"¡Cobro registrado! Recibo N° {id_pago}")

                # Plantilla WhatsApp
                mensaje_w = f"""🧾 *COMPROBANTE DE ABONO* 🧾
----------------------------------------
📌 *Recibo:* {id_pago}
📅 *Fecha:* {fecha_str}
👤 *Cliente:* {cliente_nombre}
----------------------------------------
💰 *Abono Recibido:* ${monto_abono:,.2f}
💳 *Método:* {metodo}
----------------------------------------
📊 *Estado de Cuenta:*
• *Saldo Anterior:* ${saldo_actual:,.2f}
• *Nuevo Saldo:* ${nuevo_saldo:,.2f}
----------------------------------------
¡Gracias por su puntualidad! 🙏"""

                st.markdown("### 📲 Enviar Comprobante por WhatsApp")
                if telefono_cliente:
                    wa_url = f"https://wa.me/{telefono_cliente}?text={urllib.parse.quote(mensaje_w)}"
                    st.markdown(f'<a href="{wa_url}" target="_blank" class="whatsapp-btn">💬 Enviar Recibo a WhatsApp</a>', unsafe_allow_html=True)
                else:
                    st.warning("El cliente no tiene teléfono registrado.")

                st.text_area("Vista previa del recibo:", value=mensaje_w, height=180)

# ==========================================
# 6. GASTOS Y CAJA CHICA
# ==========================================
elif menu == "💸 Caja y Gastos":
    st.subheader("Control de Gastos Operativos y Caja Chica")

    with st.form("form_gasto"):
        col1, col2 = st.columns(2)
        with col1:
            desc = st.text_input("Descripción del Gasto (Ej: Gasolina, Almuerzo, Repuesto)")
            monto_g = st.number_input("Monto ($)", min_value=0.5, step=1.0)
        with col2:
            tipo_g = st.selectbox("Categoría", ["Gasolina / Movilidad", "Viáticos", "Mantenimiento", "Retiro de Ganancias", "Otro"])

        submitted_g = st.form_submit_button("Registrar Gasto")
        if submitted_g and desc:
            fecha_g = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
            run_query("INSERT INTO gastos (fecha, descripcion, monto, tipo) VALUES (?, ?, ?, ?)", (fecha_g, desc, monto_g, tipo_g), fetch=False)
            st.success("¡Gasto registrado correctamente en caja!")

    gastos_df = pd.read_sql("SELECT * FROM gastos", sqlite3.connect("control_cobros.db"))
    if not gastos_df.empty:
        st.dataframe(gastos_df, use_container_width=True)
    else:
        st.info("No hay gastos registrados.")

# ==========================================
# 7. AJUSTES
# ==========================================
elif menu == "⚙️ Ajustes / Base de Datos":
    st.subheader("Gestión de Respaldos")
    st.markdown("Tu base de datos está guardada localmente en SQLite (`control_cobros.db`). Puedes descargar tus reportes en CSV.")

    pagos_df = pd.read_sql("SELECT * FROM pagos", sqlite3.connect("control_cobros.db"))
    if not pagos_df.empty:
        csv = pagos_df.to_csv(index=False).encode("utf-8")
        st.download_button("📥 Descargar Base de Pagos (CSV)", data=csv, file_name="pagos_exportados.csv", mime="text/csv")
