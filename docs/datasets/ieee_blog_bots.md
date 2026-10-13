# Dataset card: Human vs. Bot Activity Dataset (Blog Platform)

- Source / DOI: IEEE DataPort, DOI `10.21227/z1tf-1v33`; local folder `Comparative Activity Patterns of Human Users and Hierarchical Bots on a Blog Platform`.
- Access date: 2026-10-13.
- Licence / terms: Not stated in the supplied `readme.md`; verify at the DOI source before redistribution.
- Citation: DOI above; author and publication citation were not observed locally.
- Modality and labels: Mouse movements, clicks, and scrolls; human plus Naive, Humanish, Mimic, and Fallible bots.
- Contents observed: `train` and `test` directories with 156 JSON files totaling about 2 MB in the depth-two inventory.
- File formats observed: One JSON object per session. `bot_info` is null for humans and contains `bot_id`, `bot_name`, and `session_timestamp` for bots. The observed schema documents `mouse_movements`, `clicks`, `scrolls`, and global `timestamps`.
- Time units and sampling rate: Documented as Unix timestamps; timestamp unit and sampling rate are not stated.
- Coordinate space: Mouse `x,y` coordinates; unit and viewport metadata are not stated.
- Known quirks: The dataset is small; bot filenames and `bot_info` expose class labels. Click metadata includes target text and CSS classes, so loaders must discard content fields.
- Loader module and version: `ml/src/botguard_ml/loaders/ieee_blog_bots.py`; P1-04.
- Canonical output shards: Parquet `mouse_events` rows, with one session processed at a time.
- Used for: External mouse test domain and held-out bot-type experiments.
- Memory/disk notes: Individual JSON sessions are small; process one session at a time.
