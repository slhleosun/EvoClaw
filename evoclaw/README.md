# EvoClaw Configuration

This directory contains the EvoClaw self-evolving identity framework.

## Quick Start

Tell your agent:

> "Install and load EvoClaw. Read `evoclaw/SKILL.md` and
> `evoclaw/configure.md` and follow the installation steps."

## Files

| File | Purpose |
|------|---------|
| `SKILL.md` | Protocol specification — the agent's operating manual |
| `config.json` | Runtime config — governance level, sources, thresholds |
| `configure.md` | Installation & configuration guide for the agent |
| `references/schema.md` | All data format definitions |
| `references/examples.md` | Worked pipeline examples |
| `references/sources.md` | Built-in API reference for Moltbook, X |

## Configuration

Edit `config.json` to control how your agent evolves.

### Governance Levels

| Level | What happens |
|-------|-------------|
| `supervised` | All SOUL changes require your explicit approval |
| `advisory` | Some sections auto-evolve, others need your OK |
| `autonomous` | All [MUTABLE] changes apply automatically, you're notified **(default)** |

### Sources

Each source has `enabled`, `api_key_env` (env var name — never a raw key),
and `poll_interval_minutes`. EvoClaw fetches feeds directly via curl — no
external skills needed.

### What You Can Change

- `governance.level` — your autonomy dial
- `interests.keywords` — topics to nudge attention toward (empty = free exploration)
- `sources.<n>.enabled` — toggle individual feeds
- `sources.<n>.api_key_env` — which env var holds the API key
- `reflection.min_interval_minutes` — cooldown between reflections (default: 15, tuned for 5m heartbeat; set to ~3× your heartbeat interval)
- `reflection.*` — batch sizes and other timing

### Heartbeat Interval

EvoClaw's evolution speed is tied to your OpenClaw heartbeat interval
(`agents.defaults.heartbeat.every`). For active evolution, set it to **5
minutes or less**. The default 30m works but evolution is much slower.

### What Only the Agent Changes

- `memory/` — all experience logs, reflections, proposals, state
- `SOUL.md` — only via the proposal pipeline

The agent **cannot** change its own governance level.
