## 2. Repository layout

```
passive-bot-guard/
├── AGENTS.md                      # canonical agent rules (Appendix G.1)
├── HANDOFF.md                     # rewritten at every task boundary (Appendix F.2)
├── PROGRESS.md                    # task table with IDs and statuses (Appendix F.1)
├── README.md
├── .env.example
├── .gitignore  .gitattributes
├── .github/copilot-instructions.md        # thin pointer to AGENTS.md
├── .cursor/rules/botguard.mdc             # thin pointer to AGENTS.md
├── config/
│   ├── datasets.example.yaml              # committed
│   └── datasets.local.yaml                # git-ignored; real Windows paths
├── docs/
│   ├── MASTER_PLAN.md                     # this file
│   ├── plan/                              # per-phase files created by scripts/split_plan.py
│   ├── decision_log.md  architecture.md  api.md  signals.md
│   ├── privacy_impact.md  threat_model.md  model_card.md  env.md  accessibility.md
│   ├── datasets/                          # one card per dataset + inventory outputs
│   └── report_assets/
├── scripts/
│   ├── tasks.py                           # cross-platform task runner (replaces make)
│   ├── status.py                          # session-start status report
│   ├── inventory.py                       # safe dataset inventory
│   ├── split_plan.py                      # splits MASTER_PLAN into docs/plan/phase_N.md
│   └── check_claims.py
├── data/                                  # git-ignored except README and fixtures
│   ├── README.md  raw_cache/  interim/  processed/  fixtures/
├── logs/                                  # git-ignored; long outputs
├── ml/        (pyproject.toml, src/botguard_ml/{schemas,loaders,synthetic,features,splits,train,calibrate,fuse,export_onnx,eval}, configs/, notebooks/, tests/)
├── backend/   (pyproject.toml, app/{main,config,schemas,store,nonce,rules,scoring,policy,tokens,ratelimit,db,retention}.py, config/, models/, tests/)
├── sdk/       (TypeScript; src/, test/)
├── portal/    (React mock portal)
├── dashboard/ (React admin UI)
├── simulator/ (bot tiers; localhost only)
├── loadtest/
├── results/   (mouse/ keyboard/ touch/ fusion/ system/)
└── .github/workflows/ci.yml
```

---
