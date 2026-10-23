"""
W11 Update Flow - Download ISO ufficiale Windows 11 (64 bit, Italiano)
direttamente dai server Microsoft, senza aprire il sito.

Il flusso replica le chiamate della pagina ufficiale
https://www.microsoft.com/it-it/software-download/windows11
(tecnica documentata dal progetto open source Fido di Pete Batard, GPLv3).

Created by Alex Lignola - (c) 2026 W11 Update Flow - All rights reserved.
"""
from __future__ import annotations

import email.utils
import http.cookiejar
import json
import re
import threading
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path

from .core import SETTINGS, human_size, iso_dir, log

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36 Edg/141.0.0.0")
MS_PAGE = "https://www.microsoft.com/{loc}/software-download/windows11"
REFERER = "https://www.microsoft.com/software-download/windows11"
ORG_ID = "y6jn8c31"
PROFILE_ID = "606624d44113"
INSTANCE_ID = "560dc9f3-1aa5-4a2f-b63c-9e18f8d0e175"
FIDO_RAW = "https://raw.githubusercontent.com/pbatard/Fido/master/Fido.ps1"
FALLBACK_EDITION_IDS = ["3813", "3262", "3113"]
LANGUAGE = "Italian"
LOCALE = "it-IT"

BUILD_TO_RELEASE = {
    "22000": "21H2", "22621": "22H2", "22631": "23H2", "26100": "24H2",
    "26200": "25H2", "26300": "26H2", "26400": "27H2", "26500": "28H2",
    "26600": "29H2", "26700": "30H2",
}


def release_from_build(build: str) -> str:
    b_str = str(build).split(".")[0].strip()
    if b_str in BUILD_TO_RELEASE:
        return BUILD_TO_RELEASE[b_str]
    try:
        b_num = int(b_str)
        if b_num >= 26100:
            offset = (b_num - 26100) // 100
            return f"{24 + offset}H2"
    except Exception:
        pass
    return f"Build {build}" if build else "—"


def parse_iso_name(name: str) -> dict:
    """Estrae build/release/lingua/arch dal nome del file ISO Microsoft."""
    info = {"build": "", "release": "", "arch": "", "lang": ""}
    m = re.search(r"_(\d{5})[._]", name)
    if m:
        info["build"] = m.group(1)
        info["release"] = release_from_build(m.group(1))
    m = re.search(r"(\d{2}H\d)", name, re.I)
    if m:
        info["release"] = m.group(1).upper()
    if re.search(r"x64|amd64", name, re.I):
        info["arch"] = "x64"
    elif re.search(r"arm64", name, re.I):
        info["arch"] = "ARM64"
    m = re.search(r"_([a-z]{2}-[a-z]{2})_", name, re.I)
    if m:
        info["lang"] = m.group(1).lower()
    elif "ital" in name.lower():
        info["lang"] = "it-it"
    return info


def _release_key(release: str) -> tuple[int, int]:
    """'25H2' -> (25, 2) per confronti ordinati; (0, 0) se sconosciuta."""
    m = re.match(r"(\d{2})H(\d)", release or "", re.I)
    return (int(m.group(1)), int(m.group(2))) if m else (0, 0)


