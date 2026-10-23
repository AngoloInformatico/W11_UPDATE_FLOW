"""
W11 Update Flow - Server locale (solo 127.0.0.1) che espone UI web + API JSON.

Created by Alex Lignola - (c) 2026 W11 Update Flow - All rights reserved.
"""
from __future__ import annotations

import json
import mimetypes
import secrets
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs

from .core import APP_NAME, LOG, SETTINGS, app_version, is_admin, iso_dir, log
from .ms_download import DOWNLOADER, TARGET_CHECKER
from .system_info import SCANNER
from .tools import HASHER, browse_iso, run_tool
from .upgrade import UPGRADER, list_isos

TOKEN = secrets.token_urlsafe(16)
LAST_BEAT = {"t": time.time()}

mimetypes.add_type("application/javascript", ".js")
mimetypes.add_type("image/svg+xml", ".svg")
mimetypes.add_type("image/x-icon", ".ico")
mimetypes.add_type("image/png", ".png")


def web_root() -> Path:
    from .core import resource_dir
    return resource_dir() / "web"


def full_state(since: int) -> dict:
    isos = list_isos()
    sel = SETTINGS.get("selected_iso")
    if (not sel or not Path(sel).exists()) and isos:
        sel = isos[0]["path"]
        SETTINGS.set("selected_iso", sel)

    from .ms_download import compare_iso_with_target
    primary_iso = next((i for i in isos if i["path"] == sel), None) or (isos[0] if isos else None)
    iso_status = {"has_iso": False, "is_outdated": False, "status": "none"}
    if primary_iso:
        cmp = compare_iso_with_target(primary_iso)
        iso_status = {
            "has_iso": True,
            "path": primary_iso["path"],
            "name": primary_iso["name"],
            "release": primary_iso.get("release", ""),
            "build": primary_iso.get("build", ""),
            "size": primary_iso.get("size", 0),
            "date": primary_iso.get("date", ""),
            "is_outdated": cmp["is_outdated"],
            "status": cmp["status"],
            "target_release": cmp["target_release"],
            "target_build": cmp["target_build"],
            "message": cmp["message"],
        }

    return {
        "app": {"name": APP_NAME, "version": app_version(), "admin": is_admin(), "iso_dir": str(iso_dir())},
        "system": SCANNER.data, "system_state": SCANNER.state,
        "target": TARGET_CHECKER.snapshot(),
        "download": DOWNLOADER.snapshot(),
        "isos": isos, "selected_iso": sel if sel and Path(sel).exists() else "",
        "iso_status": iso_status,
        "upgrade": UPGRADER.snapshot(),
        "hash": HASHER.snapshot(),
        "settings": SETTINGS.all(),
        "logs": LOG.since(since),
    }


class Handler(BaseHTTPRequestHandler):
    server_version = "W11UpdateFlow"

    def log_message(self, *args):  # silenzia il log di default
        pass

    # ------------------------------------------------------------ helpers
    def _json(self, data, code=200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _body(self) -> dict:
        n = int(self.headers.get("Content-Length") or 0)
        if not n:
            return {}
        try:
            return json.loads(self.rfile.read(n).decode("utf-8"))
        except Exception:
            return {}

    def _authorized(self) -> bool:
        return self.headers.get("X-W11UF-Token") == TOKEN

    # ------------------------------------------------------------ GET
    def do_GET(self):
        url = urlparse(self.path)
        if url.path.startswith("/api/"):
            if not self._authorized():
                return self._json({"error": "unauthorized"}, 403)
            if url.path == "/api/state":
                LAST_BEAT["t"] = time.time()
                since = int(parse_qs(url.query).get("since", ["0"])[0] or 0)
                return self._json(full_state(since))
            return self._json({"error": "not found"}, 404)

        rel = url.path.lstrip("/") or "index.html"
        root = web_root().resolve()
        target = (root / rel).resolve()
        if root not in target.parents and target != root or not target.is_file():
            target = root / "index.html"
        data = target.read_bytes()
        if target.name == "index.html":
            data = data.replace(b"__W11UF_TOKEN__", TOKEN.encode())
        self.send_response(200)
        ctype = mimetypes.guess_type(str(target))[0] or "application/octet-stream"
        if ctype.startswith("text/") or ctype.endswith("javascript"):
            ctype += "; charset=utf-8"
        self.send_header("Content-Type", ctype)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    # ------------------------------------------------------------ POST
    def do_POST(self):
        if not self._authorized():
            return self._json({"error": "unauthorized"}, 403)
        path = urlparse(self.path).path
        body = self._body()
        LAST_BEAT["t"] = time.time()

        if path == "/api/scan":
            SCANNER.scan_async()
            TARGET_CHECKER.check_async(force=True)
            return self._json({"ok": True})
        if path == "/api/target/check":
            TARGET_CHECKER.check_async(force=True)
            return self._json({"ok": True})
        if path == "/api/download/start":
            # ISO già presente (e nessun download parziale da riprendere): verifica aggiornamenti
            if not body.get("force") and DOWNLOADER.state != "paused" and DOWNLOADER.has_local_iso():
                ok = DOWNLOADER.check_update()
                return self._json({"ok": ok, "checking": True})
            ok = DOWNLOADER.start()
            if ok:
                log("Richiesta download ISO ufficiale Windows 11 · Italiano · x64")
            return self._json({"ok": ok})
        if path == "/api/download/replace":
            r_path = body.get("replace_path")
            ok = DOWNLOADER.start(replace=True, replace_path=r_path)
            if ok:
                log("Download della nuova ISO avviato: la vecchia verrà eliminata al termine", "warn")
            return self._json({"ok": ok})
        if path == "/api/download/pause":
            DOWNLOADER.pause()
            return self._json({"ok": True})
        if path == "/api/download/cancel":
            DOWNLOADER.cancel()
            return self._json({"ok": True})
        if path == "/api/iso/select":
            p = body.get("path", "")
            if p and Path(p).exists():
                SETTINGS.set("selected_iso", p)
                log(f"ISO selezionata: {Path(p).name}")
                return self._json({"ok": True})
            return self._json({"ok": False, "msg": "File non trovato"})
        if path == "/api/iso/browse":
            def job():
                p = browse_iso()
                if p:
                    SETTINGS.set("selected_iso", p)
                    log(f"ISO esterna selezionata: {p}", "ok")
            threading.Thread(target=job, daemon=True).start()
            return self._json({"ok": True})
        if path == "/api/settings":
            for k in ("upgrade_mode", "upgrade_method", "create_restore_point", "remove_watermark"):
                if k in body:
                    SETTINGS.set(k, body[k])
            return self._json({"ok": True})
        if path == "/api/upgrade/start":
            ok, msg = UPGRADER.start(
                SETTINGS.get("selected_iso"), SETTINGS.get("upgrade_mode"), SETTINGS.get("upgrade_method"),
                bool(SETTINGS.get("create_restore_point")), bool(SETTINGS.get("remove_watermark")))
            return self._json({"ok": ok, "msg": msg})
        if path.startswith("/api/tool/"):
            return self._json(run_tool(path.rsplit("/", 1)[-1], body))
        if path == "/api/quit":
            LAST_BEAT["t"] = 0
            return self._json({"ok": True})
        return self._json({"error": "not found"}, 404)


def start_server() -> tuple[ThreadingHTTPServer, int]:
    srv = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    srv.daemon_threads = True
    port = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, port
