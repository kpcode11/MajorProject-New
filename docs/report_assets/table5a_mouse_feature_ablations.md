# Table 5a — Mouse Feature-Group and Shortcut-Feature Ablation

| configuration | model | roc_auc | n_features | n_train_groups | n_test_groups |
| --- | --- | --- | --- | --- | --- |
| all_with_shortcuts | logistic_regression | 0.9902 | 120 | 3254 | 814 |
| all_without_shortcuts | logistic_regression | 0.9862 | 108 | 3254 | 814 |
| group_kinematics | logistic_regression | 0.9648 | 54 | 3254 | 814 |
| group_geometry | logistic_regression | 0.8890 | 21 | 3254 | 814 |
| group_timing | logistic_regression | 0.9687 | 38 | 3254 | 814 |
| group_click | logistic_regression | 0.5330 | 9 | 3254 | 814 |
