import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.ticker import FuncFormatter

# Configuración de la página
st.set_page_config(page_title="Comparador de Créditos", layout="wide")

# Inicializar el estado de la sesión para guardar los créditos
if 'creditos' not in st.session_state:
    st.session_state['creditos'] = []

st.title("Simulador y Comparador de Créditos")
st.markdown("""
**Nuevas Funciones:**
1. Agrega múltiples opciones de crédito para comparar cuál te conviene más.
2. Ingresa tus ingresos para verificar si puedes pagar las cuotas (Capacidad de Pago).
""")

# --- BARRA LATERAL (ENTRADAS) ---
with st.sidebar:
    st.header("1. Tus Datos Financieros")
    ingresos = st.number_input("Ingresos Mensuales ($)", min_value=0.0, value=1500000.0, step=50000.0)
    
    st.divider()
    
    st.header("2. Agregar Nuevo Crédito")
    nombre_simulacion = st.text_input("Nombre del Escenario (ej. Banco A)", value=f"Opción {len(st.session_state['creditos']) + 1}")
    monto = st.number_input("Monto del Préstamo ($)", min_value=1000.0, value=1000000.0, step=10000.0)
    tasa = st.number_input("Tasa Anual (%)", min_value=0.1, value=12.0, step=0.1)
    plazo = st.number_input("Plazo (Meses)", min_value=1, value=12, step=1)
    
    if st.button("Agregar a la Comparación"):
        # Guardamos los datos en la lista de la sesión
        nuevo_credito = {
            "nombre": nombre_simulacion,
            "monto": monto,
            "tasa": tasa,
            "plazo": int(plazo)
        }
        st.session_state['creditos'].append(nuevo_credito)
        st.success(f"¡{nombre_simulacion} agregado!")

    st.divider()
    
    if len(st.session_state['creditos']) > 0:
        st.write(f"**Créditos guardados:** {len(st.session_state['creditos'])}")
        if st.button("Borrar todos los créditos"):
            st.session_state['creditos'] = []
            st.rerun()

# --- FUNCIONES DE CÁLCULO ---

def calcular_tabla(P, tasa_anual, n):
    r = (tasa_anual / 100) / 12
    
    if r > 0:
        cuota = P * (r * (1 + r)**n) / ((1 + r)**n - 1)
    else:
        cuota = P / n

    datos = []
    saldo = P
    acum_interes = 0
    
    for k in range(1, n + 1):
        interes = saldo * r
        amortizacion = cuota - interes
        
        # Ajuste final
        if k == n:
            amortizacion = saldo
            cuota = amortizacion + interes
            saldo = 0
        else:
            saldo -= amortizacion
            
        acum_interes += interes
        
        datos.append({
            "Mes": k,
            "Saldo": saldo,
            "Interés Acumulado": acum_interes,
            "Cuota": cuota
        })
        
    return pd.DataFrame(datos), cuota, acum_interes

def format_millions(x, pos):
    """Formatear valores del eje Y en millones"""
    if x >= 1_000_000:
        return f'${x/1_000_000:.1f}M'
    elif x >= 1_000:
        return f'${x/1_000:.0f}K'
    else:
        return f'${x:.0f}'

# --- LÓGICA PRINCIPAL ---

if len(st.session_state['creditos']) == 0:
    st.info("👈 Comienza agregando un crédito desde la barra lateral.")
