"""Gráficas de Plotly con la apariencia del tablero."""
import pandas as pd
import plotly.graph_objects as go

from tablero.calculos import filtrar_fechas, gastos_del_rango
from tablero.formato import DIAS, MESES, fecha_larga, mes_es, moneda

# ---------------------------------------------------------------------------
# Paleta: la misma de la página. Los colores de datos están validados contra
# daltonismo sobre el fondo SUPERFICIE.
# ---------------------------------------------------------------------------
FONDO = "#0B1628"
SUPERFICIE = "#12213A"
BORDE = "#27405F"
TEXTO = "#EDF2F9"
TEXTO_SUAVE = "#B0BED2"
ACENTO = "#2DE2C5"
COLORES_SERIES = ["#10A68F", "#4C8EF0", "#BC8520", "#A77BE0", "#D9687F"]
COLOR_OTROS = "#6B7F99"


def estilo(fig, alto=340, leyenda=False):
    """Aplica la misma apariencia a todas las gráficas."""
    fig.update_layout(
        height=alto,
        paper_bgcolor=SUPERFICIE,
        plot_bgcolor=SUPERFICIE,
        font=dict(family="Inter, Segoe UI, sans-serif", color=TEXTO_SUAVE, size=13),
        margin=dict(l=12, r=16, t=16, b=12),
        hoverlabel=dict(bgcolor=FONDO, bordercolor=BORDE, font=dict(color=TEXTO, size=13)),
        showlegend=leyenda,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0, font=dict(color=TEXTO)),
        dragmode=False,  # en celular, deslizar debe mover la página y no la gráfica
    )
    fig.update_xaxes(gridcolor=BORDE, zerolinecolor=BORDE, linecolor=BORDE, automargin=True)
    fig.update_yaxes(gridcolor=BORDE, zerolinecolor=BORDE, linecolor=BORDE, automargin=True)
    return fig


def marcas_fecha(dias):
    """Elige marcas del eje en español: por día, semana o mes según el rango."""
    if len(dias) <= 10:
        marcas = list(dias)
    elif len(dias) <= 62:
        marcas = list(dias[::7])
    else:
        marcas = [d for d in dias if d.day == 1] or [dias[0]]
    return marcas, [f"{d.day} {MESES[d.month - 1]}" for d in marcas]


def grafica_ventas_diarias(ventas, inicio, fin):
    """Línea de ventas por día; los días sin venta aparecen en cero."""
    dias = pd.date_range(inicio, fin)
    serie = ventas.groupby("Fecha")["Total"].sum().reindex(dias, fill_value=0)
    fig = go.Figure(go.Scatter(
        x=dias, y=serie.values, mode="lines+markers" if len(dias) == 1 else "lines",  # un solo día no traza línea
        line=dict(color=ACENTO, width=2),
        customdata=[[fecha_larga(d), moneda(v)] for d, v in serie.items()],
        hovertemplate="%{customdata[0]}<br><b>%{customdata[1]}</b><extra></extra>",
    ))
    marcas, textos = marcas_fecha(dias)
    fig.update_xaxes(tickvals=marcas, ticktext=textos, showgrid=False)
    fig.update_yaxes(tickformat="$,.2f", rangemode="tozero")
    return estilo(fig)


def grafica_calor(ventas):
    """Mapa de calor de ventas por día de la semana y hora."""
    tabla = ventas.assign(Dia=ventas["Fecha"].dt.day_of_week).pivot_table(
        index="Dia", columns="HoraNum", values="Total", aggfunc="sum", fill_value=0)
    horas = range(tabla.columns.min(), tabla.columns.max() + 1)
    tabla = tabla.reindex(index=range(7), columns=horas, fill_value=0)
    fig = go.Figure(go.Heatmap(
        z=tabla.values, x=[f"{h}h" for h in horas], y=DIAS,
        colorscale=[[0, "#16273F"], [1, ACENTO]], xgap=2, ygap=2,
        customdata=[[moneda(v) for v in fila] for fila in tabla.values],
        hovertemplate="%{y} a las %{x}<br><b>%{customdata}</b><extra></extra>",
        # Horizontal: en celular una barra vertical con centavos le quita ancho al mapa
        colorbar=dict(orientation="h", y=-0.14, yanchor="top", thickness=10, nticks=4,
                      tickprefix="$", tickformat=",.2f", outlinewidth=0),
    ))
    fig.update_xaxes(showgrid=False, type="category")
    fig.update_yaxes(showgrid=False, autorange="reversed")
    return estilo(fig, alto=410)


