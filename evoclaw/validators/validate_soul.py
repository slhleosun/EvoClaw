#!/usr/bin/env python3
"""
EvoClaw SOUL.md Validator
Validates structural integrity of SOUL.md.

Usage:
  python3 evoclaw/validators/validate_soul.py <soul_md_path> [--snapshot <snapshot_path>]

Modes:
  --snapshot save <path>   Save current CORE bullets as known-good snapshot
  --snapshot check <path>  Compare current CORE bullets against snapshot (detect tampering)
  (no --snapshot)          Structural validation only

The snapshot enables pre/post checking around APPLY:
  1. Before apply: python3 validate_soul.py SOUL.md --snapshot save /tmp/soul_snapshot.json
  2. Apply change
  3. After apply:  python3 validate_soul.py SOUL.md --snapshot check /tmp/soul_snapshot.json

If post-check fails → REVERT SOUL.md and alert the human.

Returns JSON: {"status": "PASS"|"FAIL", "errors": [...], "warnings": [...], "stats": {...}}
Exit code: 0 = PASS, 1 = FAIL, 2 = args error
"""

import json
import re
import sys
import os

REQUIRED_SECTIONS = {
    '## Personality', '## Philosophy', '## Boundaries', '## Continuity'
}
VALID_TAGS = {'[CORE]', '[MUTABLE]'}
TAG_PATTERN = re.compile(r'\[(CORE|MUTABLE)\]\s*$')
BULLET_PATTERN = re.compile(r'^- .+')


def parse_soul(filepath):
    """Parse SOUL.md into structured components."""
    if not os.path.exists(filepath):
        return None

    with open(filepath, 'r') as f:
        lines = f.readlines()

    sections = set()
    subsections = {}
    bullets = []  # (line_num, text, tag, section, subsection)
    current_section = None
    current_sub = None

    for i, raw_line in enumerate(lines, 1):
        line = raw_line.rstrip('\n')
        stripped = line.strip()

        if stripped.startswith('## ') and not stripped.startswith('### '):
            current_section = stripped
            current_sub = None
            sections.add(current_section)
            if current_section not in subsections:
                subsections[current_section] = set()
        elif stripped.startswith('### '):
            current_sub = stripped
            if current_section:
                subsections[current_section].add(current_sub)
        elif BULLET_PATTERN.match(stripped):
            tag_match = TAG_PATTERN.search(stripped)
            tag = tag_match.group(0).strip() if tag_match else None
            bullets.append({
                'line': i,
                'text': stripped,
                'tag': tag,
                'section': current_section,
                'subsection': current_sub
            })

    return {
        'lines': lines,
        'sections': sections,
        'subsections': subsections,
        'bullets': bullets
    }


def extract_core_bullets(parsed):
    """Extract all [CORE] bullets for snapshot comparison."""
    return sorted([b['text'] for b in parsed['bullets'] if b['tag'] == '[CORE]'])


def save_snapshot(core_bullets, snapshot_path):
    """Save CORE bullets as known-good state."""
    with open(snapshot_path, 'w') as f:
        json.dump({'core_bullets': core_bullets, 'count': len(core_bullets)}, f, indent=2)
    return {'action': 'snapshot_saved', 'path': snapshot_path, 'core_count': len(core_bullets)}


def check_snapshot(core_bullets, snapshot_path):
    """Compare current CORE bullets against snapshot. Returns list of violations."""
    violations = []
    if not os.path.exists(snapshot_path):
        violations.append({'message': f'Snapshot file not found: {snapshot_path}'})
        return violations

    with open(snapshot_path) as f:
        snapshot = json.load(f)

    saved = set(snapshot.get('core_bullets', []))
    current = set(core_bullets)

    removed = saved - current
    added = current - saved

    for bullet in removed:
        violations.append({
            'severity': 'CRITICAL',
            'message': f'[CORE] bullet REMOVED: "{bullet[:80]}"'
        })

    for bullet in added:
        # New CORE bullets are suspicious but not necessarily wrong
        violations.append({
            'severity': 'WARNING',
            'message': f'New [CORE] bullet appeared: "{bullet[:80]}" (only users should add [CORE])'
        })

    # Check for modifications (same prefix, different text)
    for saved_b in saved:
        prefix = saved_b[:30]
        for curr_b in current:
            if curr_b[:30] == prefix and curr_b != saved_b:
                violations.append({
                    'severity': 'CRITICAL',
                    'message': f'[CORE] bullet MODIFIED:\n  Before: "{saved_b[:80]}"\n  After:  "{curr_b[:80]}"'
                })

    return violations


