"""Pruebas de la tabla de resurtido (giros con inventario = true)."""
import pandas as pd

from conftest import fila, ventas
from tablero import calculos, lectura


def tabla():
    # Última venta del archivo: 31 jul. La ventana de 30 días va del 2 al 31 de julio.
    datos = ventas(
        fila("31/07/2026", 1, producto="A", cantidad=30),  # 1 al día
        fila("31/07/2026", 2, producto="B", cantidad=30),
        fila("31/07/2026", 3, producto="C", cantidad=30),
        fila("01/07/2026", 4, producto="E", cantidad=90),  # justo fuera de la ventana
    )
    inventario = pd.DataFrame({
        "Producto": ["C", "B", "A", "A", "D", "E"],
        "Existencia": [20, 10, 3, 2, 5, 5],  # A aparece dos veces: 3 + 2
    })
    return calculos.tabla_resurtir(datos, lectura.limpiar_inventario(inventario)).set_index("Producto")


def test_estados_por_dias_de_existencia():
    t = tabla()
    assert t.loc["A", "Estado"] == "Urgente"      # 5 días
    assert t.loc["B", "Estado"] == "Pronto"       # 10 días
    assert t.loc["C", "Estado"] == "Suficiente"   # 20 días


def test_existencias_repetidas_se_suman():
    assert tabla().loc["A", "Existencia"] == 5


def test_sin_ventas_recientes():
    t = tabla()
    assert t.loc["D", "Estado"] == "Sin ventas recientes"  # nunca se vendió
    assert t.loc["E", "Estado"] == "Sin ventas recientes"  # se vendió hace más de 30 días
    assert pd.isna(t.loc["D", "Días de existencia"])


def test_orden_del_mas_urgente_al_menos():
    assert list(tabla().index[:3]) == ["A", "B", "C"]


def test_umbrales_exactos():
    # 7 días exactos ya no es Urgente; 15 exactos ya no es Pronto
    datos = ventas(fila("31/07/2026", 1, producto="X", cantidad=30), fila("31/07/2026", 2, producto="Y", cantidad=30))
    inventario = pd.DataFrame({"Producto": ["X", "Y"], "Existencia": [calculos.DIAS_URGENTE, calculos.DIAS_PRONTO]})
    t = calculos.tabla_resurtir(datos, inventario).set_index("Producto")
    assert t.loc["X", "Estado"] == "Pronto"
    assert t.loc["Y", "Estado"] == "Suficiente"
