# Data directory

This directory holds generated and cached project data only. Raw datasets remain
read-only at the path configured in `config/datasets.local.yaml` and must never
be copied into the repository. Generated shards, models, and logs are ignored by
Git.

`fixtures/` may contain only tiny, synthetic test fixtures with no typed text or
personal data.
