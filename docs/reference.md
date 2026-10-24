# Referencia técnica

## Interfaz de consola

```text
python monitor.py [--config CONFIG] [--timeout TIMEOUT] [--output OUTPUT]
```

| Opción | Valor por defecto | Comportamiento |
| --- | --- | --- |
| `--config` | `sites.json` junto a `monitor.py` | Lista JSON no vacía de páginas. |
| `--timeout` | `10` segundos | Límite por operación de red; admite valores mayores que 0 y hasta 60. |
| `--output` | `reports` | Carpeta relativa al directorio de ejecución, salvo que se indique una ruta absoluta. |
| `--help` | — | Muestra la ayuda y termina. |

Las páginas se consultan de forma secuencial. El timeout no es un límite global de
ejecución: varias operaciones o redirecciones pueden aumentar el tiempo total.

## Configuración

| Campo | Tipo | Uso |
| --- | --- | --- |
| `name` | `string` | Nombre de la comprobación; obligatorio y no vacío. |
| `url` | `string` | URL HTTP o HTTPS completa; obligatoria y sin credenciales. |
| `expected_host` | `string` | Hostname final esperado; por defecto, el de `url`. |
| `expected_text` | `string` | Texto que debe aparecer en el HTML; vacío u omitido desactiva esta comprobación. |

Se rechazan campos desconocidos. `www.example.com` y `example.com` son hostnames
distintos; una redirección legítima requiere configurar su hostname final.

El programa sigue redirecciones HTTP antes de validar el destino, por lo que
`expected_host` es una comprobación del resultado, no una restricción de acceso
a dominios. El puerto y la ruta no forman parte de esa comparación.

La búsqueda de contenido normaliza espacios y usa `casefold()` para comparar
sin distinguir mayúsculas. `HTMLParser` excluye datos de elementos `script` y
`style`; no evalúa CSS ni determina qué texto es visible en pantalla. Las entidades
HTML se decodifican. Se utiliza el charset declarado por el servidor o UTF-8.

Las URLs de Weblift apuntan directamente a sus páginas HTML para evitar depender
de la navegación JavaScript de la portada.

## Clasificación de resultados

| Estado | Condición |
| --- | --- |
| `OK` | HTTP 200, hostname esperado y comprobaciones habilitadas correctas. |
| `HTTP_ERROR` | Error HTTP o estado final distinto de 200. |
| `UNEXPECTED_HOST` | La respuesta termina en un hostname diferente. |
| `CONTENT_MISSING` | HTTP 200 sin el texto esperado en el HTML procesado. |
| `TIMEOUT` | Una operación de red excede el tiempo configurado. |
| `NETWORK_ERROR` | Fallo de conexión, incluida resolución DNS o validación TLS. |
| `BODY_TOO_LARGE` | El cuerpo supera 1.000.000 de bytes. |
| `REQUEST_ERROR` | Otro error de lectura o interpretación de la respuesta. |

Cada página produce un resultado. Una respuesta puede incumplir varias condiciones;
se informa la primera detectada. En respuestas recibidas normalmente se comprueba
hostname, estado HTTP, tamaño y contenido, en ese orden. Las excepciones HTTP se
registran directamente como `HTTP_ERROR`.

La lectura solicita hasta 1.000.001 bytes para detectar que se excedió el límite.
El tiempo se mide con `time.perf_counter()` y se expresa en milisegundos.

## Formato de los reportes

```text
reports/
  report_20261023T232631_524186Z.csv
  report_20261023T232631_524186Z.html
```

El CSV usa UTF-8 con BOM y conserva una fila por página, en el orden de la
configuración:

```text
name,url,checked_at_utc,status,http_status,elapsed_ms,final_url,detail
```

`http_status` queda vacío si no se recibió una respuesta HTTP. Las fechas de cada
consulta se guardan en UTC. El timestamp del nombre se obtiene al generar los
reportes; puede diferir de la hora de inicio de las consultas.

El HTML resume resultados y destinos finales. Los valores se escapan antes de
insertarlos para que nombres o diagnósticos no se interpreten como etiquetas HTML.
Los ejemplos versionados en `docs/examples/` conservan una ejecución real;
los nuevos reportes de `reports/` permanecen fuera de Git.

## Archivos del proyecto

| Ruta | Responsabilidad |
| --- | --- |
| `monitor.py` | Modelos de datos, configuración, peticiones, reportes e interfaz de consola. |
| `sites.json` | Configuración de las cinco páginas públicas incluidas. |
| `run.cmd` | Lanzador opcional de Windows con detección de Python. |
| `tests/test_monitor.py` | Pruebas con un servidor local temporal y archivos aislados. |
| `.github/workflows/tests.yml` | Ejecución de pruebas en cada push y pull request. |
