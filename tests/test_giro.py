"""Pruebas de la configuración: marca.toml y giros/<giro>/giro.toml."""
import shutil

import pytest

from conftest import GIROS
from tablero.giro import (COLUMNAS_VENTAS, RAIZ, ErrorConfiguracion, cargar_giro, cargar_marca,
                          giros_disponibles)


def test_estan_los_tres_giros():
    assert {"tienda", "farmacia", "restaurante"} <= set(GIROS)


def test_cada_giro_carga_completo(giro):
    assert giro.archivo_demo.is_file() and giro.plantilla.is_file()
    assert len(giro.columnas_ventas) == len(COLUMNAS_VENTAS)
    assert giro.traducir("Producto") == giro.col_producto
    assert giro.traducir("Persona") == giro.col_persona
    assert giro.traducir("Total") == "Total"


def test_restaurante_traduce_platillo_y_mesero():
    restaurante = cargar_giro("restaurante")
    assert "Platillo" in restaurante.columnas_ventas and "Mesero" in restaurante.columnas_ventas
    assert restaurante.inventario is False


def test_cada_giro_tiene_su_archivo_de_entrada(giro):
    entrada = RAIZ / f"{giro.clave}.py"
    assert entrada.is_file(), f"falta {entrada.name} en la raíz para publicar este giro en Streamlit"
    assert f'main("{giro.clave}")' in entrada.read_text(encoding="utf-8")


@pytest.fixture
def giros_tmp(tmp_path):
    """Copia de giros/tienda en una carpeta temporal, para romperla sin tocar la real."""
    shutil.copytree(RAIZ / "giros" / "tienda", tmp_path / "prueba")
    return tmp_path


def reescribir(giros_tmp, viejo, nuevo):
    ruta = giros_tmp / "prueba" / "giro.toml"
    texto = ruta.read_text(encoding="utf-8")
    assert viejo in texto
    ruta.write_text(texto.replace(viejo, nuevo), encoding="utf-8")


def test_campo_faltante_dice_cual(giros_tmp):
    reescribir(giros_tmp, 'negocio_demo = "Abarrotes El Puerto"\n', "")
    with pytest.raises(ErrorConfiguracion, match="falta 'negocio_demo'"):
        cargar_giro("prueba", giros_tmp)


def test_inventario_debe_ser_booleano(giros_tmp):
    reescribir(giros_tmp, "inventario = true", 'inventario = "sí"')
    with pytest.raises(ErrorConfiguracion, match="'inventario' debe ser true o false"):
        cargar_giro("prueba", giros_tmp)


def test_archivo_demo_inexistente(giros_tmp):
    reescribir(giros_tmp, 'archivo_demo = "ventas_tienda.xlsx"', 'archivo_demo = "no_existe.xlsx"')
    with pytest.raises(ErrorConfiguracion, match="no existe el archivo no_existe.xlsx"):
        cargar_giro("prueba", giros_tmp)


def test_giro_inexistente():
    with pytest.raises(ErrorConfiguracion, match="No existe"):
        cargar_giro("no-existe")


def test_giros_disponibles_lee_las_carpetas(giros_tmp):
    assert giros_disponibles(giros_tmp) == ["prueba"]


def test_marca(tmp_path):
    marca = cargar_marca()
    assert marca.nombre and marca.enlace_whatsapp == f"https://wa.me/{marca.whatsapp}"
    mala = tmp_path / "marca.toml"
    mala.write_text('nombre = "X"\nwhatsapp = "+52 921 123"\n', encoding="utf-8")
    with pytest.raises(ErrorConfiguracion, match="solo dígitos"):
        cargar_marca(mala)
