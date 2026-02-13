#!/usr/bin/env python3
"""
EvoClaw Reflection Validator
Validates memory/reflections/REF-*.json files.

Usage:
  python3 evoclaw/validators/validate_reflection.py <json_file> [--experiences-dir memory/experiences]

Returns JSON: {"status": "PASS"|"FAIL", "errors": [...], "warnings": [...]}
Exit code: 0 = PASS, 1 = FAIL, 2 = file not found
"""

import json
import re
import sys
import os
import glob

ID_PATTERN = re.compile(r'^REF-\d{8}-\d{3}$')
EXP_ID_PATTERN = re.compile(r'^EXP-\d{8}-\d{4}$')
PROP_ID_PATTERN = re.compile(r'^PROP-\d{8}-\d{3}$')
VALID_TYPES = {'routine_batch', 'notable_batch', 'pivotal_immediate'}
VALID_TRIGGERS = {'gap', 'drift', 'contradiction', 'growth', 'refinement'}

REQUIRED_FIELDS = {
    'id', 'timestamp', 'type', 'experience_ids', 'summary',
    'insights', 'soul_relevance', 'proposal_decision', 'proposals'
}
REQUIRED_DECISION_FIELDS = {'should_propose', 'triggers_fired', 'reasoning'}


def load_experience_ids(exp_dir):
    """Load all known experience IDs from experience files."""
    known = set()
    if not exp_dir or not os.path.isdir(exp_dir):
        return None  # Can't verify — return None to skip check
    for filepath in glob.glob(os.path.join(exp_dir, '*.jsonl')):
        try:
            with open(filepath) as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                        if 'id' in entry:
                            known.add(entry['id'])
                    except json.JSONDecodeError:
                        pass
        except IOError:
            pass
    return known


