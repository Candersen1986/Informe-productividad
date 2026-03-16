"""
Motor principal del Informe Dinámico de Remuneraciones y Productividad.

Flujo:
  1. Extrae liquidaciones desde la API de BUK
  2. Carga la facturación mensual (CSV/Excel o demo)
  3. Cruza ambas fuentes por RUT y período
  4. Calcula KPIs de productividad por consultor
  5. Exporta resumen en Excel y lo imprime en consola
"""

import sys
import pandas as pd
from tabulate import tabulate

import buk_client
from datos_facturacion import cargar_facturacion, generar_facturacion_demo


# ──────────────────────────────────────────────
# 1. Extracción y normalización de datos BUK
# ──────────────────────────────────────────────

def extraer_remuneraciones_buk(periodos: list[str]) -> pd.DataFrame:
    """
    Extrae las liquidaciones de BUK para los períodos indicados.
    Retorna DataFrame con: rut, nombre, periodo, sueldo_base, total_haberes,
                           costo_empresa, descuentos_legales, liquido
    """
    registros = []
    for periodo in periodos:
        print(f"  → Obteniendo liquidaciones BUK para {periodo}...")
        try:
            payrolls = buk_client.get_payroll(periodo)
        except Exception as e:
            print(f"    ⚠ Error al obtener BUK [{periodo}]: {e}")
            continue

        for p in payrolls:
            emp = p.get("employee", {})
            registros.append({
                "rut":              _normalizar_rut(emp.get("identifier", emp.get("rut", ""))),
                "nombre":           f"{emp.get('first_name','')} {emp.get('last_name','')}".strip(),
                "periodo":          periodo,
                "sueldo_base":      float(p.get("base_salary", 0) or 0),
                "total_haberes":    float(p.get("total_haber", p.get("gross_salary", 0)) or 0),
                "descuentos_legales": float(p.get("total_descuento_legal", p.get("legal_discounts", 0)) or 0),
                "liquido":          float(p.get("net_salary", p.get("liquid_salary", 0)) or 0),
                # Costo empresa = haberes + cotizaciones patronales
                "costo_empresa":    float(p.get("employer_cost", p.get("total_cost", 0)) or 0),
            })

    if not registros:
        return pd.DataFrame()

    df = pd.DataFrame(registros)
    # Si costo_empresa no vino en el payload, estimarlo (aprox +20 % del total_haberes)
    mask = df["costo_empresa"] == 0
    df.loc[mask, "costo_empresa"] = df.loc[mask, "total_haberes"] * 1.20
    return df


def _normalizar_rut(rut: str) -> str:
    """Normaliza formato de RUT para hacer join: sin puntos, con guión."""
    rut = str(rut).strip().replace(".", "").upper()
    if "-" not in rut and len(rut) > 1:
        rut = rut[:-1] + "-" + rut[-1]
    return rut


# ──────────────────────────────────────────────
# 2. Datos demo de BUK (para pruebas sin credenciales)
# ──────────────────────────────────────────────

def generar_remuneraciones_demo(periodos: list[str]) -> pd.DataFrame:
    """Genera liquidaciones ficticias para demostración."""
    import random
    random.seed(42)
    consultores = [
        ("12345678-9", "Ana Torres"),
        ("98765432-1", "Carlos Muñoz"),
        ("11111111-1", "María López"),
        ("22222222-2", "Pedro Soto"),
    ]
    registros = []
    for periodo in periodos:
        for rut, nombre in consultores:
            base = random.randint(1_500_000, 3_500_000)
            haberes = base + random.randint(100_000, 500_000)
            registros.append({
                "rut":               rut,
                "nombre":            nombre,
                "periodo":           periodo,
                "sueldo_base":       base,
                "total_haberes":     haberes,
                "descuentos_legales": int(haberes * 0.20),
                "liquido":           int(haberes * 0.80),
                "costo_empresa":     int(haberes * 1.20),
            })
    return pd.DataFrame(registros)


# ──────────────────────────────────────────────
# 3. Cruce y KPIs
# ──────────────────────────────────────────────

