# Table 5b — Rule-Layer vs ML-Model Ablation Across Simulator Bot Tiers

> Compares deterministic environment rules only, ML models only, and combined max(model, rule).

| bot_tier | description | n_sessions | rules_only_caught_rate | model_only_caught_rate | combined_max_caught_rate | mean_rule_score | mean_model_score | mean_combined_score |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| tier1_http | No token / plain HTTP | 25 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | 0.0000 | 1.0000 |
| tier2_playwright | Headless WebDriver + software WebGL + 0 moves | 25 | 1.0000 | 1.0000 | 1.0000 | 0.7260 | 0.5000 | 0.7260 |
| tier3_stealth | Stealth init-script + linear mechanical mouse | 25 | 1.0000 | 1.0000 | 1.0000 | 0.3000 | 0.9620 | 0.9620 |
| tier4_humanlike | Cubic Bezier + smoothstep + Gaussian jitter | 25 | 0.0000 | 1.0000 | 0.9200 | 0.0000 | 0.7840 | 0.7840 |