def compare_iso_with_target(iso_dict: dict, target_dict: dict | None = None) -> dict:
    """Confronta una ISO (locale o esterna) con la versione obiettivo di Windows 11.

    Restituisce:
    - is_outdated: bool (True se la ISO è precedente alla versione obiettivo)
    - local_release: str
    - local_build: str
    - target_release: str
    - target_build: str
    - status: 'outdated' | 'uptodate' | 'newer' | 'unknown'
    - message: str
    """
    if not target_dict:
        try:
            target_dict = TARGET_CHECKER.snapshot()
        except Exception:
            target_dict = {}

    tgt_rel = (target_dict or {}).get("release") or "26H2"
    tgt_bld = str((target_dict or {}).get("build") or (target_dict or {}).get("base_build") or "0").split(".")[0]

    loc_rel = iso_dict.get("release") or ""
    loc_bld = str(iso_dict.get("build") or "0").split(".")[0]

    rk_loc = _release_key(loc_rel)
    rk_tgt = _release_key(tgt_rel)

    bld_loc = int(loc_bld) if loc_bld.isdigit() else 0
    bld_tgt = int(tgt_bld) if tgt_bld.isdigit() else 0

    is_outdated = False
    status = "uptodate"

    if rk_loc != (0, 0) and rk_tgt != (0, 0):
        if rk_loc < rk_tgt:
            is_outdated = True
            status = "outdated"
        elif rk_loc > rk_tgt:
            status = "newer"
        elif bld_loc and bld_tgt and bld_loc < bld_tgt:
            is_outdated = True
            status = "outdated"
    elif bld_loc and bld_tgt:
        if bld_loc < bld_tgt:
            is_outdated = True
            status = "outdated"
        elif bld_loc > bld_tgt:
            status = "newer"

    if is_outdated:
        msg = f"La ISO presente ({loc_rel or 'Build ' + loc_bld}) è precedente alla versione obiettivo ({tgt_rel})."
    elif status == "newer":
        msg = f"La ISO presente ({loc_rel or 'Build ' + loc_bld}) è più recente dell'obiettivo standard ({tgt_rel})."
    else:
        msg = f"La ISO presente ({loc_rel or tgt_rel}) è allineata all'ultima versione stabile ufficiale ({tgt_rel})."

    return {
        "is_outdated": is_outdated,
        "status": status,
        "local_release": loc_rel,
        "local_build": loc_bld,
        "target_release": tgt_rel,
        "target_build": tgt_bld,
        "message": msg,
    }


def local_isos() -> list[Path]:
    """ISO complete presenti nella cartella ISO, dalla più recente alla più vecchia."""
    try:
        files = [p for p in iso_dir().glob("*.iso") if p.is_file() and p.stat().st_size > 1024 ** 3]
    except Exception:
        return []
    files.sort(key=lambda p: (_release_key(parse_iso_name(p.name)["release"]), p.stat().st_mtime),
               reverse=True)
    return files


def _is_newer(remote: dict, local: dict, remote_name: str, local_name: str) -> bool:
    """Confronta release (es. 24H2 vs 25H2), poi build, poi nome file (es. ...x64v2.iso)."""
    rk, lk = _release_key(remote.get("release", "")), _release_key(local.get("release", ""))
    if rk != (0, 0) and lk != (0, 0) and rk != lk:
        return rk > lk
    rb = str(remote.get("build") or "").split(".")[0].strip()
    lb = str(local.get("build") or "").split(".")[0].strip()
    if rb.isdigit() and lb.isdigit() and int(rb) != int(lb):
        return int(rb) > int(lb)
    return remote_name.lower() != local_name.lower()


def _remote_meta(url: str) -> tuple[int, str]:
    """Dimensione e data (Last-Modified) della ISO remota senza scaricarla."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Range": "bytes=0-0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            size = 0
            m = re.search(r"/(\d+)\s*$", resp.headers.get("Content-Range") or "")
            if m:
                size = int(m.group(1))
            elif resp.status == 200:
                size = int(resp.headers.get("Content-Length") or 0)
            date = ""
            lm = resp.headers.get("Last-Modified")
            if lm:
                try:
                    date = email.utils.parsedate_to_datetime(lm).strftime("%d/%m/%Y")
                except Exception:
                    date = lm
            return size, date
    except Exception as exc:
        log(f"Metadati ISO remota non disponibili: {exc}", "warn")
        return 0, ""


class MicrosoftApiError(RuntimeError):
    pass


class _Http:
    def __init__(self):
        self.jar = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.jar))

    def get(self, url: str, referer: str | None = None, timeout: int = 30) -> str:
        headers = {"User-Agent": UA, "Accept-Language": "it-IT,it;q=0.9,en;q=0.8"}
        if referer:
            headers["Referer"] = referer
        req = urllib.request.Request(url, headers=headers)
        with self.opener.open(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", "replace")


def _edition_ids(http: _Http) -> list[str]:
    """Trova l'ID edizione più recente: pagina Microsoft -> Fido -> fallback."""
    ids: list[str] = []
    try:
        page = http.get(MS_PAGE.format(loc="it-it"))
        ids = re.findall(r'<option[^>]*value="(\d{3,5})"', page)
    except Exception as exc:
        log(f"Pagina Microsoft non leggibile: {exc}", "warn")
    if not ids:
        try:
            src = http.get(FIDO_RAW, timeout=15)
            m = re.search(r'"Windows 11 Home/Pro/Edu",\s*@\((\d+)', src)
            if m:
                ids = [m.group(1)]
        except Exception:
            pass
    seen, out = set(), []
    for i in ids + FALLBACK_EDITION_IDS:
        if i not in seen:
            seen.add(i)
            out.append(i)
    return out


