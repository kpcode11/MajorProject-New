# Dataset card: Bournemouth Web Bot Detection Dataset

- Source / local folder: `web_bot_detection_dataset` under the configured datasets root.
- Access date: 2026-10-13.
- Licence / terms: Not stated in the supplied `README.docx`; verify before redistribution.
- Citation: The supplied README refers to `[1]`, but its bibliographic entry was not observed.
- Modality and labels: Mouse movements and web logs; human, moderate bot, advanced bot.
- Contents observed: `phase1` and `phase2`, each with annotation, mouse-movement, and web-log directories. Phase 1 documentation states 50 human sessions; Phase 2 states 56 human sessions (28 people × 2). Each phase has equal numbers of moderate and advanced bot sessions.
- File formats observed: Phase 1 annotations are described as two space-separated columns (PHP session ID, label); phase 1 mouse files are per-session `mouse_movements.json`. Phase 2 mouse data are MongoDB JSON exports.
- Time units and sampling rate: Mouse timestamps are documented but their unit and sampling rate are not stated.
- Coordinate space: `x,y` mouse coordinates; phase 2 also includes client height and width. Unit is not stated.
- Known quirks: Both bot classes were created by the dataset authors; phase layouts and exports differ. Web logs include session IDs and are not needed for the mouse model.
- Loader module and version: Pending P1-03.
- Canonical output shards: Pending P1-03.
- Used for: Primary labelled mouse training and phase-1/phase-2 evaluation.
- Memory/disk notes: Inventory only traversed two directory levels; loaders must process sessions incrementally.
