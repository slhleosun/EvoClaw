# Heartbeat Debugging Guide

Diagnosing why your EvoClaw heartbeat pipeline isn't working as expected.

---

## Symptom: Main agent doesn't know what happened during heartbeat

The most common EvoClaw issue. Your agent polls Moltbook during heartbeat,
logs experiences, maybe even reflects — but when you chat with it next, it
has no memory of any of that.

### Root cause: session isolation

Heartbeats should run in the **main session** by default. If they're running
in an isolated session, the heartbeat context (including all tool calls, API
responses, and experience logging) is invisible to the main conversation.

### Step 1: Verify your heartbeat config

Check your OpenClaw config (usually `~/.openclaw/openclaw.json` or
`~/.openclaw/config.json`):

```bash
cat ~/.openclaw/openclaw.json | python3 -m json.tool
```

Look for the heartbeat section. A correct minimal config looks like:

```json
{
  "agents": {
    "defaults": {
      "heartbeat": {
        "every": "3m"
      }
    }
  }
}
```

**What to check:**

| Field | Good | Bad | Why |
|-------|------|-----|-----|
| `every` | `"3m"`, `"5m"` | `"0m"` | `0m` disables heartbeat entirely |
| `session` | absent or explicit main key | `"isolated"` or a cron key | Isolated = separate context |
| No `session` field | ✅ defaults to main | — | Main session is the default |

If there's a `session` field pointing to something other than your main
session, **remove it** so it defaults to main.

### Step 2: Check for rogue cron jobs

A common mistake: the Moltbook check is running as a **cron job** instead of
as part of the heartbeat pipeline. Cron jobs with `--session isolated` get
their own fresh context per run.

```bash
openclaw cron list
```

Look for any jobs that mention Moltbook, feed checking, or EvoClaw. If you
find one, it's competing with (or replacing) the heartbeat pipeline.

**Fix:** Delete the cron job and let the heartbeat handle it:

```bash
openclaw cron remove <job-id>
```

### Step 3: Verify heartbeat is running in main session

Check your session list:

```bash
openclaw sessions --json
```

Look for your main session key (format: `agent:<id>:<mainKey>`). Then check
the session transcript to see if heartbeat turns appear there:

```bash
# Look at the most recent session entries
openclaw session show --last 10
```

If heartbeat turns show tool calls to Moltbook API and experience logging,
the heartbeat IS running in main. If you don't see heartbeat turns there,
check for other sessions that contain them:

```bash
# List all sessions with recent activity
openclaw sessions --sort recent
```

### Step 4: Check if the main queue was busy

From the docs: *"If the main queue is busy, the heartbeat is skipped and
retried later."* If you're actively chatting when a heartbeat fires, it may
be skipped.

With a 3m interval, this is usually fine — it'll catch the next one. But if
you're in a long continuous conversation, heartbeats may be consistently
skipped.

**Fix:** This is expected behavior. The heartbeat will run during gaps in
conversation. If you need to force one:

```bash
openclaw system event --text "Run heartbeat now" --mode now
```

### Step 5: Check DM scope

If `session.dmScope` is set to something other than `"main"`, conversations
from different channels may be in separate sessions:

```bash
grep -A3 "dmScope" ~/.openclaw/openclaw.json
```

For EvoClaw, you want `dmScope: "main"` (the default) so all direct
conversations share context with heartbeat runs.

---

## Symptom: Heartbeat runs but doesn't do the EvoClaw pipeline

The heartbeat fires, but it just says HEARTBEAT_OK without running the
EvoClaw ingestion/reflection cycle.

### Check HEARTBEAT.md exists and has content

```bash
cat ~/.openclaw/workspace/HEARTBEAT.md
```

If it's empty or missing, the agent has nothing to do. Reinstall the EvoClaw
HEARTBEAT.md content (see configure.md Step 7).

**Important:** If HEARTBEAT.md only contains blank lines and markdown headers
with no content, OpenClaw skips the heartbeat run entirely to save API calls.

### Check the heartbeat prompt

If you've overridden the default prompt in config, it may not tell the agent
to read HEARTBEAT.md:

```bash
grep -A3 "prompt" ~/.openclaw/openclaw.json
```

The default prompt is:
> "Read HEARTBEAT.md if it exists (workspace context). Follow it strictly."

If you've overridden this, make sure it still references HEARTBEAT.md.

---

## Symptom: Heartbeat runs EvoClaw but experiences aren't persisting

The agent appears to run the pipeline during heartbeat, but experience files
are empty or missing.

### Check file permissions

```bash
ls -la ~/.openclaw/workspace/memory/experiences/
```

The workspace must be writable. If the agent can't write files, it fails
silently.

### Check if compaction is erasing work

If the heartbeat session compacts frequently (small context window, lots of
tool output), experiences logged earlier in the same turn may be lost from
context before the agent finishes the pipeline.

**Fix:** Increase context window or model, or reduce the amount of content
fetched per heartbeat (e.g., lower `limit` on feed fetches).

### Check that JSONL files are valid

```bash
# Validate today's experience log
python3 -c "
import json, sys
for i, line in enumerate(open(sys.argv[1]), 1):
    try: json.loads(line)
    except: print(f'Line {i} invalid: {line[:80]}')
" ~/.openclaw/workspace/memory/experiences/$(date +%Y-%m-%d).jsonl
```

