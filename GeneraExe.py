"""
W11 Update Flow - Script di Compilazione Eseguibile (.exe)
Genera il file eseguibile standalone nella cartella dist/ utilizzando PyInstaller.

Prima della generazione, verifica e incrementa automaticamente la versione
se i sorgenti sono stati modificati.

Created by Alex Lignola - © 2026 W11 Update Flow - All rights reserved.
https://www.youtube.com/@AngoloInformatico
https://github.com/AngoloInformatico
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DIST_DIR = ROOT / "dist"
BUILD_DIR = ROOT / "build"


def check_pyinstaller():
    try:
        import PyInstaller  # noqa: F401
    except ImportError:
        print("[!] PyInstaller non trovato. Installazione in corso...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])


def build_exe():
    print("=" * 65)
    print("  W11 Update Flow - Compilazione Eseguibile Standalone")
    print("  Created by Alex Lignola - © 2026 All rights reserved")
    print("=" * 65)

    check_pyinstaller()

    # 1. Verifica e aggiornamento automatico della versione
    from app.versioning import bump_if_changed, load
    ver = bump_if_changed(verbose=True)
    v_data = load()
    print(f"[*] Versione di rilascio: v{ver} (Build {v_data.get('build', 1)})")

    # 2. Pulizia cartelle di build precedenti
    if BUILD_DIR.exists():
        print("[*] Pulizia cartella build temporanea...")
        shutil.rmtree(BUILD_DIR, ignore_errors=True)

    DIST_DIR.mkdir(parents=True, exist_ok=True)

    # 3. Parametri PyInstaller
    main_py = str(ROOT / "main.py")
    web_dir = f"{ROOT / 'web'};web"
    version_file = f"{ROOT / 'version.json'};."
    icon_dir = f"{ROOT / 'Icona'};Icona"
    icon_file = ROOT / "Icona" / "icon.ico"

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onefile",
        "--windowed",
        "--uac-admin",
        "--name", "W11 Update Flow",
        "--icon", str(icon_file),
        "--add-data", web_dir,
        "--add-data", version_file,
        "--add-data", icon_dir,
        "--distpath", str(DIST_DIR),
        "--workpath", str(BUILD_DIR),
        "--specpath", str(BUILD_DIR),
        main_py,
    ]

    print("[*] Esecuzione PyInstaller in corso...")
    print(" ".join(f'"{c}"' if " " in c else c for c in cmd))
    print("-" * 65)

    ret = subprocess.call(cmd)
    if ret == 0:
        exe_path = DIST_DIR / "W11 Update Flow.exe"
        size_mb = exe_path.stat().st_size / (1024 * 1024) if exe_path.exists() else 0
        print("-" * 65)
        print(f"[OK] Compilazione completata con successo!")
        print(f"[OK] File generato: {exe_path}")
        print(f"[OK] Dimensione: {size_mb:.2f} MB")
        print(f"[OK] Versione incorporata: {ver}")
        print("=" * 65)
    else:
        print(f"[ERRORE] Compilazione fallita con codice di uscita: {ret}", file=sys.stderr)
        sys.exit(ret)


if __name__ == "__main__":
    build_exe()
