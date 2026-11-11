"""Datos de prueba pequeños y armados a mano, y el giro como parámetro.

Las pruebas que reciben `giro` corren una vez por cada carpeta de giros/.
Las filas usan los nombres internos (Producto, Persona); para armar un
Excel como el del negocio se usa giro.columnas_ventas.
"""
from io import BytesIO

import pandas as pd
import pytest

from tablero.giro import COLUMNAS_VENTAS, cargar_giro, giros_disponibles
from tablero.lectura import limpiar_ventas

GIROS = giros_disponibles()


@pytest.fixture(params=GIROS)
def giro(request):
    return cargar_giro(request.param)


def fila(fecha, ticket, producto="Agua", cantidad=1, total=10.0, categoria="Bebidas",
         hora="12:00", metodo="Efectivo", persona="Ana"):
    """Una fila cruda de la hoja Ventas, con los nombres internos de columna."""
    precio = total / cantidad if isinstance(total, (int, float)) and cantidad else total
    valores = [fecha, hora, ticket, producto, categoria, cantidad, precio, total, metodo, persona]
    return dict(zip(COLUMNAS_VENTAS, valores))


def ventas(*filas):
    """Ventas ya limpias, como las recibe el tablero después de leer el Excel."""
    return limpiar_ventas(pd.DataFrame(list(filas)), [])


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
