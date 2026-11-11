"""Pruebas de la lectura del Excel subido: formato, tamaño y archivos maliciosos."""
import zipfile
from io import BytesIO

import pytest

from tablero import lectura


def test_excel_de_ejemplo_se_lee(giro):
    ventas, _, inventario, _ = lectura.leer_libro(giro.archivo_demo.read_bytes(), giro)
    assert not ventas.empty
    assert (inventario is not None) == giro.inventario


def test_plantilla_pasa_el_limite_descomprimido(giro):
    lectura.revisar_zip(giro.plantilla.read_bytes())  # no debe lanzar


def test_zip_que_se_infla_se_rechaza_antes_de_abrirlo(monkeypatch, giro):
    # 2 MB de ceros comprimen a unos KB; con el límite en 1 MB debe rechazarse
    memoria = BytesIO()
    with zipfile.ZipFile(memoria, "w", zipfile.ZIP_DEFLATED) as libro:
        libro.writestr("xl/worksheets/sheet1.xml", b"0" * (2 * 1024 * 1024))
    monkeypatch.setattr(lectura, "LIMITE_DESCOMPRIMIDO", 1024 * 1024)

    def no_debe_llamarse(*args, **kwargs):
        raise AssertionError("se intentó abrir el archivo antes de revisar su tamaño")

    monkeypatch.setattr(lectura.pd, "read_excel", no_debe_llamarse)
    with pytest.raises(lectura.ArchivoGrande):
        lectura.leer_libro(memoria.getvalue(), giro)


def test_archivo_que_no_es_excel_da_error_de_formato(giro):
    with pytest.raises(lectura.ErrorFormato, match="no se pudo abrir"):
        lectura.leer_libro(b"esto no es un archivo de Excel", giro)


def test_openpyxl_usa_defusedxml():
    from openpyxl.xml import DEFUSEDXML
    assert DEFUSEDXML, "falta defusedxml: openpyxl quedaría expuesto a ataques XML"
