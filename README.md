# W11 Update Flow

<p align="center">
  <b>Aggiornamento automatizzato di Windows 11 su PC non idonei</b><br>
  <i>Download con 1 clic della ISO ufficiale Microsoft, iniezione bypass hardware e conservazione al 100% di file, programmi e impostazioni.</i>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Versione-1.0.3-B8F23A?style=for-the-badge" alt="Versione">
  <img src="https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/JavaScript-F7DF1E?style=for-the-badge&logo=javascript&logoColor=black" alt="JavaScript">
  <img src="https://img.shields.io/badge/HTML5%20%2F%20CSS3-E34F26?style=for-the-badge&logo=html5&logoColor=white" alt="HTML5 e CSS3">
  <a href="LICENSE"><img src="https://img.shields.io/badge/Licenza-GPL%20v3-0078D6?style=for-the-badge" alt="Licenza GPLv3"></a>
</p>

<p align="center">
  <img src="ScreenShot/Image.png" alt="Schermata di W11 Update Flow" width="900">
</p>

<p align="center">
  📘 <a href="GUIDA_UTILIZZO.md"><b>Guida all'Utilizzo</b></a>  ·  📄 <a href="LICENSE"><b>Licenza GPLv3</b></a>
</p>

---

## 📌 Cos'è W11 Update Flow?

**W11 Update Flow** è un'applicazione desktop moderna progettata per semplificare e automatizzare il passaggio alle versioni più recenti di Windows 11 (**24H2, 25H2, 26H2** e successive) su tutti i computer con hardware non ufficialmente idoneo (macchine prodotte negli ultimi 15 anni prive di TPM 2.0, Secure Boot o dotate di processori non presenti nella lista ufficiale di Microsoft).

A differenza dei metodi manuali complessi, **W11 Update Flow** gestisce l'intero ciclo in un'interfaccia grafica moderna, intuitiva e professionale:
1. **Analizza** la compatibilità del PC (verificando il supporto CPU a `SSE4.2`/`POPCNT`, RAM, spazio libero e BitLocker).
2. **Scarica con 1 clic** la ISO ufficiale di Windows 11 a 64 bit in italiano direttamente dai server CDN di Microsoft, salvandola nella cartella dedicata `ISO/` dell'applicazione.
3. **Avvia l'aggiornamento** montando l'immagine ed eseguendo il comando di bypass nel terminale di setup (`setup.exe /product server /compat IgnoreWarning /MigrateDrivers All`), applicando le necessarie chiavi di registro (`MoSetup`, `LabConfig`, `HwReqChk`).

> [!NOTE]
> **Nessuna perdita di dati**: la procedura esegue un aggiornamento in-place, preservando tutti i documenti personali, le applicazioni installate, i driver e le impostazioni del sistema operativo.

---

## ✨ Funzionalità Principali

- 🚀 **Download ISO Ufficiale con 1 Clic**:
  - Connessione diretta ai server Microsoft (`software.download.prss.microsoft.com`).
  - Scaricamento automatico dell'ultima build disponibile a 64-bit in lingua italiana.
  - Supporto per pausa, ripresa, annullamento e ripresa automatica dei download parziali.
  - Cartella dedicata `ISO/` creata e gestita automaticamente all'interno del percorso dell'applicazione.
  - **Verifica aggiornamenti ISO**: se la ISO è già presente, premendo di nuovo *Scarica ISO* l'app confronta la ISO locale con quella pubblicata sul sito Microsoft e avvisa se esiste una versione più aggiornata; scegliendo di scaricarla, la vecchia ISO viene eliminata al termine del download.

- 🛡️ **Motore di Bypass Hardware Automatico**:
  - Aggiramento dei blocchi per TPM 2.0, Secure Boot, RAM minima e modello CPU.
  - Metodo principale certificato: `setup.exe /product server /compat IgnoreWarning /MigrateDrivers All /DynamicUpdate Disable`.
  - Metodo alternativo selezionabile: estrazione locale e neutralizzazione del modulo `appraiserres.dll`.
  - Configurazione automatica delle chiavi di registro di bypass prima del lancio.

