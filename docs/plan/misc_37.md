## Questions for the human (if BLOCKED)
- Question — option A — option B
```

### F.3 Dataset card (`docs/datasets/<key>.md`)

```markdown
# Dataset card: <name>
- Source URL / DOI:
- Local folder (relative to datasets root):
- Access date:
- Licence / terms (copy the key points):
- Citation:
- Modality and labels (human / bot types):
- Contents (users, sessions, sizes):
- File formats as OBSERVED (not assumed):
- Time units and sampling rate:
- Coordinate space and screen information:
- Known quirks / issues:
- Loader module and version:
- Canonical output shards:
- Used for: (train / validate / cross-dataset test / human-FPR stress test)
- Memory/disk notes (how it is read safely):
```

### F.4 Resume prompts (the human pastes one into the next tool)

1. **Fresh start:** "Read AGENTS.md in the repository root. Run `python scripts/status.py`, read HANDOFF.md, then continue the current task. Follow the rules in AGENTS.md. Work in small steps and update PROGRESS.md and HANDOFF.md after every task."
2. **After a cut-off:** "The previous tool ran out of tokens. Read AGENTS.md, run `python scripts/status.py`, read HANDOFF.md, check `git status` and `git diff --stat`, run `python scripts/tasks.py test-fast`, then decide whether to keep or stash uncommitted changes (record the decision in HANDOFF.md) and continue the in-progress task."
3. **Start a phase:** "Read AGENTS.md and docs/plan/phase_N.md. Create branch phase-N-<name>. Start with the first TODO task of Phase N. Stop at any [HUMAN] task and ask me."
4. **Review before accepting results:** "Review the current results for leakage, dataset-fingerprint effects and unrealistically high scores before I accept them. Use the Pitfalls sections and Appendix E. Do not change code; write findings to docs/review_notes.md."
5. **Phase finished:** "Run the acceptance criteria of Phase N, list which pass or fail, summarise deviations from the plan, update PROGRESS.md and HANDOFF.md, and propose the next phase."

---
