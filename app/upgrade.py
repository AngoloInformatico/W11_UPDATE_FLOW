"""
W11 Update Flow - Procedura di aggiornamento per PC non idonei.

Metodo principale (consigliato):
  setup.exe /product server ...  -> Windows Setup salta la valutazione hardware
  (TPM 2.0, Secure Boot, CPU non in elenco) mantenendo file, app e impostazioni.

Metodo alternativo:
  copia locale dei file di installazione e neutralizzazione di
  sources\\appraiserres.dll (modulo di valutazione compatibilità).

In entrambi i casi vengono applicate le chiavi di registro di bypass
(MoSetup / LabConfig / PCHC / HwReqChk).

Created by Alex Lignola - (c) 2026 W11 Update Flow - All rights reserved.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import threading
import time
from pathlib import Path

from .core import SETTINGS, iso_dir, log, run_cmd, run_ps

LOCAL_SETUP_DIR = Path(os.environ.get("SystemDrive", "C:") + "\\W11UpdateFlow_Setup")

REG_BYPASS = [
    r'reg add "HKLM\SYSTEM\Setup\MoSetup" /v AllowUpgradesWithUnsupportedTPMOrCPU /t REG_DWORD /d 1 /f',
    r'reg add "HKLM\SYSTEM\Setup\LabConfig" /v BypassTPMCheck /t REG_DWORD /d 1 /f',
    r'reg add "HKLM\SYSTEM\Setup\LabConfig" /v BypassSecureBootCheck /t REG_DWORD /d 1 /f',
    r'reg add "HKLM\SYSTEM\Setup\LabConfig" /v BypassRAMCheck /t REG_DWORD /d 1 /f',
    r'reg add "HKLM\SYSTEM\Setup\LabConfig" /v BypassStorageCheck /t REG_DWORD /d 1 /f',
    r'reg add "HKLM\SYSTEM\Setup\LabConfig" /v BypassCPUCheck /t REG_DWORD /d 1 /f',
    r'reg add "HKCU\Software\Microsoft\PCHC" /v UpgradeEligibility /t REG_DWORD /d 1 /f',
    r'reg add "HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\AppCompatFlags\HwReqChk" '
    r'/v HwReqChkVars /t REG_MULTI_SZ /s , /d "SQ_SecureBootCapable=TRUE,SQ_SecureBootEnabled=TRUE,'
    r'SQ_TpmVersion=2,SQ_RamMB=8192" /f',
]

REG_WATERMARK = [
    r'reg add "HKCU\Control Panel\UnsupportedHardwareNotificationCache" /v SV1 /t REG_DWORD /d 0 /f',
    r'reg add "HKCU\Control Panel\UnsupportedHardwareNotificationCache" /v SV2 /t REG_DWORD /d 0 /f',
]

REG_REVERT = [
    r'reg delete "HKLM\SYSTEM\Setup\MoSetup" /v AllowUpgradesWithUnsupportedTPMOrCPU /f',
    r'reg delete "HKLM\SYSTEM\Setup\LabConfig" /f',
    r'reg delete "HKCU\Software\Microsoft\PCHC" /v UpgradeEligibility /f',
    r'reg delete "HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\AppCompatFlags\HwReqChk" /v HwReqChkVars /f',
]


def run_reg_lines(lines: list[str]) -> int:
    errors = 0
    for line in lines:
        log(f"> {line}", "cmd")
        code, out = run_cmd(["cmd.exe", "/c", line])
        if code != 0:
            errors += 1
            log(out or f"Codice di uscita {code}", "warn")
    return errors


def mount_iso(path: str) -> str:
    """Monta l'ISO e restituisce la lettera di unità (es. 'E:')."""
    p = path.replace("'", "''")
    script = (
        f"$img = Get-DiskImage -ImagePath '{p}';"
        f"if (-not $img.Attached) {{ $img = Mount-DiskImage -ImagePath '{p}' -PassThru }};"
        "Start-Sleep -Milliseconds 800;"
        f"$v = Get-DiskImage -ImagePath '{p}' | Get-Volume;"
        "Write-Output ($v.DriveLetter | Select-Object -First 1)"
    )
    log(f"> Mount-DiskImage -ImagePath \"{path}\"", "cmd")
    code, out, err = run_ps(script, timeout=120)
    letter = (out or "").strip()[-1:] if out else ""
    if not letter or not letter.isalpha():
        raise RuntimeError(f"Impossibile montare l'ISO. {err}")
    return f"{letter.upper()}:"


