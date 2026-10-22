import datetime
import sqlite3
import pandas as pd
import streamlit as st
import urllib.parse

# Configuración de la Página
st.set_page_config(
    page_title="ControlCobro PRO - Tesorería y Préstamos",
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
        padding: 16px;
        border-radius: 12px;
        color: white;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        margin-bottom: 10px;
    }
    .metric-title {
        font-size: 12px;
        color: #94a3b8;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .metric-value {
        font-size: 22px;
        color: #f8fafc;
        font-weight: 700;
        margin-top: 4px;
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
# 🗄️ BASE DE DATOS Y TESORERÍA
# ==========================================
def init_db():
    conn = sqlite3.connect("control_cobros_pro.db", check_same_thread=False)
    cursor = conn.cursor()
    
    # Clientes
    cursor.execute('''CREATE TABLE IF NOT EXISTS clientes (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        nombre TEXT,
                        telefono TEXT,
                        direccion TEXT,
                        score INTEGER
                    )''')
    
    # Préstamos
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

    # Cuotas del Plan
    cursor.execute('''CREATE TABLE IF NOT EXISTS cuotas_plan (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        id_prestamo TEXT,
                        nro_cuota INTEGER,
                        fecha_vencimiento TEXT,
                        monto_cuota REAL,
                        estado TEXT
                    )''')

    # Pagos y Abonos (con destino de fondo)
    cursor.execute('''CREATE TABLE IF NOT EXISTS pagos (
                        id_pago TEXT PRIMARY KEY,
                        fecha TEXT,
                        cliente TEXT,
                        id_prestamo TEXT,
                        monto_abono REAL,
                        saldo_restante REAL,
                        metodo TEXT,
                        fondo_destino TEXT
                    )''')

    # Gastos de Calle
    cursor.execute('''CREATE TABLE IF NOT EXISTS gastos (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        fecha TEXT,
                        descripcion TEXT,
                        monto REAL,
                        tipo TEXT,
                        fondo_origen TEXT
                    )''')

    # Inyecciones de Capital y Préstamos Externos
    cursor.execute('''CREATE TABLE IF NOT EXISTS capital_externo (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        fecha TEXT,
                        tipo TEXT, -- 'Inyección Propia' o 'Préstamo Externo'
                        fuente TEXT, -- Nombre de quien presta o inversor
                        monto REAL,
                        fondo_destino TEXT
                    )''')

    # Transferencias Internas entre Fondos
    cursor.execute('''CREATE TABLE IF NOT EXISTS transferencias (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        fecha TEXT,
                        monto REAL,
                        fondo_origen TEXT,
                        fondo_destino TEXT
                    )''')

    conn.commit()
    conn.close()

init_db()

def run_query(query, params=(), fetch=True):
    conn = sqlite3.connect("control_cobros_pro.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute(query, params)
    conn.commit()
    result = cursor.fetchall() if fetch else None
    conn.close()
    return result

# ==========================================
# 🧭 NAVEGACIÓN Y MENÚ
# ==========================================
st.markdown("<h1 style='color: #0f172a; font-weight: 800;'>💸 ControlCobro <span style='color: #2563eb;'>PRO (Tesorería & Ruta)</span></h1>", unsafe_allow_html=True)
st.markdown("<p style='color: #64748b; margin-top: -15px;'>Sistema integral con control de fondos (Efectivo, Pago Móvil, Binance), inyecciones y transferencias.</p>", unsafe_allow_html=True)
st.markdown("---")

menu = st.sidebar.selectbox("📂 Módulos del Sistema", [
    "📊 Dashboard y Tesorería", 
    "🏍️ Ruta de Cobro", 
    "👥 Clientes", 
    "📝 Otorgar Préstamo", 
    "💳 Registrar Abono", 
    "🏦 Caja, Transferencias & Capital",
    "💸 Gastos Operativos",
    "⚙️ Ajustes / Reportes"
])

# ==========================================
# 1. DASHBOARD Y TESORERÍA
# ==========================================
if menu == "📊 Dashboard y Tesorería":
    st.subheader("Estado General y Balances por Fondo")

    # Calcular saldos actuales por cada fondo
    # Fondos: Efectivo, Pago Móvil, Binance
    fondos = ["Efectivo", "Pago Móvil", "Binance"]
    saldos_fondos = {}

    for f in fondos:
        # Ingresos por cobros
        cobros_f = pd.read_sql(f"SELECT SUM(monto_abono) FROM pagos WHERE fondo_destino = '{f}'", sqlite3.connect("control_cobros_pro.db")).iloc[0, 0] or 0.0
        # Ingresos por inyección o capital externo
        cap_f = pd.read_sql(f"SELECT SUM(monto) FROM capital_externo WHERE fondo_destino = '{f}'", sqlite3.connect("control_cobros_pro.db")).iloc[0, 0] or 0.0
        # Transferencias recibidas
        trans_entradas = pd.read_sql(f"SELECT SUM(monto) FROM transferencias WHERE fondo_destino = '{f}'", sqlite3.connect("control_cobros_pro.db")).iloc[0, 0] or 0.0
        
        # Salidas por gastos
        gastos_f = pd.read_sql(f"SELECT SUM(monto) FROM gastos WHERE fondo_origen = '{f}'", sqlite3.connect("control_cobros_pro.db")).iloc[0, 0] or 0.0
        # Transferencias enviadas
        trans_salidas = pd.read_sql(f"SELECT SUM(monto) FROM transferencias WHERE fondo_origen = '{f}'", sqlite3.connect("control_cobros_pro.db")).iloc[0, 0] or 0.0
        # Salidas por otorgar préstamos (suponiendo que salen de efectivo o banco por defecto)
        prestamos_salida = pd.read_sql("SELECT SUM(monto_prestado) FROM prestamos", sqlite3.connect("control_cobros_pro.db")).iloc[0, 0] or 0.0 if f == "Efectivo" else 0.0

        saldos_fondos[f] = (cobros_f + cap_f + trans_entradas) - (gastos_f + trans_salidas + prestamos_salida)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f'<div class="metric-card"><div class="metric-title">💵 Efectivo Disponible</div><div class="metric-value">${saldos_fondos["Efectivo"]:,.2f}</div></div>', unsafe_allow_html=True)
    with col2:
        st.markdown(f'<div class="metric-card"><div class="metric-title">📱 Pago Móvil / Banco</div><div class="metric-value" style="color: #38bdf8;">${saldos_fondos["Pago Móvil"]:,.2f}</div></div>', unsafe_allow_html=True)
    with col3:
        st.markdown(f'<div class="metric-card"><div class="metric-title">🪙 Binance / USDT</div><div class="metric-value" style="color: #facc15;">${saldos_fondos["Binance"]:,.2f}</div></div>', unsafe_allow_html=True)

    st.markdown("---")
    
    prestamos_df = pd.read_sql("SELECT * FROM prestamos", sqlite3.connect("control_cobros_pro.db"))
    total_cartera = prestamos_df["saldo_pendiente"].sum() if not prestamos_df.empty else 0
    total_cobrado = pd.read_sql("SELECT SUM(monto_abono) FROM pagos", sqlite3.connect("control_cobros_pro.db")).iloc[0,0] or 0

    col4, col5 = st.columns(2)
    with col4:
        st.markdown(f'<div class="metric-card"><div class="metric-title">Cartera Activa Total</div><div class="metric-value">${total_cartera:,.2f}</div></div>', unsafe_allow_html=True)
    with col5:
        st.markdown(f'<div class="metric-card"><div class="metric-title">Total Cobrado Histórico</div><div class="metric-value" style="color: #4ade80;">${total_cobrado:,.2f}</div></div>', unsafe_allow_html=True)

# ==========================================
# 2. RUTA DE COBRO DE HOY
# ==========================================
elif menu == "🏍️ Ruta de Cobro":
    st.subheader("Cuotas del Día y Vencidas")
    hoy_str = datetime.date.today().strftime("%Y-%m-%d")
    cuotas_hoy = pd.read_sql(f"SELECT * FROM cuotas_plan WHERE fecha_vencimiento <= '{hoy_str}' AND estado = 'Pendiente'", sqlite3.connect("control_cobros_pro.db"))

    if cuotas_hoy.empty:
        st.success("🎉 ¡Todo al día! No hay cuotas pendientes para hoy.")
    else:
        for idx, row in cuotas_hoy.iterrows():
            prestamo_info = run_query("SELECT cliente FROM prestamos WHERE id_prestamo = ?", (row["id_prestamo"],))
            cliente_nombre = prestamo_info[0][0] if prestamo_info else "Desconocido"
            cliente_data = run_query("SELECT telefono, direccion FROM clientes WHERE nombre = ?", (cliente_nombre,))
            telefono, direccion = cliente_data[0] if cliente_data else ("", "")

            with st.expander(f"📌 {cliente_nombre} | Cuota #{row['nro_cuota']} - ${row['monto_cuota']:,.2f} (Vence: {row['fecha_vencimiento']})"):
                st.write(f"🏠 **Dirección:** {direccion}")
                if telefono:
                    msg = f"Hola {cliente_nombre}, le escribimos para recordarle su cuota de ${row['monto_cuota']:,.2f} del préstamo {row['id_prestamo']}. ¡Gracias!"
                    wa_url = f"https://wa.me/{telefono}?text={urllib.parse.quote(msg)}"
                    st.markdown(f'<a href="{wa_url}" target="_blank" class="whatsapp-btn">💬 Enviar Recordatorio WhatsApp</a>', unsafe_allow_html=True)

# ==========================================
# 3. GESTIÓN DE CLIENTES
# ==========================================
elif menu == "👥 Clientes":
    st.subheader("Directorio de Prestatarios")
    with st.form("form_cliente"):
        col1, col2 = st.columns(2)
        with col1:
            nombre = st.text_input("Nombre y Apellido")
            telefono = st.text_input("Teléfono (ej: 584120000000)")
        with col2:
            direccion = st.text_input("Dirección")
            score = st.slider("Score", 1, 5, 3)
        if st.form_submit_button("Guardar Cliente") and nombre:
            run_query("INSERT INTO clientes (nombre, telefono, direccion, score) VALUES (?, ?, ?, ?)", (nombre, telefono, direccion, score), fetch=False)
            st.success(f"¡Cliente {nombre} registrado!")

    clientes_df = pd.read_sql("SELECT * FROM clientes", sqlite3.connect("control_cobros_pro.db"))
    if not clientes_df.empty: st.dataframe(clientes_df, use_container_width=True)

# ==========================================
# 4. OTORGAR PRÉSTAMO (CON FECHA PERSONALIZADA)
# ==========================================
elif menu == "📝 Otorgar Préstamo":
    st.subheader("Crear Crédito con Fecha Personalizada")
    clientes_df = pd.read_sql("SELECT nombre FROM clientes", sqlite3.connect("control_cobros_pro.db"))

    if clientes_df.empty:
        st.warning("⚠️ Registra un cliente primero.")
    else:
        with st.form("form_prestamo"):
            cliente_sel = st.selectbox("Cliente", clientes_df["nombre"].tolist())
            col1, col2 = st.columns(2)
            with col1:
                monto = st.number_input("Monto Prestado ($)", min_value=10.0, step=10.0)
                interes = st.number_input("Interés Total (%)", min_value=0.0, value=20.0, step=5.0)
                fecha_inicio_input = st.date_input("Fecha de Inicio del Préstamo", value=datetime.date.today())
            with col2:
                cuotas = st.number_input("Número de Cuotas", min_value=1, value=10, step=1)
                frecuencia = st.selectbox("Frecuencia", ["Diario", "Semanal", "Quincenal", "Mensual"])

            if st.form_submit_button("Aprobar Préstamo y Generar Cuotas"):
                total_con_interes = monto * (1 + (interes / 100))
                id_p = f"PRE-{len(pd.read_sql('SELECT * FROM prestamos', sqlite3.connect('control_cobros_pro.db')))+1:03d}"
                f_inicio_str = fecha_inicio_input.strftime("%Y-%m-%d")

                run_query("INSERT INTO prestamos VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", 
                          (id_p, cliente_sel, monto, interes, total_con_interes, cuotas, frecuencia, total_con_interes, "Activo", f_inicio_str), fetch=False)

                # Generar plan de cuotas a partir de la fecha seleccionada
                monto_cuota = total_con_interes / cuotas
                fecha_base = fecha_inicio_input

                for i in range(1, int(cuotas) + 1):
                    if frecuencia == "Diario": fecha_base += datetime.timedelta(days=1)
                    elif frecuencia == "Semanal": fecha_base += datetime.timedelta(weeks=1)
                    elif frecuencia == "Quincenal": fecha_base += datetime.timedelta(days=15)
                    elif frecuencia == "Mensual": fecha_base += datetime.timedelta(days=30)

                    run_query("INSERT INTO cuotas_plan (id_prestamo, nro_cuota, fecha_vencimiento, monto_cuota, estado) VALUES (?, ?, ?, ?, ?)",
                              (id_p, i, fecha_base.strftime("%Y-%m-%d"), monto_cuota, "Pendiente"), fetch=False)

                st.success(f"¡Préstamo {id_p} creado exitosamente con fecha inicial {f_inicio_str}!")

# ==========================================
# 5. REGISTRAR ABONO Y DISTRIBUCIÓN DE FONDO
# ==========================================
elif menu == "💳 Registrar Abono":
    st.subheader("Cobro y Destino del Dinero")
    activos_df = pd.read_sql("SELECT * FROM prestamos WHERE estado = 'Activo'", sqlite3.connect("control_cobros_pro.db"))

    if activos_df.empty:
        st.info("No hay préstamos activos.")
    else:
        prestamo_id = st.selectbox("Seleccionar Préstamo", activos_df["id_prestamo"].tolist())
        p_info = activos_df[activos_df["id_prestamo"] == prestamo_id].iloc[0]
        cliente_nombre, saldo_actual = p_info["cliente"], p_info["saldo_pendiente"]

        c_info = run_query("SELECT telefono FROM clientes WHERE nombre = ?", (cliente_nombre,))
        telefono_cliente = c_info[0][0] if c_info else ""

        st.markdown(f"**Cliente:** `{cliente_nombre}` | **Saldo Pendiente:** `${saldo_actual:,.2f}`")

        with st.form("form_abono"):
            monto_abono = st.number_input("Monto del Abono ($)", min_value=1.0, max_value=float(saldo_actual), step=1.0)
            metodo = st.selectbox("Método de Pago", ["Efectivo", "Pago Móvil", "Transferencia", "Binance"])
            fondo_destino = st.selectbox("¿A qué caja/fondo va dirigido este dinero?", ["Efectivo", "Pago Móvil", "Binance"])
            
            if st.form_submit_button("Registrar Cobro y Actualizar Fondo"):
                nuevo_saldo = saldo_actual - monto_abono
                id_pago = f"REC-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
                fecha_str = datetime.datetime.now().strftime("%d/%m/%Y %I:%M %p")

                nuevo_estado = "Cancelado" if nuevo_saldo <= 0 else "Activo"
                run_query("UPDATE prestamos SET saldo_pendiente = ?, estado = ? WHERE id_prestamo = ?", (nuevo_saldo, nuevo_estado, prestamo_id), fetch=False)
                run_query("INSERT INTO pagos VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (id_pago, fecha_str, cliente_nombre, prestamo_id, monto_abono, nuevo_saldo, metodo, fondo_destino), fetch=False)
                
                st.success(f"¡Cobro registrado! Ingresado a fondo: **{fondo_destino}**")

                # WhatsApp
                mensaje_w = f"""🧾 *COMPROBANTE DE ABONO* 🧾\n📌 Recibo: {id_pago}\n📅 Fecha: {fecha_str}\n👤 Cliente: {cliente_nombre}\n💰 Abono: ${monto_abono:,.2f}\n📊 Nuevo Saldo: ${nuevo_saldo:,.2f}\n¡Gracias por su pago! 🙏"""
                if telefono_cliente:
                    wa_url = f"https://wa.me/{telefono_cliente}?text={urllib.parse.quote(mensaje_w)}"
                    st.markdown(f'<a href="{wa_url}" target="_blank" class="whatsapp-btn">💬 Enviar Recibo por WhatsApp</a>', unsafe_allow_html=True)

# ==========================================
# 6. CAJA, TRANSFERENCIAS Y CAPITAL EXTERNO
# ==========================================
elif menu == "🏦 Caja, Transferencias & Capital":
    st.subheader("Gestión de Fondos, Transferencias e Inyecciones")
    
    tab1, tab2, tab3 = st.tabs(["📥 Inyección / Préstamo Externo", "🔄 Transferir entre Fondos", "📋 Historial de Movimientos"])

    with tab1:
        with st.form("form_capital"):
            st.markdown("### Registrar Entrada de Dinero Externo o Propio")
            tipo_cap = st.selectbox("Tipo de Entrada", ["Inyección de Capital Propio", "Préstamo Externo (Deuda)"])
            fuente = st.text_input("Fuente / Inversionista / Prestamista (Ej: Ahorros Personales o Juan Pérez)")
            monto_c = st.number_input("Monto ($)", min_value=1.0, step=10.0)
            fondo_dest_c = st.selectbox("Fondo donde ingresa el dinero", ["Efectivo", "Pago Móvil", "Binance"])

            if st.form_submit_button("Registrar Ingreso de Capital"):
                fecha_c = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                run_query("INSERT INTO capital_externo (fecha, tipo, fuente, monto, fondo_destino) VALUES (?, ?, ?, ?, ?)", 
                          (fecha_c, tipo_cap, fuente, monto_c, fondo_dest_c), fetch=False)
                st.success(f"¡Ingreso de ${monto_c:,.2f} registrado en {fondo_dest_c}!")

    with tab2:
        with st.form("form_transf"):
            st.markdown("### Mover Dinero entre tus Cuentas / Fondos")
            monto_t = st.number_input("Monto a Transferir ($)", min_value=1.0, step=5.0)
            col_o, col_d = st.columns(2)
            with col_o:
                origen = st.selectbox("Fondo Origen", ["Efectivo", "Pago Móvil", "Binance"])
            with col_d:
                destino = st.selectbox("Fondo Destino", ["Efectivo", "Pago Móvil", "Binance"])

            if st.form_submit_button("Ejecutar Transferencia"):
                if origen == destino:
                    st.error("El fondo de origen y destino no pueden ser iguales.")
                else:
                    fecha_t = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                    run_query("INSERT INTO transferencias (fecha, monto, fondo_origen, fondo_destino) VALUES (?, ?, ?, ?)",
                              (fecha_t, monto_t, origen, destino), fetch=False)
                    st.success(f"¡Transferencia exitosa de ${monto_t:,.2f} desde {origen} hacia {destino}!")

    with tab3:
        st.markdown("### Historial de Capital y Préstamos Externos")
        cap_df = pd.read_sql("SELECT * FROM capital_externo", sqlite3.connect("control_cobros_pro.db"))
        if not cap_df.empty: st.dataframe(cap_df, use_container_width=True)
        else: st.info("No hay registros de capital externo.")

        st.markdown("### Historial de Transferencias Internas")
        trans_df = pd.read_sql("SELECT * FROM transferencias", sqlite3.connect("control_cobros_pro.db"))
        if not trans_df.empty: st.dataframe(trans_df, use_container_width=True)
        else: st.info("No hay transferencias registradas.")

# ==========================================
# 7. GASTOS OPERATIVOS
# ==========================================
elif menu == "💸 Gastos Operativos":
    st.subheader("Control de Gastos de Calle y Viáticos")
    with st.form("form_gasto"):
        desc = st.text_input("Descripción (Ej: Gasolina, Almuerzo, Repuesto Moto)")
        monto_g = st.number_input("Monto ($)", min_value=0.5, step=1.0)
        fondo_g = st.selectbox("¿De qué fondo sale el dinero?", ["Efectivo", "Pago Móvil", "Binance"])
        tipo_g = st.selectbox("Categoría", ["Gasolina / Movilidad", "Viáticos", "Mantenimiento", "Retiro", "Otro"])

        if st.form_submit_button("Registrar Gasto") and desc:
            fecha_g = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
            run_query("INSERT INTO gastos (fecha, descripcion, monto, tipo, fondo_origen) VALUES (?, ?, ?, ?, ?)", 
                      (fecha_g, desc, monto_g, tipo_g, fondo_g), fetch=False)
            st.success("¡Gasto registrado con éxito!")

    gastos_df = pd.read_sql("SELECT * FROM gastos", sqlite3.connect("control_cobros_pro.db"))
    if not gastos_df.empty: st.dataframe(gastos_df, use_container_width=True)
    else: st.info("No hay gastos registrados.")

# ==========================================
# 8. AJUSTES
# ==========================================
elif menu == "⚙️ Ajustes / Reportes":
    st.subheader("Exportación de Reportes")
    pagos_df = pd.read_sql("SELECT * FROM pagos", sqlite3.connect("control_cobros_pro.db"))
    if not pagos_df.empty:
        csv = pagos_df.to_csv(index=False).encode("utf-8")
        st.download_button("📥 Descargar Historial de Pagos (CSV)", data=csv, file_name="pagos_controlcobro.csv", mime="text/csv")
    else:
        st.info("No hay pagos para exportar.")
