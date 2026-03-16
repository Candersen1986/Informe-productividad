"""
Cliente para la API REST de BUK.
Documentación: https://app.buk.cl/api/docs
"""
import os
import requests
from dotenv import load_dotenv

load_dotenv()

BUK_API_TOKEN = os.getenv("BUK_API_TOKEN", "")
BUK_COMPANY_SLUG = os.getenv("BUK_COMPANY_SLUG", "")
BASE_URL = f"https://app.buk.cl/api/v1/c/{BUK_COMPANY_SLUG}"


def _headers():
    return {
        "Authorization": f"Token token={BUK_API_TOKEN}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def _get(endpoint: str, params: dict = None) -> dict | list:
    """GET paginado: recorre todas las páginas y concatena resultados."""
    url = f"{BASE_URL}/{endpoint}"
    results = []
    page = 1
    while True:
        p = {"per_page": 100, "page": page, **(params or {})}
        resp = requests.get(url, headers=_headers(), params=p, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        # La API de BUK puede devolver lista directa o {"data": [...]}
        if isinstance(data, list):
            batch = data
        elif isinstance(data, dict):
            batch = data.get("data", data.get("employees", data.get("payrolls", [])))
        else:
            batch = []

        results.extend(batch)

        # Si devolvió menos de per_page, ya no hay más páginas
        if len(batch) < 100:
            break
        page += 1

    return results


# ──────────────────────────────────────────────
# Endpoints principales
# ──────────────────────────────────────────────

def get_employees() -> list[dict]:
    """Retorna todos los empleados activos de la empresa."""
    return _get("employees")


def get_payroll(periodo: str) -> list[dict]:
    """
    Retorna el detalle de liquidaciones para un periodo dado.
    periodo: 'YYYY-MM'  ej: '2025-01'
    """
    year, month = periodo.split("-")
    return _get("payrolls", params={"year": year, "month": month})


def get_payroll_items(periodo: str) -> list[dict]:
    """
    Retorna los ítems (haberes/descuentos) del período.
    Útil para desglosar sueldo base, bonos, colación, movilización, etc.
    """
    year, month = periodo.split("-")
    return _get("payroll_items", params={"year": year, "month": month})
