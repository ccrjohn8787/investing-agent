## GitHub Project Board Setup

This repo tracks milestones from `docs/ROADMAP.md` via a GitHub Project board. Use these steps to create and maintain the board.

### Create the Project
1. In GitHub UI, go to the repo → Projects → “New project” → “Board”. Name it “DBOT Roadmap”.
2. Columns: `Backlog`, `In Progress`, `Review`, `Done`. Enable auto-archive of `Done` after 14 days.
3. Add saved views: `Milestones` (group by label), `Agents` (filter `label:agent`), `Connectors` (filter `label:connector`).

### Labels
- Priority labels (DBOT Quality Gap): `P0-Evaluation`, `P1-Evidence`, `P2-Writer`, `P3-Comparables`, `P4-Prompts`, `P5-Router`, `P6-Structure`, `P7-Dashboard`, `P8-UI`.
- Component labels: `agent`, `kernel`, `connector`, `writer`, `cli`, `docs`, `ui`, `evaluation`.
- Status labels: `completed`, `in-progress`, `pending`.

### Seed Issues (suggested)
- Create one issue per milestone with a checklist matching `docs/ROADMAP.md` and link to it.
- Create issues for near-term next actions (router heuristic, market/consensus/comparables transforms, citations enforcement, UST/prices metadata).

### Automation (optional)
- Use GitHub Actions to add labels based on paths (e.g., changes in `investing_agent/agents/**` → label `agent`).
- Consider using `gh` CLI locally to bulk-create issues/labels (script not included here).

### Keep in Sync
- When closing a milestone item, update `docs/ROADMAP.md` and move the corresponding card to `Done`.
- Reference milestone IDs in PR titles or descriptions.

