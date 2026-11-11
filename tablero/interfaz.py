"""Interfaz de Streamlit, común a todos los giros. Se arranca con main("<giro>")."""
import pandas as pd
import streamlit as st

from tablero.calculos import (DIAS_CONSUMO, DIAS_PRONTO, DIAS_URGENTE, calcular_indicadores, calcular_utilidad,
                              excel_filtrado, filtrar_ventas, gastos_del_rango, periodo_anterior, tabla_resurtir,
                              variacion)
from tablero.formato import fecha_es, moneda, nombre_archivo
from tablero.giro import cargar_giro, cargar_marca
from tablero.graficas import (BORDE, SUPERFICIE, TEXTO_SUAVE, grafica_calor, grafica_categorias, grafica_mensual,
                              grafica_montos, grafica_productos, grafica_ventas_diarias)
from tablero.lectura import ArchivoGrande, ErrorFormato, leer_libro

MARCA = cargar_marca()
WHATSAPP = MARCA.enlace_whatsapp
NEGOCIO_VACIO = "Tu negocio"
MIME_EXCEL = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
MENSAJE_ERROR = ("No pudimos leer tu archivo. Revisa que tenga el formato de la hoja para llenar "
                 f"o [escríbeme por WhatsApp]({WHATSAPP}).")


@st.cache_data(show_spinner="Cargando datos…")
def cargar_demo(clave_giro):
    """Lee el Excel de ejemplo del giro; solo estos datos ficticios van a la caché."""
    giro = cargar_giro(clave_giro)
    return leer_libro(giro.archivo_demo.read_bytes(), giro)


def cargar_subido(subido, giro):
    """Lee el Excel subido y lo guarda solo en la sesión de esta visita.

    No usa st.cache_data: esa caché es del servidor y sobreviviría a la visita.
    """
    if st.session_state.get("libro_id") != subido.file_id:
        with st.spinner("Cargando datos…"):
            libro = leer_libro(subido.getvalue(), giro)
        st.session_state["libro"] = libro
        st.session_state["libro_id"] = subido.file_id
    return st.session_state["libro"]


def mostrar_grafica(fig):
    """Muestra una gráfica a todo el ancho y sin barra de herramientas."""
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False, "scrollZoom": False})


def aplicar_css():
    """Ajustes que config.toml no cubre: tarjetas y márgenes en celular."""
    st.markdown(f"""
    <style>
      h1 {{ font-size: clamp(1.5rem, 1.1rem + 2vw, 2.25rem) !important; line-height: 1.2 !important; }}
      [data-testid="stMetric"] {{ background: {SUPERFICIE}; border: 1px solid {BORDE}; border-radius: 12px; padding: 14px 16px; }}
      [data-testid="stMetricValue"] {{ font-size: clamp(1.4rem, 1.2rem + .6vw, 1.75rem); font-variant-numeric: tabular-nums; }}
      .pie-demo {{ text-align: center; color: {TEXTO_SUAVE}; font-size: .9rem; margin-top: 2rem; padding-top: 1rem; border-top: 1px solid {BORDE}; }}
      @media (max-width: 640px) {{
        .block-container {{ padding: 3.5rem 1rem 2rem !important; }}
      }}
    </style>
    """, unsafe_allow_html=True)


def elegir_origen(giro):
    """Dibuja la sección de datos y devuelve (archivo subido o None, nombre del negocio)."""
    hojas = "Ventas, Gastos e Inventario" if giro.inventario else "Ventas y Gastos"
    with st.sidebar.expander("Usar mi propio Excel", expanded=True):
        negocio = st.text_input("Nombre del negocio", max_chars=60, placeholder=NEGOCIO_VACIO)
        st.caption(f"Debe tener las hojas {hojas} con las mismas columnas que el ejemplo.")
        subido = st.file_uploader("Sube tu archivo de Excel", type="xlsx")
        st.caption("Máximo 10 MB. Tu archivo se procesa solo durante tu visita y no se guarda.")
        st.download_button("Descargar hoja para llenar", giro.plantilla.read_bytes(), file_name=giro.plantilla.name,
                           mime=MIME_EXCEL, width="stretch")
        st.download_button("Descargar Excel de ejemplo", giro.archivo_demo.read_bytes(),
                           file_name=giro.archivo_demo.name, mime=MIME_EXCEL, width="stretch")
    return subido, negocio.strip()


