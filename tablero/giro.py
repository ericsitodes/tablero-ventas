"""Configuración: la marca (marca.toml) y cada giro (giros/<giro>/giro.toml)."""
import tomllib
from dataclasses import dataclass
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
CARPETA_GIROS = RAIZ / "giros"

# Nombres internos de las columnas de Ventas. "Producto" y "Persona" se
# traducen a lo que el giro llama así en su Excel (Platillo, Mesero…).
COLUMNAS_VENTAS = ["Fecha", "Hora", "Ticket", "Producto", "Categoría", "Cantidad",
                   "Precio unitario", "Total", "Método de pago", "Persona"]


class ErrorConfiguracion(Exception):
    """Un archivo .toml de configuración falta o está incompleto."""


def _leer_toml(ruta):
    try:
        with open(ruta, "rb") as archivo:
            return tomllib.load(archivo)
    except FileNotFoundError:
        raise ErrorConfiguracion(f"No existe {ruta}") from None
    except tomllib.TOMLDecodeError as error:
        raise ErrorConfiguracion(f"{ruta} tiene un error de formato: {error}") from None


def _texto(datos, clave, donde):
    valor = datos.get(clave)
    if not isinstance(valor, str) or not valor.strip():
        raise ErrorConfiguracion(f"{donde}: falta '{clave}' o está vacío")
    return valor.strip()


@dataclass(frozen=True)
class Marca:
    nombre: str
    whatsapp: str

    @property
    def enlace_whatsapp(self):
        return f"https://wa.me/{self.whatsapp}"


def cargar_marca(ruta=RAIZ / "marca.toml"):
    datos = _leer_toml(ruta)
    whatsapp = _texto(datos, "whatsapp", ruta.name)
    if not whatsapp.isdigit():
        raise ErrorConfiguracion(f"{ruta.name}: 'whatsapp' debe llevar solo dígitos, como 529211234567")
    return Marca(nombre=_texto(datos, "nombre", ruta.name), whatsapp=whatsapp)


@dataclass(frozen=True)
class Giro:
    clave: str
    negocio_demo: str
    archivo_demo: Path
    plantilla: Path
    inventario: bool
    titulo_resurtir: str
    categorias: tuple
    col_producto: str
    col_persona: str
    productos: str

    @property
    def columnas_ventas(self):
        """Columnas de Ventas con los nombres que ve el negocio, en el orden interno."""
        return [self.traducir(c) for c in COLUMNAS_VENTAS]

    def traducir(self, columna):
        """Nombre interno -> nombre del giro ("Persona" -> "Mesero")."""
        return {"Producto": self.col_producto, "Persona": self.col_persona}.get(columna, columna)


def cargar_giro(clave, carpeta_giros=CARPETA_GIROS):
    carpeta = carpeta_giros / clave
    ruta = carpeta / "giro.toml"
    donde = f"giros/{clave}/giro.toml"
    datos = _leer_toml(ruta)

    columnas = datos.get("columnas")
    textos = datos.get("textos")
    if not isinstance(columnas, dict) or not isinstance(textos, dict):
        raise ErrorConfiguracion(f"{donde}: faltan las secciones [columnas] o [textos]")
    inventario = datos.get("inventario")
    if not isinstance(inventario, bool):
        raise ErrorConfiguracion(f"{donde}: 'inventario' debe ser true o false")
    categorias = datos.get("categorias")
    if not isinstance(categorias, list) or not all(isinstance(c, str) for c in categorias):
        raise ErrorConfiguracion(f"{donde}: 'categorias' debe ser una lista de textos")

    archivos = {}
    for campo in ("archivo_demo", "plantilla"):
        archivos[campo] = carpeta / _texto(datos, campo, donde)
        if not archivos[campo].is_file():
            raise ErrorConfiguracion(f"{donde}: no existe el archivo {archivos[campo].name}")

    return Giro(
        clave=clave,
        negocio_demo=_texto(datos, "negocio_demo", donde),
        archivo_demo=archivos["archivo_demo"],
        plantilla=archivos["plantilla"],
        inventario=inventario,
        titulo_resurtir=_texto(datos, "titulo_resurtir", donde),
        categorias=tuple(categorias),
        col_producto=_texto(columnas, "producto", f"{donde} [columnas]"),
        col_persona=_texto(columnas, "persona", f"{donde} [columnas]"),
        productos=_texto(textos, "productos", f"{donde} [textos]"),
    )


def giros_disponibles(carpeta_giros=CARPETA_GIROS):
    return sorted(p.parent.name for p in carpeta_giros.glob("*/giro.toml"))