def resolve_iso_link() -> dict:
    """Restituisce {url, filename, expires, build, release} per Win11 x64 Italiano."""
    http = _Http()
    log("Connessione ai server Microsoft…")
    last_error = "Impossibile ottenere il link"
    for edition in _edition_ids(http):
        sid = str(uuid.uuid4())
        try:
            # 1) whitelisting della sessione
            http.get(f"https://vlscppe.microsoft.com/tags?org_id={ORG_ID}&session_id={sid}")
            # 2) handshake ov-df
            js = http.get(f"https://ov-df.microsoft.com/mdt.js?instanceId={INSTANCE_ID}&PageId=si&session_id={sid}")
            w = re.search(r"[?&]w=([A-F0-9]+)", js)
            rt = re.search(r'rticks\="\+?(\d+)', js)
            if w and rt:
                http.get(f"https://ov-df.microsoft.com/?session_id={sid}&CustomerId={INSTANCE_ID}"
                         f"&PageId=si&w={w.group(1)}&mdt={int(time.time() * 1000)}&rticks={rt.group(1)}")
            # 3) SKU per lingua
            sku_id = None
            for attempt in range(3):
                data = json.loads(http.get(
                    "https://www.microsoft.com/software-download-connector/api/getskuinformationbyproductedition"
                    f"?profile={PROFILE_ID}&productEditionId={edition}&SKU=undefined"
                    f"&friendlyFileName=undefined&Locale={LOCALE}&sessionID={sid}"))
                if data.get("Errors"):
                    last_error = data["Errors"][0].get("Value", "Errore SKU")
                    time.sleep(2)
                    continue
                for sku in data.get("Skus", []):
                    if sku.get("Language") == LANGUAGE:
                        sku_id = sku.get("Id")
                break
            if not sku_id:
                continue
            log(f"Edizione {edition} · SKU italiano {sku_id}")
            # 4) link di download
            data = json.loads(http.get(
                "https://www.microsoft.com/software-download-connector/api/GetProductDownloadLinksBySku"
                f"?profile={PROFILE_ID}&productEditionId=undefined&SKU={sku_id}"
                f"&friendlyFileName=undefined&Locale={LOCALE}&sessionID={sid}", referer=REFERER))
            errors = data.get("Errors") or (data.get("ValidationContainer") or {}).get("Errors")
            if errors:
                if errors[0].get("Type") == 9:
                    raise MicrosoftApiError(
                        "Microsoft ha temporaneamente bloccato le richieste da questo indirizzo IP "
                        "(codice 715-123130). Riprova più tardi o cambia rete.")
                last_error = errors[0].get("Value", "Errore link")
                continue
            for opt in data.get("ProductDownloadOptions", []):
                if opt.get("DownloadType") == 1:  # x64
                    url = opt["Uri"]
                    filename = url.split("?")[0].rsplit("/", 1)[-1]
                    info = parse_iso_name(filename)
                    log(f"Link ufficiale ottenuto: {filename}", "ok")
                    if info.get("release"):
                        try:
                            TARGET_CHECKER.update_from_source(info["release"], info.get("build", ""), "ms_download_api")
                        except Exception:
                            pass
                    return {"url": url, "filename": filename,
                            "expires": data.get("DownloadExpirationDatetime", ""),
                            "build": info["build"], "release": info["release"]}
        except MicrosoftApiError:
            raise
        except Exception as exc:
            last_error = str(exc)
            log(f"Tentativo edizione {edition} fallito: {exc}", "warn")
    raise MicrosoftApiError(last_error)


