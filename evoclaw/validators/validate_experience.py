#!/usr/bin/env python3
"""
EvoClaw Experience Validator
Validates memory/experiences/YYYY-MM-DD.jsonl files.

Usage:
  python3 evoclaw/validators/validate_experience.py <jsonl_file> [--config evoclaw/config.json]

Returns JSON: {"status": "PASS"|"FAIL", "errors": [...], "warnings": [...], "stats": {...}}
Exit code: 0 = PASS, 1 = FAIL, 2 = file not found
"""

import json
import re
import sys
import os
from datetime import datetime, timezone

ID_PATTERN = re.compile(r'^EXP-\d{8}-\d{4}$')
VALID_SIGNIFICANCE = {'routine', 'notable', 'pivotal'}
BUILTIN_SOURCES = {'conversation', 'moltbook', 'x', 'heartbeat', 'flush_harvest', 'other'}
REQUIRED_FIELDS = {'id', 'timestamp', 'source', 'content', 'significance', 'significance_reason', 'reflected'}


def load_config_sources(config_path):
    """Load additional valid source names from config.json."""
    extra = set()
    if config_path and os.path.exists(config_path):
        try:
            with open(config_path) as f:
                cfg = json.load(f)
            for key in cfg.get('sources', {}):
                extra.add(key)
        except Exception:
            pass
    return BUILTIN_SOURCES | extra


def parse_iso(ts):
    """Check if timestamp is valid ISO-8601."""
    try:
        # Handle both Z and +00:00 formats
        ts = ts.replace('Z', '+00:00')
        dt = datetime.fromisoformat(ts)
        return dt
    except (ValueError, TypeError):
        return None


def validate(filepath, config_path=None):
    errors = []
    warnings = []
    valid_sources = load_config_sources(config_path)
    seen_ids = set()
    line_count = 0
    notable_pivotal_ids = []

    if not os.path.exists(filepath):
        return {
            'status': 'FAIL',
            'file': filepath,
            'errors': [{'line': None, 'field': None, 'message': f'File not found: {filepath}'}],
            'warnings': [],
            'stats': {}
        }

    with open(filepath, 'r') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            line_count += 1

            # Parse JSON
            try:
                entry = json.loads(line)
            except json.JSONDecodeError as e:
                errors.append({
                    'line': line_num,
                    'field': None,
                    'message': f'Invalid JSON: {str(e)[:80]}'
                })
                continue

            if not isinstance(entry, dict):
                errors.append({
                    'line': line_num,
                    'field': None,
                    'message': f'Expected JSON object, got {type(entry).__name__}'
                })
                continue

            # Required fields
            for field in REQUIRED_FIELDS:
                if field not in entry:
                    errors.append({
                        'line': line_num,
                        'field': field,
                        'message': f'Missing required field: {field}'
                    })

            # ID format
            eid = entry.get('id', '')
            if eid and not ID_PATTERN.match(eid):
                errors.append({
                    'line': line_num,
                    'field': 'id',
                    'message': f'Invalid ID format: "{eid}" (expected EXP-YYYYMMDD-NNNN)'
                })

            # Duplicate ID
            if eid in seen_ids:
                errors.append({
                    'line': line_num,
                    'field': 'id',
                    'message': f'Duplicate ID: {eid}'
                })
            seen_ids.add(eid)

            # Timestamp
            ts = entry.get('timestamp')
            if ts:
                dt = parse_iso(ts)
                if dt is None:
                    errors.append({
                        'line': line_num,
                        'field': 'timestamp',
                        'message': f'Invalid ISO-8601 timestamp: "{ts}"'
                    })
                elif dt.tzinfo and dt > datetime.now(timezone.utc):
                    warnings.append({
                        'line': line_num,
                        'message': f'Timestamp is in the future: {ts}'
                    })

            # Source
            source = entry.get('source', '')
            if source and source not in valid_sources:
                errors.append({
                    'line': line_num,
                    'field': 'source',
                    'message': f'Unknown source: "{source}" (valid: {sorted(valid_sources)})'
                })

            # Significance
            sig = entry.get('significance', '')
            if sig and sig not in VALID_SIGNIFICANCE:
                errors.append({
                    'line': line_num,
                    'field': 'significance',
                    'message': f'Invalid significance: "{sig}" (valid: routine, notable, pivotal)'
                })

            # Track notable/pivotal for promotion check
            if sig in ('notable', 'pivotal'):
                notable_pivotal_ids.append(eid)

            # Content non-empty
            content = entry.get('content', '')
            if isinstance(content, str) and not content.strip():
                errors.append({
                    'line': line_num,
                    'field': 'content',
                    'message': 'Content is empty'
                })

            # Significance reason non-empty
            reason = entry.get('significance_reason', '')
            if isinstance(reason, str) and not reason.strip():
                warnings.append({
                    'line': line_num,
                    'message': 'significance_reason is empty'
                })

            # Reflected is boolean
            reflected = entry.get('reflected')
            if reflected is not None and not isinstance(reflected, bool):
                errors.append({
                    'line': line_num,
                    'field': 'reflected',
                    'message': f'reflected must be boolean, got {type(reflected).__name__}: {reflected}'
                })

    status = 'FAIL' if errors else 'PASS'
    return {
        'status': status,
        'file': filepath,
        'errors': errors,
        'warnings': warnings,
        'stats': {
            'total_entries': line_count,
            'unique_ids': len(seen_ids),
            'notable_pivotal_count': len(notable_pivotal_ids),
            'notable_pivotal_ids': notable_pivotal_ids
        }
    }


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: validate_experience.py <jsonl_file> [--config config.json]', file=sys.stderr)
        sys.exit(2)

    filepath = sys.argv[1]
    config_path = None
    if '--config' in sys.argv:
        idx = sys.argv.index('--config')
        if idx + 1 < len(sys.argv):
            config_path = sys.argv[idx + 1]

    result = validate(filepath, config_path)
    print(json.dumps(result, indent=2))
    sys.exit(0 if result['status'] == 'PASS' else 1)
