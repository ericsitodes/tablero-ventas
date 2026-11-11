"""Textos en español para montos, fechas y nombres de archivo."""
import re
import unicodedata

# Fechas en español escritas a mano: en la nube no hay locale es_MX instalado
MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]
DIAS = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]


def moneda(valor):
    """1234.5 -> $1,234.50"""
    signo = "-" if valor < 0 else ""
    return f"{signo}${abs(valor):,.2f}"


def fecha_es(dia):
    """Convierte una fecha en texto como 5 jul 2026."""
    return f"{dia.day} {MESES[dia.month - 1]} {dia.year}"


def fecha_larga(dia):
    """Convierte una fecha en texto como Dom 5 jul 2026."""
    return f"{DIAS[dia.weekday()]} {fecha_es(dia)}"


def mes_es(periodo):
    """Convierte un periodo mensual en texto como jul 2026."""
    return f"{MESES[periodo.month - 1]} {periodo.year}"


def nombre_archivo(negocio):
    """Convierte "Doña Lupe, Centro" en dona_lupe_centro para nombrar archivos."""
    sin_acentos = unicodedata.normalize("NFKD", negocio).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "_", sin_acentos.lower()).strip("_") or "tu_negocio"


def filas_texto(n):
    """1 -> "1 fila"; 3 -> "3 filas"."""
    return f"{n:,} fila" if n == 1 else f"{n:,} filas"
