# Keyboard Model — Feature Importance & Held-Out K3 Analysis

## 1. Per-Generator Detection Summary (`K1`, `K2`, Held-Out `K3`, `K4`)

| Model | Generator | Role | ROC-AUC | PR-AUC | Recall @ 1% FPR | Recall @ 5% FPR | Mean Bot Score |
| :--- | :--- | :--- | ---: | ---: | ---: | ---: | ---: |
| `logistic_regression` | `K1` | In-Distribution | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.9992 |
| `logistic_regression` | `K2` | In-Distribution | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.9921 |
| `logistic_regression` | `K3` | Held-Out (Zero-Shot) | 0.8415 | 0.8676 | 0.0353 | 0.2492 | 0.0133 |
| `logistic_regression` | `K4` | In-Distribution | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.9957 |
| `lightgbm_tuned` | `K1` | In-Distribution | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| `lightgbm_tuned` | `K2` | In-Distribution | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| `lightgbm_tuned` | `K3` | Held-Out (Zero-Shot) | 0.9951 | 0.9939 | 0.9851 | 0.9988 | 0.0067 |
| `lightgbm_tuned` | `K4` | In-Distribution | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |

## 2. Why Held-Out `K3` Evades Linear Models at 1% FPR but Is Caught by Non-Linear Trees

- **`K1` (Constant-Interval), `K2` (Uniform-Random), and `K4` (Copy-Paste Burst)** are
  perfectly separated (`ROC-AUC = 1.0000`, `Recall@1%FPR = 1.0000`) by both Scaled Logistic
  Regression and LightGBM because their first-order interval statistics (`dwell_cv`,
  `flight_cv`, `identical_interval_fraction`, `flight_min`) diverge strongly from human typing.
- **`K3` (Log-Normal Human-Distribution Mimic, Excluded from Training)** samples `dwell` and
  `flight` intervals from log-normal distributions fitted strictly on positive intervals of
  the training-split Aalto human participants.
  - Because `K3` matches human mean and variance, a linear hyperplane (`LogisticRegression`)
    trained only on `K1`/`K2`/`K4` achieves `ROC-AUC = 0.8415` on `K3`,
    with `Recall@1%FPR = 0.0353` and `Recall@5%FPR = 0.2492`.
  - **Tuned LightGBM achieves `0.9951` ROC-AUC and `0.9851` Recall @ 1% FPR**
    on held-out `K3` (`0.9969` overall ROC-AUC across all 4 generators) because tree splits
    capture higher-order structure that independent i.i.d. log-normal draws lack: zero key
    rollover (`rollover_ratio = 0`), zero correction events (`backspace_ratio = 0`), and
    missing digram autocorrelation (`lag1_autocorr_flight`).

## 3. Top 10 Standardized Features

| Rank | Feature | Standardized LR Coef | `|LR Coef|` | LightGBM Split Importance |
| ---: | :--- | ---: | ---: | ---: |
| 1 | `flight_p5` | +2.1350 | 2.1350 | 32 |
| 2 | `dwell_skew` | -1.9578 | 1.9578 | 388 |
| 3 | `rollover_ratio` | -1.8288 | 1.8288 | 19 |
| 4 | `burst_len_mean` | +1.6425 | 1.6425 | 165 |
| 5 | `typing_speed_cps` | +1.5208 | 1.5208 | 222 |
| 6 | `flight_median` | +1.4740 | 1.4740 | 29 |
| 7 | `burst_count` | -1.3588 | 1.3588 | 69 |
| 8 | `identical_interval_fraction` | +1.1150 | 1.1150 | 49 |
| 9 | `flight_p95` | -1.0877 | 1.0877 | 75 |
| 10 | `dwell_kurt` | -1.0659 | 1.0659 | 326 |
