# Site Health Monitor Python

Herramienta en Python para comprobar disponibilidad, detectar enlaces rotos y generar reportes de mantenimiento de sitios web.

Primera versión por consola, sin dependencias externas. Comprueba páginas públicas
de Aptia y Weblift y guarda reportes CSV y HTML con los resultados.

## Requisitos y ejecución

Python 3.12 o posterior. No hace falta instalar paquetes ni configurar claves.
Desde la carpeta del proyecto:

```powershell
python monitor.py
```

Si en Windows utilizas el lanzador de Python, puedes ejecutar `py -3 monitor.py`.
También puedes usar `./run.cmd` desde PowerShell: intenta utilizar el lanzador
`py` y, si no encuentra Python, el runtime de Codex cuando está disponible.
No instala software ni cambia la configuración del sistema.
Al terminar se muestran las rutas de los reportes. Abre el archivo HTML en tu
navegador o el CSV en una hoja de cálculo. `reports/` no se publica en Git.

Opciones:

```powershell
python monitor.py --config sites.json --timeout 10 --output reports
python monitor.py --help
```

El timeout se aplica a cada operación de red, no al tiempo total de la ejecución.
Las páginas se consultan una a una. El programa no queda ejecutándose en segundo plano.

## Qué comprueba

1. Realiza una petición GET y sigue las redirecciones HTTP.
2. Comprueba que la respuesta sea HTTP 200 y termine en el dominio esperado.
3. Lee como máximo 1 MB y busca un texto esperado, sin contar scripts o estilos.
4. Registra el resultado, la URL final y el tiempo de conexión y lectura.
5. Genera reportes CSV y HTML con nombre único y fecha UTC.

Una página que responde 200 puede fallar la comprobación si muestra contenido
equivocado. Un error en una página no impide comprobar las siguientes.

## Configuración

`sites.json` contiene una lista explícita de páginas. Por ejemplo:

```json
[
  {
    "name": "Mi página",
    "url": "https://example.com/",
    "expected_host": "example.com",
    "expected_text": "Example Domain"
  }
]
```

`name` y `url` son obligatorios. Si omites `expected_host`, se utiliza el dominio
de la URL original. `expected_text` es opcional; ignora mayúsculas y diferencias
de espacios. `www.example.com` y `example.com` se consideran dominios diferentes.
Si una redirección legítima termina en otro dominio, configúralo explícitamente.
No incluyas credenciales ni información privada en las URLs o la configuración.

En Weblift se comprueban directamente las páginas de inicio y proyectos:
la portada utiliza navegación con JavaScript, que este programa no ejecuta.

## Resultados y códigos de salida

| Resultado | Significado |
| --- | --- |
| `OK` | HTTP 200, dominio y contenido esperado correctos. |
| `HTTP_ERROR` | Error HTTP o respuesta final distinta de 200. |
| `UNEXPECTED_HOST` | La respuesta termina en otro dominio. |
| `CONTENT_MISSING` | Responde 200, pero falta el texto esperado en el HTML. |
| `TIMEOUT` | Una operación de red excedió la espera configurada. |
| `NETWORK_ERROR` | No fue posible conectar; por ejemplo, fallo DNS o TLS. |
| `BODY_TOO_LARGE` | La respuesta supera el límite de 1 MB. |
| `REQUEST_ERROR` | Otro problema de lectura o interpretación. |

Códigos de salida: **0**, todas correctas; **1**, alguna comprobación falló;
**2**, configuración inválida o error al guardar reportes. Esto permite integrar
el programa posteriormente en otras herramientas.

## Pruebas

```powershell
python -m unittest discover -s tests -v
```

Las pruebas levantan un servidor HTTP local temporal. Comprueban respuestas válidas,
redirecciones, errores 404/500, contenido incorrecto, timeout, tamaño máximo,
reportes y códigos de salida. No necesitan conexión a Internet. GitHub Actions
ejecuta estas pruebas, sin consultar las páginas en producción.

## Estructura

```text
monitor.py                    Lectura, peticiones y reportes
run.cmd                       Lanzador opcional para Windows
sites.json                    Páginas y expectativas configuradas
tests/test_monitor.py         Pruebas con servidor local
.github/workflows/tests.yml   Verificación automática
reports/                      Resultados locales (ignorado por Git)
```

## Alcance y límites

- Es una observación puntual; no calcula disponibilidad mensual ni certifica un sitio.
- No ejecuta JavaScript, comprueba botones, envía formularios ni conversa con asistentes.
- El tiempo medido no representa la carga visual ni las métricas de rendimiento de un navegador.
- Todavía no descubre enlaces rotos ni revisa imágenes: comprueba las URLs configuradas.
- No analiza la seguridad o la legalidad de las webs.
- Se concibió para practicar Python con sitios propios y explicar cada decisión del código.

## Próximos pasos

Descubrir y comprobar enlaces internos, revisar imágenes, comparar ejecuciones
y añadir comprobaciones de navegador si resultan necesarias.
