#!/usr/bin/env python3
"""
EvoClaw Proposal Validator
Validates proposals in pending.jsonl AGAINST the actual SOUL.md file.

This is the most critical validator — it prevents SOUL.md corruption by
catching mismatched current_content before the apply step.

Usage:
  python3 evoclaw/validators/validate_proposal.py <proposals_jsonl> <soul_md_path>

Returns JSON: {"status": "PASS"|"FAIL", "errors": [...], "warnings": [...]}
Exit code: 0 = PASS, 1 = FAIL, 2 = args error
"""

import json
import re
import sys
import os

ID_PATTERN = re.compile(r'^PROP-\d{8}-\d{3}$')
REF_ID_PATTERN = re.compile(r'^REF-\d{8}-\d{3}$')
VALID_CHANGE_TYPES = {'add', 'modify', 'remove'}
MUTABLE_TAG = '[MUTABLE]'
CORE_TAG = '[CORE]'


def load_soul(soul_path):
    """Load SOUL.md content and extract structure."""
    if not os.path.exists(soul_path):
        return None, None, None

    with open(soul_path, 'r') as f:
        content = f.read()
        lines = content.split('\n')

    # Extract section headers
    sections = set()
    subsections = {}  # section -> set of subsections
    current_section = None

    for line in lines:
        if line.startswith('## ') and not line.startswith('### '):
            current_section = line.strip()
            sections.add(current_section)
            subsections[current_section] = set()
        elif line.startswith('### ') and current_section:
            subsections[current_section].add(line.strip())

    # Extract all bullet lines (stripped)
    bullet_lines = set()
    for line in lines:
        stripped = line.strip()
        if stripped.startswith('- '):
            bullet_lines.add(stripped)

    return sections, subsections, bullet_lines


