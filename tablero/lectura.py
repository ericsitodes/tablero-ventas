"""Lectura y validación del Excel: hojas, columnas, tipos, tamaño y archivos maliciosos."""
import unicodedata
import zipfile
from io import BytesIO

import pandas as pd
from openpyxl import load_workbook

from tablero.formato import filas_texto
from tablero.giro import COLUMNAS_VENTAS, cargar_marca

WHATSAPP = cargar_marca().enlace_whatsapp
LIMITE_FILAS = 200_000  # filas de la hoja Ventas; el tamaño lo limita config.toml (10 MB)
# Un .xlsx es un ZIP: 10 MB comprimidos pueden ocupar cientos al abrirse. 200 000 filas son ~100 MB.
LIMITE_DESCOMPRIMIDO = 120 * 1024 * 1024

COLUMNAS_GASTOS = ["Mes", "Concepto", "Monto"]
COLUMNAS_TEXTO = ("Producto", "Categoría", "Método de pago", "Persona")  # se limpian de espacios de más

# Meses en español dentro de fechas escritas como texto, para poder leerlas
MESES_TEXTO = {"enero": "jan", "febrero": "feb", "marzo": "mar", "abril": "apr", "mayo": "may",
               "junio": "jun", "julio": "jul", "agosto": "aug", "septiembre": "sep", "setiembre": "sep",
               "octubre": "oct", "noviembre": "nov", "diciembre": "dec",
               "ene": "jan", "abr": "apr", "ago": "aug", "dic": "dec"}


class ErrorFormato(Exception):
    """El Excel subido no tiene el formato esperado."""


class ArchivoGrande(ErrorFormato):
    """La hoja Ventas pasa de LIMITE_FILAS."""


def clave(texto):
    """Compara nombres sin mayúsculas, acentos ni espacios de más: " CATEGORIA " = "Categoría"."""
    sin_acentos = unicodedata.normalize("NFKD", str(texto)).encode("ascii", "ignore").decode()
    return " ".join(sin_acentos.lower().split())


def buscar_hoja(hojas, nombre):
    """Devuelve el nombre real de la hoja, o explica cuáles trae el archivo."""
    for real in hojas:
        if clave(real) == clave(nombre):
            return real
    raise ErrorFormato(f'Falta la hoja "{nombre}". Tu archivo tiene: {", ".join(map(str, hojas))}.')


def leer_hoja(hojas, nombre, columnas):
    """Toma una hoja y comprueba que traiga todas las columnas, en cualquier orden."""
    tabla = hojas[buscar_hoja(hojas, nombre)]
    reales = {clave(c): c for c in tabla.columns}
    faltantes = [c for c in columnas if clave(c) not in reales]
    if faltantes:
        raise ErrorFormato(f'A la hoja "{nombre}" le faltan columnas: {", ".join(faltantes)}.')
    tabla = tabla[[reales[clave(c)] for c in columnas]].copy()
    tabla.columns = columnas
    return tabla.dropna(how="all")  # las filas vacías no cuentan como errores


def a_numero(serie):
    """Convierte números escritos como texto ("$1,250.50"); lo que no es número queda vacío."""
    if pd.api.types.is_numeric_dtype(serie):
        return serie
    texto = serie.astype("string").str.replace(r"[$,\s]", "", regex=True)
    return pd.to_numeric(texto, errors="coerce").astype("float64")


def a_fecha(serie):
    """Lee fechas reales y de texto: 15/07/2026, 2026-07-15, 15 jul 2026 o 15 de julio de 2026."""
    if pd.api.types.is_datetime64_any_dtype(serie):
        return serie
    texto = serie.astype("string").str.strip().str.lower().str.replace(r"\bde\b", " ", regex=True)
    texto = texto.str.replace(r"\b(" + "|".join(MESES_TEXTO) + r")\b",
                              lambda m: MESES_TEXTO[m.group(1)], regex=True)
    anio_primero = texto.str.match(r"\d{4}[-/]").fillna(False).astype(bool)  # 2026-07-15
    con_dia_primero = pd.to_datetime(texto.where(~anio_primero), errors="coerce", dayfirst=True, format="mixed")
    con_anio_primero = pd.to_datetime(texto.where(anio_primero), errors="coerce", format="mixed")
    fechas = con_dia_primero.fillna(con_anio_primero)
    # Sin año ("julio 4") se lee como el año 1: una fecha así no es confiable
    return fechas.where(fechas.dt.year.between(2000, 2100))


