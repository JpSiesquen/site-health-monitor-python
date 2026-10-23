"""Comprueba páginas públicas y genera reportes. Solo usa la biblioteca estándar."""

import argparse
import csv
import html
import json
import socket
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from html.parser import HTMLParser
from http.client import HTTPException
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen


MAX_BODY_BYTES = 1_000_000
USER_AGENT = "SiteHealthMonitorPython/0.1 (+https://github.com/JpSiesquen/site-health-monitor-python)"


@dataclass
class Site:
    name: str
    url: str
    expected_host: str
    expected_text: str = ""


@dataclass
class Result:
    name: str
    url: str
    checked_at_utc: str
    status: str
    http_status: int | None
    elapsed_ms: int
    final_url: str
    detail: str


class PageText(HTMLParser):
    """Extrae texto del HTML sin contar código JavaScript ni estilos."""

    def __init__(self):
        super().__init__()
        self.parts = []
        self.ignored_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self.ignored_depth += 1

    def handle_endtag(self, tag):
        if tag in ("script", "style") and self.ignored_depth:
            self.ignored_depth -= 1

    def handle_data(self, data):
        if not self.ignored_depth:
            self.parts.append(data)


def load_sites(path: Path) -> list[Site]:
    """Valida la configuración antes de realizar peticiones."""
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, list) or not data:
        raise ValueError("La configuración debe ser una lista no vacía de páginas.")
    sites = []
    for position, entry in enumerate(data, start=1):
        if not isinstance(entry, dict):
            raise ValueError(f"Página {position}: se esperaba un objeto JSON.")
        if set(entry) - {"name", "url", "expected_host", "expected_text"}:
            raise ValueError(f"Página {position}: contiene campos desconocidos.")
        name, url = entry.get("name"), entry.get("url")
        if not isinstance(name, str) or not name.strip():
            raise ValueError(f"Página {position}: falta un nombre válido.")
        if not isinstance(url, str):
            raise ValueError(f"Página {position}: falta una URL válida.")
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https") or not parsed.hostname:
            raise ValueError(f"Página {position}: usa una URL HTTP o HTTPS completa.")
        if parsed.username or parsed.password:
            raise ValueError(f"Página {position}: no incluyas credenciales en la URL.")
        host = entry.get("expected_host", parsed.hostname)
        text = entry.get("expected_text", "")
        if not isinstance(host, str) or not host.strip() or "/" in host or ":" in host:
            raise ValueError(f"Página {position}: expected_host debe ser un nombre de dominio.")
        if not isinstance(text, str):
            raise ValueError(f"Página {position}: expected_text debe ser texto.")
        sites.append(Site(name.strip(), url, host.strip().lower(), text))
    return sites


def check_site(site: Site, timeout: float) -> Result:
    """Hace un GET, sigue redirecciones y valida la respuesta obtenida."""
    checked_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    started = time.perf_counter()
    status, http_status, final_url = "OK", None, site.url
    detail = "Respuesta correcta."
    request = Request(site.url, headers={"User-Agent": USER_AGENT})
    try:
        with urlopen(request, timeout=timeout) as response:
            http_status = response.status
            final_url = response.geturl()
            body = response.read(MAX_BODY_BYTES + 1)
            if urlparse(final_url).hostname != site.expected_host:
                status = "UNEXPECTED_HOST"
                detail = f"Se esperaba el dominio {site.expected_host}."
            elif http_status != 200:
                status, detail = "HTTP_ERROR", f"Se esperaba HTTP 200; llegó {http_status}."
            elif len(body) > MAX_BODY_BYTES:
                status, detail = "BODY_TOO_LARGE", "La respuesta supera el límite de 1 MB."
            elif site.expected_text:
                encoding = response.headers.get_content_charset() or "utf-8"
                parser = PageText()
                parser.feed(body.decode(encoding, errors="replace"))
                text = " ".join(" ".join(parser.parts).split()).casefold()
                expected = " ".join(site.expected_text.split()).casefold()
                if expected not in text:
                    status = "CONTENT_MISSING"
                    detail = f"No se encontró el texto esperado: {site.expected_text}"
    except HTTPError as error:
        http_status, final_url = error.code, error.geturl()
        status, detail = "HTTP_ERROR", f"El servidor respondió HTTP {error.code}."
        error.close()
    except (TimeoutError, socket.timeout):
        status, detail = "TIMEOUT", "Se agotó el tiempo de espera de una operación de red."
    except URLError as error:
        if isinstance(error.reason, (TimeoutError, socket.timeout)):
            status, detail = "TIMEOUT", "Se agotó el tiempo de espera de una operación de red."
        else:
            status, detail = "NETWORK_ERROR", f"No se pudo completar la conexión: {error.reason}"
    except (OSError, ValueError, LookupError, HTTPException) as error:
        status, detail = "REQUEST_ERROR", f"No se pudo interpretar la respuesta: {error}"
    elapsed_ms = round((time.perf_counter() - started) * 1000)
    return Result(site.name, site.url, checked_at, status, http_status, elapsed_ms, final_url, detail)


