# Table 7a — Mouse Precision & PR-AUC Under 1%, 5%, and 20% Bot Prevalence

> Reweighted test-set evaluation per Appendix E.4.

| modality | split | bot_prevalence | weighted_pr_auc | precision_at_1pct_fpr | recall_at_1pct_fpr | precision_at_5pct_fpr | recall_at_5pct_fpr | n_human_eval | n_bot_eval |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| mouse | in_dist_bournemouth | 0.0100 | 0.6903 | 0.4814 | 0.9496 | 0.1671 | 0.9938 | 2419 | 2739 |
| mouse | in_dist_bournemouth | 0.0500 | 0.9124 | 0.8287 | 0.9496 | 0.5112 | 0.9938 | 2419 | 2739 |
| mouse | in_dist_bournemouth | 0.2000 | 0.9783 | 0.9583 | 0.9496 | 0.8324 | 0.9938 | 2419 | 2739 |
| mouse | cross_phase_P1_to_P2 | 0.0100 | 0.2187 | 0.2804 | 0.3897 | 0.1457 | 0.8461 | 7225 | 8052 |
| mouse | cross_phase_P1_to_P2 | 0.0500 | 0.5760 | 0.6700 | 0.3897 | 0.4706 | 0.8461 | 7225 | 8052 |
| mouse | cross_phase_P1_to_P2 | 0.2000 | 0.8544 | 0.9060 | 0.3897 | 0.8085 | 0.8461 | 7225 | 8052 |
| mouse | cross_dataset_Bournemouth_to_IEEE | 0.0100 | 0.8205 | 0.4081 | 0.8173 | 0.1468 | 0.8842 | 501 | 613 |
| mouse | cross_dataset_Bournemouth_to_IEEE | 0.0500 | 0.8862 | 0.7822 | 0.8173 | 0.4728 | 0.8842 | 501 | 613 |
| mouse | cross_dataset_Bournemouth_to_IEEE | 0.2000 | 0.9463 | 0.9446 | 0.8173 | 0.8099 | 0.8842 | 501 | 613 |