def unmount_iso(path: str) -> bool:
    p = path.replace("'", "''")
    log(f"> Dismount-DiskImage -ImagePath \"{path}\"", "cmd")
    code, _, err = run_ps(f"Dismount-DiskImage -ImagePath '{p}' | Out-Null", timeout=60)
    if code != 0:
        log(err, "warn")
    return code == 0


def create_restore_point() -> bool:
    script = (
        r"reg add 'HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\SystemRestore' "
        r"/v SystemRestorePointCreationFrequency /t REG_DWORD /d 0 /f | Out-Null;"
        "Enable-ComputerRestore -Drive \"$env:SystemDrive\\\" -ErrorAction SilentlyContinue;"
        "Checkpoint-Computer -Description 'W11 Update Flow - prima dell aggiornamento' "
        "-RestorePointType MODIFY_SETTINGS -ErrorAction Stop; 'OK'"
    )
    log("> Checkpoint-Computer -Description 'W11 Update Flow'", "cmd")
    code, out, err = run_ps(script, timeout=600)
    if "OK" in out:
        log("Punto di ripristino creato", "ok")
        return True
    log(f"Punto di ripristino non creato: {err[:300]}", "warn")
    return False


def build_setup_args(mode: str) -> list[str]:
    args = ["/product", "server", "/compat", "IgnoreWarning", "/MigrateDrivers", "All",
            "/DynamicUpdate", "Disable", "/Telemetry", "Disable"]
    if mode in ("auto", "silent"):
        args += ["/auto", "upgrade", "/EULA", "accept"]
    if mode == "silent":
        args += ["/quiet"]
    return args