def validate(filepath, exp_dir=None):
    errors = []
    warnings = []

    if not os.path.exists(filepath):
        return {
            'status': 'FAIL',
            'file': filepath,
            'errors': [{'field': None, 'message': f'File not found: {filepath}'}],
            'warnings': []
        }

    try:
        with open(filepath) as f:
            ref = json.load(f)
    except json.JSONDecodeError as e:
        return {
            'status': 'FAIL',
            'file': filepath,
            'errors': [{'field': None, 'message': f'Invalid JSON: {e}'}],
            'warnings': []
        }

    if not isinstance(ref, dict):
        return {
            'status': 'FAIL',
            'file': filepath,
            'errors': [{'field': None, 'message': f'Expected JSON object, got {type(ref).__name__}'}],
            'warnings': []
        }

    # Required fields
    for field in REQUIRED_FIELDS:
        if field not in ref:
            errors.append({'field': field, 'message': f'Missing required field: {field}'})

    # ID format
    rid = ref.get('id', '')
    if rid and not ID_PATTERN.match(rid):
        errors.append({'field': 'id', 'message': f'Invalid ID format: "{rid}" (expected REF-YYYYMMDD-NNN)'})

    # Type
    rtype = ref.get('type', '')
    if rtype and rtype not in VALID_TYPES:
        errors.append({'field': 'type', 'message': f'Invalid type: "{rtype}" (valid: {sorted(VALID_TYPES)})'})

    # Experience IDs
    exp_ids = ref.get('experience_ids', [])
    if not isinstance(exp_ids, list):
        errors.append({'field': 'experience_ids', 'message': 'experience_ids must be an array'})
    elif len(exp_ids) == 0:
        errors.append({'field': 'experience_ids', 'message': 'experience_ids is empty — reflection must reference at least one experience'})
    else:
        for eid in exp_ids:
            if not EXP_ID_PATTERN.match(str(eid)):
                errors.append({'field': 'experience_ids', 'message': f'Invalid experience ID format: "{eid}"'})

        # Referential integrity check
        known_ids = load_experience_ids(exp_dir)
        if known_ids is not None:
            for eid in exp_ids:
                if eid not in known_ids:
                    errors.append({
                        'field': 'experience_ids',
                        'message': f'Experience ID not found in experience files: {eid}'
                    })

    # Insights
    insights = ref.get('insights', [])
    if not isinstance(insights, list):
        errors.append({'field': 'insights', 'message': 'insights must be an array'})
    elif len(insights) == 0:
        errors.append({'field': 'insights', 'message': 'insights is empty — every reflection must produce at least one insight'})

    # Summary non-empty
    summary = ref.get('summary', '')
    if isinstance(summary, str) and not summary.strip():
        errors.append({'field': 'summary', 'message': 'summary is empty'})

    # ========================================
    # PROPOSAL DECISION — Critical checks
    # ========================================
    decision = ref.get('proposal_decision')
    proposals = ref.get('proposals', [])

    if decision is None:
        errors.append({
            'field': 'proposal_decision',
            'message': 'MISSING proposal_decision — every reflection MUST include explicit proposal reasoning'
        })
    elif not isinstance(decision, dict):
        errors.append({
            'field': 'proposal_decision',
            'message': f'proposal_decision must be an object, got {type(decision).__name__}'
        })
    else:
        # Required subfields
        for field in REQUIRED_DECISION_FIELDS:
            if field not in decision:
                errors.append({
                    'field': f'proposal_decision.{field}',
                    'message': f'Missing required field in proposal_decision: {field}'
                })

        should = decision.get('should_propose')
        triggers = decision.get('triggers_fired', [])
        reasoning = decision.get('reasoning', '')

        # Type checks
        if should is not None and not isinstance(should, bool):
            errors.append({
                'field': 'proposal_decision.should_propose',
                'message': f'should_propose must be boolean, got {type(should).__name__}'
            })

        if not isinstance(triggers, list):
            errors.append({
                'field': 'proposal_decision.triggers_fired',
                'message': 'triggers_fired must be an array'
            })
        else:
            for t in triggers:
                if t not in VALID_TRIGGERS:
                    errors.append({
                        'field': 'proposal_decision.triggers_fired',
                        'message': f'Invalid trigger: "{t}" (valid: {sorted(VALID_TRIGGERS)})'
                    })

        # Reasoning non-empty
        if isinstance(reasoning, str) and not reasoning.strip():
            errors.append({
                'field': 'proposal_decision.reasoning',
                'message': 'reasoning is empty — must explain why proposing or not'
            })

        # ========================================
        # CRITICAL CONSISTENCY CHECKS
        # ========================================

        if isinstance(should, bool) and isinstance(proposals, list):
            # should_propose=true but no proposals created
            if should and len(proposals) == 0:
                errors.append({
                    'field': 'proposals',
                    'message': (
                        'INCONSISTENCY: proposal_decision.should_propose is TRUE '
                        'but proposals array is EMPTY. If you decided to propose, '
                        'you must create the proposal. Either create it or change '
                        'should_propose to false with updated reasoning.'
                    )
                })

            # should_propose=false but proposals exist
            if not should and len(proposals) > 0:
                errors.append({
                    'field': 'proposals',
                    'message': (
                        'INCONSISTENCY: proposal_decision.should_propose is FALSE '
                        'but proposals array has entries. Either should_propose should '
                        'be true, or proposals should be empty.'
                    )
                })

            # should_propose=true but no triggers fired
            if should and isinstance(triggers, list) and len(triggers) == 0:
                errors.append({
                    'field': 'proposal_decision.triggers_fired',
                    'message': (
                        'INCONSISTENCY: should_propose is TRUE but no triggers_fired. '
                        'At least one trigger (gap/drift/contradiction/growth/refinement) '
                        'must be identified to justify a proposal.'
                    )
                })

    # Proposal ID format
    if isinstance(proposals, list):
        for pid in proposals:
            if not PROP_ID_PATTERN.match(str(pid)):
                errors.append({
                    'field': 'proposals',
                    'message': f'Invalid proposal ID format: "{pid}" (expected PROP-YYYYMMDD-NNN)'
                })

    status = 'FAIL' if errors else 'PASS'
    return {
        'status': status,
        'file': filepath,
        'errors': errors,
        'warnings': warnings
    }


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: validate_reflection.py <json_file> [--experiences-dir memory/experiences]', file=sys.stderr)
        sys.exit(2)

    filepath = sys.argv[1]
    exp_dir = None
    if '--experiences-dir' in sys.argv:
        idx = sys.argv.index('--experiences-dir')
        if idx + 1 < len(sys.argv):
            exp_dir = sys.argv[idx + 1]

    result = validate(filepath, exp_dir)
    print(json.dumps(result, indent=2))
    sys.exit(0 if result['status'] == 'PASS' else 1)
