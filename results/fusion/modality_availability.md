# Table 6b — Missing-Modality Availability Evaluation

> Absent modalities are never penalised or treated as bot signals.

| regime | mouse_present | keyboard_present | example_mouse_score | example_keyboard_score | average_fused | noisy_or_fused | treated_as_bot_on_missing |
| --- | --- | --- | --- | --- | --- | --- | --- |
| both_available | True | True | 0.1500 | 0.2500 | 0.2000 | 0.3625 | False |
| mouse_only_available | True | False | 0.1500 | NaN | 0.1500 | 0.1500 | False |
| keyboard_only_available | False | True | NaN | 0.2500 | 0.2500 | 0.2500 | False |
| neither_available | False | False | NaN | NaN | NaN | NaN | False |
