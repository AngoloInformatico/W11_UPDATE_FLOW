"""
W11 Update Flow - Punto di avvio.

Avvia il server locale e apre l'interfaccia in una finestra applicazione
(Microsoft Edge in modalità --app, sempre presente su Windows 10/11),
senza dipendenze esterne.

Created by Alex Lignola - (c) 2026 W11 Update Flow - All rights reserved.
https://www.youtube.com/@AngoloInformatico
https://github.com/AngoloInformatico
"""
from __future__ import annotations

import ctypes
import os
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

from app.core import APP_NAME, data_dir, is_admin, is_frozen, iso_dir, log


def hide_console():
    """Nasconde la finestra del terminale Windows se visibile."""
    try:
        hwnd = ctypes.windll.kernel32.GetConsoleWindow()
        if hwnd:
            ctypes.windll.user32.ShowWindow(hwnd, 0)  # 0 = SW_HIDE
    except Exception:
        pass


def relaunch_as_admin() -> bool:
    if is_frozen():
        exe = sys.executable
        params = " ".join(f'"{a}"' for a in sys.argv[1:])
    else:
        exe_path = Path(sys.executable)
        pythonw = exe_path.with_name("pythonw.exe")
        exe = str(pythonw) if pythonw.exists() else sys.executable
        params = " ".join(f'"{a}"' for a in [os.path.abspath(sys.argv[0])] + sys.argv[1:])

    # 0 = SW_HIDE (non apre la finestra del terminale per il processo elevato)
    rc = ctypes.windll.shell32.ShellExecuteW(None, "runas", exe, params, os.getcwd(), 0)
    return rc > 32


def single_instance() -> bool:
    ctypes.windll.kernel32.CreateMutexW(None, False, "Global\\W11UpdateFlow_SingleInstance")
    return ctypes.windll.kernel32.GetLastError() != 183  # ERROR_ALREADY_EXISTS


def find_browser() -> str | None:
    pf = [os.environ.get(k, "") for k in ("ProgramFiles(x86)", "ProgramFiles", "LOCALAPPDATA")]
    candidates = []
    for base in pf:
        if base:
            candidates += [Path(base) / "Microsoft/Edge/Application/msedge.exe",
                           Path(base) / "Google/Chrome/Application/chrome.exe"]
    for c in candidates:
        if c.exists():
            return str(c)
    return None


def open_window(url: str):
    browser = find_browser()
    if browser:
        profile = data_dir() / "webview"
        args = [browser, f"--app={url}", f"--user-data-dir={profile}", "--window-size=1320,860",
                "--no-first-run", "--no-default-browser-check", "--disable-features=Translate,msEdgeSidebarV2",
                "--disable-extensions", "--lang=it"]
        subprocess.Popen(args, creationflags=0x08000000)
    else:
        webbrowser.open(url)


def main():
    if os.name != "nt":
        print("W11 Update Flow funziona solo su Windows.")
        return

    # Nasconde immediatamente la finestra del terminale Windows
    if "--show-console" not in sys.argv and "--debug" not in sys.argv:
        hide_console()

    if not is_admin() and "--no-elevate" not in sys.argv:
        if relaunch_as_admin():
            return
    # Registra l'App ID per la barra delle applicazioni di Windows
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("AngoloInformatico.W11UpdateFlow.1.0")
    except Exception:
        pass

    if not single_instance():
        ctypes.windll.user32.MessageBoxW(None, f"{APP_NAME} è già in esecuzione.", APP_NAME, 0x40)
        return
    if not is_frozen():
        try:
            from app.versioning import bump_if_changed
            bump_if_changed()
        except Exception:
            pass

    iso_dir()  # garantisce la cartella ISO
    from app.server import LAST_BEAT, start_server
    from app.system_info import SCANNER
    from app.ms_download import TARGET_CHECKER
    from app.core import app_version

    srv, port = start_server()
    log(f"{APP_NAME} v{app_version()} avviato")
    SCANNER.scan_async()
    TARGET_CHECKER.check_async()
    url = f"http://127.0.0.1:{port}/"
    open_window(url)

    # Rimane attivo finché la finestra invia heartbeat; chiude dopo 25s di silenzio
    # (un download interrotto riprende automaticamente al riavvio dell'app)
    LAST_BEAT["t"] = time.time() + 40  # tolleranza all'avvio
    try:
        while True:
            time.sleep(2)
            if LAST_BEAT["t"] == 0 or time.time() - LAST_BEAT["t"] > 25:
                break
    except KeyboardInterrupt:
        pass
    from app.ms_download import DOWNLOADER
    DOWNLOADER.pause()
    time.sleep(0.5)
    srv.shutdown()


if __name__ == "__main__":
    main()
