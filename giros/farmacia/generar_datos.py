"""Genera el Excel de ejemplo con datos ficticios de "Farmacia Brisas del Golfo".

Uso: python generar_datos.py

La semilla es fija, así que cada ejecución produce exactamente los mismos datos.
"""

from pathlib import Path

import numpy as np
import pandas as pd
from openpyxl.styles import Font

FECHA_INICIO = "2026-04-01"
FECHA_FIN = "2026-09-30"
DIAS_RECIENTES = 30

SEMILLA = 2030
ARCHIVO = Path(__file__).parent / "ventas_farmacia.xlsx"

# Catálogo: (producto, categoría, precio en MXN, popularidad relativa)
CATALOGO = [
    ("Paracetamol 500 mg", "Medicinas", 38, 60), ("Ibuprofeno 400 mg", "Medicinas", 62, 42),
    ("Loratadina 10 mg", "Medicinas", 74, 26), ("Omeprazol 20 mg", "Medicinas", 88, 24),
    ("Naproxeno 250 mg", "Medicinas", 69, 20), ("Antiácido masticable", "Medicinas", 54, 22),
    ("Jarabe para la tos", "Medicinas", 128, 22), ("Suero oral 500 ml", "Medicinas", 26, 36),
    ("Crema antihistamínica", "Medicinas", 96, 10),
    ("Jabón antibacterial", "Higiene", 32, 20), ("Pasta dental 100 ml", "Higiene", 48, 18),
    ("Shampoo 400 ml", "Higiene", 86, 14), ("Desodorante", "Higiene", 72, 16),
    ("Protector solar FPS 50", "Higiene", 245, 8),
    ("Pañales etapa 3", "Bebé", 215, 18), ("Toallitas húmedas", "Bebé", 52, 20),
    ("Fórmula infantil 400 g", "Bebé", 285, 7), ("Crema para rozaduras", "Bebé", 92, 6),
    ("Vitamina C 1 g", "Vitaminas", 115, 16), ("Complejo B", "Vitaminas", 138, 9),
    ("Multivitamínico", "Vitaminas", 265, 5),
    ("Alcohol 250 ml", "Primeros auxilios", 34, 14), ("Gasas estériles", "Primeros auxilios", 28, 11),
    ("Curitas 20 piezas", "Primeros auxilios", 36, 14),
]

METODOS_PAGO = ["Efectivo", "Tarjeta", "Transferencia"]
PESOS_PAGO = [0.52, 0.38, 0.10]
CAJEROS = {"Sofía": (1, 1.3), "Daniel": (3, 1.1), "Rosa": (5, 1.0), "Óscar": (0, 0.8)}
TICKETS_POR_DIA = [70, 66, 66, 68, 74, 80, 62]
FACTOR_MES = {4: 1.02, 5: 1.0, 6: 1.05, 7: 0.96, 8: 0.94, 9: 1.08}
PESOS_HORA = {8: 4, 9: 8, 10: 10, 11: 10, 12: 8, 13: 7, 14: 6, 15: 5, 16: 5, 17: 7,
              18: 9, 19: 11, 20: 11, 21: 8, 22: 4}
PRODUCTOS_POR_TICKET = ([1, 2, 3, 4, 5], [0.42, 0.31, 0.16, 0.08, 0.03])
COSTO_MERCANCIA = (0.68, 0.71)
GASTOS_FIJOS = {"Renta": 18000, "Nómina": 46000, "Otros": 7000}
LUZ_ALTA, LUZ_BAJA = (7000, 8500), (5000, 6000)


