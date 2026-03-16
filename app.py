"""
Dashboard web - Informe Dinámico de Remuneraciones y Productividad
Powered by Streamlit + BUK API
"""

import io
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

from informe import (
    extraer_remuneraciones_buk,
    generar_remuneraciones_demo,
    calcular_kpis,
    resumen_acumulado,
)
from datos_facturacion import cargar_facturacion, generar_facturacion_demo

# ──────────────────────────────────────────────
# Configuración de página
# ──────────────────────────────────────────────
st.set_page_config(
    page_title="Productividad Consultores | Singulares",
    page_icon="📊",
    layout="wide",
)

# ──────────────────────────────────────────────
# Estilos
# ──────────────────────────────────────────────
st.markdown("""
<style>
    .metric-card {
        background: #f8f9fa;
        border-radius: 10px;
        padding: 16px 20px;
        border-left: 4px solid #4e79a7;
    }
    .ratio-high   { color: #2ca02c; font-weight: bold; }
    .ratio-mid    { color: #ff7f0e; font-weight: bold; }
    .ratio-low    { color: #d62728; font-weight: bold; }
    .stDataFrame  { font-size: 13px; }
</style>
""", unsafe_allow_html=True)


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────

def _clp(valor):
    try:
        return f"${valor:,.0f}"
    except Exception:
        return "N/A"


def _color_ratio(val):
    try:
        v = float(val)
        if v >= 2.0:
            return "color: #2ca02c; font-weight:bold"
        if v >= 1.0:
            return "color: #ff7f0e; font-weight:bold"
        return "color: #d62728; font-weight:bold"
    except Exception:
        return ""


def exportar_excel(df_detalle: pd.DataFrame, df_resumen: pd.DataFrame) -> bytes:
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df_detalle.to_excel(writer, sheet_name="Detalle Mensual", index=False)
        df_resumen.to_excel(writer, sheet_name="Resumen Consultores", index=False)
    return buf.getvalue()


def generar_periodos_opciones():
    """Genera lista de períodos disponibles: últimos 24 meses."""
    from datetime import date
    from dateutil.relativedelta import relativedelta
    hoy = date.today()
    return [(hoy - relativedelta(months=i)).strftime("%Y-%m") for i in range(24)]


# ──────────────────────────────────────────────
# Sidebar – Configuración
# ──────────────────────────────────────────────
with st.sidebar:
    st.image("https://singulares.buk.cl/favicon.ico", width=40)
    st.title("⚙️ Configuración")

    modo_demo = st.toggle("Modo Demo (datos ficticios)", value=False)

    st.markdown("---")
    st.subheader("📅 Períodos a analizar")

    try:
        opciones = generar_periodos_opciones()
    except ImportError:
        # fallback sin dateutil
        from datetime import date
        hoy = date.today()
        opciones = [
            f"{hoy.year}-{str(m).zfill(2)}"
            for m in range(hoy.month, 0, -1)
        ] + [
            f"{hoy.year - 1}-{str(m).zfill(2)}"
            for m in range(12, 0, -1)
        ]

    periodos_sel = st.multiselect(
        "Selecciona uno o más períodos",
        options=opciones,
        default=opciones[:3],
        help="Formato YYYY-MM",
    )

    st.markdown("---")
    st.subheader("📁 Facturación")
    archivo_fact = st.file_uploader(
        "Sube tu archivo de facturación (CSV o Excel)",
        type=["csv", "xlsx", "xls"],
        help="Columnas requeridas: rut, periodo, facturacion",
    )

    if not modo_demo:
        st.info("💡 El archivo debe tener: rut, periodo (YYYY-MM), facturacion")

    st.markdown("---")
    st.download_button(
        label="📥 Descargar plantilla CSV",
        data=open("/app/facturacion_ejemplo.csv" if False else "facturacion_ejemplo.csv", "rb").read()
             if __import__("os").path.exists("facturacion_ejemplo.csv")
             else b"rut,nombre,periodo,facturacion\n12345678-9,Consultor1,2025-01,5000000\n",
        file_name="plantilla_facturacion.csv",
        mime="text/csv",
    )


# ──────────────────────────────────────────────
# Header principal
# ──────────────────────────────────────────────
st.title("📊 Informe de Productividad por Consultor")
st.caption("Facturación vs Costo Empresa (BUK API) · Singulares")

if not periodos_sel:
    st.warning("⚠️ Selecciona al menos un período en el panel izquierdo.")
    st.stop()

# ──────────────────────────────────────────────
# Carga de datos
# ──────────────────────────────────────────────
with st.spinner("Cargando datos..."):

    # Remuneraciones
    if modo_demo:
        df_rem = generar_remuneraciones_demo(periodos_sel)
    else:
        try:
            df_rem = extraer_remuneraciones_buk(periodos_sel)
            if df_rem.empty:
                st.error("❌ No se obtuvieron datos de BUK. Verifica el token en el archivo .env")
                st.stop()
        except Exception as e:
            st.error(f"❌ Error al conectar con BUK: {e}")
            st.stop()

    # Facturación
    if modo_demo and archivo_fact is None:
        df_fact = generar_facturacion_demo()
    elif archivo_fact is not None:
        try:
            if archivo_fact.name.endswith((".xlsx", ".xls")):
                df_fact = pd.read_excel(archivo_fact, dtype={"rut": str})
            else:
                df_fact = pd.read_csv(archivo_fact, dtype={"rut": str})
            df_fact.columns = [c.strip().lower() for c in df_fact.columns]
            df_fact["facturacion"] = pd.to_numeric(df_fact["facturacion"], errors="coerce").fillna(0)
        except Exception as e:
            st.error(f"❌ Error al leer archivo de facturación: {e}")
            st.stop()
    else:
        st.info("📂 Sube tu archivo de facturación en el panel izquierdo, o activa el Modo Demo.")
        st.stop()

    # Cruce y KPIs
    df_detalle = calcular_kpis(df_rem, df_fact)
    df_resumen = resumen_acumulado(df_detalle)