class IsoDownloader:
    CHUNK = 1024 * 1024

    def __init__(self):
        self._lock = threading.Lock()
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._cancel = False
        self._check_seq = 0
        self.check: dict = {"id": 0, "state": "idle"}  # idle|checking|newer|uptodate|missing|error
        self._replace_path: str | None = None
        self.reset()
        self._detect_partial()

    def _detect_partial(self):
        try:
            parts = sorted(iso_dir().glob("*.iso.part"), key=lambda p: p.stat().st_mtime, reverse=True)
            if parts:
                p = parts[0]
                self.filename = p.name[:-5]
                self.done = p.stat().st_size
                info = parse_iso_name(self.filename)
                self.release, self.build = info["release"], info["build"]
                self.state = "paused"
        except Exception:
            pass

    def reset(self):
        self.state = "idle"      # idle|resolving|downloading|paused|done|error|cancelled
        self.filename = ""
        self.path = ""
        self.total = 0
        self.done = 0
        self.speed = 0.0
        self.eta = 0
        self.error = ""
        self.release = ""
        self.build = ""
        self._link: dict | None = getattr(self, "_link", None)

    # ------------------------------------------------------------------ API
    def snapshot(self) -> dict:
        pct = (self.done / self.total * 100) if self.total else 0
        return {
            "state": self.state, "filename": self.filename, "path": self.path,
            "total": self.total, "done": self.done, "percent": round(pct, 2),
            "speed": self.speed, "speed_h": human_size(self.speed) + "/s" if self.speed else "—",
            "done_h": human_size(self.done), "total_h": human_size(self.total) if self.total else "—",
            "eta": self.eta, "error": self.error, "release": self.release, "build": self.build,
            "check": dict(self.check),
        }

    def has_local_iso(self) -> bool:
        return bool(local_isos())

    def check_update(self) -> bool:
        """Avvia in background il confronto tra la ISO locale e quella sul sito Microsoft."""
        with self._lock:
            if (self._thread and self._thread.is_alive()) or self.check.get("state") == "checking":
                return False
            self._check_seq += 1
            self.check = {"id": self._check_seq, "state": "checking"}
            threading.Thread(target=self._run_check, daemon=True).start()
            return True

    def start(self, replace: bool = False, replace_path: str | None = None) -> bool:
        with self._lock:
            if self._thread and self._thread.is_alive():
                return False
            if replace:
                if replace_path and Path(replace_path).exists():
                    self._replace_path = str(replace_path)
                else:
                    self._replace_path = self.check.get("local_path") or None
                    if not self._replace_path:
                        locals_ = local_isos()
                        if locals_:
                            self._replace_path = str(locals_[0])
            elif self.state != "paused":
                self._replace_path = None
            self._stop.clear()
            self._cancel = False
            self.error = ""
            self._thread = threading.Thread(target=self._run, daemon=True)
            self._thread.start()
            return True

    def pause(self):
        if self.state == "downloading":
            self._stop.set()

    def cancel(self):
        self._cancel = True
        self._stop.set()
        if not (self._thread and self._thread.is_alive()):
            self._cleanup_part()
            self.reset()
            self.state = "cancelled"

    # -------------------------------------------------------------- interni
    def _cleanup_part(self):
        if self.filename:
            part = iso_dir() / (self.filename + ".part")
            try:
                part.unlink(missing_ok=True)
            except Exception:
                pass

    def _run_check(self):
        cid = self.check["id"]
        try:
            locals_ = local_isos()
            if not locals_:
                self.check = {"id": cid, "state": "missing"}
                return
            log("Verifica presenza di una ISO più recente sul sito Microsoft…")
            link = resolve_iso_link()
            link["_ts"] = time.time()
            self._link = link
            remote_name = link["filename"]
            same = next((p for p in locals_ if p.name.lower() == remote_name.lower()), None)
            local = same or locals_[0]
            lst = local.stat()
            linfo = parse_iso_name(local.name)
            rsize, rdate = _remote_meta(link["url"])
            if same:
                # stesso nome file: Microsoft può ripubblicarlo aggiornato -> confronta la dimensione
                newer = bool(rsize) and rsize != lst.st_size
            else:
                newer = _is_newer(link, linfo, remote_name, local.name)
            self.check = {
                "id": cid, "state": "newer" if newer else "uptodate",
                "local_path": str(local), "local_name": local.name,
                "local_release": linfo["release"] or "—", "local_size_h": human_size(lst.st_size),
                "local_date": time.strftime("%d/%m/%Y", time.localtime(lst.st_mtime)),
                "remote_name": remote_name, "remote_release": link.get("release") or "—",
                "remote_size_h": human_size(rsize) if rsize else "—", "remote_date": rdate or "—",
            }
            if newer:
                log(f"Disponibile una ISO più aggiornata: {remote_name} (locale: {local.name})", "warn")
            else:
                log(f"La ISO locale è già la più recente: {local.name}", "ok")
        except Exception as exc:
            self.check = {"id": cid, "state": "error", "error": str(exc)}
            log(f"Verifica aggiornamento ISO non riuscita: {exc}", "error")

    def _finalize(self, final: Path):
        """Dopo un download riuscito: seleziona la nuova ISO ed elimina la vecchia (se richiesto)."""
        try:
            SETTINGS.set("selected_iso", str(final))
        except Exception:
            pass
        old, self._replace_path = self._replace_path, None
        if not old:
            return
        old_p = Path(old)
        try:
            if old_p.exists() and old_p.resolve() != final.resolve():
                old_p.unlink()
                log(f"Vecchia ISO eliminata: {old_p.name}", "ok")
        except Exception as exc:
            log(f"Impossibile eliminare la vecchia ISO {old_p.name} (è montata o in uso?): {exc}", "warn")

    def _link_valid(self) -> bool:
        if not self._link:
            return False
        return time.time() - self._link.get("_ts", 0) < 20 * 3600

    def _run(self):
        try:
            if not self._link_valid():
                self.state = "resolving"
                link = resolve_iso_link()
                link["_ts"] = time.time()
                self._link = link
            link = self._link
            self.filename = link["filename"]
            self.release = link.get("release", "")
            self.build = link.get("build", "")
            final = iso_dir() / self.filename
            replacing_same = bool(self._replace_path) and Path(self._replace_path).name.lower() == final.name.lower()
            if final.exists() and final.stat().st_size > 1024 ** 3 and not replacing_same:
                self.total = self.done = final.stat().st_size
                self.path = str(final)
                self.state = "done"
                log(f"ISO già presente: {final.name}", "ok")
                return
            self._download(link["url"], final)
        except Exception as exc:
            self.state = "error"
            self.error = str(exc)
            log(f"Download non riuscito: {exc}", "error")

    def _download(self, url: str, final: Path):
        part = final.with_name(final.name + ".part")
        self.state = "downloading"
        retries = 0
        log(f"Download in corso in {final.parent}")
        while True:
            offset = part.stat().st_size if part.exists() else 0
            headers = {"User-Agent": UA}
            if offset:
                headers["Range"] = f"bytes={offset}-"
            try:
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=45) as resp:
                    if offset and resp.status != 206:
                        offset = 0  # il server non supporta resume
                    length = int(resp.headers.get("Content-Length") or 0)
                    self.total = offset + length
                    self.done = offset
                    mode = "ab" if offset else "wb"
                    t0, b0 = time.time(), self.done
                    with open(part, mode) as fh:
                        while True:
                            if self._stop.is_set():
                                break
                            chunk = resp.read(self.CHUNK)
                            if not chunk:
                                break
                            fh.write(chunk)
                            self.done += len(chunk)
                            dt = time.time() - t0
                            if dt >= 1.0:
                                inst = (self.done - b0) / dt
                                self.speed = inst if not self.speed else self.speed * 0.6 + inst * 0.4
                                self.eta = int((self.total - self.done) / self.speed) if self.speed else 0
                                t0, b0 = time.time(), self.done
                if self._stop.is_set():
                    self.speed = 0
                    if self._cancel:
                        self._cleanup_part()
                        name = self.filename
                        self.reset()
                        self.state = "cancelled"
                        log(f"Download annullato ({name})", "warn")
                    else:
                        self.state = "paused"
                        log("Download in pausa", "warn")
                    return
                if self.total and self.done < self.total:
                    raise IOError("Connessione interrotta")
                part.replace(final)
                self.path = str(final)
                self.speed = 0
                self.eta = 0
                self.state = "done"
                log(f"ISO scaricata: {final.name} ({human_size(self.total)})", "ok")
                self._finalize(final)
                return
            except urllib.error.HTTPError as exc:
                if exc.code in (403, 410):
                    # link scaduto: ne richiede uno nuovo
                    log("Link scaduto, ne richiedo uno nuovo…", "warn")
                    self._link = resolve_iso_link()
                    self._link["_ts"] = time.time()
                    url = self._link["url"]
                    continue
                if exc.code == 416:
                    part.replace(final)
                    self.path = str(final)
                    self.state = "done"
                    self._finalize(final)
                    return
                raise
            except (urllib.error.URLError, IOError, TimeoutError) as exc:
                retries += 1
                if retries > 8:
                    raise
                log(f"Rete instabile ({exc}), riprovo tra {min(retries * 3, 15)}s… [{retries}/8]", "warn")
                time.sleep(min(retries * 3, 15))