def grafica_barras_h(etiquetas, valores, hover, texto, alto=None):
    """Barras horizontales de una sola serie, con la mayor arriba."""
    fig = go.Figure(go.Bar(
        x=valores, y=etiquetas, orientation="h", marker=dict(color=ACENTO, cornerradius=4),
        text=texto, textposition="outside", textfont=dict(color=TEXTO), cliponaxis=False,
        customdata=hover, hovertemplate="%{y}<br><b>%{customdata}</b><extra></extra>",
    ))
    fig.update_xaxes(visible=False, range=[0, max(valores) * 1.5])
    fig.update_yaxes(autorange="reversed", showgrid=False, tickfont=dict(color=TEXTO))
    return estilo(fig, alto=alto or 56 * len(etiquetas) + 40)


def grafica_productos(productos):
    """Barras de unidades vendidas por producto (o platillo)."""
    return grafica_barras_h(
        productos["Producto"], productos["Cantidad"],
        [f"{c:,.0f} piezas · {moneda(t)}" for c, t in zip(productos["Cantidad"], productos["Total"])],
        [f"{c:,.0f}" for c in productos["Cantidad"]],
        alto=38 * len(productos) + 40,
    )


def grafica_montos(serie):
    """Barras de ventas por grupo, de mayor a menor (pago y cajero o mesero)."""
    serie = serie.sort_values(ascending=False)
    textos = [moneda(v) for v in serie]
    return grafica_barras_h(serie.index, serie.values, textos, textos)


def color_categoria(categorias, orden):
    """Asigna colores fijos según el orden del giro; las categorías desconocidas toman los libres.

    El color sigue a la categoría, no a su posición, para que no cambie al filtrar.
    """
    fijos = dict(zip(orden, COLORES_SERIES))
    libres = [c for c in COLORES_SERIES if c not in [fijos[n] for n in categorias if n in fijos]]
    colores = []
    for categoria in categorias:
        if categoria in fijos:
            colores.append(fijos[categoria])
        else:
            colores.append(libres.pop(0) if libres else COLOR_OTROS)
    return colores


def grafica_categorias(ventas, orden):
    """Dona de ventas por categoría, con leyenda y porcentaje directo."""
    serie = ventas.groupby("Categoría")["Total"].sum().sort_values(ascending=False)
    fig = go.Figure(go.Pie(
        labels=serie.index, values=serie.values, hole=0.62, sort=False, direction="clockwise",
        marker=dict(colors=color_categoria(list(serie.index), orden), line=dict(color=SUPERFICIE, width=2)),
        textinfo="percent", textposition="outside", textfont=dict(color=TEXTO), automargin=True,
        customdata=[moneda(v) for v in serie.values],
        hovertemplate="%{label}<br><b>%{customdata}</b> · %{percent}<extra></extra>",
    ))
    return estilo(fig, alto=380, leyenda=True)


def grafica_mensual(ventas, gastos, inicio, fin):
    """Ingresos, gastos y utilidad por mes en barras agrupadas."""
    gastos_rango = gastos_del_rango(gastos, inicio, fin)
    rango = filtrar_fechas(ventas, inicio, fin)
    ingresos = rango.groupby(rango["Fecha"].dt.to_period("M"))["Total"].sum().reindex(gastos_rango.index, fill_value=0)
    utilidad = ingresos - gastos_rango
    meses = [mes_es(m) for m in gastos_rango.index]

    series = (("Ingresos", ingresos, COLORES_SERIES[0]), ("Gastos", gastos_rango, COLORES_SERIES[1]),
              ("Utilidad", utilidad, COLORES_SERIES[2]))
    fig = go.Figure()
    for nombre, valores, color in series:
        fig.add_trace(go.Bar(
            name=nombre, x=meses, y=valores.values, marker=dict(color=color, cornerradius=4),
            customdata=[moneda(v) for v in valores.values],
            hovertemplate=f"{nombre}: <b>%{{customdata}}</b><extra></extra>",
        ))
    # Solo la utilidad lleva etiqueta: es el dato que importa de esta gráfica
    fig.data[2].update(text=[moneda(v) for v in utilidad.values],
                       textposition="outside", textangle=-90, textfont=dict(color=TEXTO), cliponaxis=False,
                       constraintext="none")
    fig.update_layout(barmode="group", bargap=0.3, bargroupgap=0.06, hovermode="x unified")
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(tickformat="$,.2f")
    return estilo(fig, alto=400, leyenda=True)
