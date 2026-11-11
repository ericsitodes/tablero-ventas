"""Pruebas de los cálculos que ve el cliente: periodos, utilidad, indicadores y lectura del Excel."""
import unicodedata
from datetime import date, datetime
from io import BytesIO

import pandas as pd
import pytest

import app
from conftest import COL_PERSONA, COL_PRODUCTO, excel, fila, gastos, ventas


# ---------------------------------------------------------------------------
# Periodo anterior
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("inicio, fin, esperado", [
    # Meses completos: los mismos meses previos
    (date(2026, 7, 1), date(2026, 9, 30), (date(2026, 4, 1), date(2026, 6, 30))),
    (date(2026, 1, 1), date(2026, 1, 31), (date(2025, 12, 1), date(2025, 12, 31))),   # cruce de año
    (date(2028, 2, 1), date(2028, 2, 29), (date(2028, 1, 1), date(2028, 1, 31))),     # febrero bisiesto
    # Rango libre: la misma cantidad de días justo antes
    (date(2026, 7, 11), date(2026, 7, 20), (date(2026, 7, 1), date(2026, 7, 10))),
    (date(2026, 7, 15), date(2026, 7, 15), (date(2026, 7, 14), date(2026, 7, 14))),   # un solo día
])
def test_periodo_anterior(inicio, fin, esperado):
    assert app.periodo_anterior(inicio, fin) == esperado


# ---------------------------------------------------------------------------
# Gastos del rango y utilidad
# ---------------------------------------------------------------------------
def test_gastos_mes_completo():
    assert app.gastos_del_rango(gastos(jul_2026=3100), date(2026, 7, 1), date(2026, 7, 31)).sum() == 3100


def test_gastos_medio_mes_se_reparten_por_dias():
    # 15 de 31 días
    assert app.gastos_del_rango(gastos(jul_2026=3100), date(2026, 7, 1), date(2026, 7, 15)).sum() == 1500


def test_gastos_dos_meses_parciales():
    # 17-31 jul = 15/31 de 3100 = 1500; 1-10 ago = 10/31 de 6200 = 2000
    serie = app.gastos_del_rango(gastos(jul_2026=3100, ago_2026=6200), date(2026, 7, 17), date(2026, 8, 10))
    assert list(serie.round(2)) == [1500, 2000]


def test_gastos_falta_un_mes_devuelve_none():
    assert app.gastos_del_rango(gastos(jul_2026=3100), date(2026, 7, 1), date(2026, 8, 31)) is None
    assert app.calcular_utilidad(ventas(fila("15/07/2026", 1)), gastos(jul_2026=3100),
                                 date(2026, 7, 1), date(2026, 8, 31)) is None


def test_utilidad_usa_todas_las_categorias_del_rango():
    datos = ventas(
        fila("10/07/2026", 1, total=4000, categoria="Bebidas"),
        fila("20/07/2026", 2, total=2000, categoria="Otra"),
        fila("05/08/2026", 3, total=9999),  # fuera del rango
    )
    assert app.calcular_utilidad(datos, gastos(jul_2026=3100), date(2026, 7, 1), date(2026, 7, 31)) == 2900


# ---------------------------------------------------------------------------
# Filtros y descarga
# ---------------------------------------------------------------------------
def datos_para_filtrar():
    return ventas(
        fila("01/07/2026", 1, categoria="Bebidas", metodo="Efectivo"),
        fila("15/07/2026", 2, categoria="Bebidas", metodo="Tarjeta"),
        fila("15/07/2026", 3, categoria="Otra", metodo="Efectivo"),
        fila("31/07/2026", 4, categoria="Otra", metodo="Tarjeta"),
    )


def test_filtro_de_fechas_incluye_ambos_extremos():
    filtradas = app.filtrar_ventas(datos_para_filtrar(), date(2026, 7, 1), date(2026, 7, 31), [], [])
    assert sorted(filtradas["Ticket"]) == [1, 2, 3, 4]  # listas vacías = todas


