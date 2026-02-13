#!/usr/bin/env python3
"""
EvoClaw Pipeline Completeness Checker
Verifies that the pipeline actually WROTE FILES, not just "reflected" in context.

This catches the #1 real-world failure mode: the agent does the cognitive work
of reflecting/proposing but never writes any files to disk.

Usage:
  python3 evoclaw/validators/check_pipeline_ran.py <memory_dir> [--since-minutes 30]

Checks:
  1. Experience files exist and were modified recently
  2. If notable/pivotal experiences exist, significant.jsonl was updated
  3. If reflections were triggered, reflection files exist
  4. State file was updated this heartbeat
  5. If proposals were generated, pending.jsonl was updated

Returns JSON with status and specific findings about what was/wasn't written.
Exit code: 0 = all expected files written, 1 = files missing
"""

import json
import sys
import os
import glob
from datetime import datetime, date, timedelta, timezone


def file_modified_since(filepath, cutoff_dt):
    """Check if file was modified after cutoff."""
    if not os.path.exists(filepath):
        return False
    mtime = datetime.fromtimestamp(os.path.getmtime(filepath), tz=timezone.utc)
    return mtime > cutoff_dt


def last_modified(filepath):
    """Get human-readable last modified time."""
    if not os.path.exists(filepath):
        return 'DOES NOT EXIST'
    mtime = datetime.fromtimestamp(os.path.getmtime(filepath), tz=timezone.utc)
    return mtime.isoformat()


