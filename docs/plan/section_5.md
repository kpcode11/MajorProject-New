## 5. Dataset inventory and data strategy

### 5.1 Where the data is

Root folder: `C:\Users\KESHAV\Downloads\datasets` (read-only inputs; see Section 0.7).

```yaml
# config/datasets.local.yaml (git-ignored)  — copy to config/datasets.example.yaml with a placeholder root
datasets_root: 'C:\Users\KESHAV\Downloads\datasets'
datasets:
  web_bot_detection:  { folder: "web_bot_detection_dataset", status: available }
  ieee_blog_bots:     { folder: "Comparative Activity Patterns of Human Users and Hierarchical Bots on a Blog Platform", status: available }
  captchasolve30k:    { folder: "CaptchaSolve30k", status: available }
  aalto_keystrokes:   { folder: "Keystrokes", status: available }
  delbot_mouse:       { folder: "DELBOT-Mouse", status: to_clone }        # not downloaded yet; see P1-07
  ul_keystroke_repo:  { folder: "FILL_IN_FOLDER_NAME", status: repo_only } # GitHub repo aronlo98/tesis; human fills in the local folder name
  becaptcha_mouse:    { status: unavailable }
  cmu_keystroke:      { status: unavailable }
  mobile_touch:       { status: none_yet }
limits: { max_ram_gb: 6, max_interim_gb: 5, default_max_sessions: 500, default_max_participants: 1000 }
```

### 5.2 Inventory table

| Key | Modality | Status | Labels | Size / notes | Role in this project |
|-----|----------|--------|--------|--------------|----------------------|
| `web_bot_detection` (Bournemouth Web Bot Detection Dataset) | Mouse + web logs | **Available** | Humans, moderate bots, advanced (human-like) bots | Two parts: part 1 has 50 human sessions plus equal numbers of moderate and advanced bot sessions; part 2 has 56 human sessions (28 users x 2, about 15-20 minutes each) plus equal bot sessions. Built on Wikipedia-derived pages. Includes a README describing the structure | **Primary labelled mouse dataset.** Treat part 1 and part 2 as two domains for cross-phase evaluation |
| `ieee_blog_bots` (IEEE DataPort, DOI 10.21227/z1tf-1v33) | Mouse + clicks + scrolls | **Available** | Humans plus 4 bot types: naive, humanish, mimic, fallible | Very small (about 0.5 MB zip; CSV/JSON; the authors cut it into 10-second samples giving about 567 samples in total). Includes `readme.md` | **External test domain and held-out-bot-type experiments.** Too small to be the main training source; report wide confidence intervals |
| `captchasolve30k` (Hugging Face `T40/CaptchaSolve30k`, also listed as `Capycap-AI/CaptchaSolve30k`) | Mouse (game tasks) | **Available** | **Humans only** | About 4.8 GB; 30,000 sessions in 3 game types; coordinates normalised to a 200x200 logical grid; 240 Hz physics ticks plus raw 1000 Hz samples stored as a base64 stream (9 bytes per sample: float32 x, float32 y, 1 byte button state); a `touchscreen` flag per session | **Human-only false-positive stress test** and source for fitting human distributions. **Not** a main training source (see 5.3) |
| `aalto_keystrokes` (Aalto 136M Keystrokes, CHI 2018) | Keyboard | **Available** (folder `Keystrokes`) | **Humans only** | 168,000 participants; about 1.4 GB zipped and 16 GB unzipped; keystroke-by-keystroke text files plus a metadata file and `readme.txt` | **Primary keyboard human data.** Sample participants; never load everything |
| `delbot_mouse` | Mouse | **Not downloaded**; public GitHub repo `chrisgdt/DELBOT-Mouse` | Human and bot (per repo) | Repository includes a dataset archive per its README (verify) | Second labelled mouse dataset for cross-dataset evaluation, if it can be obtained (P1-07) |
| `ul_keystroke_repo` | Keyboard | **Repo only** (`github.com/aronlo98/tesis`); dataset not obtained | Unknown | Contents unknown; inspect only | Low priority; may contain code or data for a web keystroke collector; use only if it holds usable data |
| `becaptcha_mouse` | Mouse | **Unavailable** | - | - | Record in decision log; do not attempt workarounds |
| `cmu_keystroke` | Keyboard | **Unavailable** | - | - | Record in decision log |
| `mobile_touch` | Touch | **None yet** | - | - | See Phase 8 decision gate and candidate sources in 5.5 |

### 5.3 Handling notes and risks per dataset

**Bournemouth (primary mouse).**
- Verify structure from its README before writing the loader. Expect separate mouse-movement data and web logs; the model uses mouse data; web logs are optional context only.
- Both bot classes were produced by the dataset authors; in-dataset scores will be optimistic. Always report cross-phase and cross-dataset results.
- Human participants were mostly researchers/volunteers in a research setting; say so in the model card.

