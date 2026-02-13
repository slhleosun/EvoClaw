#!/usr/bin/env python3
"""
EvoClaw Soul Evolution Visualizer
Reads SOUL.md + memory/ and generates an interactive timeline visualization.

Usage:
  python3 soul-viz.py <workspace-path> [--serve [port]]

Examples:
  python3 soul-viz.py ./workspace-evoclaw-demo --serve 8080
  python3 soul-viz.py ./workspace-evoclaw-demo   # writes soul-evolution.html
"""

import json
import re
import sys
import os
import glob
from datetime import datetime
from pathlib import Path

def parse_soul_md(content: str) -> list:
    """Parse SOUL.md into a tree of sections → subsections → bullets."""
    nodes = []
    current_section = None
    current_subsection = None

    for line in content.split("\n"):
        line_stripped = line.strip()

        # Skip header block, empty lines, horizontal rules
        if not line_stripped or line_stripped.startswith(">") or line_stripped == "---":
            continue
        if line_stripped.startswith("# SOUL") or line_stripped.startswith("_This file"):
            continue

        # ## Section
        if line_stripped.startswith("## "):
            current_section = line_stripped
            current_subsection = None
            nodes.append({
                "type": "section",
                "text": line_stripped.replace("## ", ""),
                "raw": line_stripped,
                "children": []
            })

        # ### Subsection
        elif line_stripped.startswith("### "):
            current_subsection = line_stripped
            if nodes:
                sub = {
                    "type": "subsection",
                    "text": line_stripped.replace("### ", ""),
                    "raw": line_stripped,
                    "parent_section": current_section,
                    "children": []
                }
                nodes[-1]["children"].append(sub)

        # - Bullet
        elif line_stripped.startswith("- "):
            tag = "CORE" if "[CORE]" in line_stripped else ("MUTABLE" if "[MUTABLE]" in line_stripped else "untagged")
            # Clean text
            text = line_stripped[2:].strip()
            text_clean = re.sub(r'\s*\[(CORE|MUTABLE)\]\s*', '', text).strip()

            bullet = {
                "type": "bullet",
                "text": text_clean,
                "raw": line_stripped,
                "tag": tag,
                "section": current_section,
                "subsection": current_subsection,
            }

            if nodes and nodes[-1]["children"]:
                nodes[-1]["children"][-1]["children"].append(bullet)
            elif nodes:
                # Bullet directly under section (no subsection)
                nodes[-1]["children"].append(bullet)

    return nodes


def load_jsonl(filepath: str) -> list:
    """Load a JSONL file into a list of dicts."""
    items = []
    if not os.path.exists(filepath):
        return items
    with open(filepath, "r") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    items.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return items


def load_json(filepath: str) -> dict:
    """Load a JSON file."""
    if not os.path.exists(filepath):
        return {}
    with open(filepath, "r") as f:
        return json.load(f)


def collect_data(workspace: str) -> dict:
    """Collect all EvoClaw data from a workspace."""
    soul_path = os.path.join(workspace, "SOUL.md")
    memory_dir = os.path.join(workspace, "memory")

    # Read SOUL.md
    with open(soul_path, "r") as f:
        soul_content = f.read()

    soul_tree = parse_soul_md(soul_content)

    # Soul changes
    changes = load_jsonl(os.path.join(memory_dir, "soul_changes.jsonl"))

    # Experiences (all days)
    experiences = []
    exp_dir = os.path.join(memory_dir, "experiences")
    if os.path.isdir(exp_dir):
        for fp in sorted(glob.glob(os.path.join(exp_dir, "*.jsonl"))):
            experiences.extend(load_jsonl(fp))

    # Reflections
    reflections = []
    ref_dir = os.path.join(memory_dir, "reflections")
    if os.path.isdir(ref_dir):
        for fp in sorted(glob.glob(os.path.join(ref_dir, "REF-*.json"))):
            reflections.append(load_json(fp))

    # Proposals
    proposals_pending = load_jsonl(os.path.join(memory_dir, "proposals", "pending.jsonl"))
    proposals_history = load_jsonl(os.path.join(memory_dir, "proposals", "history.jsonl"))

    # Significant
    significant = load_jsonl(os.path.join(memory_dir, "significant", "significant.jsonl"))

    # State
    state = load_json(os.path.join(memory_dir, "evoclaw-state.json"))

    # Pipeline reports
    pipeline = []
    pipe_dir = os.path.join(memory_dir, "pipeline")
    if os.path.isdir(pipe_dir):
        for fp in sorted(glob.glob(os.path.join(pipe_dir, "*.json"))):
            pipeline.append(load_json(fp))
        for fp in sorted(glob.glob(os.path.join(pipe_dir, "*.jsonl"))):
            pipeline.extend(load_jsonl(fp))

    return {
        "soul_tree": soul_tree,
        "soul_raw": soul_content,
        "changes": changes,
        "experiences": experiences,
        "reflections": reflections,
        "proposals_pending": proposals_pending,
        "proposals_history": proposals_history,
        "significant": significant,
        "state": state,
        "pipeline": pipeline,
    }


def generate_html(data: dict) -> str:
    """Generate the interactive visualization HTML."""
    data_json = json.dumps(data, indent=None, default=str)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>EvoClaw — Soul Evolution</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@300;400;500;700&family=DM+Sans:ital,wght@0,300;0,400;0,500;0,700;1,400&display=swap');

* {{ margin: 0; padding: 0; box-sizing: border-box; }}

:root {{
  --bg: #0a0a0f;
  --bg-card: #12121a;
  --bg-hover: #1a1a28;
  --border: #1e1e30;
  --text: #c8c8d8;
  --text-dim: #6a6a80;
  --text-bright: #eeeef4;
  --accent: #7c6ff0;
  --accent-glow: rgba(124, 111, 240, 0.15);
  --core: #e05050;
  --core-bg: rgba(224, 80, 80, 0.08);
  --core-border: rgba(224, 80, 80, 0.25);
  --mutable: #50c878;
  --mutable-bg: rgba(80, 200, 120, 0.08);
  --mutable-border: rgba(80, 200, 120, 0.25);
  --section-personality: #f0a050;
  --section-philosophy: #7c6ff0;
  --section-boundaries: #e05050;
  --section-continuity: #50b8e0;
  --section-default: #888;
  --timeline-line: #2a2a40;
}}

html {{ font-size: 15px; }}

body {{
  background: var(--bg);
  color: var(--text);
  font-family: 'DM Sans', sans-serif;
  min-height: 100vh;
  overflow-x: hidden;
}}

/* Grain overlay */
body::after {{
  content: '';
  position: fixed; inset: 0;
  background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)' opacity='0.03'/%3E%3C/svg%3E");
  pointer-events: none;
  z-index: 9999;
}}

/* Header */
.header {{
  padding: 3rem 2rem 2rem;
  text-align: center;
  position: relative;
}}
.header::before {{
  content: '';
  position: absolute; top: 0; left: 50%; transform: translateX(-50%);
  width: 600px; height: 300px;
  background: radial-gradient(ellipse, var(--accent-glow), transparent 70%);
  pointer-events: none;
}}
.header h1 {{
  font-family: 'JetBrains Mono', monospace;
  font-weight: 300;
  font-size: 2.2rem;
  letter-spacing: 0.15em;
  color: var(--text-bright);
  position: relative;
}}
.header h1 .evo {{ color: var(--accent); }}
.header h1 .claw {{ color: var(--text-dim); }}
.header .subtitle {{
  font-size: 0.85rem;
  color: var(--text-dim);
  margin-top: 0.6rem;
  font-family: 'JetBrains Mono', monospace;
  letter-spacing: 0.05em;
}}
.header .subtitle .evo {{ color: var(--accent); }}
.header .subtitle .claw {{ color: var(--text-dim); }}
.stats-bar {{
  display: flex; justify-content: center; gap: 2.5rem;
  margin-top: 1.5rem; flex-wrap: wrap;
}}
.stat {{
  text-align: center;
}}
.stat .num {{
  font-family: 'JetBrains Mono', monospace;
  font-size: 1.6rem; font-weight: 700;
  color: var(--text-bright);
}}
.stat .label {{
  font-size: 0.7rem; color: var(--text-dim);
  text-transform: uppercase; letter-spacing: 0.1em;
  margin-top: 0.2rem;
}}

/* Layout */
.main {{
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 2rem 4rem;
  display: grid;
  grid-template-columns: 1fr 380px;
  gap: 2rem;
}}
@media (max-width: 900px) {{
  .main {{ grid-template-columns: 1fr; }}
}}

/* Soul Map */
.soul-map {{
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 1.5rem;
  position: relative;
}}
.soul-map h2 {{
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.8rem; font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.15em;
  color: var(--text-dim);
  margin-bottom: 1.2rem;
  padding-bottom: 0.8rem;
  border-bottom: 1px solid var(--border);
}}