- 🔍 **Analisi Approfondita del Sistema**:
  - Controllo delle istruzioni `SSE4.2` e `POPCNT` (requisito hardware inderogabile del kernel di Windows 11 24H2+).
  - Rilevamento dello stato di BitLocker (per evitare blocchi imprevisti durante il riavvio).
  - Verifica dello spazio libero su disco (richiesti almeno 20-30 GB).
  - Rilevamento di riavvii di sistema in sospeso.

- 🧰 **Suite di Strumenti & Sicurezza Integrata**:
  - Creazione con un clic di un **Punto di Ripristino del Sistema** preventivo.
  - Rimozione automatica dell'avviso desktop **"Requisiti di sistema non soddisfatti"** (`UnsupportedHardwareNotificationCache`).
  - **Estensione della finestra di rollback da 10 a 60 giorni** tramite DISM (`/Set-OSUninstallWindow /Value:60`).
  - Calcolo e verifica del checksum crittografico **SHA-256** per garantire l'integrità della ISO scaricata.
  - Smontaggio automatico delle unità virtuali ISO e pulizia file temporanei.
  - Accesso rapido ai log di installazione di Windows Setup (`$WINDOWS.~BT\Sources\Panther`).

- 🎨 **Design System Moderno & Curato**:
  - Interfaccia scura in grafite profonda con accento *signal-lime*.
  - Tipografia avanzata *Segoe UI Variable* e componenti modulari ad alta leggibilità.
  - Indicatori animati in tempo reale (anello di prontezza del sistema, timeline dell'aggiornamento e console eventi in streaming).
  - Esecuzione in finestra applicazione nativa tramite Edge/Chrome (nessun framework pesante richiesto).

---

## 💻 Requisiti di Sistema

| Componente | Requisito Minimo | Requisito Consigliato |
| :--- | :--- | :--- |
| **Sistema Operativo** | Windows 10 (64-bit) o Windows 11 (21H2, 22H2, 23H2) | Windows 11 con ultimi aggiornamenti cumulativi |
| **Architettura CPU** | 64-bit (x64 / AMD64) con supporto a **SSE4.2 / POPCNT** | CPU prodotta dal 2010 in poi |
| **Memoria RAM** | 4 GB | 8 GB o superiore |
| **Spazio su Disco C:** | Almeno 20 GB liberi | 30 GB o superiore liberi |
| **Connessione Internet** | Connessione a banda larga (per il download della ISO da ~5-6 GB) | Fibra ottica / ADSL stabile |

---

## 📁 Struttura del Progetto

```text
W11 UPDATE FLOW/
├── app/                        # Moduli Python del backend
│   ├── __init__.py             # Inizializzazione package
│   ├── core.py                 # Gestione percorsi, log, settings e PowerShell runner
│   ├── ms_download.py          # Download diretto ISO da server Microsoft (x64, IT)
│   ├── server.py               # Server locale asincrono HTTP (127.0.0.1) con token
│   ├── system_info.py          # Scanner compatibilità PC (CPU, TPM, RAM, BitLocker)
│   ├── tools.py                # Utilità: SHA-256, punto di ripristino, watermark, rollback
│   ├── upgrade.py              # Pipeline di aggiornamento e iniezione bypass
│   └── versioning.py           # Avanzamento automatico versione (SHA-256 hash sorgenti)
├── web/                        # Interfaccia grafica Web (HTML5 / CSS3 / Vanilla JS)
│   ├── css/
│   │   └── styles.css          # Design system completo e componenti
│   ├── js/
│   │   └── app.js              # Logica frontend, polling e gestione timeline
│   └── index.html              # Template principale dell'applicazione
├── ISO/                        # Cartella dedicata di salvataggio immagini ISO (creata all'avvio)
├── ScreenShot/                 # Screenshot dell'applicazione usati nella documentazione
├── GeneraExe.py                # Script di compilazione per generare l'eseguibile standalone
├── main.py                     # Entry point dell'applicazione (gestione elevazione admin)
├── requirements.txt            # Dipendenze Python (PyInstaller per la compilazione)
├── version.json                # Tracciamento versione e build dell'applicazione
├── .gitignore                  # Esclusioni per il repository Git
├── GUIDA_UTILIZZO.md           # Guida passo-passo all'utilizzo dell'applicazione
├── LICENSE                     # Testo della licenza GNU GPL v3
└── README.md                   # Documentazione ufficiale del progetto
```

---

## 🚀 Istruzioni per l'Uso

> [!TIP]
> Per una spiegazione completa di ogni schermata e funzione consulta la **[Guida all'Utilizzo](GUIDA_UTILIZZO.md)**.

### 1. Esecuzione da Sorgenti Python

1. Assicurati di avere installato **Python 3.10 o versione superiore** a 64 bit su Windows.
2. Clona il repository o scarica la cartella dei sorgenti:
   ```powershell
   git clone https://github.com/AngoloInformatico/W11-Update-Flow.git
   cd "W11-Update-Flow"
   ```
3. Avvia l'applicazione (richiede privilegi di amministratore):
   ```powershell
   python main.py
   ```
   *L'applicazione richiederà automaticamente l'elevazione UAC se non avviata già come amministratore.*

---

### 2. Generazione del File Eseguibile (.exe)

Per distribuire l'applicazione come file eseguibile singolo standalone (`W11 Update Flow.exe`), esegui lo script dedicato:

```powershell
python GeneraExe.py
```

Lo script effettuerà:
1. La verifica e l'incremento automatico della versione in `version.json` se i sorgenti sono stati modificati.
2. L'incorporamento di tutte le risorse grafiche della cartella `web/` e del manifesto di elevazione UAC.
3. Il salvataggio del file eseguibile finale nella cartella `dist/`:
   ```text
   dist/W11 Update Flow.exe
   ```

---

## 🔄 Avanzamento Automatico della Versione

W11 Update Flow include un sistema integrato di versioning semantico automatico in `app/versioning.py`. Ad ogni modifica apportata ai file sorgente (`.py`, `.html`, `.css`, `.js`), all'avvio successivo o durante l'esecuzione di `GeneraExe.py`, la versione di patch viene incrementata in modo deterministico attraverso il calcolo dell'hash SHA-256 dei contenuti:
```text
v1.0.0 (Build 1) -> v1.0.1 (Build 2) -> ...
```

---

## ⚖️ Esclusione di Responsabilità & Clausole di Salvaguardia (Disclaimer)

> [!CAUTION]
> **LEGGERE ATTENTAMENTE PRIMA DELL'USO**: L'utilizzo di **W11 Update Flow** avviene a esclusivo rischio e pericolo dell'utente. Il software interagisce a basso livello con il sistema operativo, il registro di Windows e i meccanismi di installazione e aggiornamento di sistema.

1. **Fornitura del software "COSÌ COM'È" ("AS IS")**:  
   Il software è fornito a puro scopo informativo, divulgativo e di supporto tecnico per utenti consapevoli ed esperti. Viene rilasciato *"così com'è"* e *"come disponibile"*, senza alcun tipo di garanzia esplicita o implicita, incluse, a titolo meramente esemplificativo, garanzie di commerciabilità, idoneità per uno scopo specifico, stabilità, affidabilità o assenza di errori.

2. **Esclusione totale di responsabilità per danni**:  
   In nessun caso l'autore (**Alex Lignola**), i collaboratori o la community de **L'Angolo Informatico** potranno essere ritenuti responsabili per qualsivoglia danno, diretto, indiretto, incidentale, speciale, punitivo o consequenziale derivante dall'uso, dall'uso improprio, dall'errata configurazione o dall'incapacità di utilizzare l'applicazione. L'esclusione di responsabilità copre, a titolo esemplificativo e non esaustivo:
   - Perdita totale o parziale di dati personali, documenti, file multimediali o software installati;
   - Corruzione del file system, del settore di avvio (MBR/GPT/BCD) o del registro di Windows;
   - Schermate blu (BSOD), loop di riavvio, blocchi di BitLocker o fallimenti nella procedura di setup di Windows;
   - Malfunzionamenti, incompatibilità di driver, periferiche o danni a componenti hardware;
   - Interruzione dell'attività lavorativa, perdita di guadagni o costi sostenuti per l'assistenza tecnica o il recupero dati.

3. **Responsabilità esclusiva dell'utente e obbligo di backup**:  
   L'utente è l'unico ed esclusivo responsabile dell'utilizzo dell'applicazione sul proprio dispositivo. Prima di avviare qualsiasi procedura di download o aggiornamento, **è dovere tassativo dell'utente effettuare una copia di backup completa e verificata di tutti i dati personali e delle configurazioni critiche** su supporti di memoria esterni o in cloud. L'utente si assume inoltre la piena responsabilità della verifica preliminare del supporto CPU (`SSE4.2`/`POPCNT`) e della conservazione della chiave di ripristino di BitLocker, qualora attivo.

4. **Compatibilità futura e aggiornamenti Microsoft**:  
   L'applicazione applica bypass documentati e metodi di compatibilità noti per l'installazione su macchine non ufficialmente idonee. L'autore non garantisce che i dispositivi aggiornati continueranno a ricevere futuri aggiornamenti cumulativi, qualitativi o di sicurezza da parte di Microsoft, né che Microsoft non introduca in futuro blocchi hardware o modifiche ai requisiti che rendano inefficaci tali procedure o instabile il sistema.

5. **Marchi e indipendenza da Microsoft Corporation**:  
   *Windows*, *Windows 11*, *Windows 10*, *Microsoft* e i rispettivi loghi o elementi grafici sono marchi registrati di **Microsoft Corporation**. **W11 Update Flow** è un progetto software indipendente e open source sviluppato in conformità alla licenza GNU GPLv3, che **non è in alcun modo affiliato, associato, autorizzato, sponsorizzato né approvato da Microsoft Corporation**.

6. **Accettazione vincolante dei termini**:  
   Il download, l'esecuzione, la clonazione o l'utilizzo a qualsiasi titolo dell'applicazione o del relativo codice sorgente implicano l'accettazione espressa, piena, incondizionata e vincolante di tutte le presenti clausole e limitazioni di responsabilità. Qualora l'utente non concordi, anche solo parzialmente, con le clausole sopra indicate, **non è autorizzato a utilizzare né ad eseguire l'applicazione**.

---

## 📄 Licenza

Questo progetto è distribuito secondo i termini della **GNU General Public License v3.0**.  
Consulta il file [LICENSE](LICENSE) per il testo completo della licenza.

---

## 👨‍💻 Autore e Community

Sviluppato da **Alex Lignola**  
Canale e community: **L'Angolo Informatico**

<p align="left">
  <a href="https://www.youtube.com/@AngoloInformatico"><img src="https://img.shields.io/badge/YouTube-@AngoloInformatico-FF0000?style=for-the-badge&logo=youtube&logoColor=white" alt="YouTube"></a>
  <a href="https://github.com/AngoloInformatico"><img src="https://img.shields.io/badge/GitHub-AngoloInformatico-181717?style=for-the-badge&logo=github&logoColor=white" alt="GitHub"></a>
</p>

- 🎥 **YouTube**: [@AngoloInformatico](https://www.youtube.com/@AngoloInformatico)
- 🐙 **GitHub Profilo**: [@AngoloInformatico](https://github.com/AngoloInformatico)
- 📦 **Tutti i Repository**: [GitHub Repositories](https://github.com/AngoloInformatico?tab=repositories)

---

## 📄 Copyright

```text
Created by Alex Lignola - © 2026 W11 Update Flow - All rights reserved.
Distribuito sotto licenza GNU General Public License v3.0 (GPLv3).
```