def limpiar_ventas(ventas, avisos):
    """Convierte los tipos de la hoja Ventas y descarta filas inservibles, avisando cuántas."""
    ventas["Fecha"] = a_fecha(ventas["Fecha"]).dt.normalize()
    ventas["Total"] = a_numero(ventas["Total"])
    ventas["Cantidad"] = a_numero(ventas["Cantidad"])
    ventas["HoraNum"] = pd.to_datetime(ventas["Hora"].astype(str), errors="coerce", format="mixed").dt.hour
    antes = len(ventas)
    ventas = ventas.dropna(subset=["Fecha", "Total", "Cantidad", "HoraNum"])
    if ventas.empty:
        raise ErrorFormato('La hoja "Ventas" no tiene filas válidas.')
    if len(ventas) < antes:
        avisos.append(f'No se incluyeron {filas_texto(antes - len(ventas))} de "Ventas" porque la fecha, '
                      "la hora, la cantidad o el total están vacíos o no se entienden.")
    ventas = ventas.assign(HoraNum=ventas["HoraNum"].astype(int))
    for columna in COLUMNAS_TEXTO:
        ventas[columna] = ventas[columna].astype(str).str.strip()
    return ventas


def limpiar_gastos(gastos, avisos):
    """Convierte los tipos de la hoja Gastos y agrega el total por mes."""
    gastos["Mes"] = a_fecha(gastos["Mes"]).dt.to_period("M")
    gastos["Monto"] = a_numero(gastos["Monto"])
    validos = gastos.dropna(subset=["Mes", "Monto"])
    if len(validos) < len(gastos):
        avisos.append(f'No se incluyeron {filas_texto(len(gastos) - len(validos))} de "Gastos" porque el mes '
                      "o el monto están vacíos o no se entienden.")
    return validos.groupby("Mes")["Monto"].sum()


def limpiar_inventario(inventario):
    """Convierte los tipos de la hoja Inventario y suma productos repetidos."""
    inventario["Producto"] = inventario["Producto"].astype(str).str.strip()
    inventario["Existencia"] = a_numero(inventario["Existencia"])
    return inventario.dropna(subset=["Existencia"]).groupby("Producto", as_index=False)["Existencia"].sum()


def contar_filas(contenido):
    """Cuenta las filas de la hoja Ventas sin leer todo el archivo; None si no se puede saber."""
    try:
        libro = load_workbook(BytesIO(contenido), read_only=True)
        for hoja in libro.worksheets:
            if clave(hoja.title) == clave("Ventas"):
                if hoja.max_row is not None:
                    return hoja.max_row
                # Algunos programas no guardan el tamaño de la hoja: contar hasta pasar el límite
                filas = 0
                for filas, _ in enumerate(hoja.iter_rows(values_only=True), start=1):
                    if filas > LIMITE_FILAS + 1:
                        break
                return filas
    except Exception:
        pass  # si no abre, pd.read_excel dará el mensaje
    return None


def revisar_tamano(filas):
    """Detiene la lectura si la hoja Ventas pasa del límite."""
    if filas is not None and filas > LIMITE_FILAS:
        raise ArchivoGrande(f"Tu archivo tiene {filas:,} filas de ventas y el tablero acepta hasta "
                            f"{LIMITE_FILAS:,}. Sube un periodo más corto, por ejemplo unos meses, "
                            f"o [escríbeme por WhatsApp]({WHATSAPP}).")


def revisar_zip(contenido):
    """Rechaza el archivo si al descomprimirse pasa de LIMITE_DESCOMPRIMIDO.

    zipfile nunca entrega más bytes de los que el archivo declara (si miente,
    falla el CRC), así que la suma declarada es un tope confiable de memoria.
    """
    try:
        with zipfile.ZipFile(BytesIO(contenido)) as libro:
            total = sum(parte.file_size for parte in libro.infolist())
    except zipfile.BadZipFile as error:
        raise ErrorFormato("El archivo no se pudo abrir como Excel (.xlsx).") from error
    if total > LIMITE_DESCOMPRIMIDO:
        raise ArchivoGrande("Tu archivo es demasiado grande para el tablero. Sube un periodo más corto, "
                            f"por ejemplo unos meses, o [escríbeme por WhatsApp]({WHATSAPP}).")


def leer_libro(contenido, giro):
    """Recibe los bytes del Excel y devuelve (ventas, gastos por mes, inventario, avisos).

    Las columnas se devuelven con los nombres internos (Producto, Persona).
    inventario es None si el giro no lo usa.
    """
    revisar_zip(contenido)
    filas = contar_filas(contenido)
    revisar_tamano(filas - 1 if filas else None)  # sin contar los títulos
    try:
        hojas = pd.read_excel(BytesIO(contenido), sheet_name=None, engine="openpyxl")
    except Exception as error:
        raise ErrorFormato("El archivo no se pudo abrir como Excel (.xlsx).") from error
    revisar_tamano(len(hojas[buscar_hoja(hojas, "Ventas")].dropna(how="all")))  # por si no se pudo contar
    avisos = []
    crudas = leer_hoja(hojas, "Ventas", giro.columnas_ventas)
    crudas.columns = COLUMNAS_VENTAS
    ventas = limpiar_ventas(crudas, avisos)
    gastos = limpiar_gastos(leer_hoja(hojas, "Gastos", COLUMNAS_GASTOS), avisos)
    inventario = None
    if giro.inventario:
        crudo = leer_hoja(hojas, "Inventario", [giro.col_producto, "Existencia"])
        crudo.columns = ["Producto", "Existencia"]
        inventario = limpiar_inventario(crudo)
    return ventas, gastos, inventario, avisos
