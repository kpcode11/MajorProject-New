## Appendix D — Synthetic bot generator specifications

All generators take `seed` and parameters. Parameters that mimic humans (means, standard deviations) are fitted on **training-split humans only**. Each synthetic session stores `bot_type` and its parameters.

### D.1 Keyboard bots (`synthetic/keyboard.py`)

| Id | Name | Behaviour |
|----|------|-----------|
| K1 | constant | Fixed dwell and flight (for example 90 ms and 120 ms) with at most 1-2 ms jitter |
| K2 | uniform | Dwell and flight drawn independently from uniform ranges (for example 40-160 ms and 50-300 ms) |
| K3 | mimic | Dwell and flight drawn from log-normal distributions fitted to the training humans' population mean and spread, independently per key (no autocorrelation structure). **Held out from training.** |
| K4 | burst | Pasted/injected input: all keys within a few milliseconds, optionally with a single long pause |

Per-session length sampled from the human length distribution. Also produce "slow bot" variants (for example K1 with 200 ms flights) to avoid the trivial rule "bots are fast".

### D.2 Touch bots (`synthetic/touch.py`)

| Id | Name | Behaviour |
|----|------|-----------|
| T1 | linear | Straight swipe, constant speed, constant pressure/size, regular sampling |
| T2 | bezier | Cubic Bezier with ease-in/out and small positional noise; pressure constant or slightly noisy |
| T3 | replay-perturb | A real training-set human gesture with small random time-scaling and offset. **Held out from training**; note that it is close to human data by construction, so report results carefully |
| T4 | tap-bot | Taps at fixed intervals with fixed dwell and identical positions |

### D.3 Human-like mouse path for the simulator (`simulator/humanlike.py`)

Used only to exercise the live system. Cubic Bezier between start and target with random control points, ease-in/ease-out time warping (smoothstep), Gaussian positional jitter of about 1-2 px, small end-of-path corrections, randomised pauses. Parameters randomised per run.

```python
import numpy as np

def bezier_path(p0, p3, n=60, jitter=1.5, rng=None):
    rng = rng or np.random.default_rng()
    p0, p3 = np.array(p0, float), np.array(p3, float)
    d = p3 - p0
    p1 = p0 + d * rng.uniform(0.2, 0.4) + rng.normal(0, 30, 2)
    p2 = p0 + d * rng.uniform(0.6, 0.8) + rng.normal(0, 30, 2)
    t = np.linspace(0, 1, n)
    t = t * t * (3 - 2 * t)                       # smoothstep easing
    t = t[:, None]
    pts = ((1 - t) ** 3) * p0 + 3 * ((1 - t) ** 2) * t * p1 + 3 * (1 - t) * t ** 2 * p2 + t ** 3 * p3
    return pts + rng.normal(0, jitter, pts.shape)
```

---