def elegir_filtros(ventas, origen):
    """Dibuja los filtros y devuelve (inicio, fin, categorías, métodos)."""
    primera = ventas["Fecha"].min().date()
    ultima = ventas["Fecha"].max().date()
    # Por defecto, los últimos 3 meses: deja un periodo anterior para comparar
    inicial = max(primera, (pd.Period(ultima, freq="M") - 2).start_time.date())

    st.sidebar.header("Ver por fecha o categoría")
    rango = st.sidebar.date_input("Rango de fechas", value=(inicial, ultima), min_value=primera,
                                  max_value=ultima, format="DD/MM/YYYY", key=f"fechas_{origen}")
    # Mientras la persona elige la segunda fecha, llega solo una
    inicio, fin = rango if len(rango) == 2 else (rango[0], rango[0])
    categorias = st.sidebar.multiselect("Categoría", sorted(ventas["Categoría"].unique()),
                                        placeholder="Todas", key=f"categorias_{origen}")
    metodos = st.sidebar.multiselect("Método de pago", sorted(ventas["Método de pago"].unique()),
                                     placeholder="Todos", key=f"metodos_{origen}")
    return inicio, fin, categorias, metodos


def mostrar_indicadores(ventas, gastos, filtradas, inicio, fin, categorias, metodos):
    """Fila de indicadores con su variación contra el periodo anterior."""
    inicio_ant, fin_ant = periodo_anterior(inicio, fin)
    hay_anterior = inicio_ant >= ventas["Fecha"].min().date()

    actual = calcular_indicadores(filtradas)
    anterior = {}
    if hay_anterior:
        anterior = calcular_indicadores(filtrar_ventas(ventas, inicio_ant, fin_ant, categorias, metodos))
    utilidad = calcular_utilidad(ventas, gastos, inicio, fin)
    utilidad_ant = calcular_utilidad(ventas, gastos, inicio_ant, fin_ant) if hay_anterior else None

    columnas = st.columns(4)
    columnas[0].metric("Ventas totales", moneda(actual["ventas"]), variacion(actual["ventas"], anterior.get("ventas")))
    columnas[1].metric("Tickets", f"{actual['tickets']:,}", variacion(actual["tickets"], anterior.get("tickets")))
    columnas[2].metric("Ticket promedio", moneda(actual["ticket_promedio"]),
                       variacion(actual["ticket_promedio"], anterior.get("ticket_promedio")))
    columnas[3].metric("Utilidad", moneda(utilidad) if utilidad is not None else "Sin gastos",
                       variacion(utilidad, utilidad_ant))

    if hay_anterior:
        st.caption(f"Variación contra el periodo anterior: {fecha_es(inicio_ant)} a {fecha_es(fin_ant)}.")
    else:
        st.caption("Sin variación: los datos no alcanzan para un periodo anterior equivalente.")
    if utilidad is None:
        st.warning('La hoja "Gastos" no tiene todos los meses de este rango; la utilidad no se puede calcular.')
    elif categorias or metodos:
        st.caption("La utilidad y la gráfica de ingresos vs. gastos consideran todas las ventas del rango, "
                   "porque los gastos no se pueden repartir por categoría ni por método de pago.")


def mostrar_graficas(ventas, gastos, filtradas, inicio, fin, giro):
    """Dibuja las siete gráficas en el orden del tablero."""
    st.subheader("Ventas por día")
    mostrar_grafica(grafica_ventas_diarias(filtradas, inicio, fin))

    st.subheader("¿Cuándo se vende más?")
    mostrar_grafica(grafica_calor(filtradas))

    productos = (filtradas.groupby("Producto")[["Cantidad", "Total"]].sum()
                 .sort_values("Cantidad", ascending=False).reset_index())
    izquierda, derecha = st.columns([3, 2])
    with izquierda:
        st.subheader(f"Top 10 {giro.productos}")
        mostrar_grafica(grafica_productos(productos.head(10)))
    with derecha:
        st.subheader("Los 5 menos vendidos")
        if len(productos) > 5:
            mostrar_grafica(grafica_productos(productos.tail(5).iloc[::-1]))
        else:
            st.caption(f"Con estos filtros hay muy pocos {giro.productos} para comparar.")

    izquierda, derecha = st.columns(2)
    with izquierda:
        st.subheader("Ventas por categoría")
        mostrar_grafica(grafica_categorias(filtradas, giro.categorias))
    with derecha:
        st.subheader("Ventas por método de pago")
        mostrar_grafica(grafica_montos(filtradas.groupby("Método de pago")["Total"].sum()))
        st.subheader(f"Ventas por {giro.col_persona.lower()}")
        mostrar_grafica(grafica_montos(filtradas.groupby("Persona")["Total"].sum()))

    st.subheader("Ingresos vs. gastos por mes")
    if gastos_del_rango(gastos, inicio, fin) is None:
        st.caption('Faltan meses en la hoja "Gastos" para mostrar esta gráfica.')
    else:
        mostrar_grafica(grafica_mensual(ventas, gastos, inicio, fin))


