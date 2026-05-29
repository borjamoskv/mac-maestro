# EXAMPLES.md — C5-REAL ERABILERA KASUAK

**Errealitate Maila: C5-REAL** | **Estetika: Industrial Noir 2026**

`mac-maestro` UI automatizazio semantikorako 25 erabilera-kasu determinista, seinale-dentsitate maximokoak.

## 01 · Exekuzio Agentikoa eta IA

| Kasua | Bektorea | Mekanismoa |
| :--- | :--- | :--- |
| **01. Mahaigaineko Agente Subiranoa** | Exekuzio Autonomoa | LLM-ek X/Y koordenatuak asmatu ordez, `ClickAction(role, title)` deterministak igortzen dituzte. |
| **02. Terminal-GUI Zubia** | CLI Fluxuak | Abiarazi Apple Mail edo Safari fluxu konplexuak zuzenean `tmux` edo `nvim`-etik. |
| **03. Ikusmen-QA Auditoriak** | CI/CD macOS Runner-ak | Exekutatu baieztapen deterministak jatorrizko Swift/Obj-C aplikazioetan GitHub Actions bidez. |
| **04. Irisgarritasun (a11y) Analisia** | AX Zuhaitzaren Miaketa | Arakatu AX zuhaitza WCAG protokoloak eta falta diren `AXHelp` etiketak egiaztatzeko. |
| **05. UI Fuzzing eta Estres Probak** | QA Fuzzing-a | Programatikoki abiarazi bundle bateko `AXButton` nodo guztiak kraskadura-bektoreak bilatzeko. |

## 02 · Legacy eta Erresistentzia Bektoreak

| Kasua | Bektorea | Mekanismoa |
| :--- | :--- | :--- |
| **06. Legacy Sistemotako Erauzketa** | Datu-Meatzaritza | Erauzi `AXStaticText` APIrik ez duten 32-biteko macOS aplikazio zaharkituetatik. |
| **07. DAW Kontrol Ez-Mapeagarria** | Musika Ekoizpena | Automatizatu MIDI baztertzen duten Ableton Live / Logic Pro UI nodo sakonak. |
| **08. Mahaigaineko CRM Automatizazioa** | Datuen Injekzioa | Erauzi mezu elektronikoen edukia eta txertatu mahaigaineko CRM-en jatorrizko inputetan. |
| **09. Jatorrizko Broker Terminalak** | Negoziazio Algoritmikoa | Exekutatu segundo-azpiko `AXPress` Erosi/Saldu nodoetan, APIrik gabeko terminaletan. |
| **10. Nabigatzaile APIen Faila-Sarea** | Web Automatizazioa | Kontrolatu Safari/Chrome UI-a, WebDriver anti-bot sistemek euste-horma ezartzen dutenean. |

## 03 · Sistema eta Azpiegitura Ops

| Kasua | Bektorea | Mekanismoa |
| :--- | :--- | :--- |
| **11. Sistemaren Segurtasun Gogortzea** | OS Konfigurazioa | Automatikoki mutatu macOS `System Settings` nodoak AX nabigazioz. |
| **12. Dialogoen Deuseztapen Inposatua** | OS Etenaldiak | Deuseztatu automatikoki "Eguneratzea Eskuragarri" edo "Diskoa Betea" `AXWindow` alertak. |
| **13. Urruneko Berreskurapen Operatiboa** | Ops Erreskatea | Konpondu hautsitako VPN konfigurazioak UI bidez, SSH konexioa ezegonkorra denean. |
| **14. Flota-Hornikuntza** | MDM Inplementazioa | Egin klik script bidez automatizatu ezin diren DMG instalatzaileetan. |
| **15. Monitore Anitzeko Kudeaketa** | Mahaigaineko Topologia | Kontsultatu `AXWindow` eta mutatu `AXPosition` / `AXSize` pantaila ezberdinen mugetan. |

## 04 · Sorkuntza eta Errendatze Automatizazioa

| Kasua | Bektorea | Mekanismoa |
| :--- | :--- | :--- |
| **16. OBS/QuickTime Orkestrazioa** | Emisioa | Hasi/Gelditu transmisioa leihoa fokatu gabe, atzeko planoko AX kakoen bitartez. |
| **17. Final Cut Pro Makroak** | Bideo Edizioa | Abiarazi urrats anitzeko errendatze-pipeline konplexuak FCPX-n, interakzio humanorik gabe. |
| **18. Keynote Pilotu Automatikoa** | Aurkezpenak | Gidatu kanpoko datu-fluxuekin sinkronizatutako diapositiba-trantsizio natiboak. |
| **19. Batch Audio Esportazioa** | Errendatze Masiboa | Begiztatu DAW proiektu-fitxategiak, "Esportazioa Amaituta" `AXSheet`-aren seinalearen zain. |
| **20. PDF Auto-Sinadura** | Lege Eragiketak | Ireki Preview, hautatu sinadura tresna, eta kokatu `AXDocument` eskualde zehatz batean. |

## 05 · Segurtasuna eta Fluxu Pertsonalak

| Kasua | Bektorea | Mekanismoa |
| :--- | :--- | :--- |
| **21. ChatOps Mahaigaineko Lotura** | Slack/Telegram | Lotu chatbot-aren `/mute` komandoa bertako Zoom `AXButton`-ari zuzenean. |
| **22. Pasahitzen Injekzio Segurua** | SecOps | Injektatu pasahitzak pasahitz-kudeatzaileekiko erresistenteak diren inprimakietan. |
| **23. Ikusizko Triajea** | Apple Mail | Artxibatu mezuak multzoka, ikusizko `AXRow` identifikatzaile zehatzekin bat egitean. |
| **24. Sandbox Epistemikoko Testak** | Malware Analisia | Erabili `MockBackend` malwareak macOS UI elementuekin nola jokatzen duen simulatzeko. |
| **25. Finder-eko Bulk Eragiketak** | Fitxategien Kudeaketa | Aldatu izena/ordenatu fitxategiak Finder-en, shell eragiketak blokeatuta dauden testuinguruetan. |
