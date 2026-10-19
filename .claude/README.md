# Claude Code configuration guide

## Files

- `../CLAUDE.md`: always-on project rules and teaching contract.
- `agents/teacher.md`: coaching and comprehension.
- `agents/supply-chain-analyst.md`: planning logic and KPI review.
- `agents/data-engineer.md`: SQL, data modelling and pipeline review.
- `agents/reviewer.md`: read-only quality review.
- `skills/*/SKILL.md`: task-specific instructions loaded when relevant.

## Suggested usage

- Use the main assistant for ordinary implementation.
- Ask the teacher agent to explain concepts or quiz you.
- Ask the supply-chain analyst to review assumptions and planning rules.
- Ask the data engineer to review schemas, ingestion and SQL.
- Ask the reviewer before merging a meaningful milestone.

Avoid invoking every agent for every task: this costs time and tokens and can produce conflicting feedback. Give each agent a narrow question and pass it the relevant files.

## Working agreements

- Agents must not claim to have run commands or tests unless they did.
- Review agents should report findings with severity, file/line references when available, evidence and suggested fixes.
- Agents should not rewrite large parts of the project during a review unless explicitly asked.
- Skills provide reusable procedures; agents provide a specialised role. Keep them distinct.