def test_filtros_de_categoria_y_metodo_se_combinan():
    filtradas = app.filtrar_ventas(datos_para_filtrar(), date(2026, 7, 2), date(2026, 7, 31),
                                   ["Bebidas"], ["Tarjeta"])
    assert list(filtradas["Ticket"]) == [2]


def test_excel_filtrado_conserva_columnas_y_fechas():
    descargado = pd.read_excel(BytesIO(app.excel_filtrado(datos_para_filtrar())), sheet_name="Ventas")
    assert list(descargado.columns) == app.COLUMNAS_VENTAS
    assert len(descargado) == 4
    assert pd.Timestamp(descargado["Fecha"].iloc[0]) == pd.Timestamp("2026-07-01")


# ---------------------------------------------------------------------------
# Indicadores y variación
# ---------------------------------------------------------------------------
def test_indicadores_cuentan_tickets_unicos():
    datos = ventas(fila("15/07/2026", 1, total=100), fila("15/07/2026", 1, total=50),
                   fila("15/07/2026", 2, total=30))
    assert app.calcular_indicadores(datos) == {"ventas": 180, "tickets": 2, "ticket_promedio": 90}


def test_indicadores_sin_ventas():
    vacio = ventas(fila("15/07/2026", 1)).iloc[0:0]
    assert app.calcular_indicadores(vacio) == {"ventas": 0, "tickets": 0, "ticket_promedio": 0}


@pytest.mark.parametrize("actual, anterior, esperado", [
    (110, 100, "+10.0%"),
    (90, 100, "-10.0%"),
    (-50, -100, "+50.0%"),  # pérdida menor que antes: mejoró
    (5, 0, None),
    (5, None, None),
    (None, 5, None),
])
def test_variacion(actual, anterior, esperado):
    assert app.variacion(actual, anterior) == esperado


# ---------------------------------------------------------------------------
# Lectura de fechas y números escritos de distintas formas
# ---------------------------------------------------------------------------
def test_fechas_reales_de_excel_no_cambian():
    serie = pd.Series(pd.to_datetime(["2026-07-15", "2026-08-01"]))
    assert app.a_fecha(serie) is serie


def test_fechas_escritas_como_texto():
    serie = pd.Series(["15/07/2026", "2026-07-15", "15 jul 2026", "15 de julio de 2026",
                       "15 de Julio de 2026", datetime(2026, 7, 15)], dtype=object)
    assert (app.a_fecha(serie) == pd.Timestamp("2026-07-15")).all()


def test_fechas_que_no_se_entienden_quedan_vacias():
    serie = pd.Series(["hola", "julio 4", None], dtype=object)
    assert app.a_fecha(serie).isna().all()


def test_numeros_escritos_como_texto():
    serie = pd.Series(["$1,250.50", " 300 ", "-50", "abc", None], dtype=object)
    resultado = app.a_numero(serie)
    assert resultado.iloc[:3].tolist() == [1250.5, 300, -50]
    assert resultado.iloc[3:].isna().all()


def test_columna_numerica_no_cambia():
    serie = pd.Series([1.5, 2.0])
    assert app.a_numero(serie) is serie


def test_formato_europeo_se_lee_mal_comportamiento_actual():
    """Documenta una limitación conocida: "1.250,50" se lee como 1.2505.

    En México se escribe 1,250.50, así que por ahora no se corrige.
    Si se corrige, cambiar esta prueba.
    """
    assert app.a_numero(pd.Series(["1.250,50"], dtype=object)).iloc[0] == pytest.approx(1.2505)


# ---------------------------------------------------------------------------
# Lectura del Excel de punta a punta
# ---------------------------------------------------------------------------
def sin_acentos_mayusculas(texto):
    return unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode().upper()


