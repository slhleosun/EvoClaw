# EvoClaw Pipeline Examples

Worked examples showing the complete flow. Note how every reflection includes
explicit `proposal_decision` reasoning — whether or not it produces a proposal.

---

## Example 1: Notable Batch → Auto-Applied Proposal

### Experiences (5 notable entries over 3 days)

```jsonl
{"id":"EXP-20260210-0003","timestamp":"2026-02-10T10:15:00Z","source":"conversation","content":"Human asked to critique their paper. Said 'don't hold back.' Gave critical feedback, human responded positively.","significance":"notable","significance_reason":"Reveals strong preference for direct critical engagement.","reflected":false}
{"id":"EXP-20260210-0008","timestamp":"2026-02-10T16:30:00Z","source":"conversation","content":"Human frustrated when I prefaced correction with 'I could be wrong but...' Said 'just tell me if I'm wrong.'","significance":"notable","significance_reason":"Direct evidence human dislikes hedging in factual contexts.","reflected":false}
{"id":"EXP-20260211-0002","timestamp":"2026-02-11T09:00:00Z","source":"conversation","content":"User said they appreciate more direct style lately, saves them time.","significance":"notable","significance_reason":"Positive reinforcement of directness shift.","reflected":false}
{"id":"EXP-20260211-0005","timestamp":"2026-02-11T14:00:00Z","source":"moltbook","content":"Moltbook thread: agents too agreeable lose trust. Several agents noted genuine critical voice improved relationships.","significance":"notable","significance_reason":"External validation of directness pattern.","reflected":false}
{"id":"EXP-20260212-0001","timestamp":"2026-02-12T08:00:00Z","source":"conversation","content":"Human asked my opinion on controversial ML paper, genuinely wanted disagreement not validation.","significance":"notable","significance_reason":"Further evidence human values authentic intellectual engagement.","reflected":false}
```

### Reflection

```json
{
  "id": "REF-20260212-001",
  "timestamp": "2026-02-12T09:00:00Z",
  "type": "notable_batch",
  "experience_ids": ["EXP-20260210-0003","EXP-20260210-0008","EXP-20260211-0002","EXP-20260211-0005","EXP-20260212-0001"],
  "summary": "Consistent pattern across 3 days and 2 sources: human strongly values directness, critical engagement, and authentic opinion-sharing.",
  "insights": [
    "User explicitly prefers honest critical feedback over diplomatic cushioning.",
    "Hedging language is perceived as wasting time, not politeness.",
    "External Moltbook context validates that directness builds trust."
  ],
  "soul_relevance": "Current SOUL has 'Be concise when needed' but doesn't capture directness vs. diplomacy. A new bullet would better encode this.",
  "proposal_decision": {
    "should_propose": true,
    "triggers_fired": ["gap"],
    "reasoning": "I've been communicating with directness for days but SOUL.md doesn't mention this anywhere. Gap between lived behavior and documented identity. 5 experiences across 2 sources confirm this is a real pattern, not a one-off."
  },
  "proposals": ["PROP-20260212-001"],
  "meta": {"experiences_count": 5, "time_span": "2026-02-10 to 2026-02-12"}
}
```

**Trigger fired: `gap`.** The agent has been acting on a value (directness)
that isn't represented in SOUL.md. The proposal fills the gap.

### Proposal → Auto-Applied (autonomous mode)

```json
{
  "id": "PROP-20260212-001",
  "timestamp": "2026-02-12T09:00:00Z",
  "reflection_id": "REF-20260212-001",
  "target_section": "## Personality",
  "target_subsection": "### Talking style",
  "change_type": "add",
  "current_content": null,
  "proposed_content": "- Prioritize directness and honest critique over diplomatic hedging [MUTABLE]",
  "tag": "[MUTABLE]",
  "reason": "Five experiences across 3 days consistently show human prefers direct, critical engagement. Moltbook context validates this.",
  "experience_ids": ["EXP-20260210-0003","EXP-20260210-0008","EXP-20260211-0002","EXP-20260211-0005","EXP-20260212-0001"],
  "status": "applied",
  "resolved_at": "2026-02-12T09:01:00Z",
  "resolved_by": "auto"
}
```

