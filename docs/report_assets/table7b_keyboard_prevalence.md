# Table 7b — Keyboard Precision & PR-AUC Under 1%, 5%, and 20% Bot Prevalence

> Reweighted test-set evaluation per Appendix E.4 (synthetic bot classes).

| modality | split | bot_prevalence | weighted_pr_auc | precision_at_1pct_fpr | recall_at_1pct_fpr | precision_at_5pct_fpr | recall_at_5pct_fpr | n_human_eval | n_bot_eval |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| keyboard | in_dist_K1_K2_K4 | 0.0100 | 1.0000 | 0.5003 | 1.0000 | 0.1678 | 1.0000 | 2775 | 3003 |
| keyboard | in_dist_K1_K2_K4 | 0.0500 | 1.0000 | 0.8391 | 1.0000 | 0.5124 | 1.0000 | 2775 | 3003 |
| keyboard | in_dist_K1_K2_K4 | 0.2000 | 1.0000 | 0.9612 | 1.0000 | 0.8331 | 1.0000 | 2775 | 3003 |
| keyboard | overall_with_held_out_K3 | 0.0100 | 0.4321 | 0.2880 | 0.4041 | 0.0973 | 0.5346 | 2775 | 7983 |
| keyboard | overall_with_held_out_K3 | 0.0500 | 0.5550 | 0.6782 | 0.4041 | 0.3597 | 0.5346 | 2775 | 7983 |
| keyboard | overall_with_held_out_K3 | 0.2000 | 0.7496 | 0.9092 | 0.4041 | 0.7274 | 0.5346 | 2775 | 7983 |