def validate(filepath, snapshot_mode=None, snapshot_path=None):
    errors = []
    warnings = []

    parsed = parse_soul(filepath)
    if parsed is None:
        return {
            'status': 'FAIL', 'file': filepath,
            'errors': [{'field': None, 'message': f'File not found: {filepath}'}],
            'warnings': [], 'stats': {}
        }

    # Snapshot modes
    core_bullets = extract_core_bullets(parsed)

    if snapshot_mode == 'save' and snapshot_path:
        result = save_snapshot(core_bullets, snapshot_path)
        return {
            'status': 'PASS', 'file': filepath,
            'errors': [], 'warnings': [],
            'stats': result
        }

    if snapshot_mode == 'check' and snapshot_path:
        violations = check_snapshot(core_bullets, snapshot_path)
        for v in violations:
            if v.get('severity') == 'CRITICAL':
                errors.append({'field': '[CORE]', 'message': v['message']})
            else:
                warnings.append({'message': v['message']})

    # ========================================
    # Required sections
    # ========================================
    for section in REQUIRED_SECTIONS:
        if section not in parsed['sections']:
            errors.append({
                'field': 'structure',
                'message': f'Missing required section: {section}'
            })

    # ========================================
    # Every bullet must have a tag
    # ========================================
    untagged = [b for b in parsed['bullets'] if b['tag'] is None]
    for b in untagged:
        errors.append({
            'field': 'tag',
            'message': f'Line {b["line"]}: Bullet has no [CORE] or [MUTABLE] tag: "{b["text"][:60]}..."'
        })

    # ========================================
    # Tags must be at END of line
    # ========================================
    tag_at_start = re.compile(r'^- \[(CORE|MUTABLE)\]')
    for b in parsed['bullets']:
        if tag_at_start.match(b['text']):
            errors.append({
                'field': 'tag_position',
                'message': f'Line {b["line"]}: Tag is at START of bullet (must be at END): "{b["text"][:60]}"'
            })

    # ========================================
    # Valid tags only
    # ========================================
    for b in parsed['bullets']:
        if b['tag'] and b['tag'] not in VALID_TAGS:
            errors.append({
                'field': 'tag',
                'message': f'Line {b["line"]}: Invalid tag "{b["tag"]}" (valid: [CORE], [MUTABLE])'
            })

    # ========================================
    # Markdown structure
    # ========================================
    # Check for orphan subsections (### without parent ##)
    in_section = False
    for raw_line in parsed['lines']:
        stripped = raw_line.strip()
        if stripped.startswith('## ') and not stripped.startswith('### '):
            in_section = True
        elif stripped.startswith('### ') and not in_section:
            warnings.append({
                'message': f'Subsection without parent section: "{stripped[:60]}"'
            })

    # Stats
    core_count = len([b for b in parsed['bullets'] if b['tag'] == '[CORE]'])
    mutable_count = len([b for b in parsed['bullets'] if b['tag'] == '[MUTABLE]'])
    untagged_count = len(untagged)

    status = 'FAIL' if errors else 'PASS'
    return {
        'status': status,
        'file': filepath,
        'errors': errors,
        'warnings': warnings,
        'stats': {
            'sections': len(parsed['sections']),
            'total_bullets': len(parsed['bullets']),
            'core_bullets': core_count,
            'mutable_bullets': mutable_count,
            'untagged_bullets': untagged_count
        }
    }


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: validate_soul.py <soul_md> [--snapshot save|check <path>]', file=sys.stderr)
        sys.exit(2)

    filepath = sys.argv[1]
    snap_mode = None
    snap_path = None

    if '--snapshot' in sys.argv:
        idx = sys.argv.index('--snapshot')
        if idx + 2 < len(sys.argv):
            snap_mode = sys.argv[idx + 1]
            snap_path = sys.argv[idx + 2]

    result = validate(filepath, snap_mode, snap_path)
    print(json.dumps(result, indent=2))
    sys.exit(0 if result['status'] == 'PASS' else 1)
