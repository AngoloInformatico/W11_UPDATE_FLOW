"""
W11 Update Flow - Strumenti e utility aggiuntive.

Created by Alex Lignola - (c) 2026 W11 Update Flow - All rights reserved.
"""
from __future__ import annotations

import hashlib
import os
import subprocess
import threading
import webbrowser
from pathlib import Path

from .core import LOG, SETTINGS, iso_dir, log, run_cmd, run_ps
from .upgrade import (REG_REVERT, REG_WATERMARK, create_restore_point, run_reg_lines,
                      unmount_iso, LOCAL_SETUP_DIR)

PANTHER = Path(os.environ.get("SystemDrive", "C:") + r"\$WINDOWS.~BT\Sources\Panther")


def _open(target: str):
    try:
        os.startfile(target)  # type: ignore[attr-defined]
    except Exception:
        subprocess.Popen(["explorer.exe", target])


class HashJob:
    def __init__(self):
        self.state = "idle"
        self.percent = 0.0
        self.result = ""
        self.file = ""

    def snapshot(self):
        return {"state": self.state, "percent": round(self.percent, 1), "result": self.result, "file": self.file}

    def start(self, path: str):
        if self.state == "running":
            return
        self.state, self.percent, self.result, self.file = "running", 0.0, "", Path(path).name
        threading.Thread(target=self._run, args=(path,), daemon=True).start()

    def _run(self, path):
        try:
            h = hashlib.sha256()
            total = os.path.getsize(path) or 1
            done = 0
            with open(path, "rb") as fh:
                while chunk := fh.read(8 * 1024 * 1024):
                    h.update(chunk)
                    done += len(chunk)
                    self.percent = done / total * 100
            self.result = h.hexdigest().upper()
            self.state = "done"
            log(f"SHA-256 {Path(path).name}: {self.result}", "ok")
        except Exception as exc:
            self.state = "error"
            self.result = str(exc)
            log(f"Verifica hash non riuscita: {exc}", "error")


HASHER = HashJob()


def browse_iso() -> str:
    script = (
        "Add-Type -AssemblyName System.Windows.Forms;"
        "$d = New-Object System.Windows.Forms.OpenFileDialog;"
        "$d.Filter = 'Immagine ISO (*.iso)|*.iso';"
        "$d.Title = 'Seleziona una ISO di Windows 11';"
        f"$d.InitialDirectory = '{str(iso_dir())}';"
        "$f = New-Object System.Windows.Forms.Form -Property @{TopMost=$true};"
        "if ($d.ShowDialog($f) -eq 'OK') { $d.FileName }"
    )
    code, out, _ = run_ps("[Threading.Thread]::CurrentThread.ApartmentState;" + script, timeout=600)
    lines = [l for l in out.splitlines() if l.lower().endswith(".iso")]
    return lines[-1].strip() if lines else ""


def _async(fn):
    threading.Thread(target=fn, daemon=True).start()


def run_tool(name: str, payload: dict | None = None) -> dict:
    payload = payload or {}
    if name == "open_iso_folder":
        _open(str(iso_dir()))
    elif name == "open_log":
        _open(str(LOG.path))
    elif name == "open_setup_logs":
        if PANTHER.exists():
            _open(str(PANTHER))
        else:
            return {"ok": False, "msg": "Log di Windows Setup non ancora presenti"}
    elif name == "restore_point":
        _async(create_restore_point)
        return {"ok": True, "msg": "Creazione punto di ripristino avviata"}
    elif name == "cleanmgr":
        subprocess.Popen(["cleanmgr.exe", "/d", os.environ.get("SystemDrive", "C:")])
    elif name == "watermark":
        n = run_reg_lines(REG_WATERMARK)
        return {"ok": n == 0, "msg": "Avviso 'Requisiti non soddisfatti' rimosso" if n == 0 else "Errore"}
    elif name == "revert":
        run_reg_lines(REG_REVERT)
        return {"ok": True, "msg": "Chiavi di bypass rimosse dal registro"}
    elif name == "extend_rollback":
        def job():
            log("> DISM /Online /Set-OSUninstallWindow /Value:60", "cmd")
            code, out = run_cmd(["dism.exe", "/Online", "/Set-OSUninstallWindow", "/Value:60"], timeout=120)
            log(out[-400:], "ok" if code == 0 else "warn")
        _async(job)
        return {"ok": True, "msg": "Estensione del periodo di ripristino avviata"}
    elif name == "recovery":
        _open("ms-settings:recovery")
    elif name == "windows_update":
        _open("ms-settings:windowsupdate")
    elif name == "rufus":
        webbrowser.open("https://rufus.ie/it/")
    elif name == "ms_page":
        webbrowser.open("https://www.microsoft.com/it-it/software-download/windows11")
    elif name == "unmount":
        iso = SETTINGS.get("selected_iso")
        if iso:
            _async(lambda: unmount_iso(iso))
        return {"ok": True, "msg": "Smontaggio ISO avviato"}
    elif name == "clean_setup_cache":
        def job():
            import shutil
            if LOCAL_SETUP_DIR.exists():
                shutil.rmtree(LOCAL_SETUP_DIR, ignore_errors=True)
            for part in iso_dir().glob("*.part"):
                part.unlink(missing_ok=True)
            log("File temporanei di W11 Update Flow rimossi", "ok")
        _async(job)
        return {"ok": True, "msg": "Pulizia avviata"}
    elif name == "verify_hash":
        iso = payload.get("path") or SETTINGS.get("selected_iso")
        if not iso or not Path(iso).exists():
            return {"ok": False, "msg": "Seleziona prima una ISO"}
        HASHER.start(iso)
        return {"ok": True, "msg": "Calcolo SHA-256 avviato"}
    elif name == "link":
        url = payload.get("url", "")
        if url.startswith("https://"):
            webbrowser.open(url)
    else:
        return {"ok": False, "msg": f"Strumento sconosciuto: {name}"}
    return {"ok": True, "msg": "Fatto"}
