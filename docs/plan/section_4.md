## 4. Canonical data schemas

All dataset loaders convert to these formats and write Parquet to `data/interim/`.

### 4.1 Mouse events table (`mouse_events.parquet`)

| Column | Type | Notes |
|--------|------|-------|
| `dataset` | str | e.g. `becaptcha_mouse` |
| `session_id` | str | unique within dataset |
| `subject_id` | str | participant id for humans; generator/run id for bots; never reused across classes |
| `label` | int | 0 = human, 1 = bot |
| `bot_type` | str | `human`, or dataset-specific bot class name |
| `t_ms` | float | milliseconds since session start |
| `x`, `y` | float | coordinates in the space named by `coord_space`; NaN-free after loader cleaning |
| `coord_space` | str | `pixels`, `norm01` or `grid200` (CaptchaSolve30k uses a 200x200 logical grid) |
| `event` | str | `move`, `down`, `up`, `click`, `scroll`, `other` |
| `screen_w`, `screen_h` | float | if available, else NaN |
| `domain` | str | task/site domain, e.g. `wiki_browsing`, `blog_platform`, `game_task` (used for domain-shift analysis) |
| `touchscreen` | bool | true if the source says input was from a touchscreen, else false/NaN |

### 4.2 Keystroke events table (`key_events.parquet`)

| Column | Type | Notes |
|--------|------|-------|
| `dataset`, `session_id`, `subject_id`, `label`, `bot_type` | as above | |
| `key_class` | str | `letter`, `digit`, `space`, `punct`, `modifier`, `enter`, `backspace`, `other` — **not** the key itself |
| `down_ms`, `up_ms` | float | key press/release times; if a dataset gives only hold/flight values, reconstruct timestamps and note it in the dataset card |

### 4.3 Touch events table (`touch_events.parquet`) — Phase 8

| Column | Type | Notes |
|--------|------|-------|
| `dataset`, `session_id`, `subject_id`, `label`, `bot_type` | as above | |
| `gesture` | str | `tap`, `swipe`, `drag`, `other` |
| `t_ms`, `x`, `y` | float | |
| `pressure`, `size` | float | NaN if unavailable |

### 4.4 Feature tables

`data/processed/<modality>_features.parquet`: one row per **segment or session** (define per modality), columns = `dataset`, `session_id`, `subject_id`, `label`, `bot_type`, `split_group`, then feature columns named exactly as in Appendix A. A matching `data/processed/<modality>_features.schema.json` lists feature names, dtypes and descriptions.

### 4.5 Dataset manifest

`data/manifest.json` records for each file: dataset name, source URL, access date, file size and modified time, SHA-256 of the **first 1 MB** for large files (full SHA-256 only for files under 100 MB), licence/terms note, loader version. The agent updates it whenever data changes.

---