.section-block {{
  margin-bottom: 1.5rem;
  border-radius: 8px;
  overflow: hidden;
  border: 1px solid var(--border);
  opacity: 0;
  transform: translateY(12px);
  transition: opacity 0.5s, transform 0.5s;
}}
.section-block.visible {{
  opacity: 1;
  transform: translateY(0);
}}
.section-header {{
  padding: 0.7rem 1rem;
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.8rem; font-weight: 500;
  letter-spacing: 0.08em;
  display: flex; align-items: center; gap: 0.6rem;
  cursor: pointer;
  user-select: none;
}}
.section-header .dot {{
  width: 8px; height: 8px; border-radius: 50%;
  flex-shrink: 0;
}}
.section-header .arrow {{
  margin-left: auto;
  font-size: 0.7rem;
  transition: transform 0.3s;
  color: var(--text-dim);
}}
.section-block.collapsed .section-header .arrow {{
  transform: rotate(-90deg);
}}
.section-block.collapsed .section-body {{
  display: none;
}}

.subsection {{
  padding: 0.3rem 1rem 0.5rem 1.6rem;
}}
.subsection-title {{
  font-size: 0.72rem;
  color: var(--text-dim);
  font-weight: 500;
  margin-bottom: 0.4rem;
  padding-left: 0.4rem;
}}

.bullet {{
  padding: 0.45rem 0.6rem;
  margin: 0.25rem 0;
  border-radius: 6px;
  font-size: 0.82rem;
  line-height: 1.45;
  display: flex;
  gap: 0.5rem;
  align-items: flex-start;
  transition: all 0.3s;
  position: relative;
}}
.bullet:hover {{
  background: var(--bg-hover);
}}
.bullet.highlight-enter {{
  animation: bulletEnter 1s ease-out;
}}
@keyframes bulletEnter {{
  0% {{ background: rgba(124, 111, 240, 0.3); transform: scale(1.02); }}
  100% {{ background: transparent; transform: scale(1); }}
}}
.bullet .tag {{
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.6rem;
  font-weight: 700;
  padding: 0.15rem 0.4rem;
  border-radius: 3px;
  flex-shrink: 0;
  margin-top: 0.15rem;
  letter-spacing: 0.05em;
}}
.bullet .tag.core {{
  color: var(--core);
  background: var(--core-bg);
  border: 1px solid var(--core-border);
}}
.bullet .tag.mutable {{
  color: var(--mutable);
  background: var(--mutable-bg);
  border: 1px solid var(--mutable-border);
}}
.bullet.is-new {{
  opacity: 0;
  max-height: 0;
  overflow: hidden;
  transition: opacity 0.6s, max-height 0.6s;
}}
.bullet.is-new.revealed {{
  opacity: 1;
  max-height: 200px;
}}

/* Right panel */
.right-panel {{
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}}

/* Timeline */
.timeline-panel {{
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 1.5rem;
}}
.timeline-panel h2 {{
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.8rem; font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.15em;
  color: var(--text-dim);
  margin-bottom: 1rem;
  padding-bottom: 0.8rem;
  border-bottom: 1px solid var(--border);
}}

.timeline-controls {{
  display: flex; align-items: center; gap: 0.6rem;
  margin-bottom: 1.2rem;
}}
.timeline-controls button {{
  background: var(--bg-hover);
  border: 1px solid var(--border);
  color: var(--text);
  padding: 0.4rem 0.8rem;
  border-radius: 6px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.72rem;
  cursor: pointer;
  transition: all 0.2s;
}}
.timeline-controls button:hover {{
  background: var(--accent);
  color: #fff;
  border-color: var(--accent);
}}
.timeline-controls button.active {{
  background: var(--accent);
  color: #fff;
  border-color: var(--accent);
}}
.timeline-slider {{
  flex: 1;
  -webkit-appearance: none;
  height: 4px;
  border-radius: 2px;
  background: var(--timeline-line);
  outline: none;
}}
.timeline-slider::-webkit-slider-thumb {{
  -webkit-appearance: none;
  width: 14px; height: 14px;
  border-radius: 50%;
  background: var(--accent);
  cursor: pointer;
  box-shadow: 0 0 8px var(--accent-glow);
}}
.timeline-label {{
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.7rem;
  color: var(--text-dim);
  min-width: 3rem;
  text-align: right;
}}

/* Change entries */
.change-entry {{
  padding: 0.8rem;
  border: 1px solid var(--border);
  border-radius: 8px;
  margin-bottom: 0.6rem;
  position: relative;
  transition: all 0.3s;
  opacity: 0;
  transform: translateX(10px);
}}
.change-entry.visible {{
  opacity: 1;
  transform: translateX(0);
}}
.change-entry:hover {{
  border-color: var(--accent);
  background: var(--bg-hover);
}}
.change-entry .change-time {{
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.65rem;
  color: var(--text-dim);
}}
.change-entry .change-type {{
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.6rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  padding: 0.1rem 0.35rem;
  border-radius: 3px;
  display: inline-block;
  margin: 0.3rem 0;
}}
.change-entry .change-type.add {{
  color: var(--mutable);
  background: var(--mutable-bg);
  border: 1px solid var(--mutable-border);
}}
.change-entry .change-type.modify {{
  color: var(--accent);
  background: var(--accent-glow);
  border: 1px solid rgba(124, 111, 240, 0.3);
}}
.change-entry .change-type.remove {{
  color: var(--core);
  background: var(--core-bg);
  border: 1px solid var(--core-border);
}}
.change-entry .change-section {{
  font-size: 0.72rem;
  color: var(--text-dim);
  margin: 0.2rem 0;
}}
.change-entry .change-content {{
  font-size: 0.78rem;
  line-height: 1.4;
  color: var(--text);
  margin-top: 0.3rem;
}}

/* Experience feed */
.feed-panel {{
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 1.5rem;
  max-height: 400px;
  overflow-y: auto;
}}
.feed-panel h2 {{
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.8rem; font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.15em;
  color: var(--text-dim);
  margin-bottom: 1rem;
  padding-bottom: 0.8rem;
  border-bottom: 1px solid var(--border);
}}
.feed-panel::-webkit-scrollbar {{
  width: 4px;
}}
.feed-panel::-webkit-scrollbar-track {{
  background: transparent;
}}
.feed-panel::-webkit-scrollbar-thumb {{
  background: var(--border);
  border-radius: 2px;
}}

