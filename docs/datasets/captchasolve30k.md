# Dataset card: CaptchaSolve30k

- Source / local folder: `CaptchaSolve30k`; supplied README identifies `Capycap-AI/CaptchaSolve30k`.
- Access date: 2026-10-13.
- Licence / terms: Apache-2.0 metadata plus supplied terms prohibiting re-identification and biometric profiling; permitted uses include AI research and bot detection. Redistribution must preserve those restrictions.
- Citation: The README requests that paper users contact its author for a DOI; no formal citation was observed locally.
- Modality and labels: Human mouse/touch trajectories only; 30,000 sessions across sheep-herding, thread-the-needle, and polygon-stacking.
- Contents observed: `train.jsonl` (3.0 GB), `validation.jsonl` (802 MB), and `test.jsonl` (812 MB), about 4.0 GB total.
- File formats observed: JSON Lines; fields include `gameType`, `duration` (milliseconds), `physicsTickCount`, `tickInputs`, base64 `inputStream`, `inputSampleCount`, and `touchscreen`.
- Time units and sampling rate: Physics ticks at 240 Hz; raw input samples at 1000 Hz. Raw samples are 9 bytes: little-endian float32 x, float32 y, button byte.
- Coordinate space: Normalized 200×200 logical grid; raw screen coordinates are not stored.
- Known quirks: Game-task domain differs from browsing; it is human-only and must not become the primary labelled training set.
- Loader module and version: Pending P1-05.
- Canonical output shards: Pending P1-05.
- Used for: Human false-positive stress test and fitting training-only human movement distributions.
- Memory/disk notes: Stream JSONL; never load a split into memory or extract data.