class UpgradeRunner:
    STEP_DEFS = [
        ("checks", "Verifica preliminare"),
        ("restore", "Punto di ripristino"),
        ("registry", "Bypass requisiti (registro)"),
        ("mount", "Montaggio ISO"),
        ("prepare", "Preparazione file di setup"),
        ("launch", "Avvio Windows Setup"),
    ]

    def __init__(self):
        self.state = "idle"
        self.error = ""
        self.command = ""
        self.drive = ""
        self.steps = []
        self._thread: threading.Thread | None = None
        self._reset_steps()

    def _reset_steps(self):
        self.steps = [{"key": k, "label": l, "status": "pending", "detail": ""} for k, l in self.STEP_DEFS]

    def _step(self, key, status, detail=""):
        for s in self.steps:
            if s["key"] == key:
                s["status"] = status
                if detail:
                    s["detail"] = detail

    def snapshot(self) -> dict:
        return {"state": self.state, "error": self.error, "steps": self.steps,
                "command": self.command, "drive": self.drive}

    def start(self, iso_path: str, mode: str, method: str, restore: bool, watermark: bool) -> tuple[bool, str]:
        if self._thread and self._thread.is_alive():
            return False, "Procedura già in corso"
        if not iso_path or not Path(iso_path).exists():
            return False, "Nessuna ISO selezionata o file non trovato"
        self.error = ""
        self.command = ""
        self._reset_steps()
        self.state = "running"
        self._thread = threading.Thread(
            target=self._run, args=(iso_path, mode, method, restore, watermark), daemon=True)
        self._thread.start()
        return True, "Avviato"

    def _run(self, iso_path, mode, method, restore, watermark):
        current = "checks"
        try:
            log("══ Avvio procedura di aggiornamento ══", "ok")
            self._step("checks", "running")
            size = Path(iso_path).stat().st_size
            if size < 3 * 1024 ** 3:
                raise RuntimeError("Il file ISO sembra incompleto o danneggiato")
            free = shutil.disk_usage(os.environ.get("SystemDrive", "C:") + "\\").free
            need = (20 if method == "server" else 27) * 1024 ** 3
            if free < need:
                raise RuntimeError(f"Spazio insufficiente su disco: servono almeno {need // 1024 ** 3} GB liberi")
            self._step("checks", "ok", Path(iso_path).name)

            current = "restore"
            if restore:
                self._step("restore", "running")
                ok = create_restore_point()
                self._step("restore", "ok" if ok else "skip", "" if ok else "Non disponibile, si prosegue")
            else:
                self._step("restore", "skip", "Disattivato")

            current = "registry"
            self._step("registry", "running")
            errs = run_reg_lines(REG_BYPASS + (REG_WATERMARK if watermark else []))
            self._step("registry", "ok" if not errs else "warn",
                       "Chiavi applicate" if not errs else f"{errs} chiavi non applicate")

            current = "mount"
            self._step("mount", "running")
            self.drive = mount_iso(iso_path)
            self._step("mount", "ok", f"Unità {self.drive}")
            log(f"ISO montata su {self.drive}", "ok")

            current = "prepare"
            setup_dir = Path(self.drive + "\\")
            if method == "appraiser":
                self._step("prepare", "running", "Copia dei file in corso…")
                if LOCAL_SETUP_DIR.exists():
                    shutil.rmtree(LOCAL_SETUP_DIR, ignore_errors=True)
                cmd = ["robocopy", self.drive + "\\", str(LOCAL_SETUP_DIR), "/E", "/R:1", "/W:1",
                       "/NFL", "/NDL", "/NJH", "/NJS", "/NP"]
                log("> " + " ".join(f'"{c}"' if " " in c else c for c in cmd), "cmd")
                code, out = run_cmd(cmd, timeout=3600)
                if code >= 8:
                    raise RuntimeError(f"Copia non riuscita (robocopy {code})")
                subprocess.run(["attrib", "-r", str(LOCAL_SETUP_DIR), "/s", "/d"],
                               creationflags=0x08000000, capture_output=True)
                appr = LOCAL_SETUP_DIR / "sources" / "appraiserres.dll"
                try:
                    if appr.exists():
                        appr.unlink()
                    appr.write_bytes(b"")
                    log("appraiserres.dll neutralizzato", "ok")
                except Exception as exc:
                    log(f"appraiserres.dll: {exc}", "warn")
                setup_dir = LOCAL_SETUP_DIR
                self._step("prepare", "ok", str(LOCAL_SETUP_DIR))
            else:
                self._step("prepare", "ok", "Avvio diretto dall'ISO montata")

            current = "launch"
            self._step("launch", "running")
            setup_exe = setup_dir / "setup.exe"
            if not setup_exe.exists():
                raise RuntimeError(f"setup.exe non trovato in {setup_dir}")
            args = build_setup_args(mode)
            self.command = f'"{setup_exe}" ' + " ".join(args)
            log(f"> {self.command}", "cmd")
            subprocess.Popen([str(setup_exe)] + args, cwd=str(setup_dir))
            self._step("launch", "ok", "Windows Setup avviato")
            self.state = "launched"
            log("Windows Setup è stato avviato. Il PC si riavvierà più volte: non spegnerlo.", "ok")
            SETTINGS.set("last_upgrade", time.strftime("%Y-%m-%d %H:%M"))
        except Exception as exc:
            self._step(current, "error", str(exc))
            self.state = "error"
            self.error = str(exc)
            log(f"Procedura interrotta: {exc}", "error")


UPGRADER = UpgradeRunner()


def list_isos() -> list[dict]:
    from .ms_download import parse_iso_name
    items = []
    for f in sorted(iso_dir().glob("*.iso"), key=lambda p: p.stat().st_mtime, reverse=True):
        st = f.stat()
        info = parse_iso_name(f.name)
        items.append({"path": str(f), "name": f.name, "size": st.st_size,
                      "date": time.strftime("%d/%m/%Y %H:%M", time.localtime(st.st_mtime)), **info})
    sel = SETTINGS.get("selected_iso")
    if sel and Path(sel).exists() and not any(i["path"] == sel for i in items):
        f = Path(sel)
        st = f.stat()
        items.append({"path": sel, "name": f.name, "size": st.st_size, "external": True,
                      "date": time.strftime("%d/%m/%Y %H:%M", time.localtime(st.st_mtime)),
                      **parse_iso_name(f.name)})
    return items
