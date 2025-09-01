#!/usr/bin/env python
import os, re, sys, json, pathlib, importlib

ROOT = pathlib.Path('.').resolve()
def read_text(p: pathlib.Path) -> str:
    try:
        return p.read_text(encoding='utf-8', errors='ignore')
    except Exception:
        return ''

def main():
    # 1) Legacy refs
    REGISTRY_PATTERN = "skills" + "/registry.yaml"
    pats = {
        'legacy_from_skills': re.compile(r"\bfrom\s+skills\."),
        'legacy_registry_path': re.compile(rf"(?<!silhouette_core/){REGISTRY_PATTERN}"),
    }
    legacy = {k: [] for k in pats}
    for p in ROOT.rglob('*'):
        if not p.is_file():
            continue
        if p.suffix.lower() not in {'.py', '.md', '.yaml', '.yml'}:
            continue
        txt = read_text(p)
        for k, pat in pats.items():
            if pat.search(txt):
                legacy[k].append(str(p.relative_to(ROOT)))

    # 2) Imports for moved wrappers
    sys.path.insert(0, str(ROOT))
    mods = [
        'silhouette_core.skills.cyber_pentest_gate.v1.wrapper',
        'silhouette_core.skills.cyber_recon_scan.v1.wrapper',
        'silhouette_core.skills.cyber_netforensics.v1.wrapper',
        'silhouette_core.skills.cyber_ir_playbook.v1.wrapper',
        'silhouette_core.skills.cyber_extension.v1.wrapper',
    ]
    import_errors = {}
    for m in mods:
        try:
            importlib.import_module(m)
            import_errors[m] = None
        except Exception as e:
            import_errors[m] = repr(e)

    # 3) Tools registry path
    tools = ROOT / 'silhouette_core/tools.py'
    tools_ok = 'silhouette_core/skills/registry.yaml' in read_text(tools) if tools.exists() else False

    # 4) Key files
    key_files = [
        '.github/workflows/ci-security.yml',
        '.github/workflows/security_tests.yml',
        'scripts/win_bootstrap_security.bat',
        'silhouette_core/cli.py',
        'silhouette_core/skills/registry.yaml',
        'silhouette_core/skills/audit.py',
        'skills/__init__.py',
        'silhouette_core/tools.py',
    ]
    exists = {k: (ROOT / k).exists() for k in key_files}

    # 5) Workflows
    def wf_ok(path):
        txt = read_text(ROOT / path)
        return all(s in txt for s in [
            'click==8.1.7',
            'data/security/seeds/cve/cve_seed.json',
            'data/security/seeds/kev/kev_seed.json',
            'docs/cyber/scope_example.txt',
        ])
    wf1_ok = wf_ok('.github/workflows/ci-security.yml')
    wf2_ok = wf_ok('.github/workflows/security_tests.yml')

    summary = {
        'legacy_refs_ok': all(len(v) == 0 for v in legacy.values()),
        'import_tests_ok': all(v is None for v in import_errors.values()),
        'tools_registry_path_ok': tools_ok,
        'key_files_ok': all(exists.values()),
        'workflows_ok': wf1_ok and wf2_ok,
    }
    print(json.dumps({
        'summary': summary,
        'legacy_refs': legacy,
        'import_errors': import_errors,
        'missing_keys': [k for k, v in exists.items() if not v],
    }, indent=2))

    if not all(summary.values()):
        sys.exit(2)

if __name__ == '__main__':
    main()
