# Tablero de ventas

Tablero de ventas para negocios pequeños, hecho por Eleva Dev con Python, pandas, Plotly y Streamlit. Un solo código sirve para varios giros (tienda, farmacia, restaurante); lo que cambia entre ellos vive en un archivo de configuración. **Todos los datos de ejemplo son ficticios.**

## Correrlo en tu computadora

Necesitas Python 3.11 o más nuevo.

```powershell
python -m venv .venv
.venv\Scripts\activate          # Linux / macOS: source .venv/bin/activate
pip install -r requirements.txt
streamlit run tienda.py         # o farmacia.py, o restaurante.py
```

Se abre en http://localhost:8501. Para detenerlo, presiona `Ctrl + C` en la terminal.

## Archivos

| Archivo | Para qué sirve |
| --- | --- |
| `tienda.py`, `farmacia.py`, `restaurante.py` | Entrada de cada giro: es el "archivo principal" que se elige en Streamlit |
| `marca.toml` | Nombre del estudio y WhatsApp de los mensajes de error y del pie de página |
| `giros/<giro>/giro.toml` | Lo que cambia entre giros: negocio de ejemplo, columnas, categorías, inventario sí o no |
| `giros/<giro>/ventas_*.xlsx` | Datos de ejemplo del giro |
| `giros/<giro>/plantilla*.xlsx` | Hoja para llenar que se descarga desde la barra lateral |
| `giros/<giro>/generar_datos.py` | Crea el Excel de ejemplo; la semilla fija da siempre los mismos datos |
| `tablero/lectura.py` | Lectura y validación del Excel |
| `tablero/calculos.py` | Periodos, utilidad, indicadores, filtros, resurtido y descarga |
| `tablero/graficas.py` | Gráficas y paleta de colores |
| `tablero/interfaz.py` | Pantalla de Streamlit |
| `tablero/giro.py` | Lee y valida `marca.toml` y los `giro.toml` |
| `tests/` | Pruebas automáticas |
| `.streamlit/config.toml` | Colores del tema y límite de subida (10 MB) |
| `.gitignore` | Evita subir Excel de clientes, entornos y secretos |

## Agregar un giro

1. Crea `giros/<giro>/` (por ejemplo `giros/optica/`) con su Excel de ejemplo, su plantilla y un `giro.toml`. Copia el de un giro parecido y cambia los valores; cada campo está comentado.
2. Crea `<giro>.py` en la raíz con estas líneas:

   ```python
   from tablero.interfaz import main

   main("optica")
   ```

3. Corre `pytest -q`: las pruebas se ejecutan solas también para el giro nuevo y te dicen si falta algo en su configuración.

## Formato para subir tu propio Excel

Hoja **Ventas**: `Fecha`, `Hora`, `Ticket`, `Producto`, `Categoría`, `Cantidad`, `Precio unitario`, `Total`, `Método de pago`, `Cajero`. Cada fila es un producto de un ticket. En restaurante, `Producto` se llama `Platillo` y `Cajero` se llama `Mesero` (lo define `[columnas]` en `giro.toml`).

Hoja **Gastos**: `Mes` (cualquier fecha de ese mes), `Concepto`, `Monto`.

Hoja **Inventario** (solo giros con `inventario = true`): `Producto`, `Existencia`.

## Pruebas

```powershell
pip install -r requirements-dev.txt
pytest -q
```

Las que dependen del giro corren una vez por cada carpeta de `giros/`. Cubren:

- los cálculos: periodo anterior, reparto de gastos, utilidad, indicadores, filtros y resurtido;
- la lectura de fechas y montos escritos de distintas formas;
- la configuración de cada giro;
- el arranque de cada app con el simulador de Streamlit;
- el rechazo de archivos que no son Excel o que al descomprimirse pasan de 120 MB (`LIMITE_DESCOMPRIMIDO` en `tablero/lectura.py`).

`defusedxml` protege a openpyxl de archivos con XML malicioso.

## Cómo se publica

Cada giro es una app distinta en Streamlit Community Cloud, todas desde este repositorio:

| Giro | Archivo principal | Demo |
| --- | --- | --- |
| Tienda | `tienda.py` | https://demo-tienda.streamlit.app/ |
| Farmacia | `farmacia.py` | https://demo-farmacia.streamlit.app/ |
| Restaurante | `restaurante.py` | https://palapa-demo.streamlit.app/ |

Las tres se actualizan solas con cada push a la rama `main`:

```powershell
git add .
git commit -m "Describe tu cambio"
git push origin main
```

Streamlit apaga las apps gratuitas sin visitas: abre el demo antes de cada reunión.

## Dónde se cambian los datos

- **Datos de ejemplo:** edita los catálogos y parámetros de `giros/<giro>/generar_datos.py` y ejecuta `python giros/<giro>/generar_datos.py`. Se reescribe el Excel de ejemplo de ese giro.
- **Nombre del negocio de ejemplo, categorías y textos:** `giros/<giro>/giro.toml`.
- **Nombre del estudio y WhatsApp:** `marca.toml`.
- **Excel de un cliente:** se sube desde la barra lateral. Nunca se copia a este repositorio; se guarda en una carpeta privada fuera de él.

## Privacidad del Excel subido

La app no escribe el archivo en disco ni lo manda a otro servicio. Se procesa en el servidor de Streamlit y queda solo en la sesión de la visita (`st.session_state`), que se borra al cerrarla. No uses `st.cache_data` con datos subidos: esa caché sobrevive a la visita, y dejaría de ser cierto el texto que se muestra bajo el botón de subir.

## Cómo se calculan los indicadores

- **Periodo anterior:** si eliges meses completos, se compara contra los mismos meses previos. Si no, contra la misma cantidad de días justo antes.
- **Utilidad:** ventas menos gastos. Si el rango cubre solo parte de un mes, el gasto de ese mes se reparte por días.
- La utilidad y la gráfica de ingresos vs. gastos ignoran los filtros de categoría y método de pago, porque los gastos no se pueden repartir de esa forma.
- **Resurtido:** existencia entre la venta diaria de los últimos 30 días del archivo. Es **Urgente** con menos de 7 días y **Pronto** con menos de 15. No cambia con los filtros.

## Licencia

Código propietario. Se puede ver, pero no copiar, modificar, redistribuir ni usar comercialmente sin autorización por escrito. Consulta [LICENSE](LICENSE).