def write_reports(results: list[Result], output_dir: Path) -> tuple[Path, Path]:
    """Conserva una pareja CSV/HTML por ejecución, sin sobrescribir historial."""
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ")
    csv_path = output_dir / f"report_{stamp}.csv"
    html_path = output_dir / f"report_{stamp}.html"
    rows = [asdict(result) for result in results]
    with csv_path.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    table_rows = []
    for result in results:
        values = (result.name, result.status, result.http_status or "—", result.elapsed_ms,
                  result.final_url, result.detail)
        cells = "".join(f"<td>{html.escape(str(value))}</td>" for value in values)
        css_class = "ok" if result.status == "OK" else "fail"
        table_rows.append(f'<tr class="{css_class}">{cells}</tr>')
    passed = sum(result.status == "OK" for result in results)
    document = f"""<!doctype html>
<html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Site Health Monitor — Reporte</title>
<style>
body{{font:16px/1.5 system-ui,sans-serif;margin:0;background:#f3f5f7;color:#17212b}}
main{{max-width:1200px;margin:40px auto;padding:24px;background:white;border-radius:12px}}
h1{{margin-bottom:8px}} .summary{{font-size:22px;font-weight:600}}
.scroll{{overflow-x:auto}} table{{border-collapse:collapse;width:100%;font-size:14px}}
th,td{{padding:12px;text-align:left;border-bottom:1px solid #dde3e8;vertical-align:top}}
th{{background:#edf1f5}} td{{overflow-wrap:anywhere}} .ok td:nth-child(2){{color:#17603c}}
.fail td:nth-child(2){{color:#a32020;font-weight:bold}} footer{{margin-top:24px;color:#465362}}
</style></head><body><main>
<h1>Site Health Monitor Python</h1>
<p>Comprobación HTTP de páginas públicas · Fechas en UTC</p>
<p class="summary">{passed} de {len(results)} comprobaciones correctas</p>
<p>Inicio: {html.escape(results[0].checked_at_utc)}</p>
<div class="scroll"><table><thead><tr>
<th>Página</th><th>Resultado</th><th>HTTP</th><th>Tiempo (ms)</th><th>Destino final</th><th>Detalle</th>
</tr></thead><tbody>{''.join(table_rows)}</tbody></table></div>
<footer>Una ejecución es una observación puntual, no una garantía de disponibilidad.
El tiempo incluye conexión y lectura del HTML. No se ejecuta JavaScript ni se envían formularios.</footer>
</main></body></html>"""
    html_path.write_text(document, encoding="utf-8")
    return csv_path, html_path


def positive_timeout(value: str) -> float:
    number = float(value)
    if not 0 < number <= 60:
        raise argparse.ArgumentTypeError("El timeout debe ser mayor que 0 y como máximo 60 segundos.")
    return number


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path(__file__).with_name("sites.json"))
    parser.add_argument("--timeout", type=positive_timeout, default=10.0,
                        help="Espera máxima por operación de red en segundos (por defecto: 10).")
    parser.add_argument("--output", type=Path, default=Path("reports"), help="Carpeta de reportes.")
    args = parser.parse_args(argv)
    try:
        sites = load_sites(args.config)
    except (OSError, ValueError) as error:
        print(f"Error de configuración: {error}", file=sys.stderr)
        return 2
    results = []
    for site in sites:
        result = check_site(site, args.timeout)
        results.append(result)
        print(f"[{result.status}] {result.name}: HTTP {result.http_status or '-'} · {result.elapsed_ms} ms")
        if result.status != "OK":
            print(f"  {result.detail}")
    try:
        csv_path, html_path = write_reports(results, args.output)
    except OSError as error:
        print(f"No se pudieron guardar los reportes: {error}", file=sys.stderr)
        return 2
    passed = sum(result.status == "OK" for result in results)
    print(f"\nResultado: {passed}/{len(results)} correctas.")
    print(f"CSV: {csv_path}\nHTML: {html_path}")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