def calcular_kpis(df_rem: pd.DataFrame, df_fact: pd.DataFrame) -> pd.DataFrame:
    """
    Cruza remuneraciones con facturación y calcula KPIs.

    KPIs calculados:
      - ratio_cobertura : facturacion / costo_empresa
          → cuántas veces el consultor "se paga a sí mismo"
          → >= 1 = se autofinancia; > 2 = genera ganancia
      - margen_bruto    : facturacion - costo_empresa
      - margen_pct      : margen_bruto / facturacion * 100
    """
    df = pd.merge(
        df_rem,
        df_fact[["rut", "periodo", "facturacion"]],
        on=["rut", "periodo"],
        how="left",
    )
    df["facturacion"] = df["facturacion"].fillna(0)

    # Ratio de cobertura (el KPI principal)
    df["ratio_cobertura"] = df.apply(
        lambda r: round(r["facturacion"] / r["costo_empresa"], 2)
        if r["costo_empresa"] > 0 else None,
        axis=1,
    )
    df["margen_bruto"] = df["facturacion"] - df["costo_empresa"]
    df["margen_pct"] = df.apply(
        lambda r: round(r["margen_bruto"] / r["facturacion"] * 100, 1)
        if r["facturacion"] > 0 else None,
        axis=1,
    )

    return df


def resumen_acumulado(df: pd.DataFrame) -> pd.DataFrame:
    """Agrega por consultor (todos los períodos combinados)."""
    grp = (
        df.groupby(["rut", "nombre"])
        .agg(
            periodos=("periodo", "nunique"),
            facturacion_total=("facturacion", "sum"),
            costo_empresa_total=("costo_empresa", "sum"),
            total_haberes_total=("total_haberes", "sum"),
            liquido_total=("liquido", "sum"),
        )
        .reset_index()
    )
    grp["ratio_cobertura_acum"] = (
        grp["facturacion_total"] / grp["costo_empresa_total"]
    ).round(2)
    grp["margen_bruto_total"] = grp["facturacion_total"] - grp["costo_empresa_total"]
    grp["margen_pct_total"] = (
        grp["margen_bruto_total"] / grp["facturacion_total"] * 100
    ).round(1)
    return grp.sort_values("ratio_cobertura_acum", ascending=False)


# ──────────────────────────────────────────────
# 4. Exportación
# ──────────────────────────────────────────────

def exportar_excel(df_detalle: pd.DataFrame, df_resumen: pd.DataFrame, archivo: str):
    """Exporta el informe completo a un archivo Excel con dos hojas."""

    def _fmt_clp(x):
        try:
            return f"${x:,.0f}"
        except Exception:
            return x

    with pd.ExcelWriter(archivo, engine="openpyxl") as writer:
        # Hoja 1: Detalle mensual
        det = df_detalle.copy()
        for col in ["sueldo_base", "total_haberes", "descuentos_legales", "liquido",
                    "costo_empresa", "facturacion", "margen_bruto"]:
            if col in det.columns:
                det[col] = det[col].apply(_fmt_clp)
        det.to_excel(writer, sheet_name="Detalle Mensual", index=False)

        # Hoja 2: Resumen acumulado
        res = df_resumen.copy()
        for col in ["facturacion_total", "costo_empresa_total", "total_haberes_total",
                    "liquido_total", "margen_bruto_total"]:
            if col in res.columns:
                res[col] = res[col].apply(_fmt_clp)
        res.to_excel(writer, sheet_name="Resumen Consultores", index=False)

    print(f"\n✔ Informe exportado → {archivo}")


# ──────────────────────────────────────────────
# 5. Impresión en consola
# ──────────────────────────────────────────────

