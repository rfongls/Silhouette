"""
Generates a conformance report over sample/generative bundles:
- Validates with JSON Schema + fhir.resources structure
- Checks simple value-set bindings (LOINC for Obs/DiagnosticReport, SNOMED for Condition, RxNorm for MedicationStatement)
Outputs:
  reports/profile_conformance.json
  reports/profile_conformance.md
"""
from __future__ import annotations
import json, pathlib, sys
from typing import Dict, Any, List

ROOT = pathlib.Path('.')
REPORTS = ROOT / 'reports'
REPORTS.mkdir(exist_ok=True, parents=True)

if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from validators.fhir_profile import validate_uscore_jsonschema, validate_structural_with_pydantic
from silhouette_core.translators.hl7v2_to_fhir import HL7v2ToFHIRTranslator, load_rules
from silhouette_core.translators.cda_to_fhir import CDAToFHIRTranslator

VS = {
    'loinc': json.loads((ROOT / 'profiles/value_sets/loinc_common.json').read_text(encoding='utf-8')),
    'snomed': json.loads((ROOT / 'profiles/value_sets/snomed_common.json').read_text(encoding='utf-8')),
    'rxnorm': json.loads((ROOT / 'profiles/value_sets/rxnorm_demo.json').read_text(encoding='utf-8')),
}


def collect_bundles() -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    # HL7 ORU/ADT fixtures
    oru_rules = load_rules('profiles/hl7v2_oru_to_fhir.yml')
    tr = HL7v2ToFHIRTranslator(oru_rules)
    oru = open('tests/fixtures/hl7/sample_oru_r01.hl7').read()
    out.append(tr.translate_text(oru))

    # CCD
    ccd = open('tests/fixtures/cda/sample_ccd.xml').read()
    out.append(CDAToFHIRTranslator().translate(ccd))

    # Expected bundles
    exp_dir = ROOT / 'tests/fixtures/fhir'
    if exp_dir.exists():
        for p in exp_dir.glob('*.json'):
            try:
                out.append(json.loads(p.read_text(encoding='utf-8')))
            except Exception:
                pass
    return out


def check_bindings(resource: Dict[str, Any]) -> List[str]:
    errs: List[str] = []
    rt = resource.get('resourceType')
    if rt == 'Observation':
        coding = (resource.get('code') or {}).get('coding', [])
        codes = [c for c in coding if c.get('system') == 'http://loinc.org']
        if not codes:
            errs.append('Observation code missing LOINC coding')
        for c in codes:
            code = c.get('code')
            if code and code not in VS['loinc']:
                errs.append(f'Observation LOINC code not in value set: {code}')
    elif rt == 'DiagnosticReport':
        coding = (resource.get('code') or {}).get('coding', [])
        codes = [c for c in coding if c.get('system') == 'http://loinc.org']
        if not codes:
            errs.append('DiagnosticReport code missing LOINC coding')
        for c in codes:
            code = c.get('code')
            if code and code not in VS['loinc']:
                errs.append(f'DiagnosticReport LOINC code not in value set: {code}')
    elif rt == 'Condition':
        coding = (resource.get('code') or {}).get('coding', [])
        codes = [c for c in coding if c.get('system') == 'http://snomed.info/sct']
        if not codes:
            errs.append('Condition code missing SNOMED coding')
        for c in codes:
            code = c.get('code')
            if code and code not in VS['snomed']:
                errs.append(f'Condition SNOMED code not in value set: {code}')
    elif rt == 'MedicationStatement':
        coding = (resource.get('medicationCodeableConcept') or {}).get('coding', [])
        codes = [c for c in coding if c.get('system', '').startswith('http://www.nlm.nih.gov/research/umls/rxnorm')]
        if not codes:
            errs.append('MedicationStatement medication missing RxNorm coding')
        for c in codes:
            code = c.get('code')
            if code and code not in VS['rxnorm']:
                errs.append(f'MedicationStatement RxNorm code not in value set: {code}')
    return errs


def main():
    bundles = collect_bundles()
    summary = {
        'bundles_evaluated': len(bundles),
        'resource_counts': {},
        'schema_errors': 0,
        'structural_errors': 0,
        'binding_errors': 0,
        'details': []
    }
    for b in bundles:
        for e in b.get('entry', []):
            r = e.get('resource', {})
            rt = r.get('resourceType', 'Unknown')
            summary['resource_counts'][rt] = summary['resource_counts'].get(rt, 0) + 1
            errs = {'schema': None, 'structural': None, 'bindings': []}
            try:
                validate_uscore_jsonschema(r)
            except Exception as ex:
                summary['schema_errors'] += 1
                errs['schema'] = str(ex)
            try:
                validate_structural_with_pydantic(r)
            except Exception as ex:
                summary['structural_errors'] += 1
                errs['structural'] = str(ex)
            berrs = check_bindings(r)
            if berrs:
                summary['binding_errors'] += len(berrs)
                errs['bindings'] = berrs
            if any([errs['schema'], errs['structural'], errs['bindings']]):
                summary['details'].append({'resourceType': rt, 'errors': errs})

    (REPORTS / 'profile_conformance.json').write_text(
        json.dumps(summary, indent=2), encoding='utf-8'
    )

    lines = []
    lines.append('# Profile Conformance Report\n')
    lines.append(f"- Bundles evaluated: **{summary['bundles_evaluated']}**")
    lines.append(f"- Resource counts: `{json.dumps(summary['resource_counts'])}`")
    lines.append(f"- Schema errors: **{summary['schema_errors']}**")
    lines.append(f"- Structural errors: **{summary['structural_errors']}**")
    lines.append(f"- Binding errors: **{summary['binding_errors']}**\n")
    if summary['details']:
        lines.append('## Details\n')
        for d in summary['details']:
            lines.append(f"- **{d['resourceType']}**: {json.dumps(d['errors'])}")
    (REPORTS / 'profile_conformance.md').write_text('\n'.join(lines), encoding='utf-8')


if __name__ == '__main__':
    main()