# ──────────────────────────────────────────────
# Métricas resumen (tarjetas superiores)
# ──────────────────────────────────────────────
total_fact  = df_resumen["facturacion_total"].sum()
total_costo = df_resumen["costo_empresa_total"].sum()
total_margen = total_fact - total_costo
ratio_empresa = total_fact / total_costo if total_costo > 0 else 0

col1, col2, col3, col4 = st.columns(4)
col1.metric("💰 Facturación Total", _clp(total_fact))
col2.metric("👥 Costo Empresa Total", _clp(total_costo))
col3.metric("📈 Margen Bruto Total", _clp(total_margen))
col4.metric("⚡ Ratio Global", f"{ratio_empresa:.2f}x",
            help="Facturación total / Costo empresa total")

st.markdown("---")

# ──────────────────────────────────────────────
# Tabla resumen por consultor
# ──────────────────────────────────────────────
st.subheader("🧑‍💼 Resumen por Consultor")

tabla = df_resumen[[
    "nombre", "periodos", "facturacion_total", "costo_empresa_total",
    "ratio_cobertura_acum", "margen_bruto_total", "margen_pct_total"
]].copy()

tabla.columns = [
    "Consultor", "Meses", "Facturación $", "Costo Empresa $",
    "Ratio Cobertura", "Margen Bruto $", "Margen %"
]

for col in ["Facturación $", "Costo Empresa $", "Margen Bruto $"]:
    tabla[col] = tabla[col].apply(_clp)

st.dataframe(
    tabla.style.applymap(_color_ratio, subset=["Ratio Cobertura"]),
    use_container_width=True,
    hide_index=True,
)

st.caption("🟢 Ratio ≥ 2.0 · 🟠 Ratio 1.0–2.0 · 🔴 Ratio < 1.0")

# ──────────────────────────────────────────────
# Gráficos
# ──────────────────────────────────────────────
st.markdown("---")
st.subheader("📉 Visualizaciones")

tab1, tab2, tab3 = st.tabs(["Ratio de Cobertura", "Facturación vs Costo", "Evolución Mensual"])

with tab1:
    fig = px.bar(
        df_resumen.sort_values("ratio_cobertura_acum"),
        x="ratio_cobertura_acum",
        y="nombre",
        orientation="h",
        title="Ratio de Cobertura por Consultor (acumulado)",
        labels={"ratio_cobertura_acum": "Ratio", "nombre": ""},
        color="ratio_cobertura_acum",
        color_continuous_scale=["#d62728", "#ff7f0e", "#2ca02c"],
        text="ratio_cobertura_acum",
    )
    fig.add_vline(x=1.0, line_dash="dash", line_color="gray", annotation_text="Equilibrio")
    fig.add_vline(x=2.0, line_dash="dot",  line_color="green", annotation_text="2x")
    fig.update_traces(texttemplate="%{text:.2f}x", textposition="outside")
    fig.update_layout(showlegend=False, coloraxis_showscale=False)
    st.plotly_chart(fig, use_container_width=True)

with tab2:
    fig2 = go.Figure()
    fig2.add_trace(go.Bar(
        name="Facturación",
        x=df_resumen["nombre"],
        y=df_resumen["facturacion_total"],
        marker_color="#4e79a7",
    ))
    fig2.add_trace(go.Bar(
        name="Costo Empresa",
        x=df_resumen["nombre"],
        y=df_resumen["costo_empresa_total"],
        marker_color="#f28e2b",
    ))
    fig2.update_layout(
        barmode="group",
        title="Facturación vs Costo Empresa (acumulado)",
        yaxis_tickformat="$,.0f",
    )
    st.plotly_chart(fig2, use_container_width=True)

with tab3:
    if len(periodos_sel) > 1:
        df_ev = df_detalle.groupby(["periodo", "nombre"]).agg(
            facturacion=("facturacion", "sum"),
            costo_empresa=("costo_empresa", "sum"),
        ).reset_index()
        df_ev["ratio"] = (df_ev["facturacion"] / df_ev["costo_empresa"]).round(2)

        fig3 = px.line(
            df_ev,
            x="periodo",
            y="ratio",
            color="nombre",
            markers=True,
            title="Evolución del Ratio de Cobertura por Consultor",
            labels={"ratio": "Ratio", "periodo": "Período", "nombre": "Consultor"},
        )
        fig3.add_hline(y=1.0, line_dash="dash", line_color="gray")
        st.plotly_chart(fig3, use_container_width=True)
    else:
        st.info("Selecciona más de un período para ver la evolución mensual.")

# ──────────────────────────────────────────────
# Detalle mensual expandible
# ──────────────────────────────────────────────
with st.expander("📋 Ver detalle mensual completo"):
    det = df_detalle.copy()
    for col in ["sueldo_base", "total_haberes", "costo_empresa", "facturacion", "margen_bruto"]:
        if col in det.columns:
            det[col] = det[col].apply(_clp)
    st.dataframe(det, use_container_width=True, hide_index=True)

# ──────────────────────────────────────────────
# Descarga Excel
# ──────────────────────────────────────────────
st.markdown("---")
excel_bytes = exportar_excel(df_detalle, df_resumen)
st.download_button(
    label="⬇️ Descargar informe completo en Excel",
    data=excel_bytes,
    file_name=f"informe_productividad_{'_'.join(periodos_sel)}.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
)

if modo_demo:
    st.warning("⚠️ Estás viendo datos ficticios. Desactiva el Modo Demo para conectar con BUK.")