def imprimir_resumen(df_resumen: pd.DataFrame):
    cols = [
        "nombre", "periodos", "facturacion_total", "costo_empresa_total",
        "ratio_cobertura_acum", "margen_bruto_total", "margen_pct_total",
    ]
    df = df_resumen[cols].copy()
    df.rename(columns={
        "nombre":               "Consultor",
        "periodos":             "Meses",
        "facturacion_total":    "Facturación $",
        "costo_empresa_total":  "Costo Empresa $",
        "ratio_cobertura_acum": "Ratio Cobertura",
        "margen_bruto_total":   "Margen Bruto $",
        "margen_pct_total":     "Margen %",
    }, inplace=True)

    for col in ["Facturación $", "Costo Empresa $", "Margen Bruto $"]:
        df[col] = df[col].apply(lambda x: f"${x:>15,.0f}" if pd.notna(x) else "N/A")

    print("\n" + "=" * 80)
    print("  INFORME DE PRODUCTIVIDAD POR CONSULTOR")
    print("=" * 80)
    print(tabulate(df, headers="keys", tablefmt="rounded_outline", showindex=False))
    print("\n  Ratio Cobertura = Facturación / Costo Empresa")
    print("  Ratio >= 1 → el consultor se autofinancia")
    print("  Ratio >= 2 → el consultor genera el doble de su costo")
    print("=" * 80)


# ──────────────────────────────────────────────
# 6. Función principal
# ──────────────────────────────────────────────

def generar_informe(
    periodos: list[str],
    archivo_facturacion: str | None = None,
    archivo_salida: str = "informe_productividad.xlsx",
    modo_demo: bool = False,
):
    """
    Genera el informe completo de remuneraciones y productividad.

    Args:
        periodos:             Lista de períodos 'YYYY-MM' a analizar.
        archivo_facturacion:  Ruta al CSV/Excel con la facturación. Si es None
                              y modo_demo=False, se pedirá por consola.
        archivo_salida:       Nombre del archivo Excel de salida.
        modo_demo:            Si True, usa datos ficticios sin necesitar BUK API.
    """
    print(f"\n{'='*60}")
    print("  INFORME DINÁMICO DE REMUNERACIONES Y PRODUCTIVIDAD")
    print(f"  Períodos: {', '.join(periodos)}")
    print(f"{'='*60}\n")

    # ── Remuneraciones ──
    if modo_demo:
        print("[DEMO] Usando remuneraciones ficticias (sin conexión a BUK)...")
        df_rem = generar_remuneraciones_demo(periodos)
    else:
        print("Extrayendo remuneraciones desde BUK API...")
        df_rem = extraer_remuneraciones_buk(periodos)
        if df_rem.empty:
            print("⚠ No se obtuvieron datos de BUK. Verifica token y empresa.")
            sys.exit(1)

    print(f"  → {len(df_rem)} registros de liquidaciones cargados.")

    # ── Facturación ──
    if modo_demo and archivo_facturacion is None:
        print("[DEMO] Usando facturación ficticia...")
        df_fact = generar_facturacion_demo()
    elif archivo_facturacion:
        print(f"Cargando facturación desde: {archivo_facturacion}")
        df_fact = cargar_facturacion(archivo_facturacion)
    else:
        ruta = input("\nRuta al archivo de facturación (CSV o XLSX): ").strip()
        df_fact = cargar_facturacion(ruta)

    print(f"  → {len(df_fact)} registros de facturación cargados.\n")

    # ── Cruce y KPIs ──
    df_detalle = calcular_kpis(df_rem, df_fact)
    df_resumen = resumen_acumulado(df_detalle)

    # ── Presentación ──
    imprimir_resumen(df_resumen)
    exportar_excel(df_detalle, df_resumen, archivo_salida)

    return df_detalle, df_resumen


# ──────────────────────────────────────────────
# Entry point
# ──────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Informe dinámico de remuneraciones y productividad (BUK API)"
    )
    parser.add_argument(
        "--periodos", "-p",
        nargs="+",
        default=["2025-01", "2025-02"],
        metavar="YYYY-MM",
        help="Períodos a analizar (ej: 2025-01 2025-02 2025-03)",
    )
    parser.add_argument(
        "--facturacion", "-f",
        default=None,
        metavar="ARCHIVO",
        help="Ruta al CSV/XLSX con la facturación mensual por consultor",
    )
    parser.add_argument(
        "--salida", "-o",
        default="informe_productividad.xlsx",
        metavar="ARCHIVO",
        help="Nombre del archivo Excel de salida (default: informe_productividad.xlsx)",
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Ejecutar con datos ficticios (sin credenciales BUK)",
    )
    args = parser.parse_args()

    generar_informe(
        periodos=args.periodos,
        archivo_facturacion=args.facturacion,
        archivo_salida=args.salida,
        modo_demo=args.demo,
    )
