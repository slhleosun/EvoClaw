#!/usr/bin/env python3
"""
EvoClaw Validator Orchestrator
Runs all validators and produces a summary report.

Usage:
  python3 evoclaw/validators/run_all.py [--workspace-root .]

Expects standard EvoClaw workspace layout:
  <root>/
    SOUL.md
    evoclaw/config.json
    memory/
      experiences/YYYY-MM-DD.jsonl
      significant/significant.jsonl
      reflections/REF-*.json
      proposals/pending.jsonl
      evoclaw-state.json

Exit code: 0 = all PASS, 1 = any FAIL
"""

import json
import sys
import os
import subprocess
from datetime import date

# Resolve paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def run_validator(script_name, args):
    """Run a validator script and capture its output."""
    script = os.path.join(SCRIPT_DIR, script_name)
    cmd = [sys.executable, script] + args
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        try:
            output = json.loads(result.stdout)
        except json.JSONDecodeError:
            output = {
                'status': 'ERROR',
                'errors': [{'message': f'Validator produced non-JSON output: {result.stdout[:200]}'}],
                'warnings': [],
                'stderr': result.stderr[:200] if result.stderr else None
            }
        return output
    except FileNotFoundError:
        return {
            'status': 'ERROR',
            'errors': [{'message': f'Validator script not found: {script}'}],
            'warnings': []
        }
    except subprocess.TimeoutExpired:
        return {
            'status': 'ERROR',
            'errors': [{'message': f'Validator timed out (30s): {script_name}'}],
            'warnings': []
        }


def main(workspace_root='.'):
    soul_path = os.path.join(workspace_root, 'SOUL.md')
    config_path = os.path.join(workspace_root, 'evoclaw', 'config.json')
    memory_dir = os.path.join(workspace_root, 'memory')
    exp_dir = os.path.join(memory_dir, 'experiences')
    today_file = os.path.join(exp_dir, f'{date.today().isoformat()}.jsonl')
    pending_file = os.path.join(memory_dir, 'proposals', 'pending.jsonl')
    state_file = os.path.join(memory_dir, 'evoclaw-state.json')
    proposals_dir = os.path.join(memory_dir, 'proposals')

    results = {}
    any_fail = False

    # 0. Workspace boundary check — MUST pass before anything else
    print('🔍 [0/7] Checking workspace boundary...')
    ws_result = run_validator('check_workspace.py', ['--workspace-root', workspace_root])
    results['workspace'] = ws_result
    if ws_result.get('status') == 'FAIL':
        print('\n🚨 WORKSPACE BOUNDARY VIOLATION')
        print('EvoClaw is NOT installed in this workspace. Pipeline must not run.')
        print('Check your agent/cron configuration.')
        for err in ws_result.get('errors', []):
            print(f'  ❌ {err.get("message", str(err))}')
        print(json.dumps({'overall': 'FAIL', 'results': results}, default=str), file=sys.stderr)
        return 1

    # 1. Validate today's experiences
    print('🔍 [1/7] Validating experiences...')
    if os.path.exists(today_file):
        results['experiences'] = run_validator(
            'validate_experience.py',
            [today_file, '--config', config_path]
        )
    else:
        results['experiences'] = {
            'status': 'SKIP',
            'message': f'No experience file for today ({date.today().isoformat()})'
        }

    # 2. Validate all recent reflection files
    print('🔍 [2/7] Validating reflections...')
    ref_dir = os.path.join(memory_dir, 'reflections')
    ref_results = []
    if os.path.isdir(ref_dir):
        import glob
        for ref_file in sorted(glob.glob(os.path.join(ref_dir, 'REF-*.json')))[-5:]:
            r = run_validator(
                'validate_reflection.py',
                [ref_file, '--experiences-dir', exp_dir]
            )
            r['file'] = ref_file
            ref_results.append(r)
    results['reflections'] = ref_results if ref_results else {'status': 'SKIP', 'message': 'No reflection files found'}

    # 3. Validate pending proposals against SOUL.md
    print('🔍 [3/7] Validating proposals against SOUL.md...')
    if os.path.exists(pending_file):
        results['proposals'] = run_validator(
            'validate_proposal.py',
            [pending_file, soul_path]
        )
    else:
        results['proposals'] = {'status': 'SKIP', 'message': 'No pending proposals'}

    # 4. Validate SOUL.md structure
    print('🔍 [4/7] Validating SOUL.md structure...')
    if os.path.exists(soul_path):
        results['soul'] = run_validator('validate_soul.py', [soul_path])
    else:
        results['soul'] = {
            'status': 'FAIL',
            'errors': [{'message': 'SOUL.md not found'}]
        }

    # 5. Validate state file
    print('🔍 [5/7] Validating state file...')
    if os.path.exists(state_file):
        results['state'] = run_validator(
            'validate_state.py',
            [state_file, '--memory-dir', memory_dir, '--proposals-dir', proposals_dir]
        )
    else:
        results['state'] = {
            'status': 'FAIL',
            'errors': [{'message': 'evoclaw-state.json not found'}]
        }

    # 6. Pipeline completeness check
    print('🔍 [6/7] Checking pipeline completeness...')
    results['pipeline'] = run_validator(
        'check_pipeline_ran.py',
        [memory_dir, '--since-minutes', '30']
    )

    # ========================================
    # Summary
    # ========================================
    print('\n' + '=' * 60)
    print('EVOCLAW VALIDATION REPORT')
    print('=' * 60)

    total_errors = 0
    total_warnings = 0

    for name, result in results.items():
        if isinstance(result, list):
            # Multiple files (reflections)
            for r in result:
                status = r.get('status', '?')
                errs = len(r.get('errors', []))
                warns = len(r.get('warnings', []))
                total_errors += errs
                total_warnings += warns
                fname = os.path.basename(r.get('file', '?'))
                icon = '✅' if status == 'PASS' else '❌' if status == 'FAIL' else '⏭️'
                print(f'  {icon} {name}/{fname}: {status} ({errs} errors, {warns} warnings)')
                if status == 'FAIL':
                    any_fail = True
        else:
            status = result.get('status', '?')
            errs = len(result.get('errors', []))
            warns = len(result.get('warnings', []))
            total_errors += errs
            total_warnings += warns
            icon = '✅' if status == 'PASS' else '❌' if status == 'FAIL' else '⏭️'
            print(f'  {icon} {name}: {status} ({errs} errors, {warns} warnings)')
            if status == 'FAIL':
                any_fail = True

    print(f'\nTotal: {total_errors} errors, {total_warnings} warnings')
    overall = 'FAIL' if any_fail else 'PASS'
    icon = '❌' if any_fail else '✅'
    print(f'{icon} Overall: {overall}')
    print('=' * 60)

    # Print errors detail
    if total_errors > 0:
        print('\n📋 ERROR DETAILS:')
        for name, result in results.items():
            if isinstance(result, list):
                for r in result:
                    for err in r.get('errors', []):
                        fname = os.path.basename(r.get('file', '?'))
                        print(f'  [{name}/{fname}] {err.get("message", str(err))}')
            else:
                for err in result.get('errors', []):
                    print(f'  [{name}] {err.get("message", str(err))}')

    # JSON output to stderr for machine consumption
    print(json.dumps({'overall': overall, 'results': results}, default=str), file=sys.stderr)

    return 0 if not any_fail else 1


if __name__ == '__main__':
    workspace = '.'
    if '--workspace-root' in sys.argv:
        idx = sys.argv.index('--workspace-root')
        if idx + 1 < len(sys.argv):
            workspace = sys.argv[idx + 1]

    sys.exit(main(workspace))
