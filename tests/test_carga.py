"""Pruebas de la lectura del Excel subido: formato, tamaño y archivos maliciosos."""
import zipfile
from io import BytesIO

import pytest

import app


def test_excel_de_ejemplo_se_lee():
    ventas = app.leer_libro(app.ARCHIVO_DEMO.read_bytes())[0]
    assert not ventas.empty


def test_plantilla_pasa_el_limite_descomprimido():
    app.revisar_zip(app.PLANTILLA.read_bytes())  # no debe lanzar


def test_zip_que_se_infla_se_rechaza_antes_de_abrirlo(monkeypatch):
    # 2 MB de ceros comprimen a unos KB; con el límite en 1 MB debe rechazarse
    memoria = BytesIO()
    with zipfile.ZipFile(memoria, "w", zipfile.ZIP_DEFLATED) as libro:
        libro.writestr("xl/worksheets/sheet1.xml", b"0" * (2 * 1024 * 1024))
    monkeypatch.setattr(app, "LIMITE_DESCOMPRIMIDO", 1024 * 1024)

    def no_debe_llamarse(*args, **kwargs):
        raise AssertionError("se intentó abrir el archivo antes de revisar su tamaño")

    monkeypatch.setattr(app.pd, "read_excel", no_debe_llamarse)
    with pytest.raises(app.ArchivoGrande):
        app.leer_libro(memoria.getvalue())


def test_archivo_que_no_es_excel_da_error_de_formato():
    with pytest.raises(app.ErrorFormato, match="no se pudo abrir"):
        app.leer_libro(b"esto no es un archivo de Excel")


def test_openpyxl_usa_defusedxml():
    from openpyxl.xml import DEFUSEDXML
    assert DEFUSEDXML, "falta defusedxml: openpyxl quedaría expuesto a ataques XML"