**IEEE blog bots (external domain).**
- Tiny. Use as a **test domain** (train on Bournemouth, test on IEEE) and for **held-out bot-type** tests (for example hold out `mimic`). The small size means confidence intervals will be wide; report them.
- DataPort normally requires a login/subscription to download; the human already has the files. Cite the DOI.

**CaptchaSolve30k (human-only, different domain).**
- It contains humans only, so it must **not** be mixed in as the human class against bots from other datasets: the model could learn "game-task style means human" instead of human vs bot (a dataset confound).
- Use it for: (a) **human false-positive stress test** (what fraction of these humans does the model flag?), (b) fitting human movement statistics for synthetic generators, (c) a dataset-fingerprint check in Phase 1.
- Coordinates are normalised to a 200x200 grid and render size was randomised, so absolute pixel features are meaningless there. Compare only **scale-invariant** features across datasets, or normalise per window.
- Terms of use (from its dataset card): no re-identification; no biometric profiling or behavioural authentication; permitted for bot-detection and ML research; redistribution of derivatives must carry the same restrictions; the author asks to be told if used in a paper. This project only does bot detection and never builds user-identification features.
- Some sessions have `touchscreen = true`. These can serve only as a weak sanity check for touch-like behaviour, not as a touch training set (no pressure/size, normalised coordinates).

**Aalto keystrokes (primary keyboard human data).**
- Free for research and non-commercial use with attribution. Cite Dhakal et al., CHI 2018, DOI 10.1145/3173574.3174220.
- Check whether the folder holds the `.zip` or the extracted text files. Do not extract the zip fully. Process participant files one at a time.
- From the dataset's publication and readme (verify against the real files): one text file per participant with per-keystroke rows including press time, release time, the displayed sentence, the typed input and a key identity/keycode column. **Map the key identity to a `key_class` in memory and drop it immediately.** Treat each typed sentence (test section) as one typing window, keeping windows with at least 10 key events.
- Browser keycode hints (verify with the readme): letters 65-90, digits 48-57 and numpad 96-105, space 32, Enter 13, Backspace 8, Shift/Ctrl/Alt 16/17/18, Tab 9, punctuation roughly 186-192 and 219-222.
- Participants vary a lot in speed and style; use participant-grouped splits and report results by speed tercile.
- Human-only: all bot data is synthetic (Appendix D.1).

**DELBOT-Mouse.** `git clone --depth 1 https://github.com/chrisgdt/DELBOT-Mouse "<datasets_root>/DELBOT-Mouse"`. Check the size of any dataset archive before extracting (see 0.7). If cloning is not possible in the agent's environment, mark `[HUMAN]` and continue with the other datasets.

### 5.4 Cross-dataset design with the data that exists

| Experiment | Train on | Test on | Notes |
|------------|----------|---------|-------|
| In-distribution | Bournemouth (grouped split) | Bournemouth held-out groups | Optimistic; report but do not headline |
| Cross-phase | Bournemouth part 1 | Bournemouth part 2 (and reverse) | Different participants and a larger site version |
| Cross-dataset | Bournemouth (+ DELBOT if obtained) | IEEE blog bots | Test set is small; wide CIs |
| Reverse cross-dataset (optional) | IEEE | Bournemouth | Small training set; treat as exploratory |
| Held-out bot type | Bournemouth minus one bot class; IEEE minus `mimic`/`fallible` | The held-out class | Shows generalisation to unseen bots |
| Human FPR stress test | Final mouse model | CaptchaSolve30k (human only) | Report share of humans flagged at the chosen thresholds, by game type |
| Keyboard | Aalto participants (grouped) + synthetic bots | Held-out participants; held-out generator K3 | Optional second human source for FPR (see Phase 3) |

### 5.5 Mobile touch: situation and candidate sources

No touch dataset is available yet. All known candidates are **human-only** (built for authentication research), so touch bots would be synthetic. Candidates to try (verify availability and terms; all are optional):

| Candidate | Where | Notes |
|-----------|-------|-------|
| HuMIdb | `github.com/BiDAlab/HuMIdb` | 600 users, many sensors; may require an access request |
| BioIdent | `ms.sapientia.ro/~manyi/bioident.html` | 71 subjects, 8 Android devices, raw stroke data download listed on the page |
| SU-AIS BB-MAS | IEEE DataPort, DOI 10.21227/rpaz-0h66 (free IEEE account) | 117 participants; swipes plus desktop/phone keystrokes; also a possible **second human keyboard source** for cross-dataset FPR checks |
| H-MOG | `cs.wm.edu/~qyang/hmog.html` | 100 volunteers, about 6 GB compressed, download needs agreeing to terms |

Phase 8 defines a decision gate: with at least one candidate obtained, train a touch model (Path A); otherwise deliver **mobile readiness without a trained touch model** (Path B) and say so clearly in the report and presentation.

---
