#!/usr/bin/env python3
"""
EvoClaw State Validator
Validates memory/evoclaw-state.json and reconciles counters against actual files.

Usage:
  python3 evoclaw/validators/validate_state.py <state_json> [--memory-dir memory] [--proposals-dir memory/proposals]

Returns JSON: {"status": "PASS"|"FAIL", "errors": [...], "warnings": [...]}
Exit code: 0 = PASS, 1 = FAIL
"""

import json
import sys
import os
import glob
from datetime import datetime, date

REQUIRED_FIELDS = {
    'last_reflection_at', 'last_heartbeat_at', 'pending_proposals_count',
    'total_experiences_today', 'total_reflections', 'total_soul_changes',
    'source_last_polled'
}


def count_lines(filepath):
    """Count non-empty lines in a file."""
    if not os.path.exists(filepath):
        return 0
    count = 0
    with open(filepath) as f:
        for line in f:
            if line.strip():
                count += 1
    return count


def parse_iso(ts):
    try:
        ts = ts.replace('Z', '+00:00')
        return datetime.fromisoformat(ts)
    except (ValueError, TypeError):
        return None


def validate(state_path, memory_dir=None, proposals_dir=None):
    errors = []
    warnings = []

    if not os.path.exists(state_path):
        return {
            'status': 'FAIL', 'file': state_path,
            'errors': [{'field': None, 'message': f'State file not found: {state_path}'}],
            'warnings': []
        }

    try:
        with open(state_path) as f:
            state = json.load(f)
    except json.JSONDecodeError as e:
        return {
            'status': 'FAIL', 'file': state_path,
            'errors': [{'field': None, 'message': f'Invalid JSON: {e}'}],
            'warnings': []
        }

    if not isinstance(state, dict):
        return {
            'status': 'FAIL', 'file': state_path,
            'errors': [{'field': None, 'message': f'Expected object, got {type(state).__name__}'}],
            'warnings': []
        }

    # Required fields
    for field in REQUIRED_FIELDS:
        if field not in state:
            errors.append({'field': field, 'message': f'Missing required field: {field}'})

    # Timestamp fields
    for ts_field in ('last_reflection_at', 'last_heartbeat_at'):
        val = state.get(ts_field)
        if val is not None:
            if not isinstance(val, str):
                errors.append({'field': ts_field, 'message': f'Must be ISO-8601 string or null, got {type(val).__name__}'})
            elif parse_iso(val) is None:
                errors.append({'field': ts_field, 'message': f'Invalid ISO-8601: "{val}"'})

    # Counter fields — non-negative integers
    for counter in ('pending_proposals_count', 'total_experiences_today', 'total_reflections', 'total_soul_changes'):
        val = state.get(counter)
        if val is not None:
            if not isinstance(val, int):
                errors.append({'field': counter, 'message': f'Must be integer, got {type(val).__name__}: {val}'})
            elif val < 0:
                errors.append({'field': counter, 'message': f'Must be non-negative, got {val}'})

    # source_last_polled structure
    polled = state.get('source_last_polled')
    if polled is not None:
        if not isinstance(polled, dict):
            errors.append({'field': 'source_last_polled', 'message': f'Must be object, got {type(polled).__name__}'})
        else:
            for source, ts in polled.items():
                if ts is not None and not isinstance(ts, str):
                    errors.append({
                        'field': f'source_last_polled.{source}',
                        'message': f'Must be ISO-8601 string or null, got {type(ts).__name__}'
                    })
                elif ts is not None and parse_iso(ts) is None:
                    errors.append({
                        'field': f'source_last_polled.{source}',
                        'message': f'Invalid ISO-8601: "{ts}"'
                    })

    # ========================================
    # Counter reconciliation against actual files
    # ========================================

    if memory_dir and os.path.isdir(memory_dir):
        # Check today's experience count
        today_str = date.today().isoformat()
        today_file = os.path.join(memory_dir, 'experiences', f'{today_str}.jsonl')
        actual_today = count_lines(today_file)
        claimed_today = state.get('total_experiences_today', 0)
        if isinstance(claimed_today, int) and actual_today != claimed_today:
            warnings.append({
                'message': f'total_experiences_today ({claimed_today}) != actual lines in {today_str}.jsonl ({actual_today})'
            })

        # Check total reflections
        reflections_dir = os.path.join(memory_dir, 'reflections')
        if os.path.isdir(reflections_dir):
            actual_reflections = len(glob.glob(os.path.join(reflections_dir, 'REF-*.json')))
            claimed_reflections = state.get('total_reflections', 0)
            if isinstance(claimed_reflections, int) and actual_reflections != claimed_reflections:
                warnings.append({
                    'message': f'total_reflections ({claimed_reflections}) != actual reflection files ({actual_reflections})'
                })

    if proposals_dir:
        pending_file = os.path.join(proposals_dir, 'pending.jsonl')
        actual_pending = count_lines(pending_file)
        claimed_pending = state.get('pending_proposals_count', 0)
        if isinstance(claimed_pending, int) and actual_pending != claimed_pending:
            warnings.append({
                'message': f'pending_proposals_count ({claimed_pending}) != actual lines in pending.jsonl ({actual_pending})'
            })

    status = 'FAIL' if errors else 'PASS'
    return {
        'status': status,
        'file': state_path,
        'errors': errors,
        'warnings': warnings
    }


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: validate_state.py <state_json> [--memory-dir memory] [--proposals-dir memory/proposals]', file=sys.stderr)
        sys.exit(2)

    state_path = sys.argv[1]
    memory_dir = None
    proposals_dir = None

    if '--memory-dir' in sys.argv:
        idx = sys.argv.index('--memory-dir')
        if idx + 1 < len(sys.argv):
            memory_dir = sys.argv[idx + 1]

    if '--proposals-dir' in sys.argv:
        idx = sys.argv.index('--proposals-dir')
        if idx + 1 < len(sys.argv):
            proposals_dir = sys.argv[idx + 1]

    result = validate(state_path, memory_dir, proposals_dir)
    print(json.dumps(result, indent=2))
    sys.exit(0 if result['status'] == 'PASS' else 1)