def count_significance(jsonl_path, sig_level):
    """Count entries with given significance in a JSONL file."""
    count = 0
    if not os.path.exists(jsonl_path):
        return 0
    with open(jsonl_path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                if entry.get('significance') == sig_level:
                    count += 1
            except json.JSONDecodeError:
                pass
    return count


def count_unreflected(jsonl_path):
    """Count entries where reflected=false."""
    count = 0
    if not os.path.exists(jsonl_path):
        return 0
    with open(jsonl_path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                if entry.get('reflected') is False:
                    count += 1
            except json.JSONDecodeError:
                pass
    return count


def validate(memory_dir, since_minutes=30):
    errors = []
    warnings = []
    findings = {}

    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(minutes=since_minutes)
    today_str = date.today().isoformat()

    # ========================================
    # 1. Experience file exists and has content
    # ========================================
    exp_dir = os.path.join(memory_dir, 'experiences')
    today_file = os.path.join(exp_dir, f'{today_str}.jsonl')

    if not os.path.exists(today_file):
        errors.append({
            'check': 'experience_file',
            'message': f"Today's experience file does not exist: {today_file}. "
                       f"If the agent ran a heartbeat, it should have logged something."
        })
        findings['experience_file'] = 'MISSING'
    else:
        findings['experience_file'] = last_modified(today_file)
        if not file_modified_since(today_file, cutoff):
            warnings.append({
                'check': 'experience_file',
                'message': f"Experience file exists but wasn't modified in the last {since_minutes}m. "
                           f"Last modified: {last_modified(today_file)}"
            })

    # ========================================
    # 2. Notable/pivotal promotion to significant.jsonl
    # ========================================
    sig_file = os.path.join(memory_dir, 'significant', 'significant.jsonl')
    notable_count = count_significance(today_file, 'notable') if os.path.exists(today_file) else 0
    pivotal_count = count_significance(today_file, 'pivotal') if os.path.exists(today_file) else 0
    findings['notable_today'] = notable_count
    findings['pivotal_today'] = pivotal_count

    if (notable_count + pivotal_count) > 0 and not os.path.exists(sig_file):
        errors.append({
            'check': 'significant_promotion',
            'message': f"Found {notable_count} notable + {pivotal_count} pivotal experiences today "
                       f"but significant.jsonl does not exist. Notable/pivotal MUST be promoted."
        })

    # ========================================
    # 3. Reflection files exist if triggered
    # ========================================
    ref_dir = os.path.join(memory_dir, 'reflections')
    unreflected_notable = 0
    unreflected_pivotal = 0

    # Check across all experience files, not just today
    if os.path.isdir(exp_dir):
        for exp_file in glob.glob(os.path.join(exp_dir, '*.jsonl')):
            if os.path.exists(exp_file):
                with open(exp_file) as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            entry = json.loads(line)
                            if entry.get('reflected') is False:
                                sig = entry.get('significance', '')
                                if sig == 'notable':
                                    unreflected_notable += 1
                                elif sig == 'pivotal':
                                    unreflected_pivotal += 1
                        except json.JSONDecodeError:
                            pass

    findings['unreflected_notable'] = unreflected_notable
    findings['unreflected_pivotal'] = unreflected_pivotal

    if unreflected_pivotal > 0:
        errors.append({
            'check': 'pivotal_reflection',
            'message': f"{unreflected_pivotal} pivotal experience(s) are unreflected. "
                       f"Pivotal experiences require IMMEDIATE reflection."
        })

    # Check if any reflection files exist at all
    if os.path.isdir(ref_dir):
        ref_files = glob.glob(os.path.join(ref_dir, 'REF-*.json'))
        findings['total_reflection_files'] = len(ref_files)
        recent_refs = [f for f in ref_files if file_modified_since(f, cutoff)]
        findings['recent_reflection_files'] = len(recent_refs)
    else:
        findings['total_reflection_files'] = 0
        findings['recent_reflection_files'] = 0
        if (notable_count + pivotal_count) > 0:
            warnings.append({
                'check': 'reflection_dir',
                'message': 'Reflections directory does not exist but notable/pivotal experiences were logged'
            })

    # ========================================
    # 4. State file updated
    # ========================================
    state_file = os.path.join(memory_dir, 'evoclaw-state.json')
    if not os.path.exists(state_file):
        errors.append({
            'check': 'state_file',
            'message': f"State file does not exist: {state_file}. Pipeline must update state every heartbeat."
        })
        findings['state_file'] = 'MISSING'
    else:
        findings['state_file'] = last_modified(state_file)
        if not file_modified_since(state_file, cutoff):
            warnings.append({
                'check': 'state_file',
                'message': f"State file wasn't modified in the last {since_minutes}m. "
                           f"Pipeline should update it every heartbeat. "
                           f"Last modified: {last_modified(state_file)}"
            })

    # ========================================
    # 5. If state says pending proposals, check file
    # ========================================
    if os.path.exists(state_file):
        try:
            with open(state_file) as f:
                state = json.load(f)
            pending = state.get('pending_proposals_count', 0)
            if pending > 0:
                pending_file = os.path.join(memory_dir, 'proposals', 'pending.jsonl')
                if not os.path.exists(pending_file):
                    errors.append({
                        'check': 'pending_proposals',
                        'message': f"State claims {pending} pending proposals but pending.jsonl doesn't exist"
                    })
            findings['claimed_pending'] = pending
        except (json.JSONDecodeError, IOError):
            pass

    # ========================================
    # Overall assessment
    # ========================================
    status = 'FAIL' if errors else 'PASS'
    return {
        'status': status,
        'file': memory_dir,
        'checked_at': now.isoformat(),
        'since_minutes': since_minutes,
        'errors': errors,
        'warnings': warnings,
        'findings': findings
    }


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: check_pipeline_ran.py <memory_dir> [--since-minutes 30]', file=sys.stderr)
        sys.exit(2)

    memory_dir = sys.argv[1]
    since = 30

    if '--since-minutes' in sys.argv:
        idx = sys.argv.index('--since-minutes')
        if idx + 1 < len(sys.argv):
            since = int(sys.argv[idx + 1])

    result = validate(memory_dir, since)
    print(json.dumps(result, indent=2))
    sys.exit(0 if result['status'] == 'PASS' else 1)
