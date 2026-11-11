"""Datos de prueba pequeños y armados a mano.

Usan app.COLUMNAS_VENTAS, así que sirven igual para Producto/Cajero
(tienda, farmacia) que para Platillo/Mesero (restaurante).
"""
from io import BytesIO

import pandas as pd

import app

COL_PRODUCTO = app.COLUMNAS_VENTAS[3]  # Producto o Platillo
COL_PERSONA = app.COLUMNAS_VENTAS[9]   # Cajero o Mesero


def fila(fecha, ticket, producto="Agua", cantidad=1, total=10.0, categoria="Bebidas",
         hora="12:00", metodo="Efectivo", persona="Ana"):
    """Una fila cruda de la hoja Ventas, como vendría en el Excel."""
    precio = total / cantidad if isinstance(total, (int, float)) and cantidad else total
    valores = [fecha, hora, ticket, producto, categoria, cantidad, precio, total, metodo, persona]
    return dict(zip(app.COLUMNAS_VENTAS, valores))


def ventas(*filas):
    """Ventas ya limpias, como las recibe el tablero después de leer el Excel."""
    return app.limpiar_ventas(pd.DataFrame(list(filas)), [])


def gastos(**por_mes):
    """gastos(jul_2026=3100) -> serie mensual como la que devuelve limpiar_gastos."""
    meses = {"ene": 1, "feb": 2, "mar": 3, "abr": 4, "may": 5, "jun": 6,
             "jul": 7, "ago": 8, "sep": 9, "oct": 10, "nov": 11, "dic": 12}
    serie = {}
    for llave, monto in por_mes.items():
        mes, anio = llave.split("_")
        serie[pd.Period(year=int(anio), month=meses[mes], freq="M")] = monto
    return pd.Series(serie, dtype="float64")


def excel(**hojas):
    """excel(Ventas=df, Gastos=df) -> bytes de un .xlsx en memoria."""
    memoria = BytesIO()
    with pd.ExcelWriter(memoria, engine="openpyxl") as escritor:
        for nombre, tabla in hojas.items():
            tabla.to_excel(escritor, sheet_name=nombre, index=False)
    return memoria.getvalue()
