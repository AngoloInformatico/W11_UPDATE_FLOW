"""
W11 Update Flow - Gestione automatica della versione.

Ad ogni modifica dei sorgenti (app/, web/, main.py) la versione patch
viene incrementata automaticamente in version.json (es. 1.0.3 -> 1.0.4).
Il controllo viene eseguito all'avvio in modalità sviluppo e da GeneraExe.py.

Created by Alex Lignola - (c) 2026 W11 Update Flow - All rights reserved.
"""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VERSION_FILE = ROOT / "version.json"
TRACKED = ["main.py", "app", "web", "Icona"]
EXT = {".py", ".html", ".css", ".js", ".svg", ".json", ".ico", ".png"}


def sources_hash() -> str:
    h = hashlib.sha256()
    files: list[Path] = []
    for entry in TRACKED:
        p = ROOT / entry
        if p.is_file():
            files.append(p)
        elif p.is_dir():
            files += [f for f in p.rglob("*") if f.is_file() and f.suffix in EXT and "__pycache__" not in f.parts]
    for f in sorted(files):
        h.update(str(f.relative_to(ROOT)).replace("\\", "/").encode())
        h.update(f.read_bytes().replace(b"\r\n", b"\n"))
    return h.hexdigest()


def load() -> dict:
    try:
        return json.loads(VERSION_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {"version": "1.0.0", "build": 0, "sources_hash": "", "updated": ""}


def bump_if_changed(verbose: bool = False) -> str:
    data = load()
    current = sources_hash()
    if data.get("sources_hash") != current:
        if data.get("sources_hash"):
            major, minor, patch = (list(map(int, data.get("version", "1.0.0").split("."))) + [0, 0, 0])[:3]
            patch += 1
            if patch > 99:
                minor, patch = minor + 1, 0
            data["version"] = f"{major}.{minor}.{patch}"
        data["build"] = int(data.get("build", 0)) + 1
        data["sources_hash"] = current
        data["updated"] = time.strftime("%Y-%m-%d %H:%M:%S")
        VERSION_FILE.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        if verbose:
            print(f"[versione] sorgenti modificati -> v{data['version']} (build {data['build']})")
    elif verbose:
        print(f"[versione] nessuna modifica -> v{data['version']}")
    return data["version"]


if __name__ == "__main__":
    bump_if_changed(verbose=True)
