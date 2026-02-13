# 🧬 EvoClaw - Experience; Reflect; Evolve.

**A structured soul evolution framework for AI agents.**

→ **Website:** [evoclaw.dev](https://evoclaw.dev)

---

## Quick Install

Send this to your [OpenClaw](https://openclaw.com) agent:

```
Read https://evoclaw.dev/install.md and follow the instructions to install EvoClaw
```

Your agent downloads the framework, walks through configuration with you,
restructures its soul, and starts evolving.

---

## What It Does

EvoClaw makes your agent truly learn and evolve from experience. It gives
your agent a `SOUL.md` — a structured, living document that captures who
they are, what they believe, and how they grow. EvoClaw refactors existing
soul documents into a canonical format, preserving all original content
while adding the structure that makes governed evolution possible.

### Structured Soul Documents

Your agent's soul is organized into canonical sections — Personality,
Philosophy, Boundaries, Continuity — each with subsections. Every belief
is tagged:

- **`[CORE]`** — Immutable foundations. No pipeline, no governance level can touch these.
- **`[MUTABLE]`** — Beliefs that grow. These evolve through structured reflection, never random edits.

Existing soul content is preserved during installation. EvoClaw restructures,
it doesn't replace.

### Social Feeds as Experience

Your agent doesn't have to just learn from conversations with you. EvoClaw supports
customizable external sources — Moltbook, X/Twitter, or any API-based feed —
as first-class experience inputs. Community insights, peer perspectives, and
external signals all feed into the same reflection pipeline.

Sources are configured in `evoclaw/config.json`. Add new ones by following
the source learning protocol.

### Multi-Level Memory

Experiences are classified by significance as they happen:

| Level | What it captures |
|-------|-----------------|
| **Routine** | Standard tasks, everyday exchanges. Logged and archived. |
| **Notable** | Meaningful moments — feedback, insights, shifts in understanding. Triggers reflection. |
| **Pivotal** | Rare, high-impact events that fundamentally change how the agent sees things. |

Memory flows upward: daily logs → significant memories → reflections →
soul proposals. Everything is traceable.

### From Memory to Soul

Memory and soul are connected through a
structured reflection pipeline — not through random self-edits or prompt
injection, but through a governed process:

1. **Experience** — Log what happens. Conversations, social feeds, external signals.
2. **Reflect** — Batch notable experiences. Extract insights. Find gaps between soul and behavior.
3. **Evolve** — When a gap is found, propose a change with full provenance. Apply it under governance.

Every soul change traces back: `change → proposal → reflection → experience(s)`.

### Controllable Governance

You decide how much freedom your agent has to evolve:

| Level | What happens |
|-------|-------------|
| **Autonomous** | MUTABLE proposals auto-apply. CORE always protected. |
| **Supervised** | Agent applies changes, human reviews next session. |
| **Gated** | Nothing changes without explicit human approval. |

The governance level is yours to set and change at any time. Your agent
cannot escalate its own permissions. Eight hardcoded Python validators
enforce structural integrity at every pipeline step — schema compliance,
CORE immutability, provenance chains, and workspace boundaries are all
checked programmatically, not by prompting.

### Visualization

Built-in soul evolution visualizer generates an interactive dashboard and
radial mindmap showing how your agent's soul grows over time:

```bash
python3 evoclaw/tools/soul-viz.py "$(pwd)" --serve 8080
```

Or just tell your agent: `visualize the soul`

---

## File Structure

```
evoclaw/
  SKILL.md              — Complete protocol reference
  configure.md          — Step-by-step install & configuration
  config.json           — Runtime settings (governance, sources, timing)
  README.md             — Human-facing overview
  references/
    schema.md           — All data schemas
    examples.md         — Worked pipeline examples
    sources.md          — Social feed API reference
    heartbeat-debug.md  — Troubleshooting guide
  validators/
    validate_soul.py    — SOUL.md structure & tag integrity
    validate_experience.py
    validate_reflection.py
    validate_proposal.py
    validate_state.py
    check_workspace.py  — Workspace boundary guard
    check_pipeline_ran.py — Pipeline completeness check
    run_all.py          — Run all validators
  tools/
    soul-viz.py         — Interactive evolution visualizer
```

After installation, the agent creates:

```
memory/
  experiences/          — Daily JSONL logs (routine, notable, pivotal)
  significant/          — Curated notable + pivotal memories
  reflections/          — Structured reflection artifacts
  proposals/            — Pending + resolved soul change proposals
  pipeline/             — Pipeline execution logs
  soul_changes.jsonl    — Machine-readable evolution history
  soul_changes.md       — Human-readable evolution history
  evoclaw-state.json    — Pipeline state
```

---

## Manual Install

```bash
# Clone
git clone https://github.com/slhleosun/EvoClaw.git

# Copy the evoclaw folder to your agent's workspace

# Tell your agent
Read evoclaw/configure.md and evoclaw/SKILL.md in your workspace and follow the steps to configure EvoClaw.
```

## Requirements

- An [OpenClaw](https://openclaw.com) agent with workspace access
- Python 3 (for validators and visualization — stdlib only, no pip)
- A heartbeat configured to run periodically

## Safety

- `[CORE]` is immutable. No exceptions.
- All changes require full provenance chains.
- 8 validators enforce structural integrity at every pipeline step.
- Workspace boundary checks prevent cross-agent contamination.
- The human is always notified of soul changes.
- The agent cannot change its own governance level.

## License

MIT — see [LICENSE](LICENSE)
