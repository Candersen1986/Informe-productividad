# Informe Dinámico de Remuneraciones y Productividad

Conecta con la API de **BUK** para extraer liquidaciones de sueldo y las cruza con la facturación mensual por consultor, calculando KPIs de productividad.

---

## KPI Principal: Ratio de Cobertura

```
Ratio = Facturación Consultor / Costo Empresa (Total Haberes + Cotizaciones Patronales)
```

| Ratio | Interpretación |
|-------|---------------|
| < 1.0 | El consultor cuesta más de lo que factura (pérdida) |
| = 1.0 | Punto de equilibrio (se autofinancia) |
| 1.0 – 2.0 | Genera margen positivo |
| ≥ 2.0 | Genera el doble (o más) de su costo → alta productividad |

---

## Instalación

```bash
pip install -r requirements.txt
cp .env.example .env
# Editar .env con tu token BUK y el slug de la empresa
```

---

## Configuración BUK

Edita `.env`:

```env
BUK_API_TOKEN=tu_token_api
BUK_COMPANY_SLUG=miempresa   # parte de la URL: app.buk.cl/c/miempresa
```

Para obtener el token: en BUK → Configuración → API → Generar Token.

---

## Uso

### Modo demo (sin BUK, datos ficticios)
```bash
python informe.py --demo
```

### Uso real con datos de BUK
```bash
# Un período
python informe.py --periodos 2025-01 --facturacion facturacion_enero.csv

# Múltiples períodos
python informe.py --periodos 2025-01 2025-02 2025-03 --facturacion facturacion.xlsx

# Especificar nombre del Excel de salida
python informe.py --periodos 2025-01 --facturacion datos.csv --salida reporte_enero.xlsx
```

### Parámetros

| Parámetro | Descripción |
|-----------|-------------|
| `--periodos` | Períodos YYYY-MM a analizar (puede ser uno o varios) |
| `--facturacion` | Ruta al CSV o XLSX con la facturación |
| `--salida` | Nombre del archivo Excel de salida |
| `--demo` | Ejecutar con datos ficticios (no requiere credenciales) |

---

## Formato del archivo de facturación

CSV o Excel con estas columnas:

```
rut,nombre,periodo,facturacion
12345678-9,Ana Torres,2025-01,8500000
12345678-9,Ana Torres,2025-02,9200000
```

Ver ejemplo completo en `facturacion_ejemplo.csv`.

---

## Salida

El script genera:
1. **Consola**: tabla resumen con todos los KPIs
2. **Excel** (`informe_productividad.xlsx`) con dos hojas:
   - **Detalle Mensual**: una fila por consultor × período
   - **Resumen Consultores**: acumulado de todos los períodos

---

## Estructura del proyecto

```
├── informe.py              # Script principal y motor de análisis
├── buk_client.py           # Cliente REST para la API de BUK
├── datos_facturacion.py    # Carga del archivo de facturación
├── facturacion_ejemplo.csv # Plantilla/ejemplo de facturación
├── .env.example            # Plantilla de variables de entorno
├── requirements.txt        # Dependencias Python
└── README.md
```
