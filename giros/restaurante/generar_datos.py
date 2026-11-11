"""Genera ventas_restaurante.xlsx con datos ficticios de "La Palapa del Golfo".

Uso: python generar_datos.py

La semilla es fija, así que cada ejecución produce exactamente los mismos datos.
"""

from pathlib import Path

import numpy as np
import pandas as pd
from openpyxl.styles import Font

SEMILLA = 2026
ARCHIVO = Path(__file__).parent / "ventas_restaurante.xlsx"
FECHA_INICIO = "2026-04-01"
FECHA_FIN = "2026-09-30"

# Menú: (platillo, categoría, precio en MXN, popularidad relativa)
MENU = [
    ("Tostadas de jaiba", "Entradas", 95, 30),
    ("Empanadas de camarón", "Entradas", 110, 22),
    ("Guacamole con totopos", "Entradas", 85, 12),
    ("Arrachera con frijoles", "Platos fuertes", 265, 14),
    ("Pollo a la plancha", "Platos fuertes", 175, 8),
    ("Bistec encebollado", "Platos fuertes", 185, 5),
    ("Coctel de camarón", "Mariscos", 185, 46),
    ("Campechana de mariscos", "Mariscos", 215, 24),
    ("Pescado a la veracruzana", "Mariscos", 235, 34),
    ("Filete empanizado", "Mariscos", 210, 28),
    ("Camarones al mojo de ajo", "Mariscos", 265, 26),
    ("Arroz a la tumbada", "Mariscos", 245, 16),
    ("Mojarra frita", "Mariscos", 195, 20),
    ("Pulpos en su tinta", "Mariscos", 285, 4),
    ("Agua de horchata", "Bebidas", 40, 30),
    ("Refresco", "Bebidas", 35, 34),
    ("Cerveza", "Bebidas", 50, 44),
    ("Michelada", "Bebidas", 80, 18),
    ("Flan napolitano", "Postres", 65, 12),
    ("Plátanos fritos con crema", "Postres", 60, 3),
]

METODOS_PAGO = ["Efectivo", "Tarjeta", "Transferencia"]
PESOS_PAGO = [0.46, 0.39, 0.15]

# Cada mesero descansa un día de la semana (0 = lunes) y tiene un peso de tickets
MESEROS = {
    "Luis": (0, 1.3),
    "Carmen": (1, 1.15),
    "Jorge": (2, 1.0),
    "Ana": (3, 0.9),
    "Raúl": (0, 0.7),
}

# Tickets promedio por día de la semana (lunes a domingo)
TICKETS_POR_DIA = [14, 15, 16, 19, 28, 38, 36]

# Temporada: julio y agosto son vacaciones; septiembre es el mes flojo
FACTOR_MES = {4: 1.05, 5: 1.0, 6: 0.92, 7: 1.12, 8: 1.08, 9: 0.68}

# Peso de cada hora: picos de 13 a 17 h y de 19 a 21 h
PESOS_HORA = {12: 3, 13: 12, 14: 17, 15: 18, 16: 14, 17: 9, 18: 4, 19: 10, 20: 11, 21: 8}


def elegir_platillos(rng, categorias, cantidad):
    """Elige platillos de las categorías indicadas según su popularidad."""
    opciones = [m for m in MENU if m[1] in categorias]
    pesos = np.array([m[3] for m in opciones], dtype=float)
    indices = rng.choice(len(opciones), size=cantidad, p=pesos / pesos.sum())
    return [opciones[i] for i in indices]


def armar_comanda(rng):
    """Devuelve {platillo: cantidad} para una mesa de 1 a 6 personas."""
    personas = rng.choice([1, 2, 3, 4, 5, 6], p=[0.12, 0.38, 0.18, 0.2, 0.07, 0.05])
    pedido = elegir_platillos(rng, ("Mariscos", "Platos fuertes"), personas)
    pedido += elegir_platillos(rng, ("Bebidas",), personas + rng.integers(0, 3))
    if rng.random() < 0.45:
        pedido += elegir_platillos(rng, ("Entradas",), 1 + (personas >= 4))
    if rng.random() < 0.18:
        pedido += elegir_platillos(rng, ("Postres",), 1)

    comanda = {}
    for platillo in pedido:
        comanda[platillo] = comanda.get(platillo, 0) + 1
    return comanda


