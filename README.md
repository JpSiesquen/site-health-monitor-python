# Site Health Monitor Python

[![Tests](https://github.com/JpSiesquen/site-health-monitor-python/actions/workflows/tests.yml/badge.svg)](https://github.com/JpSiesquen/site-health-monitor-python/actions/workflows/tests.yml)
![Python 3.12+](https://img.shields.io/badge/Python-3.12%2B-3776AB?logo=python&logoColor=white)

Monitor HTTP por consola para verificar disponibilidad, destino final y contenido
de páginas web. Genera reportes CSV y HTML por ejecución, sin dependencias externas.

Una respuesta HTTP 200 puede ocultar una redirección incorrecta o una página que
perdió contenido. El monitor comprueba esas condiciones contra expectativas
definidas por URL y registra cada fallo sin interrumpir las comprobaciones restantes.

## Comprobaciones

- **Respuesta HTTP:** exige estado 200 y clasifica errores del servidor y de conexión.
- **Destino final:** detecta redirecciones a un hostname distinto del configurado.
- **Contenido:** verifica un texto esperado en el HTML, excluyendo scripts y estilos.
- **Tiempo y tamaño:** registra la duración de la petición, aplica un timeout por
  operación de red y limita la lectura del cuerpo a 1 MB.

La configuración incluida cubre cinco páginas públicas de [Aptia](https://aptia.cl/)
y [Weblift Agency](https://webliftagency.me/).

## Ejecución

Requiere **Python 3.12 o posterior**.

```bash
git clone https://github.com/JpSiesquen/site-health-monitor-python.git
cd site-health-monitor-python
python monitor.py
```

Para seleccionar configuración, tiempo de espera y destino de los reportes:

```bash
python monitor.py --config sites.json --timeout 10 --output reports
```

En Windows también está disponible `py -3 monitor.py` o el lanzador `./run.cmd`.
Este último utiliza el lanzador `py` o el runtime de Codex si está disponible.

## Configuración por página

```json
[
  {
    "name": "Aptia — inicio",
    "url": "https://aptia.cl/",
    "expected_host": "aptia.cl",
    "expected_text": "Don Tata"
  }
]
```

`name` y `url` son obligatorios. `expected_host` toma por defecto el hostname de
la URL original; `expected_text` es opcional. La búsqueda de texto normaliza
espacios y mayúsculas. La configuración se valida antes de iniciar las peticiones.

## Reportes e integración

Cada ejecución escribe un **CSV con los resultados** y un **HTML para revisión**
en `reports/`. Los nombres incluyen fecha UTC y microsegundos para conservar el
historial. Se registran página, URL original, fecha de consulta, resultado, estado
HTTP, tiempo, URL final y diagnóstico.

[CSV de una ejecución real](docs/examples/report.csv) ·
[Reporte HTML de esa ejecución](docs/examples/report.html)

El ejemplo corresponde al **23 de octubre de 2026**. Los resultados guardados
describen esa ejecución, no el estado actual de los sitios.

| Código de salida | Resultado |
| --- | --- |
| `0` | Todas las comprobaciones correctas. |
| `1` | Una o más páginas incumplen las condiciones esperadas. |
| `2` | Configuración inválida o error al guardar reportes. |

Los códigos de salida permiten incorporar la comprobación a scripts o pipelines.
La [referencia técnica](docs/reference.md) detalla los estados, opciones y formato CSV.

## Verificación

```bash
python -m unittest discover -s tests -v
```

La suite utiliza un servidor HTTP local para comprobar respuestas válidas,
redirecciones, errores 404/500, contenido incorrecto, timeout, límite de lectura,
generación de reportes y códigos de salida. GitHub Actions ejecuta las pruebas en
Python 3.12; los tests no dependen de las webs en producción.

## Diseño y alcance

El flujo separa validación de configuración (`load_sites`), comprobación de páginas
(`check_site`) y generación de reportes (`write_reports`). `Site` y `Result`
definen los datos de entrada y salida; `main` coordina la ejecución secuencial.

El monitor realiza comprobaciones puntuales sobre URLs explícitas y HTML estático.
No ejecuta JavaScript, envía formularios ni descubre enlaces o imágenes. El tiempo
registrado incluye conexión y lectura del cuerpo; no mide la carga visual en un navegador.
