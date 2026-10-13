# Dataset card: DELBOT-Mouse

- Source: `https://github.com/chrisgdt/DELBOT-Mouse`, shallow clone at the configured dataset root.
- Access date: 2026-10-13.
- Licence / terms: Repository `LICENSE.md`; verify the upstream licence before redistribution.
- Citation: Christophe Grandmont, DELBOT-Mouse repository; no formal publication citation was observed in the repository README.
- Modality and labels: Mouse trajectories from human sessions and bot generators, including `pynput`, `naturalmousemotion`, `pyhm`, and GAN-generated trajectories.
- Contents observed: `python/dataset.tar.gz`, 4,623,382 bytes compressed and approximately 17.5 MB uncompressed; 3,551 text trajectories.
- File format observed: One `resolution:w,h` header followed by comma-separated `timestamp,event,x,y` rows. Event types include `Move`, `Pressed`, `Released`, and touch variants.
- Time units and sampling rate: Relative event timestamps are observed in milliseconds; no fixed sampling rate is claimed.
- Coordinate space: Pixel coordinates with per-session resolution metadata.
- Known quirks: The source is a prototype dataset with generator-specific directories and a small human sample. The loader streams tar members and does not extract the archive. Two small samples were extracted to ignored `data/raw_cache/delbot_samples/` for inspection.
- Loader module and version: `ml/src/botguard_ml/loaders/delbot_mouse.py`; P1-07.
- Canonical output shards: Parquet `mouse_events`, with generator category as `bot_type` and `circle_task` as domain.
- Used for: Optional supplemental bot-generator training and cross-source robustness checks; not required for the primary Bournemouth training set.
- Memory/disk notes: Archive members are parsed one at a time; no full archive extraction is required.
