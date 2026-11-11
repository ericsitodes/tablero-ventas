"""Arranca la app de cada giro con el simulador de Streamlit."""
from streamlit.testing.v1 import AppTest

from tablero.giro import RAIZ


def test_app_arranca_sin_errores(giro):
    at = AppTest.from_file(str(RAIZ / f"{giro.clave}.py"), default_timeout=120).run()
    assert not at.exception, [e.value for e in at.exception]
    assert not at.error
    assert at.title[0].value == f"Tablero de ventas · {giro.negocio_demo}"
    subtitulos = [s.value for s in at.subheader]
    assert f"Top 10 {giro.productos}" in subtitulos
    assert f"Ventas por {giro.col_persona.lower()}" in subtitulos
    assert (giro.titulo_resurtir in subtitulos) == giro.inventario