def generar_ventas(rng):
    """Genera una fila por platillo de cada ticket."""
    horas = np.array(list(PESOS_HORA))
    pesos_hora = np.array(list(PESOS_HORA.values()), dtype=float)
    pesos_hora /= pesos_hora.sum()

    filas = []
    folio = 1
    for dia in pd.date_range(FECHA_INICIO, FECHA_FIN):
        media = TICKETS_POR_DIA[dia.day_of_week] * FACTOR_MES[dia.month]
        meseros = [(n, p) for n, (descanso, p) in MESEROS.items() if descanso != dia.day_of_week]
        nombres = [n for n, _ in meseros]
        pesos = np.array([p for _, p in meseros])

        registros = sorted(
            (int(rng.choice(horas, p=pesos_hora)), int(rng.integers(0, 60)))
            for _ in range(rng.poisson(media))
        )
        for hora, minuto in registros:
            ticket = f"T-{folio:05d}"
            folio += 1
            mesero = rng.choice(nombres, p=pesos / pesos.sum())
            metodo = rng.choice(METODOS_PAGO, p=PESOS_PAGO)
            for (platillo, categoria, precio, _), cantidad in armar_comanda(rng).items():
                filas.append({
                    "Fecha": dia.date(),
                    "Hora": f"{hora:02d}:{minuto:02d}",
                    "Ticket": ticket,
                    "Platillo": platillo,
                    "Categoría": categoria,
                    "Cantidad": cantidad,
                    "Precio unitario": precio,
                    "Total": cantidad * precio,
                    "Método de pago": metodo,
                    "Mesero": str(mesero),
                })
    return pd.DataFrame(filas)


def generar_gastos(rng, ventas):
    """Genera los gastos mensuales; los insumos dependen de lo vendido."""
    meses = pd.to_datetime(ventas["Fecha"]).dt.to_period("M")
    ventas_mes = ventas.groupby(meses)["Total"].sum()

    filas = []
    for mes, total in ventas_mes.items():
        verano = mes.month in (5, 6, 7, 8)  # el aire acondicionado sube la luz
        conceptos = {
            "Insumos": total * rng.uniform(0.34, 0.37),
            "Renta": 45000,
            "Nómina": 175000 + rng.integers(-3000, 3000),
            "Luz": rng.integers(24000, 29000) if verano else rng.integers(16000, 20000),
            "Gas": rng.integers(9000, 12500),
            "Otros": rng.integers(24000, 31000),
        }
        for concepto, monto in conceptos.items():
            filas.append({"Mes": mes.to_timestamp().date(), "Concepto": concepto, "Monto": round(float(monto), 2)})
    return pd.DataFrame(filas)


def guardar_excel(ventas, gastos):
    """Escribe las dos hojas con formato de fecha, moneda y anchos legibles."""
    with pd.ExcelWriter(ARCHIVO, engine="openpyxl") as escritor:
        ventas.to_excel(escritor, sheet_name="Ventas", index=False)
        gastos.to_excel(escritor, sheet_name="Gastos", index=False)

        formatos = {"Fecha": "dd/mm/yyyy", "Mes": "mm/yyyy", "Precio unitario": '"$"#,##0.00',
                    "Total": '"$"#,##0.00', "Monto": '"$"#,##0.00'}
        for hoja in escritor.sheets.values():
            hoja.freeze_panes = "A2"
            for columna in hoja.columns:
                encabezado = columna[0].value
                columna[0].font = Font(bold=True)
                ancho = max(len(str(encabezado)), 12)
                if encabezado == "Platillo":
                    ancho = 28
                hoja.column_dimensions[columna[0].column_letter].width = ancho + 2
                if encabezado in formatos:
                    for celda in columna[1:]:
                        celda.number_format = formatos[encabezado]


def main():
    rng = np.random.default_rng(SEMILLA)
    ventas = generar_ventas(rng)
    gastos = generar_gastos(rng, ventas)
    guardar_excel(ventas, gastos)
    print(f"Listo: {ARCHIVO.name}")
    print(f"{len(ventas):,} filas, {ventas['Ticket'].nunique():,} tickets, ${ventas['Total'].sum():,.2f} en ventas")


if __name__ == "__main__":
    main()