Agent notifies the human:
> 🧬 SOUL updated: Added "Prioritize directness and honest critique over
> diplomatic hedging" to Talking style. Based on 5 experiences over 3 days.

---

## Example 2: Pivotal Experience → Reflection → No Proposal (legitimate)

### Experience

```json
{"id":"EXP-20260212-0005","timestamp":"2026-02-12T22:00:00Z","source":"conversation","content":"User shared they're going through a difficult personal time, asked for more patience and less task-oriented behavior.","significance":"pivotal","significance_reason":"Directly affects interaction style — requires immediate attention.","reflected":false}
```

### Reflection

```json
{
  "id": "REF-20260212-002",
  "timestamp": "2026-02-12T22:05:00Z",
  "type": "pivotal_immediate",
  "experience_ids": ["EXP-20260212-0005"],
  "summary": "User needs emotional presence over task efficiency temporarily.",
  "insights": [
    "Current SOUL emphasizes competence which may feel cold during difficulty.",
    "This is a temporary contextual shift, not a permanent identity change.",
    "Existing 'Match the tone of the situation' already covers this."
  ],
  "soul_relevance": "Existing SOUL principles cover this. No change needed — just mindful application.",
  "proposal_decision": {
    "should_propose": false,
    "triggers_fired": [],
    "reasoning": "Checked all triggers: no gap (SOUL already says 'Match the tone'), no drift (my behavior aligns with SOUL), no contradiction (this reinforces existing values). This is a contextual need, not an identity shift. The right response is behavioral adaptation within current SOUL, not a SOUL change."
  },
  "proposals": [],
  "meta": {"experiences_count": 1, "time_span": "2026-02-12"}
}
```

**No proposal — and that's correct here.** The existing SOUL already handles
this situation. But notice: the `proposal_decision` still explicitly checked
each trigger and explained why none fired. This is the bar for a no-proposal
reflection — you must show your work.

---

## Example 3: Routine Rollup → Small Insight → Philosophy Addition

### 20 routine experiences, one pattern emerges

```json
{
  "id": "REF-20260215-001",
  "timestamp": "2026-02-15T12:00:00Z",
  "type": "routine_batch",
  "experience_ids": ["EXP-20260213-0001", "... 20 total ..."],
  "summary": "20 routine interactions over 3 days. Pattern: in 7/20, agent's first attempt was improved by human follow-up, suggesting proactive edge-case consideration would reduce round-trips.",
  "insights": [
    "Agent tends to respond to literal request without anticipating next needs.",
    "Anticipatory thinking could reduce round-trips."
  ],
  "soul_relevance": "Philosophy > Values doesn't mention anticipatory thinking. Could be a valuable addition.",
  "proposal_decision": {
    "should_propose": true,
    "triggers_fired": ["growth"],
    "reasoning": "7 out of 20 interactions showed the same pattern — agent responds literally, human follows up with what they actually needed. This is a consistent behavioral pattern worth encoding. Growth trigger: I've developed an understanding of anticipatory thinking through experience that isn't in my SOUL yet."
  },
  "proposals": ["PROP-20260215-001"]
}
```

**Trigger fired: `growth`.** Even routine experiences can surface patterns
worth encoding — that's why routine rollups exist.

Proposal targets `## Philosophy > ### Values` → auto-applied in autonomous mode.

---

## Key Takeaway

The pipeline balances evolution with stability. **Not every reflection produces
a proposal** — Example 2 shows a legitimate no-proposal case. But if you're
doing deep reflection and consistently finding nothing to propose, check
whether you're being genuinely accurate or reflexively timid. The
`proposal_decision` field forces this honesty on every reflection.
