"""
W11 Update Flow - Analisi di compatibilità del PC.

Created by Alex Lignola - (c) 2026 W11 Update Flow - All rights reserved.
"""
from __future__ import annotations

import ctypes
import platform
import shutil
import threading
import time

from .core import human_size, is_admin, log, run_ps_json
from .ms_download import release_from_build

PF_SSE4_2_INSTRUCTIONS_AVAILABLE = 38

PS_SCAN = r"""
$ErrorActionPreference = 'SilentlyContinue'
$cv  = Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion'
$os  = Get-CimInstance Win32_OperatingSystem
$cpu = Get-CimInstance Win32_Processor | Select-Object -First 1
$cs  = Get-CimInstance Win32_ComputerSystem
$bios= Get-CimInstance Win32_BIOS
$tpm = Get-CimInstance -Namespace 'root\cimv2\security\microsofttpm' -ClassName Win32_Tpm
$tpmVer = ''
if ($tpm) { $tpmVer = ($tpm.SpecVersion -split ',')[0].Trim() }
$sb = $null
try { $sb = Confirm-SecureBootUEFI } catch { $sb = $null }
$fw = 'BIOS'
if ($env:firmware_type) { $fw = $env:firmware_type }
try { if (Test-Path 'HKLM:\SYSTEM\CurrentControlSet\Control\SecureBoot\State') { $fw = 'UEFI' } } catch {}
$bl = ''
try { $bv = Get-BitLockerVolume -MountPoint $env:SystemDrive; $bl = [string]$bv.ProtectionStatus } catch {}
$pending = (Test-Path 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Component Based Servicing\RebootPending') -or (Test-Path 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\WindowsUpdate\Auto Update\RebootRequired')
$mo  = (Get-ItemProperty 'HKLM:\SYSTEM\Setup\MoSetup').AllowUpgradesWithUnsupportedTPMOrCPU
[pscustomobject]@{
  product   = [string]$cv.ProductName
  edition   = [string]$cv.EditionID
  display   = [string]$cv.DisplayVersion
  build     = [string]$cv.CurrentBuild
  ubr       = [string]$cv.UBR
  caption   = [string]$os.Caption
  osarch    = [string]$os.OSArchitecture
  lang      = [string](Get-Culture).Name
  uilang    = [string](Get-UICulture).Name
  cpu       = [string]$cpu.Name.Trim()
  cores     = [int]$cpu.NumberOfCores
  threads   = [int]$cpu.NumberOfLogicalProcessors
  ram       = [int64]$cs.TotalPhysicalMemory
  model     = ([string]$cs.Manufacturer + ' ' + [string]$cs.Model).Trim()
  biosdate  = [string]$bios.ReleaseDate.ToString('yyyy')
  tpm       = $tpmVer
  secureboot= $sb
  firmware  = $fw
  bitlocker = $bl
  pending   = [bool]$pending
  mosetup   = [int]$mo
} | ConvertTo-Json -Compress
"""


def _sse42() -> bool:
    try:
        return bool(ctypes.windll.kernel32.IsProcessorFeaturePresent(PF_SSE4_2_INSTRUCTIONS_AVAILABLE))
    except Exception:
        return False


