# Table 2b — Keyboard Model Baselines (Aalto + Synthetic K1/K2/K4)

> Keyboard bot classes K1-K4 are synthetic (Appendix D.1); Aalto is human-only.

| model | accuracy | balanced_accuracy | roc_auc | n_train | n_test | n_train_groups | n_test_groups |
| --- | --- | --- | --- | --- | --- | --- | --- |
| majority | 0.4803 | 0.5000 | 0.5000 | 24104 | 5778 | 12750 | 3188 |
| logistic_regression | 0.9997 | 0.9996 | 1.0000 | 24104 | 5778 | 12750 | 3188 |
| random_forest | 1.0000 | 1.0000 | 1.0000 | 24104 | 5778 | 12750 | 3188 |
| lightgbm | 1.0000 | 1.0000 | 1.0000 | 24104 | 5778 | 12750 | 3188 |