def validate(proposals_path, soul_path):
    errors = []
    warnings = []
    seen_ids = set()

    # Load SOUL.md
    sections, subsections, bullet_lines = load_soul(soul_path)
    if sections is None:
        errors.append({
            'line': None, 'field': None,
            'message': f'SOUL.md not found at: {soul_path}'
        })
        return {
            'status': 'FAIL', 'file': proposals_path,
            'errors': errors, 'warnings': warnings
        }

    if not os.path.exists(proposals_path):
        # Empty pending is fine
        return {
            'status': 'PASS', 'file': proposals_path,
            'errors': [], 'warnings': [{'message': f'File not found (no pending proposals): {proposals_path}'}]
        }

    with open(proposals_path, 'r') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue

            try:
                prop = json.loads(line)
            except json.JSONDecodeError as e:
                errors.append({
                    'line': line_num, 'field': None,
                    'message': f'Invalid JSON: {str(e)[:80]}'
                })
                continue

            if not isinstance(prop, dict):
                errors.append({
                    'line': line_num, 'field': None,
                    'message': f'Expected JSON object, got {type(prop).__name__}'
                })
                continue

            pid = prop.get('id', f'<line {line_num}>')

            # ========================================
            # CRITICAL: [CORE] violation check
            # ========================================
            tag = prop.get('tag', '')
            if tag == CORE_TAG:
                errors.append({
                    'line': line_num, 'field': 'tag',
                    'message': f'🚨 BLOCKED: Proposal {pid} attempts to modify [CORE]. '
                               f'This is NEVER allowed. tag must be [MUTABLE].'
                })

            if tag != MUTABLE_TAG and tag != CORE_TAG:
                errors.append({
                    'line': line_num, 'field': 'tag',
                    'message': f'Invalid tag: "{tag}" (must be exactly "[MUTABLE]")'
                })

            # Check current_content for [CORE] tag
            current = prop.get('current_content', '')
            if current and CORE_TAG in str(current):
                errors.append({
                    'line': line_num, 'field': 'current_content',
                    'message': f'🚨 BLOCKED: Proposal {pid} targets a [CORE] bullet. '
                               f'[CORE] bullets are immutable.'
                })

            # ID format
            pid_val = prop.get('id', '')
            if pid_val and not ID_PATTERN.match(pid_val):
                errors.append({
                    'line': line_num, 'field': 'id',
                    'message': f'Invalid ID format: "{pid_val}" (expected PROP-YYYYMMDD-NNN)'
                })

            # Duplicate ID
            if pid_val in seen_ids:
                errors.append({
                    'line': line_num, 'field': 'id',
                    'message': f'Duplicate proposal ID: {pid_val}'
                })
            seen_ids.add(pid_val)

            # Change type
            change_type = prop.get('change_type', '')
            if change_type and change_type not in VALID_CHANGE_TYPES:
                errors.append({
                    'line': line_num, 'field': 'change_type',
                    'message': f'Invalid change_type: "{change_type}" (valid: add, modify, remove)'
                })

            # ========================================
            # CRITICAL: proposed_content format
            # ========================================
            proposed = prop.get('proposed_content', '')
            if change_type in ('add', 'modify') and proposed:
                if not proposed.startswith('- '):
                    errors.append({
                        'line': line_num, 'field': 'proposed_content',
                        'message': f'proposed_content must start with "- " (bullet prefix). Got: "{proposed[:40]}..."'
                    })
                if not proposed.rstrip().endswith(MUTABLE_TAG):
                    errors.append({
                        'line': line_num, 'field': 'proposed_content',
                        'message': f'proposed_content must end with [MUTABLE]. Got: "...{proposed[-30:]}"'
                    })

            # ========================================
            # CRITICAL: current_content existence in SOUL.md
            # ========================================
            if change_type in ('modify', 'remove') and current:
                current_stripped = current.strip()
                if current_stripped not in bullet_lines:
                    # Try fuzzy match to give helpful error
                    close = [b for b in bullet_lines if b[:30] == current_stripped[:30]]
                    hint = ''
                    if close:
                        hint = f' Closest match: "{close[0]}"'
                    errors.append({
                        'line': line_num, 'field': 'current_content',
                        'message': (
                            f'🚨 CRITICAL: current_content not found in SOUL.md. '
                            f'This will FAIL during apply. '
                            f'Looking for: "{current_stripped[:60]}..."{hint}'
                        )
                    })

            if change_type in ('modify', 'remove') and not current:
                errors.append({
                    'line': line_num, 'field': 'current_content',
                    'message': f'current_content is required for {change_type} operations (must match exact line in SOUL.md)'
                })

            # ========================================
            # Target section/subsection existence
            # ========================================
            target_section = prop.get('target_section', '')
            target_sub = prop.get('target_subsection', '')

            if target_section and target_section not in sections:
                errors.append({
                    'line': line_num, 'field': 'target_section',
                    'message': f'Section not found in SOUL.md: "{target_section}" (existing: {sorted(sections)})'
                })

            if target_section and target_sub:
                section_subs = subsections.get(target_section, set())
                if section_subs and target_sub not in section_subs:
                    errors.append({
                        'line': line_num, 'field': 'target_subsection',
                        'message': f'Subsection not found under {target_section}: "{target_sub}" (existing: {sorted(section_subs)})'
                    })

            # Reflection ID format
            ref_id = prop.get('reflection_id', '')
            if ref_id and not REF_ID_PATTERN.match(ref_id):
                errors.append({
                    'line': line_num, 'field': 'reflection_id',
                    'message': f'Invalid reflection ID format: "{ref_id}"'
                })

            # Reason non-empty
            reason = prop.get('reason', '')
            if isinstance(reason, str) and not reason.strip():
                errors.append({
                    'line': line_num, 'field': 'reason',
                    'message': 'reason is empty — proposals must justify the change'
                })

    status = 'FAIL' if errors else 'PASS'
    return {
        'status': status,
        'file': proposals_path,
        'errors': errors,
        'warnings': warnings
    }


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print('Usage: validate_proposal.py <proposals_jsonl> <soul_md_path>', file=sys.stderr)
        sys.exit(2)

    result = validate(sys.argv[1], sys.argv[2])
    print(json.dumps(result, indent=2))
    sys.exit(0 if result['status'] == 'PASS' else 1)