class SystemScanner:
    def __init__(self):
        self.data: dict = {}
        self.state = "idle"
        self._lock = threading.Lock()

    def scan_async(self):
        with self._lock:
            if self.state == "scanning":
                return
            self.state = "scanning"
        threading.Thread(target=self._scan, daemon=True).start()

    def _scan(self):
        log("Analisi del sistema in corso…")
        try:
            raw = run_ps_json(PS_SCAN, timeout=90)
        except Exception as exc:
            log(f"Analisi PowerShell parziale: {exc}", "warn")
            raw = {}
        try:
            du = shutil.disk_usage("C:\\")
            free, total_disk = du.free, du.total
        except Exception:
            free, total_disk = 0, 0

        build = raw.get("build", "") or platform.version().split(".")[-1]
        product = raw.get("product", "")
        try:
            if int(build) >= 22000 and "Windows 10" in product:
                product = product.replace("Windows 10", "Windows 11")  # bug noto del registro
        except ValueError:
            pass
        ram = int(raw.get("ram") or 0)
        sse = _sse42()
        is64 = "64" in (raw.get("osarch") or platform.machine())
        tpm = raw.get("tpm") or ""
        sb = raw.get("secureboot")

        checks = []

        def add(key, label, value, status, hint=""):
            checks.append({"key": key, "label": label, "value": value, "status": status, "hint": hint})

        add("arch", "Architettura 64 bit", raw.get("osarch") or platform.machine(),
            "ok" if is64 else "fail", "" if is64 else "Windows 11 esiste solo a 64 bit.")
        add("cpu", "CPU SSE4.2 / POPCNT", "Supportato" if sse else "Non supportato",
            "ok" if sse else "fail",
            "" if sse else "Dalla 24H2 Windows 11 richiede SSE4.2/POPCNT: non aggirabile.")
        add("ram", "Memoria RAM", human_size(ram) if ram else "—",
            "ok" if ram >= 4 * 1024 ** 3 else ("warn" if ram >= 3 * 1024 ** 3 else "fail"),
            "" if ram >= 4 * 1024 ** 3 else "Consigliati almeno 4 GB (bypass attivo).")
        add("disk", "Spazio libero su C:", human_size(free),
            "ok" if free >= 30 * 1024 ** 3 else ("warn" if free >= 20 * 1024 ** 3 else "fail"),
            "" if free >= 30 * 1024 ** 3 else "Servono almeno 20-30 GB liberi per l'aggiornamento.")
        add("tpm", "TPM", f"TPM {tpm}" if tpm else "Assente / non rilevato",
            "ok" if tpm.startswith("2") else "bypass",
            "" if tpm.startswith("2") else "Requisito aggirato automaticamente.")
        add("secureboot", "Secure Boot",
            "Attivo" if sb is True else ("Disattivo" if sb is False else "Non supportato (BIOS legacy)"),
            "ok" if sb is True else "bypass", "" if sb is True else "Requisito aggirato automaticamente.")
        add("firmware", "Firmware", raw.get("firmware") or "—", "ok" if raw.get("firmware") == "UEFI" else "bypass")
        add("pending", "Riavvio in sospeso", "Sì" if raw.get("pending") else "No",
            "warn" if raw.get("pending") else "ok",
            "Riavvia il PC prima di aggiornare." if raw.get("pending") else "")
        add("bitlocker", "BitLocker", "Attivo" if raw.get("bitlocker") == "On" else "Non attivo",
            "warn" if raw.get("bitlocker") == "On" else "ok",
            "Salva la chiave di ripristino BitLocker prima di procedere." if raw.get("bitlocker") == "On" else "")
        add("admin", "Privilegi amministratore", "Sì" if is_admin() else "No",
            "ok" if is_admin() else "fail", "" if is_admin() else "Riavvia l'app come amministratore.")

        blocking = [c for c in checks if c["status"] == "fail"]
        self.data = {
            "product": product or "Windows",
            "edition": raw.get("edition", ""),
            "display": raw.get("display", "") or release_from_build(build),
            "build": build,
            "ubr": raw.get("ubr", ""),
            "lang": raw.get("uilang") or raw.get("lang", ""),
            "cpu": raw.get("cpu", platform.processor()),
            "cores": raw.get("cores", 0),
            "threads": raw.get("threads", 0),
            "ram_h": human_size(ram) if ram else "—",
            "disk_free_h": human_size(free),
            "disk_total_h": human_size(total_disk),
            "model": raw.get("model", ""),
            "biosyear": raw.get("biosdate", ""),
            "mosetup": raw.get("mosetup", 0),
            "checks": checks,
            "ready": not blocking,
            "blocking": len(blocking),
            "bypass_needed": any(c["status"] == "bypass" for c in checks),
            "scanned_at": time.strftime("%H:%M"),
        }
        self.state = "done"
        log(f"Sistema: {self.data['product']} {self.data['display']} (build {build}.{self.data['ubr']})", "ok")
        if blocking:
            log(f"{len(blocking)} requisiti bloccanti rilevati", "warn")


SCANNER = SystemScanner()
