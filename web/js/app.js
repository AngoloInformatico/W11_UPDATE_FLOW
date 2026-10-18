/**
 * W11 Update Flow - Frontend Logic
 * Created by Alex Lignola - © 2026 W11 Update Flow - All rights reserved.
 * https://www.youtube.com/@AngoloInformatico
 * https://github.com/AngoloInformatico
 */

(function () {
  "use strict";

  const TOKEN = window.__W11UF_TOKEN__ ||
    (document.querySelector('meta[name="w11uf-token"]') || {}).content || "";

  let lastLogId = 0;
  let currentState = null;
  let pollTimer = null;
  let currentView = "dashboard";
  let lastCheckId = null; // ultimo esito di verifica aggiornamento ISO già mostrato

  // ---------------------------------------------------------------------------
  // API Helper
  // ---------------------------------------------------------------------------
  async function api(path, method = "GET", body = null) {
    const opts = {
      method,
      headers: {
        "X-W11UF-Token": TOKEN,
        "Content-Type": "application/json",
      },
    };
    if (body) {
      opts.body = JSON.stringify(body);
    }
    const res = await fetch(path, opts);
    if (!res.ok) {
      throw new Error(`HTTP ${res.status}`);
    }
    return await res.json();
  }

  // ---------------------------------------------------------------------------
  // Toasts
  // ---------------------------------------------------------------------------
  function toast(msg, type = "info") {
    const container = document.getElementById("toasts");
    if (!container) return;
    const el = document.createElement("div");
    el.className = `toast ${type === "error" ? "err" : ""}`;
    el.innerHTML = `
      <svg class="icon"><polyline points="20 6 9 17 4 12"/></svg>
      <div>${msg}</div>
    `;
    container.appendChild(el);
    setTimeout(() => {
      el.classList.add("out");
      setTimeout(() => el.remove(), 320);
    }, 4000);
  }

  // ---------------------------------------------------------------------------
  // Navigation & View Switching
  // ---------------------------------------------------------------------------
  const VIEW_TITLES = {
    dashboard: { title: "Dashboard", sub: "Flusso di aggiornamento e stato del sistema" },
    compat: { title: "Verifica Compatibilità PC", sub: "Rilevamento componenti hardware e requisiti aggirati" },
    download: { title: "Download ISO Ufficiale", sub: "Scaricamento diretto da server Microsoft e gestione archivio" },
    upgrade: { title: "Avvio Aggiornamento", sub: "Iniezione stringhe di bypass ed esecuzione guidata" },
    tools: { title: "Strumenti & Utility", sub: "Punto di ripristino, rimozione watermark, estensione rollback e diagnostica" },
    logs: { title: "Console & Registri", sub: "Flusso eventi in tempo reale e comandi di sistema eseguiti" },
    about: { title: "Informazioni", sub: "Dettagli sul progetto, canali ufficiali e copyright" },
  };

  function switchView(viewName) {
    if (!VIEW_TITLES[viewName]) return;
    currentView = viewName;

    // Toggle Nav buttons
    document.querySelectorAll(".nav-item").forEach((btn) => {
      btn.classList.toggle("active", btn.dataset.view === viewName);
    });

    // Toggle Views
    document.querySelectorAll(".view").forEach((view) => {
      view.classList.toggle("active", view.id === `view-${viewName}`);
    });

    // Update Topbar
    const info = VIEW_TITLES[viewName];
    document.getElementById("crumb-title").textContent = info.title;
    document.getElementById("crumb-sub").textContent = info.sub;
  }

  // ---------------------------------------------------------------------------
  // Rendering: System & Hardware
  // ---------------------------------------------------------------------------
  function renderSystem(sys, state) {
    if (!sys || Object.keys(sys).length === 0) return;

    // Admin badge
    const adminEl = document.getElementById("admin-text");
    const adminBadge = document.getElementById("admin-badge");
    if (currentState && currentState.app) {
      const isAdmin = currentState.app.admin;
      adminEl.textContent = isAdmin ? "Amministratore (Attivo)" : "Utente Standard (Limitato)";
      adminBadge.style.color = isAdmin ? "var(--ok)" : "var(--warn)";
    }

    // Topbar Pill
    const pillHw = document.getElementById("pill-hw-text");
    const pillDot = document.getElementById("pill-hw-dot");
    if (sys.ready) {
      pillHw.textContent = "PC Idoneo per Bypass";
      pillDot.className = "badge-dot ok";
    } else {
      pillHw.textContent = `${sys.blocking} Requisiti Bloccanti`;
      pillDot.className = "badge-dot err";
    }

    // Version Path in Hero
    const fromEl = document.getElementById("vp-from");
    const fromBuildEl = document.getElementById("vp-from-build");
    const currVer = sys.display || "Win 11";
    fromEl.textContent = currVer;
    fromBuildEl.textContent = `Build ${sys.build}${sys.ubr ? "." + sys.ubr : ""}`;

    // Target Version
    const targetEl = document.getElementById("vp-to");
    targetEl.textContent = "25H2 / 26H2";

    // Dashboard mini summary
    const setKV = (id, val) => {
      const el = document.getElementById(id);
      if (el) el.textContent = val || "—";
    };
    setKV("d-model", sys.model);
    setKV("d-cpu", sys.cpu);
    const sseCheck = (sys.checks || []).find((c) => c.key === "cpu");
    setKV("d-sse", sseCheck ? sseCheck.value : "—");
    setKV("d-ram", sys.ram_h);
    setKV("d-disk", `${sys.disk_free_h} liberi su C:`);
    const tpmCheck = (sys.checks || []).find((c) => c.key === "tpm");
    setKV("d-tpm", tpmCheck ? tpmCheck.value : "—");
    const sbCheck = (sys.checks || []).find((c) => c.key === "secureboot");
    setKV("d-sb", sbCheck ? `${sbCheck.value} (${sys.firmware || "UEFI"})` : "—");

    // Full Compatibility View
    setKV("c-os", sys.product);
    setKV("c-build", `${sys.build}.${sys.ubr} (${sys.display})`);
    setKV("c-lang", sys.lang);
    setKV("c-arch", sys.osarch || "x64 (64-bit)");
    setKV("c-model", sys.model);
    setKV("c-bios", sys.biosyear);
    setKV("c-cpu", sys.cpu);
    setKV("c-cores", `${sys.cores} Core / ${sys.threads} Thread logici`);
    setKV("c-ram", sys.ram_h);
    setKV("c-disk", `${sys.disk_free_h} liberi (Totale: ${sys.disk_total_h})`);
    const blCheck = (sys.checks || []).find((c) => c.key === "bitlocker");
    setKV("c-bl", blCheck ? blCheck.value : "—");
    const pendingCheck = (sys.checks || []).find((c) => c.key === "pending");
    setKV("c-reboot", pendingCheck ? pendingCheck.value : "No");

    // Checks Container in compat view
    const checksBox = document.getElementById("checks-container");
    if (checksBox && sys.checks) {
      checksBox.innerHTML = sys.checks
        .map((c) => {
          let badgeClass = "ok";
          let badgeText = "SODDISFATTO";
          if (c.status === "fail") {
            badgeClass = "fail";
            badgeText = "NON IDONEO";
          } else if (c.status === "warn") {
            badgeClass = "warn";
            badgeText = "ATTENZIONE";
          } else if (c.status === "bypass") {
            badgeClass = "bypass";
            badgeText = "AGGIRATO CON BYPASS";
          }
          return `
            <div class="check ${c.status}">
              <div class="check-ico">
                <svg class="icon"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
              </div>
              <div>
                <div class="check-label">${c.label}</div>
                <div class="check-hint">${c.hint || "Controllo compatibilità hardware di Windows 11."}</div>
              </div>
              <div class="check-val">
                <div>${c.value}</div>
                <span class="tag ${badgeClass}">${badgeText}</span>
              </div>
            </div>
          `;
        })
        .join("");
    }

    // Step 1 status on Flow Card
    const s1Tag = document.getElementById("flow-s1-tag");
    const s1Card = document.getElementById("flow-step-1");
    if (sys.ready) {
      s1Tag.className = "tag ok";
      s1Tag.textContent = "Pronto";
      s1Card.className = "step done";
    } else {
      s1Tag.className = "tag fail";
      s1Tag.textContent = `${sys.blocking} Bloccanti`;
      s1Card.className = "step";
    }

    // Update Readiness Ring
    updateRing(sys);
  }

  // ---------------------------------------------------------------------------
  // Readiness Ring
  // ---------------------------------------------------------------------------
  function updateRing(sys) {
    let score = 25; // base system scanner ok
    if (sys && sys.ready) score += 35; // hardware ready for bypass
    if (currentState && currentState.selected_iso) score += 20; // ISO ready
    if (currentState && currentState.upgrade && currentState.upgrade.state === "launched") {
      score = 100;
    } else if (currentState && currentState.selected_iso && sys && sys.ready) {
      score = 90;
    }

    const valEl = document.getElementById("ring-val");
    const capEl = document.getElementById("ring-cap");
    const bar = document.getElementById("ring-bar");
    if (valEl) valEl.innerHTML = `${score}<small>%</small>`;
    if (capEl) {
      capEl.textContent = score >= 90 ? "Pronto per l'aggiornamento" : "Passaggi preliminari…";
    }
    if (bar) {
      const circ = 2 * Math.PI * 50; // 314.16
      const offset = circ - (circ * score) / 100;
      bar.style.strokeDashoffset = offset;
    }
  }

  // ---------------------------------------------------------------------------
  // Rendering: Download & ISOs
  // ---------------------------------------------------------------------------
  function renderDownload(dl, isos, selectedIso) {
    if (!dl) return;

    // ISO directory path
    const dlPathEl = document.getElementById("dl-folder-path");
    if (dlPathEl && currentState.app) {
      dlPathEl.textContent = currentState.app.iso_dir;
    }

    // Topbar Pill
    const pillIso = document.getElementById("pill-iso-text");
    if (selectedIso) {
      const fname = selectedIso.split(/[\\/]/).pop();
      pillIso.textContent = fname;
    } else if (isos && isos.length > 0) {
      pillIso.textContent = isos[0].name;
    } else {
      pillIso.textContent = "Nessuna ISO";
    }

    // Download Hero Stats
    const stState = document.getElementById("st-state");
    const stDone = document.getElementById("st-done");
    const stSpeed = document.getElementById("st-speed");
    const stEta = document.getElementById("st-eta");
    const barFill = document.getElementById("dl-progress-fill");
    const barBox = document.getElementById("dl-progress-bar");

    const btnAction = document.getElementById("btn-dl-action");
    const btnText = document.getElementById("btn-dl-text");
    const btnPause = document.getElementById("btn-dl-pause");
    const btnCancel = document.getElementById("btn-dl-cancel");

    // Flow Step 2 & Hero button
    const s2Tag = document.getElementById("flow-s2-tag");
    const s2Card = document.getElementById("flow-step-2");
    const heroDlBtn = document.getElementById("btn-hero-download");
    const heroDlBtnText = document.getElementById("btn-hero-download-text");

    if (dl.state === "downloading") {
      stState.textContent = `Scaricamento (${dl.percent}%)`;
      stDone.textContent = `${dl.done_h} / ${dl.total_h}`;
      stSpeed.textContent = dl.speed_h;
      stEta.textContent = dl.eta > 0 ? `${Math.round(dl.eta / 60)} min rimasti` : "Calcolo…";
      barFill.style.width = `${dl.percent}%`;
      barBox.className = "progress lg";

      btnText.textContent = "Download in corso…";
      btnAction.disabled = true;
      btnPause.style.display = "inline-flex";
      btnCancel.style.display = "inline-flex";

      s2Tag.className = "tag live";
      s2Tag.textContent = `${dl.percent}%`;
      s2Card.className = "step current";

      if (heroDlBtnText) heroDlBtnText.textContent = `Scaricamento ${dl.percent}%`;
    } else if (dl.state === "resolving") {
      stState.textContent = "Connessione server Microsoft…";
      barBox.className = "progress lg indeterminate";
      btnText.textContent = "Risoluzione link…";
      btnAction.disabled = true;
      btnPause.style.display = "none";
      btnCancel.style.display = "inline-flex";

      s2Tag.className = "tag warn";
      s2Tag.textContent = "Connessione…";
      s2Card.className = "step current";
    } else if (dl.state === "paused") {
      stState.textContent = "In pausa";
      stDone.textContent = `${dl.done_h} / ${dl.total_h}`;
      stSpeed.textContent = "—";
      stEta.textContent = "Pausa";
      barBox.className = "progress lg paused";

      btnText.textContent = "Riprendi Scaricamento";
      btnAction.disabled = false;
      btnPause.style.display = "none";
      btnCancel.style.display = "inline-flex";

      s2Tag.className = "tag warn";
      s2Tag.textContent = "In Pausa";
    } else if (dl.state === "done") {
      stState.textContent = "Completato con successo";
      stDone.textContent = `${dl.total_h} / ${dl.total_h}`;
      stSpeed.textContent = "0 B/s";
      stEta.textContent = "Completato";
      barFill.style.width = "100%";
      barBox.className = "progress lg";

      btnText.textContent = "ISO Pronta per l'Uso";
      btnAction.disabled = false;
      btnPause.style.display = "none";
      btnCancel.style.display = "none";

      s2Tag.className = "tag ok";
      s2Tag.textContent = "Completato";
      s2Card.className = "step done";

      if (heroDlBtnText) heroDlBtnText.textContent = "ISO Scaricata con Successo";
    } else {
      // idle, error, cancelled
      stState.textContent = dl.state === "error" ? `Errore: ${dl.error}` : "In attesa";
      stDone.textContent = "0 B / —";
      stSpeed.textContent = "—";
      stEta.textContent = "—";
      barFill.style.width = "0%";
      barBox.className = "progress lg";

      btnText.textContent = "Avvia Scaricamento (1-Clic)";
      btnAction.disabled = false;
      btnPause.style.display = "none";
      btnCancel.style.display = "none";

      if (isos && isos.length > 0) {
        s2Tag.className = "tag ok";
        s2Tag.textContent = "ISO Presente";
        s2Card.className = "step done";
      } else {
        s2Tag.className = "tag";
        s2Tag.textContent = "In Attesa";
        s2Card.className = "step";
      }
    }

    // Verifica aggiornamento ISO in corso
    if (dl.check && dl.check.state === "checking") {
      stState.textContent = "Verifica versione sul sito Microsoft…";
      barBox.className = "progress lg indeterminate";
      btnText.textContent = "Verifica aggiornamenti…";
      btnAction.disabled = true;
      if (heroDlBtnText) heroDlBtnText.textContent = "Verifica aggiornamenti…";
    }

    // Render ISO Library list
    const isoListContainer = document.getElementById("iso-list-container");
    if (isoListContainer) {
      if (!isos || isos.length === 0) {
        isoListContainer.innerHTML = `
          <div class="empty">
            <svg class="icon"><ellipse cx="12" cy="12" rx="10" ry="10"/><circle cx="12" cy="12" r="3"/></svg>
            <div>Nessuna ISO trovata nella cartella ISO. Fai clic su <b>Avvia Scaricamento</b> per scaricare la versione ufficiale.</div>
          </div>
        `;
      } else {
        isoListContainer.innerHTML = isos
          .map((iso) => {
            const isSel = iso.path === selectedIso;
            const sizeH = (iso.size / 1024 ** 3).toFixed(2) + " GB";
            return `
              <div class="iso ${isSel ? "selected" : ""}" data-path="${iso.path.replace(/"/g, "&quot;")}">
                <div class="radio"></div>
                <div class="iso-ico">
                  <svg class="icon"><ellipse cx="12" cy="12" rx="10" ry="10"/><circle cx="12" cy="12" r="3"/></svg>
                </div>
                <div>
                  <div class="iso-name">${iso.name} ${iso.external ? '<span class="tag info plain" style="margin-left:6px">Esterna</span>' : ""}</div>
                  <div class="iso-meta">
                    <span>Dimensione: <b>${sizeH}</b></span> •
                    <span>Versione: <b>${iso.release || "Windows 11"}</b></span> •
                    <span>Data: ${iso.date}</span>
                  </div>
                </div>
                <div>
                  ${isSel ? '<span class="tag accent">Selezionata</span>' : '<button class="btn btn-sm btn-ghost btn-select-iso">Seleziona</button>'}
                </div>
              </div>
            `;
          })
          .join("");

        // Attach clicks
        isoListContainer.querySelectorAll(".iso").forEach((el) => {
          el.addEventListener("click", () => {
            const p = el.getAttribute("data-path");
            if (p) selectIso(p);
          });
        });
      }
    }

    // Update Selected ISO display in Upgrade View
    const upgName = document.getElementById("upg-iso-name");
    const upgMeta = document.getElementById("upg-iso-meta");
    const s3Tag = document.getElementById("flow-s3-tag");
    const s3Card = document.getElementById("flow-step-3");

    if (selectedIso) {
      const fn = selectedIso.split(/[\\/]/).pop();
      upgName.textContent = fn;
      upgMeta.textContent = selectedIso;
      s3Tag.className = "tag ok";
      s3Tag.textContent = "Pronto";
      s3Card.className = "step current";
    } else {
      upgName.textContent = "Nessuna ISO selezionata";
      upgMeta.textContent = "Scarica una ISO dalla sezione Download o selezionala dall'elenco";
      s3Tag.className = "tag";
      s3Tag.textContent = "Manca ISO";
      s3Card.className = "step";
    }
  }

  async function selectIso(path) {
    try {
      await api("/api/iso/select", "POST", { path });
      toast(`ISO selezionata: ${path.split(/[\\/]/).pop()}`, "ok");
    } catch (e) {
      toast(`Errore selezione ISO: ${e.message}`, "error");
    }
  }

  // ---------------------------------------------------------------------------
  // Verifica aggiornamento ISO (ISO locale vs ISO sul sito Microsoft)
  // ---------------------------------------------------------------------------
  function handleIsoCheck(chk) {
    if (!chk) return;
    if (lastCheckId === null) {
      // primo polling: non riproporre esiti vecchi, ma gestisce una verifica ancora in corso
      lastCheckId = chk.state === "checking" ? chk.id - 1 : chk.id;
      return;
    }
    if (!chk.id || chk.id <= lastCheckId || chk.state === "checking") return;
    lastCheckId = chk.id;

    if (chk.state === "newer") {
      const set = (id, val) => {
        const el = document.getElementById(id);
        if (el) el.textContent = val || "—";
      };
      set("iso-upd-local-rel", chk.local_release);
      set("iso-upd-local-name", chk.local_name);
      set("iso-upd-local-meta", `${chk.local_size_h} · ${chk.local_date}`);
      set("iso-upd-remote-rel", chk.remote_release);
      set("iso-upd-remote-name", chk.remote_name);
      set("iso-upd-remote-meta", `${chk.remote_size_h} · ${chk.remote_date}`);
      const dlg = document.getElementById("dlg-iso-update");
      if (dlg && !dlg.open) dlg.showModal();
    } else if (chk.state === "uptodate") {
      toast(`La ISO presente è già la più aggiornata (${chk.local_release} · ${chk.local_name})`, "ok");
    } else if (chk.state === "missing") {
      api("/api/download/start", "POST", { force: true }).catch(() => {});
    } else if (chk.state === "error") {
      toast(`Impossibile verificare gli aggiornamenti: ${chk.error}`, "error");
    }
  }

  // ---------------------------------------------------------------------------
  // Rendering: Upgrade Flow & Timeline
  // ---------------------------------------------------------------------------
  function updateCmdPreview() {
    const mode = document.querySelector("#seg-mode button.on")?.dataset.val || "auto";
    const method = document.querySelector("#seg-method button.on")?.dataset.val || "server";

    let args = '<span class="p">setup.exe</span> <span class="f">/product</span> <span class="v">server</span> <span class="f">/compat</span> <span class="v">IgnoreWarning</span> <span class="f">/MigrateDrivers</span> <span class="v">All</span> <span class="f">/DynamicUpdate</span> <span class="v">Disable</span>';

    if (mode === "auto" || mode === "silent") {
      args += ' <span class="f">/auto</span> <span class="v">upgrade</span> <span class="f">/EULA</span> <span class="v">accept</span>';
    }
    if (mode === "silent") {
      args += ' <span class="f">/quiet</span>';
    }

    if (method === "appraiser") {
      args = `<span style="color:var(--muted)">[Copia locale + rimozione appraiserres.dll] &amp;&amp;</span> ${args}`;
    }

    const cmdEl = document.getElementById("cmd-preview");
    if (cmdEl) cmdEl.innerHTML = args;
  }

  function renderUpgrade(upg) {
    if (!upg) return;

    const statusTag = document.getElementById("upg-status-tag");
    const timeline = document.getElementById("timeline-container");
    const btnStart = document.getElementById("btn-start-upgrade");

    if (upg.state === "running") {
      statusTag.className = "tag live";
      statusTag.textContent = "Procedura in Corso";
      btnStart.disabled = true;
    } else if (upg.state === "launched") {
      statusTag.className = "tag ok";
      statusTag.textContent = "Setup Avviato";
      btnStart.disabled = false;
    } else if (upg.state === "error") {
      statusTag.className = "tag err";
      statusTag.textContent = "Errore";
      btnStart.disabled = false;
    } else {
      statusTag.className = "tag";
      statusTag.textContent = "Inattivo";
      btnStart.disabled = false;
    }

    // Render Timeline steps
    if (timeline && upg.steps) {
      timeline.innerHTML = upg.steps
        .map((step, idx) => {
          let dotContent = `${idx + 1}`;
          if (step.status === "ok") dotContent = "✓";
          if (step.status === "error") dotContent = "✕";

          return `
            <div class="tl ${step.status}">
              <div class="tl-dot">${dotContent}</div>
              <div>
                <div class="tl-title">${step.label}</div>
                <div class="tl-detail">${step.detail || (step.status === "running" ? "Operazione in esecuzione…" : "In attesa")}</div>
              </div>
              <div>
                <span class="tag ${step.status === "ok" ? "ok" : step.status === "running" ? "accent" : step.status === "error" ? "err" : ""}">${step.status.toUpperCase()}</span>
              </div>
            </div>
          `;
        })
        .join("");
    }
  }

  // ---------------------------------------------------------------------------
  // Rendering: Hash Tool
  // ---------------------------------------------------------------------------
  function renderHash(h) {
    if (!h) return;
    const bar = document.getElementById("hash-progress-bar");
    const fill = document.getElementById("hash-progress-fill");
    const res = document.getElementById("hash-result");
    const btn = document.getElementById("btn-calc-hash");

    if (h.state === "running") {
      bar.style.display = "block";
      fill.style.width = `${h.percent}%`;
      res.value = `Calcolo in corso (${h.percent}%)…`;
      btn.disabled = true;
    } else if (h.state === "done") {
      bar.style.display = "none";
      res.value = h.result;
      btn.disabled = false;
    } else if (h.state === "error") {
      bar.style.display = "none";
      res.value = `Errore: ${h.result}`;
      btn.disabled = false;
    }
  }

  // ---------------------------------------------------------------------------
  // Rendering: Logs
  // ---------------------------------------------------------------------------
  function appendLogs(logs) {
    if (!logs || logs.length === 0) return;

    const dashConsole = document.getElementById("dash-console");
    const fullConsole = document.getElementById("full-console");

    logs.forEach((item) => {
      if (item.id > lastLogId) lastLogId = item.id;

      const lineHtml = `
        <div class="ln ${item.lvl}">
          <span class="t">${item.t}</span>
          <span class="m">${item.msg.replace(/</g, "&lt;").replace(/>/g, "&gt;")}</span>
        </div>
      `;

      if (dashConsole) {
        dashConsole.insertAdjacentHTML("beforeend", lineHtml);
        dashConsole.scrollTop = dashConsole.scrollHeight;
      }
      if (fullConsole) {
        fullConsole.insertAdjacentHTML("beforeend", lineHtml);
        fullConsole.scrollTop = fullConsole.scrollHeight;
      }
    });

    // Pulse logs dot in sidebar if we got warning or errors
    const logsDot = document.getElementById("dot-logs");
    const hasWarn = logs.some((l) => l.lvl === "warn" || l.lvl === "error");
    if (logsDot && hasWarn && currentView !== "logs") {
      logsDot.className = "badge-dot warn";
    }
  }

  // ---------------------------------------------------------------------------
  // Master Poll Loop
  // ---------------------------------------------------------------------------
  async function pollState() {
    try {
      const state = await api(`/api/state?since=${lastLogId}`);
      currentState = state;

      // Update brand version
      if (state.app && state.app.version) {
        const vEl = document.getElementById("brand-ver");
        const avEl = document.getElementById("about-version");
        if (vEl) vEl.textContent = `v${state.app.version}`;
        if (avEl) avEl.textContent = state.app.version;
      }

      renderSystem(state.system, state.system_state);
      renderDownload(state.download, state.isos, state.selected_iso);
      handleIsoCheck(state.download && state.download.check);
      renderUpgrade(state.upgrade);
      renderHash(state.hash);
      appendLogs(state.logs);
    } catch (err) {
      console.warn("Poll state error:", err);
    } finally {
      const interval =
        currentState?.download?.state === "downloading" ||
        currentState?.upgrade?.state === "running" ||
        currentState?.hash?.state === "running"
          ? 600
          : 1200;
      pollTimer = setTimeout(pollState, interval);
    }
  }

  // ---------------------------------------------------------------------------
  // Event Listeners & Actions
  // ---------------------------------------------------------------------------
  function setupEvents() {
    // Navigation
    document.querySelectorAll(".nav-item").forEach((btn) => {
      btn.addEventListener("click", () => {
        const v = btn.dataset.view;
        if (v) switchView(v);
      });
    });

    // In-page view targets
    document.addEventListener("click", (e) => {
      const t = e.target.closest("[data-view-target]");
      if (t) {
        switchView(t.dataset.viewTarget);
      }
    });

    // Re-check scanner
    const triggerScan = async () => {
      try {
        await api("/api/scan", "POST");
        toast("Scansione hardware avviata", "info");
      } catch (e) {
        toast("Impossibile avviare la scansione", "error");
      }
    };
    document.getElementById("btn-quick-scan")?.addEventListener("click", triggerScan);
    document.getElementById("btn-recheck")?.addEventListener("click", triggerScan);

    // Download controls
    const triggerDownload = async () => {
      try {
        const res = await api("/api/download/start", "POST");
        if (res.checking) {
          if (res.ok) {
            toast("ISO già presente: verifico se sul sito Microsoft c'è una versione più aggiornata…", "info");
            switchView("download");
          } else {
            toast("Verifica o download già in corso", "warn");
          }
        } else if (res.ok) {
          toast("Connessione ai server Microsoft in corso…", "info");
          switchView("download");
        } else {
          toast("Download già in corso", "warn");
        }
      } catch (e) {
        toast(`Errore avvio download: ${e.message}`, "error");
      }
    };

    document.getElementById("btn-hero-download")?.addEventListener("click", triggerDownload);
    document.getElementById("btn-flow-download")?.addEventListener("click", triggerDownload);
    document.getElementById("btn-dl-action")?.addEventListener("click", triggerDownload);

    // Dialog aggiornamento ISO
    const isoUpdDlg = document.getElementById("dlg-iso-update");
    document.getElementById("btn-iso-upd-keep")?.addEventListener("click", () => {
      isoUpdDlg.close();
      toast("ISO attuale mantenuta", "info");
    });
    document.getElementById("btn-iso-upd-download")?.addEventListener("click", async () => {
      isoUpdDlg.close();
      try {
        const res = await api("/api/download/replace", "POST");
        if (res.ok) {
          toast("Download della nuova ISO avviato: la vecchia verrà eliminata al termine", "info");
          switchView("download");
        } else {
          toast("Download già in corso", "warn");
        }
      } catch (e) {
        toast(`Errore avvio download: ${e.message}`, "error");
      }
    });

    document.getElementById("btn-dl-pause")?.addEventListener("click", async () => {
      await api("/api/download/pause", "POST");
      toast("Download messo in pausa", "warn");
    });

    document.getElementById("btn-dl-cancel")?.addEventListener("click", async () => {
      if (confirm("Vuoi davvero annullare lo scaricamento?")) {
        await api("/api/download/cancel", "POST");
        toast("Download annullato", "warn");
      }
    });

    // ISO browse & open folder
    document.getElementById("btn-browse-iso")?.addEventListener("click", async () => {
      toast("Finestra di selezione aperta…", "info");
      await api("/api/iso/browse", "POST");
    });

    const openIsoFolder = () => api("/api/tool/open_iso_folder", "POST");
    document.getElementById("btn-open-iso-folder")?.addEventListener("click", openIsoFolder);
    document.getElementById("btn-hero-folder")?.addEventListener("click", openIsoFolder);

    // Segmented Mode Buttons
    document.querySelectorAll("#seg-mode button").forEach((btn) => {
      btn.addEventListener("click", async () => {
        document.querySelectorAll("#seg-mode button").forEach((b) => b.classList.remove("on"));
        btn.classList.add("on");
        updateCmdPreview();
        await api("/api/settings", "POST", { upgrade_mode: btn.dataset.val });
      });
    });

    // Segmented Method Buttons
    document.querySelectorAll("#seg-method button").forEach((btn) => {
      btn.addEventListener("click", async () => {
        document.querySelectorAll("#seg-method button").forEach((b) => b.classList.remove("on"));
        btn.classList.add("on");
        updateCmdPreview();
        await api("/api/settings", "POST", { upgrade_method: btn.dataset.val });
      });
    });

    // Toggles
    document.getElementById("toggle-restore")?.addEventListener("change", async (e) => {
      await api("/api/settings", "POST", { create_restore_point: e.target.checked });
    });
    document.getElementById("toggle-watermark")?.addEventListener("change", async (e) => {
      await api("/api/settings", "POST", { remove_watermark: e.target.checked });
    });

    // Upgrade Dialog Modal
    const dlg = document.getElementById("dlg-confirm-upgrade");
    const openUpgradeModal = () => {
      if (!currentState?.selected_iso) {
        toast("Scarica o seleziona prima una ISO di Windows 11", "warn");
        switchView("download");
        return;
      }
      dlg.showModal();
    };

    document.getElementById("btn-hero-upgrade")?.addEventListener("click", openUpgradeModal);
    document.getElementById("btn-flow-upgrade")?.addEventListener("click", () => switchView("upgrade"));
    document.getElementById("btn-start-upgrade")?.addEventListener("click", openUpgradeModal);

    document.getElementById("btn-dlg-cancel")?.addEventListener("click", () => dlg.close());
    document.getElementById("btn-dlg-proceed")?.addEventListener("click", async () => {
      dlg.close();
      try {
        const res = await api("/api/upgrade/start", "POST");
        if (res.ok) {
          toast("Procedura di aggiornamento avviata!", "ok");
          switchView("upgrade");
        } else {
          toast(res.msg || "Impossibile avviare l'aggiornamento", "error");
        }
      } catch (e) {
        toast(`Errore: ${e.message}`, "error");
      }
    });

    // Tools Buttons
    document.querySelectorAll(".tool[data-tool]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const toolName = btn.dataset.tool;
        try {
          const res = await api(`/api/tool/${toolName}`, "POST");
          if (res.ok) {
            toast(res.msg || "Operazione completata", "ok");
          } else {
            toast(res.msg || "Errore esecuzione strumento", "error");
          }
        } catch (e) {
          toast(`Errore strumento: ${e.message}`, "error");
        }
      });
    });

    // Calc SHA-256
    document.getElementById("btn-calc-hash")?.addEventListener("click", async () => {
      if (!currentState?.selected_iso) {
        toast("Nessuna ISO selezionata", "warn");
        return;
      }
      try {
        await api("/api/tool/verify_hash", "POST", { path: currentState.selected_iso });
        toast("Calcolo SHA-256 avviato in background", "info");
      } catch (e) {
        toast(`Errore: ${e.message}`, "error");
      }
    });

    // Copy and Open Logs
    document.getElementById("btn-copy-logs")?.addEventListener("click", () => {
      const fullConsole = document.getElementById("full-console");
      if (fullConsole) {
        navigator.clipboard.writeText(fullConsole.innerText);
        toast("Registro copiato negli appunti", "ok");
      }
    });
    document.getElementById("btn-open-log-file")?.addEventListener("click", () => {
      api("/api/tool/open_log", "POST");
    });
  }

  // ---------------------------------------------------------------------------
  // Init
  // ---------------------------------------------------------------------------
  document.addEventListener("DOMContentLoaded", () => {
    setupEvents();
    updateCmdPreview();
    pollState();
  });
})();
