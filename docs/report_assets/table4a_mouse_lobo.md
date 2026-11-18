# Table 4a — Mouse Leave-One-Bot-Type-Out (LOBO) Generalisation

| held_out_bot_type | dataset | n_bot_windows | n_bot_sessions | n_eval_human_windows | roc_auc | pr_auc | mean_bot_score | bot_recall_at_05 | bot_recall_at_1pct_fpr | bot_recall_at_5pct_fpr |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| advanced | web_bot_detection | 8303 | 170 | 964 | 0.9710 | 0.9935 | 0.0585 | 0.0426 | 0.2025 | 0.9026 |
| fallible | ieee_blog_bots | 302 | 35 | 111 | 0.9947 | 0.9972 | 0.9420 | 0.9702 | 0.9603 | 0.9735 |
| gan | delbot_mouse | 1899 | 1899 | 237 | 0.4872 | 0.8627 | 0.0286 | 0.0274 | 0.0026 | 0.0026 |
| humanish | ieee_blog_bots | 59 | 12 | 111 | 0.9927 | 0.9858 | 0.9120 | 0.9322 | 0.8983 | 0.9492 |
| mimic | ieee_blog_bots | 252 | 35 | 111 | 0.9950 | 0.9964 | 0.9461 | 0.9762 | 0.9762 | 0.9802 |
| moderate | web_bot_detection | 4174 | 170 | 964 | 0.9195 | 0.9671 | 0.0701 | 0.0640 | 0.0630 | 0.3896 |
| naturalmousemotion | delbot_mouse | 877 | 234 | 237 | 0.8365 | 0.9397 | 0.4603 | 0.7651 | 0.0274 | 0.7640 |
| pyhm | delbot_mouse | 55 | 55 | 237 | 0.9490 | 0.8475 | 0.7955 | 0.8364 | 0.5818 | 0.6909 |
| pynput | delbot_mouse | 531 | 351 | 237 | 0.8202 | 0.8753 | 0.3050 | 0.3446 | 0.3107 | 0.3107 |