def mostrar_resurtir(ventas, inventario, giro):
    """Muestra los productos que se van a acabar, del más urgente al menos."""
    st.subheader(giro.titulo_resurtir)
    tabla = tabla_resurtir(ventas, inventario)
    urgentes = int((tabla["Estado"] == "Urgente").sum())
    pronto = int((tabla["Estado"] == "Pronto").sum())
    columnas = st.columns(2)
    columnas[0].metric(f"Urgente: menos de {DIAS_URGENTE} días", urgentes)
    columnas[1].metric(f"Pronto: menos de {DIAS_PRONTO} días", pronto)
    st.dataframe(
        tabla[tabla["Estado"].isin(["Urgente", "Pronto"])].rename(columns={"Producto": giro.col_producto}),
        hide_index=True, width="stretch",
        column_config={
            "Existencia": st.column_config.NumberColumn(format="%d"),
            "Venta diaria": st.column_config.NumberColumn(format="%.1f"),
            "Días de existencia": st.column_config.NumberColumn(format="%.0f"),
        },
    )
    st.caption(f"Calculado con las ventas de los últimos {DIAS_CONSUMO} días del archivo; no cambia con los filtros.")


def mostrar_pie(es_demo):
    """Pie de página; "de ejemplo" solo aplica al Excel de ejemplo."""
    texto = f"Tablero de ejemplo creado por {MARCA.nombre}" if es_demo else f"Tablero creado por {MARCA.nombre}"
    st.markdown(f'<div class="pie-demo">{texto}</div>', unsafe_allow_html=True)


def main(clave_giro):
    giro = cargar_giro(clave_giro)
    st.set_page_config(page_title=f"Tablero de ventas · {giro.negocio_demo}", page_icon="📊", layout="wide")
    aplicar_css()
    zona_titulo = st.empty()  # el título depende del Excel, que se conoce después
    subido, negocio = elegir_origen(giro)

    libro, origen = None, "demo"
    if subido is None:
        for llave in ("libro", "libro_id", "fallo_id"):
            st.session_state.pop(llave, None)
    elif st.session_state.get("fallo_id") == subido.file_id:
        st.error(f"{MENSAJE_ERROR} Mientras, te muestro el tablero de ejemplo.")
    else:
        try:
            libro, origen = cargar_subido(subido, giro), subido.file_id
        except ArchivoGrande as error:
            st.warning(f"{error} Mientras, te muestro el tablero de ejemplo.")
        except ErrorFormato as error:
            st.error(f"No pudimos leer tu archivo: {error} Revisa que tenga el formato de la hoja para llenar "
                     f"o [escríbeme por WhatsApp]({WHATSAPP}). Mientras, te muestro el tablero de ejemplo.")
        except Exception as error:
            print(f"Error al leer un Excel subido: {type(error).__name__}", flush=True)  # nunca datos del archivo
            st.error(f"{MENSAJE_ERROR} Mientras, te muestro el tablero de ejemplo.")

    es_demo = libro is None
    if es_demo:
        libro = cargar_demo(clave_giro)
        st.info("Este es un tablero de ejemplo. Sube tu Excel en el menú lateral para ver el tuyo.")

    nombre_negocio = giro.negocio_demo if es_demo else negocio or NEGOCIO_VACIO
    titulo = f"Tablero de ventas · {nombre_negocio}"
    st.set_page_config(page_title=titulo, page_icon="📊", layout="wide")
    zona_titulo.title(titulo)

    zona = st.empty()  # si algo falla a medio dibujar, se vacía y se muestra el ejemplo
    try:
        with zona.container():
            mostrar_tablero(libro, origen, es_demo, nombre_negocio, giro)
    except Exception as error:
        if es_demo:
            raise
        print(f"Error al procesar un Excel subido: {type(error).__name__}", flush=True)
        zona.empty()
        for llave in ("libro", "libro_id"):
            st.session_state.pop(llave, None)
        st.session_state["fallo_id"] = subido.file_id
        st.rerun()


def mostrar_tablero(libro, origen, es_demo, nombre_negocio, giro):
    """Dibuja avisos, filtros, indicadores, gráficas, resurtido (si aplica) y pie."""
    ventas, gastos, inventario, avisos = libro
    if not es_demo:
        for aviso in avisos:
            st.warning(aviso)
    inicio, fin, categorias, metodos = elegir_filtros(ventas, origen)
    filtradas = filtrar_ventas(ventas, inicio, fin, categorias, metodos)

    if filtradas.empty:
        st.info("No hay ventas con estos filtros. Prueba con otro rango de fechas.")
    else:
        mostrar_indicadores(ventas, gastos, filtradas, inicio, fin, categorias, metodos)
        mostrar_graficas(ventas, gastos, filtradas, inicio, fin, giro)
        st.download_button("Descargar datos filtrados en Excel", excel_filtrado(filtradas, giro),
                           file_name=f"ventas_{nombre_archivo(nombre_negocio)}.xlsx", mime=MIME_EXCEL)
    if giro.inventario:
        mostrar_resurtir(ventas, inventario, giro)
    mostrar_pie(es_demo)