DOWNLOADER = IsoDownloader()


class TargetVersionChecker:
    """Verifica e traccia dinamicamente l'ultima versione stabile ufficiale di Windows 11.

    Interroga i canali ufficiali Microsoft (Learn Release Information e pagina di Download)
    in modo che l'obiettivo dell'applicazione sia sempre e automaticamente l'ultima release
    stabile (es. 26H2, 27H2, 28H2...), senza hardcoding di versioni statiche.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._thread: threading.Thread | None = None
        self.state = "idle"  # idle | checking | done | error
        self.release = SETTINGS.get("cached_target_release") or "26H2"
        self.build = SETTINGS.get("cached_target_build") or "26300"
        self.date = SETTINGS.get("cached_target_date") or ""
        self.source = "cache" if SETTINGS.get("cached_target_release") else "fallback"
        self.error = ""
        self.checked_at = 0.0

    def snapshot(self) -> dict:
        subtitle = f"Build {self.build} · Ufficiale Microsoft" if self.build else "Ultima build ufficiale Microsoft"
        return {
            "state": self.state,
            "release": self.release,
            "build": self.build,
            "date": self.date,
            "source": self.source,
            "error": self.error,
            "title": f"Windows 11 {self.release}",
            "subtitle": subtitle,
            "checked_at": time.strftime("%H:%M", time.localtime(self.checked_at)) if self.checked_at else "",
        }

    def check_async(self, force: bool = False):
        with self._lock:
            if not force and self.state == "done" and (time.time() - self.checked_at < 600):
                return
            if self._thread and self._thread.is_alive():
                return
            self.state = "checking"
            self._thread = threading.Thread(target=self._run, daemon=True)
            self._thread.start()

    def update_from_source(self, release: str, build: str = "", source: str = "ms_download_api"):
        if not release:
            return
        with self._lock:
            if _release_key(release) >= _release_key(self.release):
                self.release = release
                if build:
                    self.build = build
                self.source = source
                self.state = "done"
                self.checked_at = time.time()
                SETTINGS.set("cached_target_release", self.release)
                if self.build:
                    SETTINGS.set("cached_target_build", self.build)

    def _run(self):
        log("Verifica ultima versione stabile Windows 11 sul sito Microsoft…")
        http = _Http()
        discovered: list[dict] = []

        # 1. Pagina ufficiale Microsoft Learn - Windows 11 Release Information (servicing channels)
        for url in [
            "https://learn.microsoft.com/en-us/windows/release-health/windows11-release-information",
            "https://learn.microsoft.com/it-it/windows/release-health/windows11-release-information",
        ]:
            try:
                html = http.get(url, timeout=15)
                table_match = re.search(
                    r'<h4 id="servicing-channels"[^>]*>.*?</h4>\s*<table>(.*?)</table>',
                    html, re.S | re.I
                )
                if not table_match:
                    table_match = re.search(r'<table>(.*?)</table>', html, re.S)
                if table_match:
                    rows = re.findall(r'<tr[^>]*>(.*?)</tr>', table_match.group(1), re.S)
                    for r in rows:
                        cells = [re.sub(r'<[^>]+>', '', c).strip() for c in re.findall(r'<td[^>]*>(.*?)</td>', r, re.S)]
                        if len(cells) >= 8:
                            ver, channel, avail, end_home, end_ent, update, rev_date, bld = cells[:8]
                            m = re.match(r'^(\d{2}H\d)$', ver.strip(), re.I)
                            if m and ("general availability" in channel.lower() or "disponibilit" in channel.lower()):
                                rel_clean = m.group(1).upper()
                                base_bld = bld.split(".")[0]
                                if base_bld.isdigit():
                                    BUILD_TO_RELEASE[base_bld] = rel_clean
                                discovered.append({
                                    "release": rel_clean,
                                    "build": bld,
                                    "date": avail,
                                    "source": "ms_release_health",
                                })
                if discovered:
                    break
            except Exception as exc:
                log(f"Controllo Microsoft Release Information ({url}): {exc}", "warn")

        # 2. Pagina ufficiale di download Microsoft Windows 11
        try:
            html = http.get(MS_PAGE.format(loc="it-it"), timeout=15)
            m = re.search(r'(?:Versione corrente|Current release)[^<\n]*\b(\d{2}H\d)\b', html, re.I)
            if m:
                rel_clean = m.group(1).upper()
                discovered.append({
                    "release": rel_clean,
                    "build": "",
                    "date": "",
                    "source": "ms_download_page",
                })
        except Exception as exc:
            log(f"Controllo pagina download Microsoft fallito: {exc}", "warn")

        # 3. Considera anche eventuali ISO già scaricate localmente
        for iso_p in local_isos():
            linfo = parse_iso_name(iso_p.name)
            if linfo.get("release"):
                discovered.append({
                    "release": linfo["release"],
                    "build": linfo.get("build", ""),
                    "date": "",
                    "source": "local_iso",
                })

        # 4. Determina l'obiettivo più recente
        with self._lock:
            if discovered:
                discovered.sort(key=lambda x: _release_key(x["release"]), reverse=True)
                best = discovered[0]
                if not best.get("build"):
                    for d in discovered:
                        if d.get("release") == best["release"] and d.get("build"):
                            best["build"] = d["build"]
                            break
                if not best.get("build"):
                    for b_k, r_v in BUILD_TO_RELEASE.items():
                        if r_v == best["release"]:
                            best["build"] = b_k
                            break

                self.release = best["release"]
                if best.get("build"):
                    self.build = best["build"]
                if best.get("date"):
                    self.date = best["date"]
                self.source = best.get("source", "microsoft")
                self.state = "done"
                self.checked_at = time.time()
                self.error = ""

                SETTINGS.set("cached_target_release", self.release)
                SETTINGS.set("cached_target_build", self.build)
                if self.date:
                    SETTINGS.set("cached_target_date", self.date)

                log(f"Ultima versione stabile Windows 11 rilevata da Microsoft: {self.release} (build {self.build})", "ok")
            else:
                self.state = "error"
                self.error = "Nessuna informazione ricevuta da Microsoft"
                log(f"Controllo versione Microsoft non riuscito, uso fallback: {self.release}", "warn")


TARGET_CHECKER = TargetVersionChecker()