def generar_ventas(rng):
    """Genera una fila por producto de cada ticket."""
    horas = np.array(list(PESOS_HORA))
    pesos_hora = np.array(list(PESOS_HORA.values()), dtype=float)
    pesos_hora /= pesos_hora.sum()
    pesos_catalogo = np.array([p[3] for p in CATALOGO], dtype=float)
    pesos_catalogo /= pesos_catalogo.sum()
    tamanos, pesos_tamano = PRODUCTOS_POR_TICKET

    filas = []
    folio = 1
    for dia in pd.date_range(FECHA_INICIO, FECHA_FIN):
        media = TICKETS_POR_DIA[dia.day_of_week] * FACTOR_MES[dia.month]
        turno = [(n, p) for n, (descanso, p) in CAJEROS.items() if descanso != dia.day_of_week]
        nombres = [n for n, _ in turno]
        pesos = np.array([p for _, p in turno])

        registros = sorted(
            (int(rng.choice(horas, p=pesos_hora)), int(rng.integers(0, 60)))
            for _ in range(rng.poisson(media))
        )
        for hora, minuto in registros:
            ticket = f"T-{folio:05d}"
            folio += 1
            cajero = str(rng.choice(nombres, p=pesos / pesos.sum()))
            metodo = str(rng.choice(METODOS_PAGO, p=PESOS_PAGO))
            indices = rng.choice(len(CATALOGO), size=rng.choice(tamanos, p=pesos_tamano), p=pesos_catalogo)
            for indice, cantidad in zip(*np.unique(indices, return_counts=True)):
                producto, categoria, precio, _ = CATALOGO[indice]
                filas.append({
                    "Fecha": dia.date(),
                    "Hora": f"{hora:02d}:{minuto:02d}",
                    "Ticket": ticket,
                    "Producto": producto,
                    "Categoría": categoria,
                    "Cantidad": int(cantidad),
                    "Precio unitario": precio,
                    "Total": int(cantidad) * precio,
                    "Método de pago": metodo,
                    "Cajero": cajero,
                })
    return pd.DataFrame(filas)


def generar_gastos(rng, ventas):
    """Genera los gastos mensuales; la mercancía depende de lo vendido."""
    meses = pd.to_datetime(ventas["Fecha"]).dt.to_period("M")
    filas = []
    for mes, total in ventas.groupby(meses)["Total"].sum().items():
        luz = LUZ_ALTA if mes.month in (5, 6, 7, 8) else LUZ_BAJA  # el aire acondicionado sube la luz
        conceptos = {"Mercancía": total * rng.uniform(*COSTO_MERCANCIA), **GASTOS_FIJOS, "Luz": rng.integers(*luz)}
        for concepto, monto in conceptos.items():
            filas.append({"Mes": mes.to_timestamp().date(), "Concepto": concepto, "Monto": round(float(monto), 2)})
    return pd.DataFrame(filas)


def generar_inventario(rng, ventas):
    """Da a cada producto entre 2 y 45 días de existencia al ritmo reciente."""
    fechas = pd.to_datetime(ventas["Fecha"])
    recientes = ventas[fechas > fechas.max() - pd.Timedelta(days=DIAS_RECIENTES)]
    venta_diaria = recientes.groupby("Producto")["Cantidad"].sum() / DIAS_RECIENTES
    filas = []
    for producto, _, _, _ in CATALOGO:
        dias = rng.uniform(2, 45)
        filas.append({"Producto": producto, "Existencia": int(round(venta_diaria.get(producto, 0) * dias))})
    return pd.DataFrame(filas)


def guardar_excel(ventas, gastos, inventario):
    """Escribe las tres hojas con formato de fecha, moneda y anchos legibles."""
    with pd.ExcelWriter(ARCHIVO, engine="openpyxl") as escritor:
        ventas.to_excel(escritor, sheet_name="Ventas", index=False)
        gastos.to_excel(escritor, sheet_name="Gastos", index=False)
        inventario.to_excel(escritor, sheet_name="Inventario", index=False)

        formatos = {"Fecha": "dd/mm/yyyy", "Mes": "mm/yyyy", "Precio unitario": '"$"#,##0.00',
                    "Total": '"$"#,##0.00', "Monto": '"$"#,##0.00'}
        for hoja in escritor.sheets.values():
            hoja.freeze_panes = "A2"
            for columna in hoja.columns:
                encabezado = columna[0].value
                columna[0].font = Font(bold=True)
                ancho = 28 if encabezado == "Producto" else max(len(str(encabezado)), 12)
                hoja.column_dimensions[columna[0].column_letter].width = ancho + 2
                if encabezado in formatos:
                    for celda in columna[1:]:
                        celda.number_format = formatos[encabezado]


def main():
    rng = np.random.default_rng(SEMILLA)
    ventas = generar_ventas(rng)
    gastos = generar_gastos(rng, ventas)
    inventario = generar_inventario(rng, ventas)
    guardar_excel(ventas, gastos, inventario)
    print(f"Listo: {ARCHIVO.name}")
    print(f"{len(ventas):,} filas, {ventas['Ticket'].nunique():,} tickets, ${ventas['Total'].sum():,.2f} en ventas")


if __name__ == "__main__":
    main()
