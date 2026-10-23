"""Pruebas locales: no dependen de Vercel ni consultan las webs públicas."""

import contextlib
import csv
import io
import json
import tempfile
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from monitor import MAX_BODY_BYTES, Site, check_site, load_sites, main, write_reports


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        if self.path == "/redirect":
            self.send_response(302)
            self.send_header("Location", "/ok")
            self.end_headers()
            return
        if self.path == "/other-host":
            self.send_response(302)
            self.send_header("Location", f"http://localhost:{self.server.server_port}/ok")
            self.end_headers()
            return
        if self.path == "/slow":
            time.sleep(0.15)
        code = 404 if self.path == "/missing" else 500 if self.path == "/error" else 200
        body = "<h1>Don Tata</h1>".encode()
        if self.path == "/wrong-content":
            body = b"<h1>Otra pagina</h1><script>const message = 'Don Tata';</script>"
        if self.path == "/large":
            body = b"x" * (MAX_BODY_BYTES + 1)
        self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            pass  # La prueba de timeout ya cerró la conexión.


class MonitorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def check(self, path, timeout=1):
        return check_site(Site("Prueba", self.base + path, "127.0.0.1", "Don Tata"), timeout)

    def test_valid_page_and_same_host_redirect(self):
        self.assertEqual(self.check("/ok").status, "OK")
        redirected = self.check("/redirect")
        self.assertEqual(redirected.status, "OK")
        self.assertEqual(redirected.final_url, self.base + "/ok")

    def test_unexpected_redirect_destination(self):
        self.assertEqual(self.check("/other-host").status, "UNEXPECTED_HOST")

    def test_http_errors_do_not_abort_next_check(self):
        for path, code in (("/missing", 404), ("/error", 500)):
            with self.subTest(path=path):
                result = self.check(path)
                self.assertEqual(result.status, "HTTP_ERROR")
                self.assertEqual(result.http_status, code)
        self.assertEqual(self.check("/ok").status, "OK")

    def test_200_without_expected_content_is_failure(self):
        result = self.check("/wrong-content")
        self.assertEqual(result.http_status, 200)
        self.assertEqual(result.status, "CONTENT_MISSING")

    def test_timeout_is_reported(self):
        self.assertEqual(self.check("/slow", timeout=0.02).status, "TIMEOUT")

    def test_body_size_is_bounded(self):
        self.assertEqual(self.check("/large").status, "BODY_TOO_LARGE")

    def test_reports_preserve_rows_and_escape_html(self):
        result = self.check("/ok")
        result.name = '<script>alert("test")</script>, nombre'
        with tempfile.TemporaryDirectory() as folder:
            csv_path, html_path = write_reports([result], Path(folder))
            with csv_path.open(encoding="utf-8-sig", newline="") as file:
                rows = list(csv.DictReader(file))
            self.assertEqual(rows[0]["name"], result.name)
            self.assertNotIn(result.name, html_path.read_text(encoding="utf-8"))
            self.assertIn("&lt;script&gt;", html_path.read_text(encoding="utf-8"))
            second_csv, _ = write_reports([result], Path(folder))
            self.assertNotEqual(csv_path, second_csv)

    def test_invalid_configurations(self):
        invalid = [[], {}, [None], [{"name": "x", "url": "file:///tmp/x"}],
                   [{"name": "x", "url": "https://user:password@example.com"}],
                   [{"name": "x", "url": "https://example.com", "expected_text": 4}],
                   [{"name": "x", "url": "https://example.com", "extra": True}]]
        with tempfile.TemporaryDirectory() as folder:
            config = Path(folder) / "sites.json"
            for data in invalid:
                with self.subTest(data=data):
                    config.write_text(json.dumps(data), encoding="utf-8")
                    with self.assertRaises(ValueError):
                        load_sites(config)

    def test_cli_exit_codes_and_real_reports(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            config = root / "sites.json"
            arguments = ["--config", str(config), "--output", str(root / "reports")]
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(main(arguments), 2)
                config.write_text(json.dumps([{"name": "Prueba", "url": self.base + "/ok"}]))
                self.assertEqual(main(arguments), 0)
                config.write_text(json.dumps([{"name": "Prueba", "url": self.base + "/missing"}]))
                self.assertEqual(main(arguments), 1)
            self.assertEqual(len(list((root / "reports").glob("*.csv"))), 2)


if __name__ == "__main__":
    unittest.main()