else:
    # Contenedores para datos procesados
    resumen_data = []
    dfs_graficos = {} # Diccionario para guardar los dataframes de cada crédito
    total_cuotas_mensuales_combinadas = 0

    # Procesar cada crédito guardado
    for credito in st.session_state['creditos']:
        df, cuota, total_int = calcular_tabla(credito['monto'], credito['tasa'], credito['plazo'])
        
        # Guardar para resumen
        resumen_data.append({
            "Nombre": credito['nombre'],
            "Monto": f"${credito['monto']:,.2f}",
            "Tasa Anual": f"{credito['tasa']}%",
            "Plazo": f"{credito['plazo']} meses",
            "Cuota Mensual": cuota, # Numérico para sumar
            "Interés Total": total_int,
            "Total a Pagar": credito['monto'] + total_int
        })
        
        # Guardar para gráficos
        dfs_graficos[credito['nombre']] = df
        
        # Sumar a la carga mensual total (asumiendo que pagas todos a la vez, o para comparar "peor escenario")
        # Nota: Si es comparación excluyente, el usuario mirará la fila. Si es acumulativo, mirará la suma.
        # Aquí mostramos la cuota individual en tabla y haremos el análisis por crédito seleccionado o el máximo.
    
    df_resumen = pd.DataFrame(resumen_data)

    # --- ANÁLISIS DE CAPACIDAD DE PAGO ---
    st.header("1. Análisis de Capacidad de Pago")
    
    # Buscamos la cuota más alta entre las opciones (asumiendo que eliges UNA de ellas)
    max_cuota = df_resumen["Cuota Mensual"].max()
    nombre_max = df_resumen.loc[df_resumen["Cuota Mensual"].idxmax(), "Nombre"]
    
    ratio_deuda = (max_cuota / ingresos) * 100 if ingresos > 0 else 0
    
    col_kpi1, col_kpi2, col_kpi3 = st.columns(3)
    col_kpi1.metric("Tus Ingresos", f"${ingresos:,.2f}")
    col_kpi1.metric("Cuota más alta (Escenario: " + nombre_max + ")", f"${max_cuota:,.2f}")
    
    # Lógica de semáforo financiero
    estado = "SALUDABLE"
    color = "green"
    mensaje = "Tus ingresos cubren cómodamente la cuota (menos del 30%)."
    
    if ratio_deuda > 30 and ratio_deuda <= 40:
        estado = "PRECAUCIÓN"
        color = "orange"
        mensaje = "La cuota representa entre el 30% y 40% de tus ingresos."
    elif ratio_deuda > 40:
        estado = "CRÍTICO"
        color = "red"
        mensaje = "¡Cuidado! La cuota supera el 40% de tus ingresos. Riesgo de sobreendeudamiento."

    with col_kpi2:
        st.markdown(f"### Carga Financiera: :{color}[{ratio_deuda:.1f}%]")
        st.caption("Porcentaje de ingresos destinado a la cuota.")

    with col_kpi3:
        st.markdown(f"### Estado: :{color}[{estado}]")
        st.write(mensaje)

    st.divider()

    # --- TABLA COMPARATIVA ---
    st.header("2. Tabla Comparativa de Opciones")
    # Formatear para mostrar
    df_show = df_resumen.copy()
    df_show["Cuota Mensual"] = df_show["Cuota Mensual"].apply(lambda x: f"${x:,.2f}")
    df_show["Interés Total"] = df_show["Interés Total"].apply(lambda x: f"${x:,.2f}")
    df_show["Total a Pagar"] = df_show["Total a Pagar"].apply(lambda x: f"${x:,.2f}")
    
    st.dataframe(df_show, hide_index=True, use_container_width=True)
    
    # Botones para eliminar créditos individuales
    st.markdown("##### Eliminar Créditos Individuales")
    cols = st.columns(min(len(st.session_state['creditos']), 4))
    for idx, credito in enumerate(st.session_state['creditos']):
        col_idx = idx % 4
        with cols[col_idx]:
            if st.button(f"🗑️ Eliminar {credito['nombre']}", key=f"delete_{idx}"):
                st.session_state['creditos'].pop(idx)
                st.rerun()

    st.divider()

    # --- GRÁFICOS COMPARATIVOS ---
    st.header("3. Gráficos Comparativos")
    
    tab1, tab2 = st.tabs(["📉 Evolución del Saldo", "💰 Intereses Acumulados"])
    
    with tab1:
        fig1, ax1 = plt.subplots(figsize=(10, 5))
        for nombre, df in dfs_graficos.items():
            ax1.plot(df["Mes"], df["Saldo"], label=nombre, linewidth=2)
        
        ax1.set_title("Comparación: ¿Qué tan rápido baja la deuda?")
        ax1.set_xlabel("Meses")
        ax1.set_ylabel("Saldo Pendiente")
        
        # Formatear el eje Y para mostrar valores en millones
        ax1.yaxis.set_major_formatter(FuncFormatter(format_millions))
        
        ax1.legend()
        ax1.grid(True, linestyle='--', alpha=0.5)
        st.pyplot(fig1)
        st.caption("Una curva más inclinada hacia abajo significa que terminas de pagar antes o amortizas más rápido.")

    with tab2:
        fig2, ax2 = plt.subplots(figsize=(10, 5))
        for nombre, df in dfs_graficos.items():
            ax2.plot(df["Mes"], df["Interés Acumulado"], label=nombre, linewidth=2)
        
        ax2.set_title("Comparación: ¿Cuánto interés termino pagando?")
        ax2.set_xlabel("Meses")
        ax2.set_ylabel("Intereses Pagados Acumulados")
        
        # Formatear el eje Y para mostrar valores en millones
        ax2.yaxis.set_major_formatter(FuncFormatter(format_millions))
        
        ax2.legend()
        ax2.grid(True, linestyle='--', alpha=0.5)
        st.pyplot(fig2)
        st.caption("La línea más baja es la opción más barata en términos de intereses totales.")

    # --- DETALLE INDIVIDUAL (EXPANDER) ---
    st.divider()
    st.subheader("Detalle Desglosado por Crédito")
    for nombre, df in dfs_graficos.items():
        with st.expander(f"Ver Tabla de Amortización: {nombre}"):
            st.dataframe(df.style.format({
                "Saldo": "${:,.2f}", 
                "Interés Acumulado": "${:,.2f}", 
                "Cuota": "${:,.2f}"
            }))