# Table 5b — Rule-Layer vs ML-Model Ablation Across Simulator Bot Tiers

> Measured by replaying the seed-42 simulator against the real scorer; a session is caught when the policy verdict on its first /v1/assess score is not allow (before any step-up). Sessions rejected before /v1/assess are excluded from the rates and counted in n_blocked_before_assess.

| bot_tier | description | n_sessions_total | n_reached_assess | n_blocked_before_assess | rules_only_caught_rate | model_only_caught_rate | combined_caught_rate | mean_rule_score | mean_model_score | mean_combined_score |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| tier1 | Plain HTTP client (no browser) | 25 | 6 | 19 | 1.0000 | 0.0000 | 1.0000 | 0.8000 | 0.0000 | 0.8000 |
| tier2 | Default headless Playwright, direct fill/click | 25 | 25 | 0 | 1.0000 | 0.0000 | 1.0000 | 0.7858 | 0.0000 | 0.7858 |
| tier3 | Playwright with automation-hiding adjustments | 25 | 25 | 0 | 0.5600 | 1.0000 | 1.0000 | 0.3981 | 0.8744 | 0.8918 |
| tier4 | Playwright with Bezier mouse paths + randomised typing | 25 | 25 | 0 | 0.2800 | 1.0000 | 1.0000 | 0.0600 | 0.9023 | 0.9023 |
