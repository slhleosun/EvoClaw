# EvoClaw Data Schemas Reference

All schemas used by EvoClaw. For full protocol, see `evoclaw/SKILL.md`.

---

## SOUL.md Bullet Format

Tags go at the **end** of the line, after content:

```markdown
- Content describing a value or behavior [MUTABLE]
- Content describing an immutable rule [CORE]
```

Never at the start: ~~`- [MUTABLE] Content`~~ is wrong.

In proposal schemas, `proposed_content` is the full line:
`"- Prioritize directness over hedging [MUTABLE]"`

---

## Experience Entry

File: `memory/experiences/YYYY-MM-DD.jsonl`

```json
{
  "id": "EXP-20260212-0001",
  "timestamp": "2026-02-12T14:30:00Z",
  "source": "conversation",
  "content": "User discussed methodology preferences, expressed frustration with verbose outputs.",
  "significance": "notable",
  "significance_reason": "Reveals core human preference that should inform communication style.",
  "reflected": false
}
```

**Source values:** `conversation`, `moltbook`, `x`, `heartbeat`, `other`

**Significance values:** `routine`, `notable`, `pivotal`

---

## Significant Memory

File: `memory/significant/significant.jsonl`

```json
{
  "id": "SIG-20260212-0001",
  "experience_id": "EXP-20260212-0001",
  "timestamp": "2026-02-12T14:30:00Z",
  "source": "conversation",
  "significance": "notable",
  "content": "User discussed methodology preferences, expressed frustration with verbose outputs.",
  "context": "Third time human expressed preference for conciseness. Pattern is consistent.",
  "reflected": false
}
```

---

## Reflection Artifact

File: `memory/reflections/REF-YYYYMMDD-NNN.json`

```json
{
  "id": "REF-20260212-001",
  "timestamp": "2026-02-12T15:00:00Z",
  "type": "notable_batch",
  "experience_ids": ["EXP-20260212-0001", "EXP-20260211-0007"],
  "summary": "Multiple interactions confirm human strongly values directness and technical precision.",
  "insights": [
    "User prefers honest, concise feedback even when blunt.",
    "Technical accuracy weighted more heavily than social comfort."
  ],
  "soul_relevance": "Current Talking Style doesn't explicitly commit to directness. Stronger statement may be warranted.",
  "proposal_decision": {
    "should_propose": true,
    "triggers_fired": ["gap"],
    "reasoning": "SOUL.md Talking Style section doesn't mention directness or technical precision, but these are clearly part of how I communicate now. Gap between lived behavior and documented identity."
  },
  "proposals": ["PROP-20260212-001"],
  "meta": {
    "experiences_count": 2,
    "time_span": "2026-02-11 to 2026-02-12"
  }
}
```

**Type values:** `routine_batch`, `notable_batch`, `pivotal_immediate`

**`proposal_decision` is mandatory.** Every reflection must explicitly reason
about whether to propose changes. `triggers_fired` uses values from the
proposal trigger checklist: `gap`, `drift`, `contradiction`, `growth`,
`refinement`. If `should_propose` is false, `reasoning` must explain what
was checked and why no change is needed.

---

## Proposal

File: `memory/proposals/pending.jsonl` or `memory/proposals/history.jsonl`

```json
{
  "id": "PROP-20260212-001",
  "timestamp": "2026-02-12T15:00:00Z",
  "reflection_id": "REF-20260212-001",
  "target_section": "## Personality",
  "target_subsection": "### Talking style",
  "change_type": "add",
  "current_content": null,
  "proposed_content": "- Prioritize directness and technical precision over diplomatic hedging [MUTABLE]",
  "tag": "[MUTABLE]",
  "reason": "Repeated interactions (EXP-20260212-0001, EXP-20260211-0007) confirm human values blunt, precise communication.",
  "experience_ids": ["EXP-20260212-0001", "EXP-20260211-0007"],
  "status": "pending",
  "resolved_at": null,
  "resolved_by": null
}
```

**Status:** `pending`, `approved`, `applied`, `rejected`
**Change type:** `add`, `modify`, `remove`
**Resolved by:** `auto`, `human`, `null`

---

## Change Log Entry

File: `memory/soul_changes.jsonl`

```json
{
  "id": "CHG-20260212-001",
  "timestamp": "2026-02-12T15:05:00Z",
  "proposal_id": "PROP-20260212-001",
  "reflection_id": "REF-20260212-001",
  "experience_ids": ["EXP-20260212-0001", "EXP-20260211-0007"],
  "section": "## Personality",
  "subsection": "### Talking style",
  "change_type": "add",
  "before": null,
  "after": "- Prioritize directness and technical precision over diplomatic hedging [MUTABLE]",
  "governance_level": "autonomous",
  "resolved_by": "auto"
}
```

---

## EvoClaw State

File: `memory/evoclaw-state.json`

```json
{
  "last_reflection_at": "2026-02-12T15:00:00Z",
  "last_heartbeat_at": "2026-02-12T15:05:00Z",
  "pending_proposals_count": 0,
  "total_experiences_today": 5,
  "total_reflections": 1,
  "total_soul_changes": 1,
  "source_last_polled": {
    "moltbook": "2026-02-12T12:00:00Z",
    "x": null
  }
}
```

---

## Configuration

File: `evoclaw/config.json`

```json
{
  "version": 1,
  "governance": {
    "level": "autonomous"
  },
  "reflection": {
    "routine_batch_size": 20,
    "notable_batch_size": 2,
    "pivotal_immediate": true,
    "min_interval_minutes": 15
  },
  "interests": {
    "keywords": ["agent identity", "AI safety"]
  },
  "sources": {
    "conversation": { "enabled": true },
    "moltbook": {
      "enabled": false,
      "api_key_env": "MOLTBOOK_API_KEY",
      "poll_interval_minutes": 5
    },
    "x": {
      "enabled": false,
      "api_key_env": "X_BEARER_TOKEN",
      "poll_interval_minutes": 5
    }
  },
  "significance_thresholds": {
    "notable_description": "Meaningfully changed perspective, revealed new information, or had emotional/intellectual weight",
    "pivotal_description": "Fundamentally challenges existing beliefs, represents a crisis or breakthrough, or requires immediate identity-level response"
  }
}
```

For `advisory` governance, also include:
```json
"governance": {
  "level": "advisory",
  "advisory_auto_sections": ["Philosophy"],
  "require_approval_sections": ["Personality", "Boundaries"]
}
```

---

## ID Generation

Pattern: `PREFIX-YYYYMMDD-NNN(N)`

| Entity | Prefix | Digits | Example |
|--------|--------|--------|---------|
| Experience | EXP | 4 | EXP-20260212-0001 |
| Significant | SIG | 4 | SIG-20260212-0001 |
| Reflection | REF | 3 | REF-20260212-001 |
| Proposal | PROP | 3 | PROP-20260212-001 |
| Change | CHG | 3 | CHG-20260212-001 |

To get the next ID: find the highest existing sequence for today, increment.
Start at 0001/001 if none exist.