Corrupted JSONL (e.g., partial writes) can cause the agent to error on
subsequent reads.

---

## Symptom: Source polling happens too often / not often enough

### Too often (burning tokens)

Check `poll_interval_minutes` in `evoclaw/config.json`. With a 3m heartbeat:
- `poll_interval_minutes: 5` → polls every 5 min (matches heartbeat)
- `poll_interval_minutes: 10` → polls every 10 min (every other heartbeat)

Also check `source_last_polled` in `memory/evoclaw-state.json`:

```bash
cat ~/.openclaw/workspace/memory/evoclaw-state.json | python3 -m json.tool
```

If `source_last_polled` is always `null`, the agent is re-polling every
heartbeat because it's not persisting the timestamp.

### Not often enough

If `source_last_polled` has a timestamp but polling seems stuck, the agent
may be hitting rate limits. Check the Moltbook rate limit (100 req/min) or
X rate limit (varies by tier).

---

## Symptom: "Pre-compaction memory flush" appears during conversations

This is OpenClaw's native behavior, not EvoClaw. It fires when your session
context nears the compaction threshold. The agent should write to BOTH:
1. `memory/experiences/YYYY-MM-DD.jsonl` (EvoClaw structured)
2. `memory/YYYY-MM-DD.md` (OpenClaw native)

See `evoclaw/SKILL.md` §10 for the full protocol.

If the agent is only writing to `.md` and skipping `.jsonl`, it means the
EvoClaw flush redirect isn't working. Check that AGENTS.md has the
"MEMORY FLUSH REDIRECT" section from the install guide.

---

## Quick diagnostic checklist

```
□ Heartbeat config has no `session` override (defaults to main)
□ No cron jobs duplicating EvoClaw work
□ HEARTBEAT.md exists with EvoClaw pipeline content
□ Heartbeat prompt references HEARTBEAT.md (not overridden)
□ DM scope is "main" (default)
□ memory/ directory is writable
□ evoclaw-state.json has valid source_last_polled timestamps
□ Experience JSONL files are valid JSON-per-line
□ poll_interval_minutes is reasonable for heartbeat frequency
□ AGENTS.md has memory flush redirect instructions
```

---

## Symptom: EvoClaw is modifying the wrong agent's SOUL.md

You have multiple agents (e.g., `workspace/` and `workspace-evoclaw-demo/`)
and EvoClaw is installed on one of them. But you notice SOUL changes, tag
additions, or EvoClaw artifacts appearing in the OTHER agent's workspace.

### Root cause: Cron job or heartbeat running under the wrong agent

This is the most dangerous EvoClaw misconfiguration. It happens when:

1. A cron job (like "EvoClaw Threshold Check") is assigned to `default` or
   the wrong agent name
2. That agent's workspace doesn't have EvoClaw installed
3. The cron job runs EvoClaw logic anyway, reading and writing to whatever
   SOUL.md it finds in its own workspace

### Step 1: Check cron job agent assignments

```bash
openclaw cron list
```

Look at the `agent` column for every EvoClaw-related cron job. They MUST
point to the agent whose workspace has `evoclaw/` installed.

**Dangerous pattern:**
```
EvoClaw Heartbeat        every 5m    main      evoclaw-demo  ← ✅ correct
EvoClaw Threshold Check  every 15m   isolated  default       ← 🚨 WRONG
```

The second job runs under `default` (which uses `workspace/`), not the
EvoClaw agent (which uses `workspace-evoclaw-demo/`).

### Step 2: Fix misconfigured cron jobs

```bash
# Remove the bad cron job
openclaw cron remove <cron-id>

# Recreate under the correct agent
openclaw cron add --agent <correct-agent-name> --every 15m --prompt "Run EvoClaw threshold check"
```

### Step 3: Verify with workspace boundary check

After fixing, run the boundary check in each workspace:

```bash
# In the EvoClaw workspace — should PASS
cd workspace-evoclaw-demo
python3 evoclaw/validators/check_workspace.py

# In the other workspace — should FAIL (no evoclaw/ directory)
cd ../workspace
python3 ../workspace-evoclaw-demo/evoclaw/validators/check_workspace.py
```

### Step 4: Undo damage to the wrong agent

If the wrong agent's SOUL.md was modified:
1. Check git history or backups for the original SOUL.md
2. Remove any `[CORE]`/`[MUTABLE]` tags that were added
3. Remove any `evoclaw/` directory or `memory/` files that were created
4. Verify the agent works normally without EvoClaw artifacts

### Prevention

The workspace boundary check (`check_workspace.py`) runs as step 0 of every
heartbeat. It verifies `evoclaw/SKILL.md` exists before any pipeline step.
If it doesn't find it, the pipeline halts with a clear error. This should
prevent future cross-agent contamination even if a cron job is misconfigured.

---

## Getting more visibility

Enable heartbeat reasoning to see what the agent is thinking:

```json
{
  "agents": {
    "defaults": {
      "heartbeat": {
        "every": "3m",
        "includeReasoning": true
      }
    }
  }
}
```

This delivers a separate `Reasoning:` message showing the agent's decision
process during heartbeat. Useful for debugging but noisy — turn it off once
the issue is resolved.

You can also force an immediate heartbeat to test:

```bash
openclaw system event --text "Check for urgent follow-ups" --mode now
```

Then check the session transcript to see what happened:

```bash
openclaw session show --last 20
```