.exp-entry {{
  padding: 0.6rem 0;
  border-bottom: 1px solid var(--border);
  font-size: 0.78rem;
  line-height: 1.4;
}}
.exp-entry:last-child {{ border-bottom: none; }}
.exp-meta {{
  display: flex; gap: 0.5rem; align-items: center;
  margin-bottom: 0.25rem;
}}
.exp-source {{
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.6rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  padding: 0.1rem 0.35rem;
  border-radius: 3px;
  background: var(--bg-hover);
  color: var(--text-dim);
}}
.exp-source.moltbook {{ color: #f0a050; background: rgba(240, 160, 80, 0.1); }}
.exp-source.conversation {{ color: var(--accent); background: var(--accent-glow); }}
.exp-sig {{
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.55rem;
  color: var(--text-dim);
}}
.exp-sig.notable {{ color: var(--mutable); }}
.exp-sig.pivotal {{ color: var(--core); }}
.exp-content {{ color: var(--text-dim); }}

/* Legend */
.legend {{
  display: flex; gap: 1.2rem; flex-wrap: wrap;
  padding: 0.8rem 1rem;
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 8px;
  font-size: 0.7rem;
}}
.legend-item {{
  display: flex; align-items: center; gap: 0.4rem;
}}
.legend-dot {{
  width: 8px; height: 8px; border-radius: 50%;
}}

/* Empty state */
.empty-state {{
  text-align: center;
  padding: 2rem;
  color: var(--text-dim);
  font-size: 0.85rem;
  font-style: italic;
}}

/* Edit mode */
.edit-bar {{
  display: flex; align-items: center; gap: 0.6rem;
  margin-bottom: 1rem;
  padding-bottom: 0.8rem;
  border-bottom: 1px solid var(--border);
}}
.edit-bar h2 {{
  margin: 0 !important; padding: 0 !important; border: none !important;
  flex-shrink: 0;
}}
.edit-bar .spacer {{ flex: 1; min-width: 0; }}
.btn-edit, .btn-save {{
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.68rem;
  padding: 0.35rem 0.7rem;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s;
  border: 1px solid var(--border);
  background: var(--bg-hover);
  color: var(--text);
  letter-spacing: 0.03em;
  flex-shrink: 0;
  position: relative;
  z-index: 2;
}}
.btn-edit:hover {{ background: var(--accent); color: #fff; border-color: var(--accent); }}
.btn-save {{
  background: rgba(80, 200, 120, 0.15);
  border-color: var(--mutable-border);
  color: var(--mutable);
}}
.btn-save:hover {{
  background: var(--mutable);
  color: #fff;
  border-color: var(--mutable);
}}
.btn-edit.active {{
  background: var(--accent);
  color: #fff;
  border-color: var(--accent);
}}

/* Editable bullets */
.bullet.editing {{
  background: var(--bg-hover);
  border: 1px solid var(--border);
  border-radius: 6px;
}}
.bullet .edit-text {{
  flex: 1;
  background: transparent;
  border: none;
  color: var(--text);
  font-family: 'DM Sans', sans-serif;
  font-size: 0.82rem;
  line-height: 1.45;
  outline: none;
  resize: none;
  min-height: 1.4em;
  overflow: hidden;
}}
.bullet .edit-text:focus {{
  color: var(--text-bright);
}}
.bullet .tag-toggle {{
  cursor: pointer;
  user-select: none;
  transition: transform 0.15s;
}}
.bullet .tag-toggle:hover {{ transform: scale(1.15); }}
.bullet .btn-delete {{
  background: none;
  border: none;
  color: var(--text-dim);
  cursor: pointer;
  font-size: 0.9rem;
  padding: 0 0.2rem;
  opacity: 0;
  transition: all 0.2s;
  flex-shrink: 0;
}}
.bullet.editing .btn-delete {{ opacity: 0.5; }}
.bullet.editing .btn-delete:hover {{ opacity: 1; color: var(--core); }}
.btn-add-bullet {{
  background: none;
  border: 1px dashed var(--border);
  border-radius: 6px;
  color: var(--text-dim);
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.7rem;
  padding: 0.35rem 0.6rem;
  cursor: pointer;
  margin: 0.3rem 0;
  width: 100%;
  text-align: left;
  transition: all 0.2s;
  display: none;
}}
.soul-map.edit-mode .btn-add-bullet {{ display: block; }}
.btn-add-bullet:hover {{
  border-color: var(--mutable);
  color: var(--mutable);
  background: var(--mutable-bg);
}}

/* Save toast */
.save-toast {{
  position: fixed;
  top: 1.5rem; left: 50%; transform: translateX(-50%);
  z-index: 500;
  background: rgba(80, 200, 120, 0.15);
  border: 1px solid var(--mutable-border);
  border-radius: 8px;
  padding: 0.5rem 1.2rem;
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.75rem;
  color: var(--mutable);
  opacity: 0;
  transition: opacity 0.3s;
  pointer-events: none;
}}
.save-toast.show {{ opacity: 1; }}

/* Mindmap link */
.mindmap-link {{
  display: flex;
  align-items: center;
  gap: 0.8rem;
  padding: 1rem 1.4rem;
  background: linear-gradient(135deg, rgba(80, 200, 120, 0.06), rgba(124, 111, 240, 0.06));
  border: 1px solid rgba(80, 200, 120, 0.2);
  border-radius: 12px;
  color: var(--text-bright);
  text-decoration: none;
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.85rem;
  font-weight: 500;
  letter-spacing: 0.03em;
  transition: all 0.3s;
  position: relative;
  overflow: hidden;
}}
.mindmap-link::before {{
  content: '';
  position: absolute; inset: 0;
  background: linear-gradient(135deg, rgba(80, 200, 120, 0.08), rgba(124, 111, 240, 0.08));
  opacity: 0;
  transition: opacity 0.3s;
}}
.mindmap-link:hover {{
  border-color: var(--mutable);
  transform: translateY(-1px);
  box-shadow: 0 4px 20px rgba(80, 200, 120, 0.1);
}}
.mindmap-link:hover::before {{ opacity: 1; }}
.mindmap-link-icon {{ font-size: 1.3rem; position: relative; }}
.mindmap-link-sub {{
  font-size: 0.65rem;
  color: var(--text-dim);
  font-weight: 300;
  letter-spacing: 0.05em;
}}
.mindmap-link-arrow {{
  margin-left: auto;
  font-size: 1.1rem;
  color: var(--mutable);
  transition: transform 0.3s;
  position: relative;
}}
.mindmap-link:hover .mindmap-link-arrow {{ transform: translateX(4px); }}
</style>
</head>
<body>
<div class="header">
  <h1>Agent Soul Evolution</h1>
  <div class="subtitle">powered by <span class="evo">evo</span><span class="claw">claw</span></div>
  <div class="stats-bar" id="stats-bar"></div>
</div>

<div style="max-width:1200px;margin:0 auto;padding:0 2rem 1rem;">
  <div class="legend" id="legend"></div>
</div>

<div class="main">
  <div style="grid-column:1/-1;">
    <a href="soul-mindmap.html" class="mindmap-link" id="mindmap-link">
      <span class="mindmap-link-icon">🌿</span>
      <span>Open Soul Mindmap</span>
      <span class="mindmap-link-sub">interactive canvas · growth animation · zoom &amp; pan</span>
      <span class="mindmap-link-arrow">→</span>
    </a>
  </div>
  <div class="soul-map" id="soul-map">
    <div class="edit-bar">
      <h2>Soul Map</h2>
      <div class="spacer"></div>
      <button class="btn-edit" id="btn-edit" onclick="toggleEditMode()">✎ Edit</button>
      <button class="btn-save" id="btn-save" onclick="saveSoul()" style="display:none">💾 Save SOUL.md</button>
    </div>
    <div id="soul-tree"></div>
  </div>

  <div class="right-panel">
    <div class="timeline-panel">
      <h2>Evolution Timeline</h2>
      <div class="timeline-controls">
        <button id="btn-play" title="Play evolution">▶</button>
        <button id="btn-reset" title="Reset to origin">⟲</button>
        <input type="range" class="timeline-slider" id="timeline-slider" min="0" max="1" value="1" step="1">
        <span class="timeline-label" id="timeline-label">—</span>
      </div>
      <div id="changes-list"></div>
    </div>

    <div class="feed-panel">
      <h2>Experience Feed</h2>
      <div id="exp-feed"></div>
    </div>
  </div>
</div>

<div class="save-toast" id="save-toast">✓ SOUL.md saved</div>

<script>
const DATA = {data_json};

const SECTION_COLORS = {{
  'Personality': '#f0a050',
  'Philosophy': '#7c6ff0',
  'Boundaries': '#e05050',
  'Continuity': '#50b8e0',
}};
function sectionColor(name) {{
  for (const [k, v] of Object.entries(SECTION_COLORS)) {{
    if (name && name.includes(k)) return v;
  }}
  return '#888';
}}

// --- Stats ---
function renderStats() {{
  const bar = document.getElementById('stats-bar');
  const tree = DATA.soul_tree;
  let core = 0, mutable = 0, totalBullets = 0;
  tree.forEach(sec => {{
    sec.children.forEach(child => {{
      if (child.type === 'bullet') {{
        totalBullets++;
        if (child.tag === 'CORE') core++;
        if (child.tag === 'MUTABLE') mutable++;
      }}
      if (child.children) child.children.forEach(b => {{
        if (b.type === 'bullet') {{
          totalBullets++;
          if (b.tag === 'CORE') core++;
          if (b.tag === 'MUTABLE') mutable++;
        }}
      }});
    }});
  }});
  const stats = [
    {{ num: DATA.experiences.length, label: 'Experiences' }},
    {{ num: DATA.reflections.length, label: 'Reflections' }},
    {{ num: DATA.changes.length, label: 'Soul Changes' }},
    {{ num: core, label: 'Core' }},
    {{ num: mutable, label: 'Mutable' }},
  ];
  bar.innerHTML = stats.map(s =>
    `<div class="stat"><div class="num">${{s.num}}</div><div class="label">${{s.label}}</div></div>`
  ).join('');
}}

// --- Legend ---
function renderLegend() {{
  const el = document.getElementById('legend');
  const items = [
    {{ color: 'var(--core)', label: 'CORE (immutable)' }},
    {{ color: 'var(--mutable)', label: 'MUTABLE (evolvable)' }},
    ...Object.entries(SECTION_COLORS).map(([k, v]) => ({{ color: v, label: k }})),
  ];
  el.innerHTML = items.map(i =>
    `<div class="legend-item"><div class="legend-dot" style="background:${{i.color}}"></div>${{i.label}}</div>`
  ).join('');
}}

// --- Soul Map ---
let allBulletEls = [];
let changesBulletMap = {{}};

let editMode = false;

function renderSoulTree(revealUpTo) {{
  const container = document.getElementById('soul-tree');
  container.innerHTML = '';
  allBulletEls = [];

  // Build set of bullets added by changes after revealUpTo
  const hiddenAfter = new Set();
  if (!editMode) {{
    const changes = DATA.changes;
    for (let i = changes.length - 1; i >= 0; i--) {{
      if (i >= revealUpTo) {{
        if (changes[i].change_type === 'add' && changes[i].after) {{
          hiddenAfter.add(changes[i].after.trim());
        }}
      }}
    }}
  }}

  DATA.soul_tree.forEach((sec, si) => {{
    const color = sectionColor(sec.text);
    const block = document.createElement('div');
    block.className = 'section-block';
    block.style.borderColor = color + '33';

    const header = document.createElement('div');
    header.className = 'section-header';
    header.style.background = color + '0d';
    header.innerHTML = `<div class="dot" style="background:${{color}}"></div>${{sec.text}}<span class="arrow">▼</span>`;
    header.onclick = () => block.classList.toggle('collapsed');
    block.appendChild(header);

    const body = document.createElement('div');
    body.className = 'section-body';

    sec.children.forEach((child, ci) => {{
      if (child.type === 'subsection') {{
        const sub = document.createElement('div');
        sub.className = 'subsection';
        sub.innerHTML = `<div class="subsection-title">${{child.text}}</div>`;

        (child.children || []).forEach((b, bi) => {{
          const bEl = renderBullet(b, hiddenAfter, [si, ci, bi]);
          sub.appendChild(bEl);
        }});

        // Add bullet button
        const addBtn = document.createElement('button');
        addBtn.className = 'btn-add-bullet';
        addBtn.textContent = '+ add bullet';
        addBtn.onclick = () => addBullet(si, ci);
        sub.appendChild(addBtn);

        body.appendChild(sub);
      }} else if (child.type === 'bullet') {{
        body.appendChild(renderBullet(child, hiddenAfter, [si, ci, -1]));
      }}
    }});

    block.appendChild(body);
    container.appendChild(block);

    setTimeout(() => block.classList.add('visible'), 80 * si);
  }});
}}

function renderBullet(b, hiddenAfter, path) {{
  const el = document.createElement('div');
  el.className = 'bullet';
  const isHidden = hiddenAfter.has(b.raw.trim());
  if (isHidden) {{
    el.classList.add('is-new');
  }}

  const tagClass = b.tag === 'CORE' ? 'core' : (b.tag === 'MUTABLE' ? 'mutable' : '');

  if (editMode) {{
    el.classList.add('editing');
    const [si, ci, bi] = path;

    // Tag toggle
    const tagEl = document.createElement('span');
    tagEl.className = `tag ${{tagClass}} tag-toggle`;
    tagEl.textContent = b.tag || 'TAG';
    tagEl.title = 'Click to toggle CORE/MUTABLE';
    tagEl.onclick = () => {{
      const next = b.tag === 'CORE' ? 'MUTABLE' : 'CORE';
      b.tag = next;
      updateBulletRaw(b);
      renderSoulTree(currentStep);
    }};
    el.appendChild(tagEl);

    // Editable text
    const input = document.createElement('textarea');
    input.className = 'edit-text';
    input.value = b.text;
    input.rows = 1;
    input.oninput = () => {{
      input.style.height = 'auto';
      input.style.height = input.scrollHeight + 'px';
      b.text = input.value;
      updateBulletRaw(b);
    }};
    // Auto-resize on mount
    setTimeout(() => {{ input.style.height = input.scrollHeight + 'px'; }}, 0);
    el.appendChild(input);

    // Delete button
    const del = document.createElement('button');
    del.className = 'btn-delete';
    del.innerHTML = '×';
    del.title = 'Remove bullet';
    del.onclick = () => {{
      deleteBullet(si, ci, bi);
    }};
    el.appendChild(del);
  }} else {{
    el.innerHTML = `
      ${{tagClass ? `<span class="tag ${{tagClass}}">${{b.tag}}</span>` : ''}}
      <span>${{b.text}}</span>
    `;
  }}

  allBulletEls.push({{ el, raw: b.raw, tag: b.tag }});
  return el;
}}

function updateBulletRaw(b) {{
  b.raw = `- ${{b.text}} [${{b.tag}}]`;
}}

function toggleEditMode() {{
  editMode = !editMode;
  const btn = document.getElementById('btn-edit');
  const saveBtn = document.getElementById('btn-save');
  const mapEl = document.getElementById('soul-map');

  if (editMode) {{
    btn.classList.add('active');
    btn.textContent = '✎ Editing';
    saveBtn.style.display = '';
    mapEl.classList.add('edit-mode');
  }} else {{
    btn.classList.remove('active');
    btn.textContent = '✎ Edit';
    saveBtn.style.display = 'none';
    mapEl.classList.remove('edit-mode');
  }}
  renderSoulTree(currentStep);
}}

function addBullet(si, ci) {{
  const sub = DATA.soul_tree[si].children[ci];
  if (!sub.children) sub.children = [];
  const sec = DATA.soul_tree[si];
  const newBullet = {{
    type: 'bullet',
    text: 'New belief',
    raw: '- New belief [MUTABLE]',
    tag: 'MUTABLE',
    section: sec.raw,
    subsection: sub.raw,
  }};
  sub.children.push(newBullet);
  renderSoulTree(currentStep);
}}

function deleteBullet(si, ci, bi) {{
  if (bi >= 0) {{
    DATA.soul_tree[si].children[ci].children.splice(bi, 1);
  }} else {{
    DATA.soul_tree[si].children.splice(ci, 1);
  }}
  renderSoulTree(currentStep);
}}

function reconstructSoulMd() {{
  let lines = [];
  lines.push('# SOUL.md - Who You Are');
  lines.push('');
  lines.push('> ⚠️ This file is managed by **EvoClaw**. Bullets tagged `[CORE]` are immutable.');
  lines.push('> Bullets tagged `[MUTABLE]` may evolve through the structured proposal pipeline.');
  lines.push('> Direct edits outside the pipeline are not permitted for `[MUTABLE]` items.');
  lines.push('> See `evoclaw/SKILL.md` for the full protocol.');
  lines.push('');
  lines.push('---');

  DATA.soul_tree.forEach(sec => {{
    lines.push('');
    lines.push(`## ${{sec.text}}`);

    sec.children.forEach(child => {{
      if (child.type === 'subsection') {{
        lines.push('');
        lines.push(`### ${{child.text}}`);
        lines.push('');
        (child.children || []).forEach(b => {{
          lines.push(`- ${{b.text}} [${{b.tag}}]`);
        }});
      }} else if (child.type === 'bullet') {{
        lines.push(`- ${{child.text}} [${{child.tag}}]`);
      }}
    }});
  }});

  lines.push('');
  lines.push('---');
  lines.push('');
  lines.push('_This file is yours to evolve. As you learn who you are, update it._');
  return lines.join('\\n');
}}

function saveSoul() {{
  const content = reconstructSoulMd();
  const toast = document.getElementById('save-toast');

  // Try server-side save first (works in --serve mode)
  fetch('/save-soul', {{
    method: 'POST',
    headers: {{ 'Content-Type': 'text/markdown' }},
    body: content
  }})
  .then(resp => {{
    if (resp.ok) {{
      toast.textContent = '✓ SOUL.md saved to workspace';
      toast.classList.add('show');
      setTimeout(() => toast.classList.remove('show'), 2500);
    }} else {{
      throw new Error('Server save failed');
    }}
  }})
  .catch(() => {{
    // Fallback: browser download (static HTML mode)
    const blob = new Blob([content], {{ type: 'text/markdown' }});
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'SOUL.md';
    a.click();
    URL.revokeObjectURL(url);
    toast.textContent = '✓ SOUL.md downloaded';
    toast.classList.add('show');
    setTimeout(() => toast.classList.remove('show'), 2500);
  }});
}}

// --- Timeline ---
let currentStep = -1;
let playing = false;
let playInterval = null;

function renderTimeline() {{
  const changes = DATA.changes;
  const slider = document.getElementById('timeline-slider');
  slider.max = changes.length;
  slider.value = changes.length;
  currentStep = changes.length;

  slider.oninput = () => {{
    currentStep = parseInt(slider.value);
    updateTimelineView();
  }};

  updateTimelineView();
}}

function updateTimelineView() {{
  const changes = DATA.changes;
  const label = document.getElementById('timeline-label');

  if (currentStep === 0) {{
    label.textContent = 'origin';
  }} else if (currentStep <= changes.length) {{
    const c = changes[currentStep - 1];
    const t = c.timestamp || '';
    label.textContent = t.slice(11, 16) || `#${{currentStep}}`;
  }}

  // Re-render soul map with visibility
  renderSoulTree(currentStep);

  // Re-render changes list
  renderChangesList(currentStep);

  // Update slider
  document.getElementById('timeline-slider').value = currentStep;
}}

function renderChangesList(upTo) {{
  const container = document.getElementById('changes-list');
  const changes = DATA.changes;

  if (changes.length === 0) {{
    container.innerHTML = '<div class="empty-state">No soul changes yet. The soul is in its original state.</div>';
    return;
  }}

  container.innerHTML = '';
  const visible = changes.slice(0, upTo);
  visible.forEach((c, i) => {{
    const el = document.createElement('div');
    el.className = 'change-entry';

    const t = c.timestamp || '';
    const time = t.slice(0, 16).replace('T', ' ');
    const section = (c.section || '').replace('## ', '') + ' › ' + (c.subsection || '').replace('### ', '');
    const content = c.after || c.before || '';
    const cleanContent = content.replace(/\\s*\\[(CORE|MUTABLE)\\]\\s*/g, '').replace(/^- /, '');

    el.innerHTML = `
      <div class="change-time">${{time}}</div>
      <span class="change-type ${{c.change_type}}">${{c.change_type}}</span>
      <div class="change-section">${{section}}</div>
      <div class="change-content">${{cleanContent}}</div>
    `;

    container.appendChild(el);
    setTimeout(() => el.classList.add('visible'), 60 * i);
  }});

  if (upTo === 0) {{
    container.innerHTML = '<div class="empty-state">⟲ Origin state — no changes applied yet</div>';
  }}
}}

// --- Play / Reset ---
document.getElementById('btn-play').onclick = () => {{
  if (playing) {{
    clearInterval(playInterval);
    playing = false;
    document.getElementById('btn-play').textContent = '▶';
    document.getElementById('btn-play').classList.remove('active');
    return;
  }}
  playing = true;
  document.getElementById('btn-play').textContent = '⏸';
  document.getElementById('btn-play').classList.add('active');
  currentStep = 0;
  updateTimelineView();

  playInterval = setInterval(() => {{
    currentStep++;
    if (currentStep > DATA.changes.length) {{
      clearInterval(playInterval);
      playing = false;
      document.getElementById('btn-play').textContent = '▶';
      document.getElementById('btn-play').classList.remove('active');
      return;
    }}
    updateTimelineView();
    // Highlight the newly revealed bullet
    const change = DATA.changes[currentStep - 1];
    if (change && change.after) {{
      const match = allBulletEls.find(b => b.raw.trim() === change.after.trim());
      if (match) {{
        match.el.classList.remove('is-new');
        match.el.classList.add('revealed');
        match.el.classList.add('highlight-enter');
        match.el.scrollIntoView({{ behavior: 'smooth', block: 'center' }});
      }}
    }}
  }}, 1800);
}};

document.getElementById('btn-reset').onclick = () => {{
  if (playing) {{
    clearInterval(playInterval);
    playing = false;
    document.getElementById('btn-play').textContent = '▶';
    document.getElementById('btn-play').classList.remove('active');
  }}
  currentStep = 0;
  updateTimelineView();
}};

// --- Experience Feed ---
function renderFeed() {{
  const container = document.getElementById('exp-feed');
  const exps = DATA.experiences.slice().reverse();

  if (exps.length === 0) {{
    container.innerHTML = '<div class="empty-state">No experiences logged yet.</div>';
    return;
  }}

  container.innerHTML = exps.map(e => {{
    const t = (e.timestamp || '').slice(11, 16);
    const sourceClass = (e.source || '').toLowerCase();
    const sigClass = (e.significance || '').toLowerCase();
    const content = (e.content || '').slice(0, 160) + ((e.content || '').length > 160 ? '…' : '');
    return `
      <div class="exp-entry">
        <div class="exp-meta">
          <span class="exp-source ${{sourceClass}}">${{e.source}}</span>
          <span class="exp-sig ${{sigClass}}">${{e.significance}}</span>
          <span style="margin-left:auto;font-family:'JetBrains Mono',monospace;font-size:0.6rem;color:var(--text-dim)">${{t}}</span>
        </div>
        <div class="exp-content">${{content}}</div>
      </div>
    `;
  }}).join('');
}}

// --- Init ---
renderStats();
renderLegend();
renderSoulTree(DATA.changes.length);
renderTimeline();
renderFeed();
</script>
</body>
</html>"""


def generate_mindmap_html(data: dict) -> str:
    """Generate the interactive canvas mindmap page."""
    data_json = json.dumps(data, indent=None, default=str)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>EvoClaw — Soul Mindmap</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@300;400;500;700&family=DM+Sans:ital,wght@0,300;0,400;0,500;0,700;1,400&display=swap');

* {{ margin: 0; padding: 0; box-sizing: border-box; }}

:root {{
  --bg: #060610;
  --text: #c8c8d8;
  --text-dim: #5a5a70;
  --text-bright: #eeeef4;
  --accent: #7c6ff0;
  --core: #e05050;
  --mutable: #50c878;
}}

body {{
  background: var(--bg);
  color: var(--text);
  font-family: 'DM Sans', sans-serif;
  overflow: hidden;
  height: 100vh;
  cursor: grab;
}}
body.dragging {{ cursor: grabbing; }}

canvas {{
  display: block;
  position: absolute;
  top: 0; left: 0;
}}

/* HUD overlay */
.hud {{
  position: fixed;
  z-index: 100;
  pointer-events: none;
}}
.hud > * {{ pointer-events: auto; }}

.hud-top {{
  top: 1.2rem; left: 50%;
  transform: translateX(-50%);
  text-align: center;
}}
.hud-top h1 {{
  font-family: 'JetBrains Mono', monospace;
  font-weight: 300;
  font-size: 1.1rem;
  letter-spacing: 0.15em;
  color: var(--text-dim);
}}
.hud-top h1 .evo {{ color: var(--accent); }}
.hud-top h1 .claw {{ color: var(--text-dim); }}
.hud-top .back-link {{
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.65rem;
  color: var(--text-dim);
  text-decoration: none;
  letter-spacing: 0.05em;
  transition: color 0.2s;
}}
.hud-top .back-link:hover {{ color: var(--mutable); }}

/* Controls bar */
.controls {{
  position: fixed;
  bottom: 1.5rem; left: 50%; transform: translateX(-50%);
  z-index: 100;
  display: flex; align-items: center; gap: 0.6rem;
  background: rgba(12, 12, 20, 0.85);
  backdrop-filter: blur(12px);
  border: 1px solid rgba(30, 30, 48, 0.6);
  border-radius: 40px;
  padding: 0.5rem 1.2rem;
}}
.controls button {{
  background: none;
  border: 1px solid rgba(30, 30, 48, 0.8);
  color: var(--text);
  width: 32px; height: 32px;
  border-radius: 50%;
  font-size: 0.8rem;
  cursor: pointer;
  transition: all 0.2s;
  display: flex; align-items: center; justify-content: center;
}}
.controls button:hover {{
  background: var(--accent);
  color: #fff;
  border-color: var(--accent);
}}
.controls button.active {{
  background: var(--accent);
  color: #fff;
  border-color: var(--accent);
}}
.controls .slider-wrap {{
  display: flex; align-items: center; gap: 0.5rem;
  min-width: 240px;
}}
.controls input[type=range] {{
  -webkit-appearance: none;
  flex: 1;
  height: 3px;
  border-radius: 2px;
  background: rgba(30, 30, 48, 0.8);
  outline: none;
}}
.controls input[type=range]::-webkit-slider-thumb {{
  -webkit-appearance: none;
  width: 14px; height: 14px;
  border-radius: 50%;
  background: var(--accent);
  cursor: pointer;
  box-shadow: 0 0 10px rgba(124, 111, 240, 0.4);
}}
.controls .step-label {{
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.65rem;
  color: var(--text-dim);
  min-width: 50px;
  text-align: center;
}}

/* Tooltip */
.tooltip {{
  position: fixed;
  z-index: 200;
  background: rgba(12, 12, 22, 0.95);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(30, 30, 48, 0.8);
  border-radius: 8px;
  padding: 0.6rem 0.8rem;
  max-width: 320px;
  font-size: 0.78rem;
  line-height: 1.45;
  color: var(--text);
  pointer-events: none;
  opacity: 0;
  transform: translateY(4px);
  transition: opacity 0.2s, transform 0.2s;
}}
.tooltip.show {{
  opacity: 1;
  transform: translateY(0);
}}
.tooltip .tt-tag {{
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.6rem;
  font-weight: 700;
  letter-spacing: 0.05em;
  margin-bottom: 0.3rem;
}}
.tooltip .tt-tag.core {{ color: var(--core); }}
.tooltip .tt-tag.mutable {{ color: var(--mutable); }}
.tooltip .tt-section {{
  font-size: 0.65rem;
  color: var(--text-dim);
  margin-bottom: 0.2rem;
}}

/* Legend */
.hud-legend {{
  position: fixed;
  bottom: 5rem; left: 50%; transform: translateX(-50%);
  z-index: 100;
  display: flex; gap: 1.2rem;
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.6rem;
  color: var(--text-dim);
  letter-spacing: 0.04em;
}}
.hud-legend .l-item {{
  display: flex; align-items: center; gap: 0.35rem;
}}
.hud-legend .l-dot {{
  width: 7px; height: 7px; border-radius: 50%;
}}

/* Change notification */
.change-toast {{
  position: fixed;
  top: 4rem; right: 1.5rem;
  z-index: 150;
  background: rgba(12, 12, 22, 0.9);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(80, 200, 120, 0.3);
  border-radius: 10px;
  padding: 0.7rem 1rem;
  max-width: 300px;
  font-size: 0.75rem;
  line-height: 1.4;
  opacity: 0;
  transform: translateX(20px);
  transition: all 0.4s;
}}
.change-toast.show {{
  opacity: 1;
  transform: translateX(0);
}}
.change-toast .ct-label {{
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.6rem;
  font-weight: 700;
  color: var(--mutable);
  text-transform: uppercase;
  letter-spacing: 0.08em;
  margin-bottom: 0.3rem;
}}
</style>
</head>
<body>

<div class="hud hud-top">
  <a href="soul-evolution.html" class="back-link">← back to dashboard</a>
  <h1><span class="evo">evo</span><span class="claw">claw</span> · mindmap</h1>
</div>

<div class="controls">
  <button id="btn-play" title="Play growth">▶</button>
  <button id="btn-reset" title="Reset to origin">⟲</button>
  <div class="slider-wrap">
    <span class="step-label" id="step-label">origin</span>
    <input type="range" id="timeline" min="0" max="1" value="1" step="1">
  </div>
  <button id="btn-fit" title="Fit to view">⊡</button>
</div>

<div class="hud-legend" id="legend"></div>

<div class="tooltip" id="tooltip">
  <div class="tt-tag" id="tt-tag"></div>
  <div class="tt-section" id="tt-section"></div>
  <div id="tt-text"></div>
</div>

<div class="change-toast" id="change-toast">
  <div class="ct-label">soul change</div>
  <div id="ct-text"></div>
</div>

<canvas id="canvas"></canvas>

<script>
const DATA = {data_json};

// --- Color palette ---
const SECTION_COLORS = {{
  'Personality': '#f0a050',
  'Philosophy': '#7c6ff0',
  'Boundaries': '#e05050',
  'Continuity': '#50b8e0',
}};
function secColor(name) {{
  for (const [k, v] of Object.entries(SECTION_COLORS)) {{
    if (name && name.includes(k)) return v;
  }}
  return '#888';
}}
function hexToRgb(hex) {{
  const r = parseInt(hex.slice(1,3),16);
  const g = parseInt(hex.slice(3,5),16);
  const b = parseInt(hex.slice(5,7),16);
  return [r, g, b];
}}

// --- Build node tree ---
function buildNodes() {{
  const nodes = [];
  const edges = [];
  let id = 0;

  // Root
  const root = {{ id: id++, type: 'root', label: 'SOUL', x: 0, y: 0, r: 28, color: '#7c6ff0', depth: 0, growStep: -1 }};
  nodes.push(root);

  let growIdx = 0;

  DATA.soul_tree.forEach((sec, si) => {{
    const color = secColor(sec.text);
    const sNode = {{ id: id++, type: 'section', label: sec.text, x: 0, y: 0, r: 18, color, depth: 1, growStep: growIdx++, parentId: root.id }};
    nodes.push(sNode);
    edges.push({{ from: root.id, to: sNode.id, color }});

    sec.children.forEach((child, ci) => {{
      if (child.type === 'subsection') {{
        const subNode = {{ id: id++, type: 'subsection', label: child.text, x: 0, y: 0, r: 12, color, depth: 2, growStep: growIdx++, parentId: sNode.id }};
        nodes.push(subNode);
        edges.push({{ from: sNode.id, to: subNode.id, color }});

        (child.children || []).forEach((b, bi) => {{
          const isAdded = DATA.changes.some(c => c.after && c.after.trim() === b.raw.trim());
          const bNode = {{
            id: id++, type: 'bullet', label: b.text, tag: b.tag,
            x: 0, y: 0, r: b.tag === 'CORE' ? 7 : 6,
            color: b.tag === 'CORE' ? '#e05050' : (b.tag === 'MUTABLE' ? '#50c878' : '#666'),
            depth: 3, growStep: growIdx++, parentId: subNode.id,
            raw: b.raw, isChangeAdded: isAdded,
            section: sec.text, subsection: child.text,
          }};
          nodes.push(bNode);
          edges.push({{ from: subNode.id, to: bNode.id, color: bNode.color }});
        }});
      }} else if (child.type === 'bullet') {{
        const b = child;
        const bNode = {{
          id: id++, type: 'bullet', label: b.text, tag: b.tag,
          x: 0, y: 0, r: b.tag === 'CORE' ? 7 : 6,
          color: b.tag === 'CORE' ? '#e05050' : (b.tag === 'MUTABLE' ? '#50c878' : '#666'),
          depth: 2, growStep: growIdx++, parentId: sNode.id,
          raw: b.raw, isChangeAdded: false,
          section: sec.text, subsection: '',
        }};
        nodes.push(bNode);
        edges.push({{ from: sNode.id, to: bNode.id, color: bNode.color }});
      }}
    }});
  }});

  // Mark change-added nodes with the change index
  DATA.changes.forEach((c, ci) => {{
    if (c.after) {{
      const match = nodes.find(n => n.raw && n.raw.trim() === c.after.trim());
      if (match) match.changeIdx = ci;
    }}
  }});

  return {{ nodes, edges, totalGrowSteps: growIdx }};
}}

// --- Layout: radial tree ---
function layoutRadial(nodes, edges) {{
  const childrenOf = {{}};
  edges.forEach(e => {{
    if (!childrenOf[e.from]) childrenOf[e.from] = [];
    childrenOf[e.from].push(e.to);
  }});

  const nodeMap = {{}};
  nodes.forEach(n => nodeMap[n.id] = n);

  function countLeaves(nid) {{
    const kids = childrenOf[nid] || [];
    if (kids.length === 0) return 1;
    return kids.reduce((s, k) => s + countLeaves(k), 0);
  }}

  function layout(nid, angleStart, angleEnd, radius) {{
    const node = nodeMap[nid];
    const kids = childrenOf[nid] || [];
    const mid = (angleStart + angleEnd) / 2;

    if (nid !== 0) {{
      node.x = Math.cos(mid) * radius;
      node.y = Math.sin(mid) * radius;
    }}

    if (kids.length === 0) return;

    const totalLeaves = countLeaves(nid);
    let cursor = angleStart;

    kids.forEach(kid => {{
      const kidNode = nodeMap[kid];
      const leaves = countLeaves(kid);
      const share = (leaves / totalLeaves) * (angleEnd - angleStart);
      const extra = radiusBonus(kidNode);
      layout(kid, cursor, cursor + share, radius + radiusStep(kidNode.depth) + extra);
      cursor += share;
    }});
  }}

  function radiusStep(depth) {{
    if (depth === 1) return 160;
    if (depth === 2) return 130;
    return 110;
  }}

  // Push change-added nodes further out from the core
  function radiusBonus(node) {{
    if (node.changeIdx !== undefined) {{
      // Each successive change gets pushed further out
      return 60 + node.changeIdx * 40;
    }}
    return 0;
  }}

  layout(0, -Math.PI, Math.PI, 0);
}}

// --- Canvas renderer ---
const canvas = document.getElementById('canvas');
const ctx = canvas.getContext('2d');
let W, H;
let camX = 0, camY = 0, camZoom = 1;
let targetCamX = 0, targetCamY = 0, targetCamZoom = 1;
let camSmooth = 0.06; // lerp speed
let isDragging = false, dragStartX, dragStartY, camStartX, camStartY;
let hoveredNode = null;
let animTime = 0;

const {{ nodes, edges, totalGrowSteps }} = buildNodes();
layoutRadial(nodes, edges);

// Current visible step
let currentStep = DATA.changes.length; // max
let maxGrowStep = totalGrowSteps;
const slider = document.getElementById('timeline');
slider.max = DATA.changes.length;
slider.value = DATA.changes.length;

// Determine which growSteps are visible at each timeline step
function getVisibleGrowStep(timelineStep) {{
  // All nodes visible except those added by changes AFTER timelineStep
  const hiddenChanges = new Set();
  for (let i = DATA.changes.length - 1; i >= timelineStep; i--) {{
    if (DATA.changes[i].after) hiddenChanges.add(DATA.changes[i].after.trim());
  }}
  return hiddenChanges;
}}

// Particles for celebrations
let particles = [];
function spawnParticles(x, y, color) {{
  const [r, g, b] = hexToRgb(color);
  for (let i = 0; i < 20; i++) {{
    const angle = Math.random() * Math.PI * 2;
    const speed = 1 + Math.random() * 3;
    particles.push({{
      x, y,
      vx: Math.cos(angle) * speed,
      vy: Math.sin(angle) * speed,
      life: 1,
      decay: 0.01 + Math.random() * 0.02,
      r, g, b,
      size: 2 + Math.random() * 3,
    }});
  }}
}}

function resize() {{
  W = window.innerWidth;
  H = window.innerHeight;
  canvas.width = W * devicePixelRatio;
  canvas.height = H * devicePixelRatio;
  canvas.style.width = W + 'px';
  canvas.style.height = H + 'px';
  ctx.setTransform(devicePixelRatio, 0, 0, devicePixelRatio, 0, 0);
}}
window.addEventListener('resize', resize);
resize();

// Node grow animation state
const nodeAnim = {{}};
nodes.forEach(n => {{
  nodeAnim[n.id] = {{ scale: 0, targetScale: 1, visible: true }};
}});

function setVisibility() {{
  const hidden = getVisibleGrowStep(currentStep);
  nodes.forEach(n => {{
    if (n.raw && hidden.has(n.raw.trim())) {{
      nodeAnim[n.id].targetScale = 0;
      nodeAnim[n.id].visible = false;
    }} else {{
      nodeAnim[n.id].targetScale = 1;
      nodeAnim[n.id].visible = true;
    }}
  }});
}}
setVisibility();
// Start fully visible
nodes.forEach(n => {{ nodeAnim[n.id].scale = nodeAnim[n.id].targetScale; }});

function screenToWorld(sx, sy) {{
  return [(sx - W/2) / camZoom + camX, (sy - H/2) / camZoom + camY];
}}

function worldToScreen(wx, wy) {{
  return [(wx - camX) * camZoom + W/2, (wy - camY) * camZoom + H/2];
}}

// --- Drawing ---
function draw() {{
  animTime += 0.016;

  // Smooth camera
  camX += (targetCamX - camX) * camSmooth;
  camY += (targetCamY - camY) * camSmooth;
  camZoom += (targetCamZoom - camZoom) * camSmooth;

  // Animate node scales
  nodes.forEach(n => {{
    const a = nodeAnim[n.id];
    a.scale += (a.targetScale - a.scale) * 0.08;
    if (Math.abs(a.scale - a.targetScale) < 0.001) a.scale = a.targetScale;
  }});

  // Update particles
  particles = particles.filter(p => {{
    p.x += p.vx;
    p.y += p.vy;
    p.vx *= 0.97;
    p.vy *= 0.97;
    p.life -= p.decay;
    return p.life > 0;
  }});

  ctx.clearRect(0, 0, W, H);

  // Background glow
  const grad = ctx.createRadialGradient(W/2, H/2, 0, W/2, H/2, Math.max(W, H) * 0.6);
  grad.addColorStop(0, 'rgba(124, 111, 240, 0.03)');
  grad.addColorStop(1, 'transparent');
  ctx.fillStyle = grad;
  ctx.fillRect(0, 0, W, H);

  ctx.save();
  ctx.translate(W/2, H/2);
  ctx.scale(camZoom, camZoom);
  ctx.translate(-camX, -camY);

  const nodeMap = {{}};
  nodes.forEach(n => nodeMap[n.id] = n);

  // Draw edges (organic bezier curves)
  edges.forEach(e => {{
    const from = nodeMap[e.from];
    const to = nodeMap[e.to];
    const aFrom = nodeAnim[from.id];
    const aTo = nodeAnim[to.id];
    const alpha = Math.min(aFrom.scale, aTo.scale);
    if (alpha < 0.01) return;

    const [r, g, b] = hexToRgb(e.color);

    ctx.beginPath();
    const dx = to.x - from.x;
    const dy = to.y - from.y;
    const dist = Math.sqrt(dx*dx + dy*dy);

    // Organic bezier: control points offset perpendicular
    const mx = (from.x + to.x) / 2;
    const my = (from.y + to.y) / 2;
    const nx = -dy / dist;
    const ny = dx / dist;
    const wobble = Math.sin(animTime * 0.5 + from.id) * 8;
    const cpx = mx + nx * wobble;
    const cpy = my + ny * wobble;

    ctx.moveTo(from.x, from.y);
    ctx.quadraticCurveTo(cpx, cpy, to.x, to.y);

    ctx.strokeStyle = `rgba(${{r}},${{g}},${{b}},${{alpha * 0.25}})`;
    ctx.lineWidth = to.depth <= 1 ? 2.5 : (to.depth === 2 ? 1.5 : 1);
    ctx.stroke();
  }});

  // Draw nodes
  nodes.forEach(n => {{
    const a = nodeAnim[n.id];
    if (a.scale < 0.01) return;

    const s = a.scale;
    const r = n.r * s;
    const [cr, cg, cb] = hexToRgb(n.color);
    const isHov = hoveredNode && hoveredNode.id === n.id;

    // Glow
    if (n.type !== 'bullet' || isHov) {{
      const glowR = r * (isHov ? 4 : 2.5);
      const glow = ctx.createRadialGradient(n.x, n.y, r * 0.5, n.x, n.y, glowR);
      glow.addColorStop(0, `rgba(${{cr}},${{cg}},${{cb}},${{s * (isHov ? 0.25 : 0.12)}})`);
      glow.addColorStop(1, 'transparent');
      ctx.fillStyle = glow;
      ctx.fillRect(n.x - glowR, n.y - glowR, glowR * 2, glowR * 2);
    }}

    // Node circle
    ctx.beginPath();
    ctx.arc(n.x, n.y, r, 0, Math.PI * 2);
    ctx.fillStyle = `rgba(${{cr}},${{cg}},${{cb}},${{s * (isHov ? 0.9 : 0.7)}})`;
    ctx.fill();

    // Border ring
    if (n.type === 'root' || n.type === 'section' || isHov) {{
      ctx.beginPath();
      ctx.arc(n.x, n.y, r + 1.5, 0, Math.PI * 2);
      ctx.strokeStyle = `rgba(${{cr}},${{cg}},${{cb}},${{s * 0.5}})`;
      ctx.lineWidth = 1;
      ctx.stroke();
    }}

    // Pulse ring for change-added nodes at current step
    if (n.changeIdx !== undefined && n.changeIdx === currentStep - 1) {{
      const pulse = (Math.sin(animTime * 3) + 1) * 0.5;
      ctx.beginPath();
      ctx.arc(n.x, n.y, r + 4 + pulse * 6, 0, Math.PI * 2);
      ctx.strokeStyle = `rgba(${{cr}},${{cg}},${{cb}},${{0.3 + pulse * 0.3}})`;
      ctx.lineWidth = 1.5;
      ctx.stroke();
    }}

    // Labels
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';

    if (n.type === 'root') {{
      ctx.font = `700 ${{14 * s}}px 'JetBrains Mono', monospace`;
      ctx.fillStyle = `rgba(255,255,255,${{s}})`;
      ctx.fillText(n.label, n.x, n.y);
    }} else if (n.type === 'section') {{
      ctx.font = `500 ${{11 * s}}px 'JetBrains Mono', monospace`;
      ctx.fillStyle = `rgba(255,255,255,${{s * 0.9}})`;
      ctx.fillText(n.label, n.x, n.y + r + 14);
    }} else if (n.type === 'subsection' && camZoom > 0.5) {{
      ctx.font = `400 ${{9 * s}}px 'DM Sans', sans-serif`;
      ctx.fillStyle = `rgba(200,200,216,${{s * 0.7}})`;
      const maxW = 100;
      ctx.fillText(n.label.length > 18 ? n.label.slice(0, 16) + '…' : n.label, n.x, n.y + r + 12);
    }}
  }});

  // Particles
  particles.forEach(p => {{
    ctx.beginPath();
    ctx.arc(p.x, p.y, p.size * p.life, 0, Math.PI * 2);
    ctx.fillStyle = `rgba(${{p.r}},${{p.g}},${{p.b}},${{p.life * 0.6}})`;
    ctx.fill();
  }});

  ctx.restore();
  requestAnimationFrame(draw);
}}

// --- Interaction ---
canvas.addEventListener('mousedown', e => {{
  isDragging = true;
  dragStartX = e.clientX;
  dragStartY = e.clientY;
  camStartX = camX;
  camStartY = camY;
  document.body.classList.add('dragging');
}});
window.addEventListener('mousemove', e => {{
  if (isDragging) {{
    const nx = camStartX - (e.clientX - dragStartX) / camZoom;
    const ny = camStartY - (e.clientY - dragStartY) / camZoom;
    camX = targetCamX = nx;
    camY = targetCamY = ny;
  }}

  // Hover detection
  const [wx, wy] = screenToWorld(e.clientX, e.clientY);
  let found = null;
  // Check in reverse (top nodes last drawn = on top)
  for (let i = nodes.length - 1; i >= 0; i--) {{
    const n = nodes[i];
    const a = nodeAnim[n.id];
    if (a.scale < 0.1) continue;
    const dx = wx - n.x;
    const dy = wy - n.y;
    const hitR = Math.max(n.r * a.scale, 10);
    if (dx*dx + dy*dy < hitR * hitR) {{
      found = n;
      break;
    }}
  }}

  hoveredNode = found;
  const tooltip = document.getElementById('tooltip');
  if (found && (found.type === 'bullet' || found.type === 'subsection')) {{
    tooltip.classList.add('show');
    tooltip.style.left = (e.clientX + 16) + 'px';
    tooltip.style.top = (e.clientY - 10) + 'px';
    // Clamp
    if (e.clientX + 340 > W) tooltip.style.left = (e.clientX - 330) + 'px';

    const tagEl = document.getElementById('tt-tag');
    const secEl = document.getElementById('tt-section');
    const textEl = document.getElementById('tt-text');

    if (found.tag) {{
      tagEl.textContent = found.tag;
      tagEl.className = 'tt-tag ' + found.tag.toLowerCase();
      tagEl.style.display = '';
    }} else {{
      tagEl.style.display = 'none';
    }}
    secEl.textContent = (found.section || '') + (found.subsection ? ' › ' + found.subsection : '');
    textEl.textContent = found.label;
  }} else {{
    tooltip.classList.remove('show');
  }}
}});
window.addEventListener('mouseup', () => {{
  isDragging = false;
  document.body.classList.remove('dragging');
}});

canvas.addEventListener('wheel', e => {{
  e.preventDefault();
  const factor = e.deltaY > 0 ? 0.9 : 1.1;
  const [wx, wy] = screenToWorld(e.clientX, e.clientY);
  camZoom *= factor;
  camZoom = Math.max(0.15, Math.min(5, camZoom));
  camX = wx - (e.clientX - W/2) / camZoom;
  camY = wy - (e.clientY - H/2) / camZoom;
  targetCamX = camX;
  targetCamY = camY;
  targetCamZoom = camZoom;
}}, {{ passive: false }});

// --- Timeline controls ---
const stepLabel = document.getElementById('step-label');

function setStep(s) {{
  currentStep = s;
  slider.value = s;
  setVisibility();
  if (s === 0) {{
    stepLabel.textContent = 'origin';
  }} else {{
    const c = DATA.changes[s - 1];
    stepLabel.textContent = (c.timestamp || '').slice(11, 16) || '#' + s;
  }}
}}

slider.oninput = () => setStep(parseInt(slider.value));

// Play
let playing = false;
let playTimer = null;
document.getElementById('btn-play').onclick = () => {{
  const btn = document.getElementById('btn-play');
  if (playing) {{
    clearInterval(playTimer);
    playing = false;
    btn.textContent = '▶';
    btn.classList.remove('active');
    return;
  }}
  playing = true;
  btn.textContent = '⏸';
  btn.classList.add('active');

  // Start at origin: all base nodes visible, no changes applied
  setStep(0);

  // Instantly grow all base (non-change) nodes with a quick stagger
  nodes.forEach(n => {{
    const a = nodeAnim[n.id];
    if (n.changeIdx === undefined && a.visible) {{
      setTimeout(() => {{ a.targetScale = 1; }}, n.growStep * 25);
    }}
  }});

  // Fit tight on the base tree first
  setTimeout(() => fitToVisible(false), 200);

  // After base tree is grown, play changes one by one at uniform pace
  const baseGrowTime = Math.min(maxGrowStep * 25 + 400, 1500);
  const changePause = 2000; // 2 seconds per change

  let changeIdx = 0;
  setTimeout(() => {{
    if (!playing) return;
    // Fit to base tree before changes start
    fitToVisible(false);

    playTimer = setInterval(() => {{
      changeIdx++;
      if (changeIdx <= DATA.changes.length) {{
        setStep(changeIdx);
        // Smoothly zoom out to include the new node
        fitToVisible(false);
        // Celebrate the new node
        const c = DATA.changes[changeIdx - 1];
        if (c && c.after) {{
          const match = nodes.find(n => n.raw && n.raw.trim() === c.after.trim());
          if (match) {{
            spawnParticles(match.x, match.y, match.color);
            const toast = document.getElementById('change-toast');
            document.getElementById('ct-text').textContent =
              c.after.replace(/\\s*\\[(CORE|MUTABLE)\\]\\s*/g, '').replace(/^- /, '').slice(0, 120);
            toast.classList.add('show');
            setTimeout(() => toast.classList.remove('show'), changePause - 300);
          }}
        }}
      }} else {{
        clearInterval(playTimer);
        playing = false;
        btn.textContent = '▶';
        btn.classList.remove('active');
      }}
    }}, changePause);
  }}, baseGrowTime);
}};

document.getElementById('btn-reset').onclick = () => {{
  if (playing) {{
    clearInterval(playTimer);
    playing = false;
    document.getElementById('btn-play').textContent = '▶';
    document.getElementById('btn-play').classList.remove('active');
  }}
  // Reset all scales to 0, then grow
  nodes.forEach(n => {{
    nodeAnim[n.id].scale = 0;
    nodeAnim[n.id].targetScale = 0;
  }});
  setStep(0);
  // Quick regrow
  setTimeout(() => {{
    nodes.forEach(n => {{
      if (!n.raw || !getVisibleGrowStep(0).has(n.raw.trim())) {{
        setTimeout(() => {{ nodeAnim[n.id].targetScale = 1; }}, n.growStep * 40);
      }}
    }});
    fitToVisible(false);
  }}, 200);
}};

// Fit camera to visible nodes, always centered on SOUL (0,0)
function fitToVisible(instant) {{
  let maxDist = 0;
  nodes.forEach(n => {{
    if (nodeAnim[n.id].scale > 0.1 || nodeAnim[n.id].targetScale > 0.5) {{
      const dist = Math.sqrt(n.x * n.x + n.y * n.y) + n.r + 40;
      if (dist > maxDist) maxDist = dist;
    }}
  }});
  maxDist = Math.max(maxDist, 80); // minimum extent
  const padding = 1.15;
  const halfExtent = maxDist * padding;
  const zoom = Math.min(W / (halfExtent * 2), H / (halfExtent * 2), 2.5);

  targetCamX = 0;
  targetCamY = 0;
  targetCamZoom = zoom;
  if (instant) {{
    camX = targetCamX;
    camY = targetCamY;
    camZoom = targetCamZoom;
  }}
}}

document.getElementById('btn-fit').onclick = () => fitToVisible(false);

// Legend
document.getElementById('legend').innerHTML = [
  {{ c: '#e05050', l: 'CORE' }},
  {{ c: '#50c878', l: 'MUTABLE' }},
  ...Object.entries(SECTION_COLORS).map(([k, v]) => ({{ c: v, l: k }})),
].map(i => `<div class="l-item"><div class="l-dot" style="background:${{i.c}}"></div>${{i.l}}</div>`).join('');

// Init
// Start fully grown
nodes.forEach(n => {{
  nodeAnim[n.id].scale = nodeAnim[n.id].targetScale;
}});
setStep(DATA.changes.length);
setTimeout(() => fitToVisible(true), 100);
draw();
</script>
</body>
</html>"""


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    workspace = sys.argv[1]

    # Check for SOUL.md at workspace root
    soul_path = os.path.join(workspace, "SOUL.md")
    if not os.path.exists(soul_path):
        # Maybe they passed the parent dir
        for candidate in ["SOUL.md", "workspace-evoclaw-demo/SOUL.md"]:
            p = os.path.join(workspace, candidate)
            if os.path.exists(p):
                workspace = os.path.dirname(p)
                break
        else:
            print(f"Error: Cannot find SOUL.md in {workspace}")
            sys.exit(1)

    print(f"Reading workspace: {workspace}")
    data = collect_data(workspace)

    print(f"  Soul sections: {len(data['soul_tree'])}")
    print(f"  Experiences: {len(data['experiences'])}")
    print(f"  Reflections: {len(data['reflections'])}")
    print(f"  Soul changes: {len(data['changes'])}")

    html = generate_html(data)
    mindmap_html = generate_mindmap_html(data)

    # --serve mode
    if "--serve" in sys.argv:
        port = 8080
        idx = sys.argv.index("--serve")
        if idx + 1 < len(sys.argv) and sys.argv[idx + 1].isdigit():
            port = int(sys.argv[idx + 1])

        import http.server
        import socketserver
        import tempfile

        out_dir = tempfile.gettempdir()
        with open(os.path.join(out_dir, "soul-evolution.html"), "w") as f:
            f.write(html)
        with open(os.path.join(out_dir, "soul-mindmap.html"), "w") as f:
            f.write(mindmap_html)

        soul_path = os.path.join(workspace, "SOUL.md")

        class EvoclawHandler(http.server.SimpleHTTPRequestHandler):
            def do_POST(self):
                if self.path == "/save-soul":
                    length = int(self.headers.get("Content-Length", 0))
                    body = self.rfile.read(length).decode("utf-8")
                    try:
                        with open(soul_path, "w") as f:
                            f.write(body)
                        self.send_response(200)
                        self.send_header("Content-Type", "text/plain")
                        self.end_headers()
                        self.wfile.write(b"OK")
                        print(f"  ✓ SOUL.md saved ({len(body)} bytes)")
                    except Exception as e:
                        self.send_response(500)
                        self.send_header("Content-Type", "text/plain")
                        self.end_headers()
                        self.wfile.write(str(e).encode())
                        print(f"  ✗ Save failed: {e}")
                else:
                    self.send_response(404)
                    self.end_headers()

            def log_message(self, format, *args):
                # Suppress GET request logging noise
                if "POST" in str(args):
                    super().log_message(format, *args)

        os.chdir(out_dir)
        print(f"\n  → Serving at http://localhost:{port}/soul-evolution.html")
        print(f"  → Mindmap at  http://localhost:{port}/soul-mindmap.html")
        print(f"  → Edits save directly to: {soul_path}\n")

        with socketserver.TCPServer(("", port), EvoclawHandler) as httpd:
            try:
                httpd.serve_forever()
            except KeyboardInterrupt:
                print("\nStopped.")
    else:
        out_dir = os.path.dirname(workspace)
        with open(os.path.join(out_dir, "soul-evolution.html"), "w") as f:
            f.write(html)
        with open(os.path.join(out_dir, "soul-mindmap.html"), "w") as f:
            f.write(mindmap_html)
        print(f"\n  → Dashboard: {os.path.join(out_dir, 'soul-evolution.html')}")
        print(f"  → Mindmap:   {os.path.join(out_dir, 'soul-mindmap.html')}")
        print(f"  → Open in browser or run: python3 -m http.server 8080")


if __name__ == "__main__":
    main()
