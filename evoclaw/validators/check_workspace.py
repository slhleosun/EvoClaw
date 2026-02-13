#!/usr/bin/env python3
"""
EvoClaw Workspace Boundary Check
MUST run before ANY EvoClaw pipeline operation.

Verifies that the current workspace actually has EvoClaw installed.
Prevents cross-agent contamination when multiple agents/workspaces exist.

Usage:
  python3 evoclaw/validators/check_workspace.py [--workspace-root .]

Checks:
  1. evoclaw/SKILL.md exists (EvoClaw is installed here)
  2. evoclaw/config.json exists and is valid JSON
  3. SOUL.md exists and contains EvoClaw tags ([CORE]/[MUTABLE])
  4. SOUL.md contains the Evolution Protocol section
  5. memory/ directory exists

If ANY check fails → EvoClaw is NOT installed in this workspace.
The pipeline MUST NOT run. This prevents editing the wrong agent's SOUL.

Exit code: 0 = safe to proceed, 1 = STOP (wrong workspace)
"""

import json
import os
import re
import sys


def check(workspace_root='.'):
    errors = []
    warnings = []

    workspace_root = os.path.abspath(workspace_root)
    workspace_name = os.path.basename(workspace_root)

    # ========================================
    # 1. EvoClaw installation marker
    # ========================================
    skill_path = os.path.join(workspace_root, 'evoclaw', 'SKILL.md')
    if not os.path.exists(skill_path):
        errors.append({
            'check': 'evoclaw_installed',
            'message': (
                f'evoclaw/SKILL.md not found in workspace "{workspace_name}" ({workspace_root}). '
                f'EvoClaw is NOT installed here. '
                f'STOP — do not run the EvoClaw pipeline in this workspace. '
                f'You may be running under the wrong agent.'
            )
        })
        # Early return — no point checking anything else
        return {
            'status': 'FAIL',
            'workspace': workspace_root,
            'workspace_name': workspace_name,
            'evoclaw_installed': False,
            'errors': errors,
            'warnings': warnings
        }

    # ========================================
    # 2. Config exists and is valid
    # ========================================
    config_path = os.path.join(workspace_root, 'evoclaw', 'config.json')
    if not os.path.exists(config_path):
        errors.append({
            'check': 'config',
            'message': 'evoclaw/config.json not found'
        })
    else:
        try:
            with open(config_path) as f:
                cfg = json.load(f)
            if not isinstance(cfg, dict):
                errors.append({
                    'check': 'config',
                    'message': 'evoclaw/config.json is not a valid JSON object'
                })
        except json.JSONDecodeError as e:
            errors.append({
                'check': 'config',
                'message': f'evoclaw/config.json is invalid JSON: {e}'
            })

    # ========================================
    # 3. SOUL.md exists and has EvoClaw tags
    # ========================================
    soul_path = os.path.join(workspace_root, 'SOUL.md')
    if not os.path.exists(soul_path):
        errors.append({
            'check': 'soul_exists',
            'message': (
                f'SOUL.md not found in workspace "{workspace_name}". '
                f'EvoClaw requires a SOUL.md file.'
            )
        })
    else:
        with open(soul_path, 'r') as f:
            soul_content = f.read()

        has_core = '[CORE]' in soul_content
        has_mutable = '[MUTABLE]' in soul_content

        if not has_core and not has_mutable:
            errors.append({
                'check': 'soul_tags',
                'message': (
                    f'SOUL.md in "{workspace_name}" has no [CORE] or [MUTABLE] tags. '
                    f'This SOUL.md has not been set up for EvoClaw. '
                    f'STOP — you may be looking at the wrong agent\'s SOUL.md.'
                )
            })

        # ========================================
        # 4. Evolution Protocol present
        # ========================================
        has_evolution = 'evolution protocol' in soul_content.lower() or 'evoclaw' in soul_content.lower()
        if not has_evolution:
            warnings.append({
                'check': 'evolution_protocol',
                'message': (
                    'SOUL.md does not mention "Evolution protocol" or "EvoClaw". '
                    'This may not be the right agent. Proceed with caution.'
                )
            })

    # ========================================
    # 5. Memory directory
    # ========================================
    memory_dir = os.path.join(workspace_root, 'memory')
    if not os.path.isdir(memory_dir):
        warnings.append({
            'check': 'memory_dir',
            'message': 'memory/ directory not found (may need to be created on first run)'
        })

    # ========================================
    # 6. Validators present
    # ========================================
    validators_dir = os.path.join(workspace_root, 'evoclaw', 'validators')
    if not os.path.isdir(validators_dir):
        warnings.append({
            'check': 'validators',
            'message': 'evoclaw/validators/ directory not found'
        })

    status = 'FAIL' if errors else 'PASS'
    return {
        'status': status,
        'workspace': workspace_root,
        'workspace_name': workspace_name,
        'evoclaw_installed': len(errors) == 0 or (len(errors) > 0 and os.path.exists(skill_path)),
        'errors': errors,
        'warnings': warnings
    }


if __name__ == '__main__':
    workspace = '.'
    if '--workspace-root' in sys.argv:
        idx = sys.argv.index('--workspace-root')
        if idx + 1 < len(sys.argv):
            workspace = sys.argv[idx + 1]

    result = check(workspace)
    print(json.dumps(result, indent=2))

    if result['status'] == 'FAIL':
        print(
            f'\n🚨 WORKSPACE BOUNDARY VIOLATION: EvoClaw pipeline must NOT run '
            f'in "{result["workspace_name"]}". Check your agent/cron configuration.',
            file=sys.stderr
        )

    sys.exit(0 if result['status'] == 'PASS' else 1)