def libro_valido():
    """Hojas Ventas, Gastos e Inventario con todo lo que el tablero debe tolerar."""
    crudas = pd.DataFrame([
        fila("15/07/2026", 1, total="$1,250.50"),
        fila("2026-07-16", 2, total=300),
        {c: None for c in app.COLUMNAS_VENTAS},          # fila vacía: se ignora sin aviso
        fila("16 de julio de 2026", 3, total=50),
        fila("16/07/2026", 4, total="no sé"),            # total ilegible: se descarta con aviso
    ])
    # Encabezados en mayúsculas, sin acentos, en otro orden y con una columna extra
    crudas.columns = [sin_acentos_mayusculas(c) for c in crudas.columns]
    crudas = crudas[crudas.columns[::-1]].assign(Notas="se ignora")
    return {
        "Ventas": crudas,
        "Gastos": pd.DataFrame({"Mes": ["2026-07-01"], "Concepto": ["Renta"], "Monto": ["3,100"]}),
        "Inventario": pd.DataFrame({"Producto": ["Agua"], "Existencia": [10]}),
    }


def test_excel_tolerante_se_lee():
    resultado = app.leer_libro(excel(**libro_valido()))
    datos, gastos_mes, avisos = resultado[0], resultado[1], resultado[-1]
    assert list(datos.columns[:len(app.COLUMNAS_VENTAS)]) == app.COLUMNAS_VENTAS
    assert sorted(datos["Total"]) == [50, 300, 1250.5]
    assert "Notas" not in datos.columns
    assert gastos_mes.to_dict() == {pd.Period("2026-07", freq="M"): 3100}
    assert len(avisos) == 1 and "1 fila " in avisos[0]


def test_excel_sin_hoja_dice_cual_falta():
    hojas = libro_valido()
    del hojas["Gastos"]
    with pytest.raises(app.ErrorFormato, match='Falta la hoja "Gastos"'):
        app.leer_libro(excel(**hojas))


def test_excel_sin_columna_dice_cual_falta():
    hojas = libro_valido()
    hojas["Ventas"] = hojas["Ventas"].drop(columns="TOTAL")
    with pytest.raises(app.ErrorFormato, match="le faltan columnas: Total"):
        app.leer_libro(excel(**hojas))


def test_limite_de_filas():
    app.revisar_tamano(app.LIMITE_FILAS)  # justo en el límite: se acepta
    with pytest.raises(app.ArchivoGrande):
        app.revisar_tamano(app.LIMITE_FILAS + 1)


# ---------------------------------------------------------------------------
# Formatos
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("valor, esperado", [(1234.5, "$1,234.50"), (-1234.5, "-$1,234.50"), (0, "$0.00")])
def test_moneda(valor, esperado):
    assert app.moneda(valor) == esperado


@pytest.mark.parametrize("negocio, esperado", [
    ("Doña Lupe, Centro", "dona_lupe_centro"),
    ("  ", "tu_negocio"),
    ("¡¡!!", "tu_negocio"),
])
def test_nombre_archivo(negocio, esperado):
    assert app.nombre_archivo(negocio) == esperado


# ---------------------------------------------------------------------------
# Gráficas: casos que ya fallaron antes (un día, un producto)
# ---------------------------------------------------------------------------
def test_graficas_con_un_solo_dia_y_un_solo_producto():
    datos = ventas(fila("15/07/2026", 1, total=100))
    dia = date(2026, 7, 15)
    productos = datos.groupby(COL_PRODUCTO)[["Cantidad", "Total"]].sum().reset_index()
    grafica_productos = getattr(app, "grafica_productos", None) or app.grafica_platillos

    linea = app.grafica_ventas_diarias(datos, dia, dia)
    assert linea.data[0].mode == "lines+markers"  # un solo punto no traza línea
    app.grafica_calor(datos)
    grafica_productos(productos)
    app.grafica_montos(datos.groupby(COL_PERSONA)["Total"].sum())
    app.grafica_categorias(datos)
    app.grafica_mensual(datos, gastos(jul_2026=3100), date(2026, 7, 1), date(2026, 7, 31))


def test_eje_de_ventas_empieza_en_cero():
    datos = ventas(fila("15/07/2026", 1, total=100), fila("16/07/2026", 2, total=200))
    fig = app.grafica_ventas_diarias(datos, date(2026, 7, 15), date(2026, 7, 16))
    assert fig.layout.yaxis.rangemode == "tozero"
