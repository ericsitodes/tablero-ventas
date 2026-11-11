"""Cálculos del tablero: filtros, periodos, utilidad, indicadores, resurtido y descarga."""
import calendar
from datetime import date, timedelta
from io import BytesIO

import pandas as pd

from tablero.giro import COLUMNAS_VENTAS

# Resurtido: días de venta que se promedian y umbrales de alerta
DIAS_CONSUMO = 30
DIAS_URGENTE = 7
DIAS_PRONTO = 15


def filtrar_fechas(ventas, inicio, fin):
    """Devuelve las ventas entre dos fechas, ambas incluidas."""
    return ventas[ventas["Fecha"].between(pd.Timestamp(inicio), pd.Timestamp(fin))]


def filtrar_ventas(ventas, inicio, fin, categorias, metodos):
    """Aplica todos los filtros. Una lista vacía significa "todas"."""
    filtradas = filtrar_fechas(ventas, inicio, fin)
    if categorias:
        filtradas = filtradas[filtradas["Categoría"].isin(categorias)]
    if metodos:
        filtradas = filtradas[filtradas["Método de pago"].isin(metodos)]
    return filtradas


def periodo_anterior(inicio, fin):
    """Devuelve el periodo equivalente que termina justo antes de inicio.

    Si el rango son meses completos, compara contra los mismos meses previos
    (jul-sep contra abr-jun); si no, contra los mismos días.
    """
    fin_anterior = inicio - timedelta(days=1)
    if inicio.day == 1 and fin.day == calendar.monthrange(fin.year, fin.month)[1]:
        meses = (fin.year - inicio.year) * 12 + fin.month - inicio.month + 1
        return (pd.Period(inicio, freq="M") - meses).start_time.date(), fin_anterior
    return fin_anterior - (fin - inicio), fin_anterior


def gastos_del_rango(gastos, inicio, fin):
    """Reparte el gasto mensual por días cuando el rango cubre solo parte del mes.

    Devuelve una serie por mes, o None si falta algún mes en la hoja Gastos.
    """
    resultado = {}
    for mes in pd.period_range(inicio, fin, freq="M"):
        if mes not in gastos.index:
            return None
        dias_mes = calendar.monthrange(mes.year, mes.month)[1]
        desde = max(inicio, date(mes.year, mes.month, 1))
        hasta = min(fin, date(mes.year, mes.month, dias_mes))
        resultado[mes] = gastos[mes] * ((hasta - desde).days + 1) / dias_mes
    return pd.Series(resultado)


def calcular_utilidad(ventas, gastos, inicio, fin):
    """Ventas de todo el negocio menos gastos del rango; None si faltan gastos.

    No usa los filtros de categoría ni de pago: los gastos no se pueden
    repartir entre categorías, y restarlos completos daría una utilidad falsa.
    """
    gastos_rango = gastos_del_rango(gastos, inicio, fin)
    if gastos_rango is None:
        return None
    return filtrar_fechas(ventas, inicio, fin)["Total"].sum() - gastos_rango.sum()


def calcular_indicadores(ventas):
    """Calcula ventas, tickets y ticket promedio de un conjunto de filas."""
    total = ventas["Total"].sum()
    tickets = ventas["Ticket"].nunique()
    return {"ventas": total, "tickets": tickets, "ticket_promedio": total / tickets if tickets else 0}


def variacion(actual, anterior):
    """Devuelve el texto de variación porcentual, o None si no se puede calcular."""
    if anterior is None or actual is None or anterior == 0:
        return None
    return f"{(actual - anterior) / abs(anterior) * 100:+.1f}%"


def excel_filtrado(ventas, giro):
    """Devuelve los bytes de un Excel con las ventas filtradas, con los nombres de columna del giro."""
    salida = ventas[COLUMNAS_VENTAS].copy()
    salida["Fecha"] = salida["Fecha"].dt.date
    salida.columns = giro.columnas_ventas
    memoria = BytesIO()
    with pd.ExcelWriter(memoria, engine="openpyxl") as escritor:
        salida.to_excel(escritor, sheet_name="Ventas", index=False)
    return memoria.getvalue()


def tabla_resurtir(ventas, inventario):
    """Calcula para cuántos días alcanza cada producto al ritmo de venta reciente.

    Usa siempre las últimas ventas del archivo, sin filtros: lo que se debe
    comprar no cambia por el periodo que se esté mirando en el tablero.
    """
    ultima = ventas["Fecha"].max()
    recientes = ventas[ventas["Fecha"] > ultima - pd.Timedelta(days=DIAS_CONSUMO)]
    venta_diaria = recientes.groupby("Producto")["Cantidad"].sum() / DIAS_CONSUMO

    tabla = inventario.copy()
    tabla["Venta diaria"] = tabla["Producto"].map(venta_diaria).fillna(0)
    con_venta = tabla["Venta diaria"] > 0
    tabla["Días de existencia"] = (tabla["Existencia"] / tabla["Venta diaria"]).where(con_venta)
    tabla["Estado"] = "Sin ventas recientes"
    tabla.loc[con_venta, "Estado"] = "Suficiente"
    tabla.loc[con_venta & (tabla["Días de existencia"] < DIAS_PRONTO), "Estado"] = "Pronto"
    tabla.loc[con_venta & (tabla["Días de existencia"] < DIAS_URGENTE), "Estado"] = "Urgente"
    return tabla.sort_values("Días de existencia", na_position="last").reset_index(drop=True)
