"""
W11 Update Flow - Core utilities
Percorsi, log in memoria, impostazioni ed esecuzione PowerShell.

Created by Alex Lignola - (c) 2026 W11 Update Flow - All rights reserved.
"""
from __future__ import annotations

import base64
import ctypes
import json
import os
import subprocess
import sys
import threading
import time
from collections import deque
from pathlib import Path

APP_NAME = "W11 Update Flow"
APP_ID = "W11UpdateFlow"

CREATE_NO_WINDOW = 0x08000000


# ---------------------------------------------------------------------------
# Percorsi
# ---------------------------------------------------------------------------
def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def base_dir() -> Path:
    """Cartella dell'applicazione (accanto all'eseguibile o radice progetto)."""
    if is_frozen():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def resource_dir() -> Path:
    """Cartella delle risorse incluse (web/, version.json)."""
    if is_frozen():
        return Path(getattr(sys, "_MEIPASS", base_dir()))
    return Path(__file__).resolve().parent.parent


def iso_dir() -> Path:
    """Cartella dedicata ISO: sempre presente nel path dell'app."""
    p = base_dir() / "ISO"
    p.mkdir(parents=True, exist_ok=True)
    return p


def data_dir() -> Path:
    root = os.environ.get("LOCALAPPDATA") or str(Path.home())
    p = Path(root) / APP_ID
    p.mkdir(parents=True, exist_ok=True)
    return p


# ---------------------------------------------------------------------------
# Versione
# ---------------------------------------------------------------------------
def app_version() -> str:
    try:
        data = json.loads((resource_dir() / "version.json").read_text(encoding="utf-8"))
        return str(data.get("version", "1.0.0"))
    except Exception:
        return "1.0.0"


# ---------------------------------------------------------------------------
# Log in memoria (consultabile dalla UI) + file
# ---------------------------------------------------------------------------
class LogBuffer:
    def __init__(self, maxlen: int = 1500):
        self._lines: deque = deque(maxlen=maxlen)
        self._seq = 0
        self._lock = threading.Lock()
        self._file = data_dir() / "w11updateflow.log"

    def add(self, msg: str, level: str = "info") -> None:
        ts = time.strftime("%H:%M:%S")
        with self._lock:
            self._seq += 1
            self._lines.append({"id": self._seq, "t": ts, "lvl": level, "msg": str(msg)})
        try:
            with open(self._file, "a", encoding="utf-8") as fh:
                fh.write(f"{time.strftime('%Y-%m-%d')} {ts} [{level.upper()}] {msg}\n")
        except Exception:
            pass

    def since(self, last_id: int) -> list:
        with self._lock:
            return [l for l in self._lines if l["id"] > last_id]

    @property
    def path(self) -> Path:
        return self._file


LOG = LogBuffer()


def log(msg: str, level: str = "info") -> None:
    LOG.add(msg, level)


# ---------------------------------------------------------------------------
# Impostazioni persistenti
# ---------------------------------------------------------------------------
class Settings:
    _defaults = {
        "selected_iso": "",
        "upgrade_mode": "auto",        # auto | guided | silent
        "upgrade_method": "server",    # server | appraiser
        "create_restore_point": True,
        "remove_watermark": True,
    }

    def __init__(self):
        self._file = data_dir() / "settings.json"
        self._data = dict(self._defaults)
        try:
            self._data.update(json.loads(self._file.read_text(encoding="utf-8")))
        except Exception:
            pass

    def get(self, key, default=None):
        return self._data.get(key, self._defaults.get(key, default))

    def set(self, key, value) -> None:
        self._data[key] = value
        try:
            self._file.write_text(json.dumps(self._data, indent=2), encoding="utf-8")
        except Exception:
            pass

    def all(self) -> dict:
        return dict(self._data)


SETTINGS = Settings()


# ---------------------------------------------------------------------------
# Privilegi e PowerShell
# ---------------------------------------------------------------------------
def is_admin() -> bool:
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def run_ps(script: str, timeout: int = 180) -> tuple[int, str, str]:
    """Esegue uno script PowerShell in modo invisibile (EncodedCommand)."""
    prefix = "$ProgressPreference='SilentlyContinue';[Console]::OutputEncoding=[Text.Encoding]::UTF8;"
    encoded = base64.b64encode((prefix + script).encode("utf-16-le")).decode("ascii")
    try:
        proc = subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
             "-EncodedCommand", encoded],
            capture_output=True, timeout=timeout, creationflags=CREATE_NO_WINDOW,
        )
        out = proc.stdout.decode("utf-8", "replace").strip()
        err = proc.stderr.decode("utf-8", "replace").strip()
        return proc.returncode, out, err
    except subprocess.TimeoutExpired:
        return 1, "", "Timeout PowerShell"
    except Exception as exc:  # pragma: no cover
        return 1, "", str(exc)


def run_ps_json(script: str, timeout: int = 180):
    code, out, err = run_ps(script, timeout)
    if not out:
        raise RuntimeError(err or "Nessun output da PowerShell")
    # ignora eventuale testo prima del JSON
    starts = [i for i in (out.find("{"), out.find("[")) if i >= 0]
    return json.loads(out[min(starts):] if starts else out)


def run_cmd(args: list[str], timeout: int = 60) -> tuple[int, str]:
    try:
        proc = subprocess.run(args, capture_output=True, timeout=timeout, creationflags=CREATE_NO_WINDOW)
        out = (proc.stdout + proc.stderr).decode("cp850", "replace").strip()
        return proc.returncode, out
    except Exception as exc:
        return 1, str(exc)


def human_size(n: float) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(n) < 1024 or unit == "TB":
            return f"{n:.1f} {unit}" if unit != "B" else f"{int(n)} B"
        n /= 1024
    return f"{n:.1f} TB"
