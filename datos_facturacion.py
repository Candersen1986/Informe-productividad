"""
Módulo para cargar la facturación mensual por consultor.

Formato esperado del CSV:
  rut,nombre,periodo,facturacion
  12345678-9,Juan Pérez,2025-01,5500000
  12345678-9,Juan Pérez,2025-02,6000000
  ...

También puede cargarse desde un Excel con la misma estructura.
"""
import pandas as pd
from pathlib import Path


def cargar_facturacion(ruta: str) -> pd.DataFrame:
    """
    Carga el archivo de facturación (CSV o XLSX).
    Retorna DataFrame con columnas: rut, nombre, periodo, facturacion
    """
    ruta = Path(ruta)
    if not ruta.exists():
        raise FileNotFoundError(f"Archivo no encontrado: {ruta}")

    if ruta.suffix.lower() in (".xlsx", ".xls"):
        df = pd.read_excel(ruta, dtype={"rut": str})
    else:
        df = pd.read_csv(ruta, dtype={"rut": str})

    # Normalizar columnas
    df.columns = [c.strip().lower() for c in df.columns]
    required = {"rut", "periodo", "facturacion"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Columnas faltantes en el archivo de facturación: {missing}")

    df["rut"] = df["rut"].str.strip()
    df["facturacion"] = pd.to_numeric(df["facturacion"], errors="coerce").fillna(0)
    df["periodo"] = df["periodo"].astype(str).str.strip()

    return df


def generar_facturacion_demo() -> pd.DataFrame:
    """
    Genera un DataFrame de facturación de ejemplo para pruebas.
    Los RUTs y nombres son ficticios.
    """
    data = [
        {"rut": "12345678-9", "nombre": "Ana Torres",    "periodo": "2025-01", "facturacion": 8_500_000},
        {"rut": "12345678-9", "nombre": "Ana Torres",    "periodo": "2025-02", "facturacion": 9_200_000},
        {"rut": "98765432-1", "nombre": "Carlos Muñoz",  "periodo": "2025-01", "facturacion": 4_800_000},
        {"rut": "98765432-1", "nombre": "Carlos Muñoz",  "periodo": "2025-02", "facturacion": 5_100_000},
        {"rut": "11111111-1", "nombre": "María López",   "periodo": "2025-01", "facturacion": 12_000_000},
        {"rut": "11111111-1", "nombre": "María López",   "periodo": "2025-02", "facturacion": 11_500_000},
        {"rut": "22222222-2", "nombre": "Pedro Soto",    "periodo": "2025-01", "facturacion": 3_200_000},
        {"rut": "22222222-2", "nombre": "Pedro Soto",    "periodo": "2025-02", "facturacion": 3_800_000},
    ]
    return pd.DataFrame(data)
